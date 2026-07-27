import asyncio
import time
import smtplib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest


class InAppNotifier:
    def __init__(self):
        self.messages = []

    async def send(self, user_id: int, title: str, content: str) -> bool:
        msg = {"user_id": user_id, "title": title, "content": content, "sent_at": datetime.utcnow()}
        self.messages.append(msg)
        return True

    async def get_unread(self, user_id: int) -> list:
        return [m for m in self.messages if m["user_id"] == user_id]


class EmailNotifier:
    def __init__(self, smtp_server: str = "localhost", smtp_port: int = 1025):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sent_emails = []

    async def send(self, to_addr: str, subject: str, body: str) -> bool:
        self.sent_emails.append({"to": to_addr, "subject": subject, "body": body, "sent_at": datetime.utcnow()})
        return True

    async def send_via_smtp(self, to_addr: str, subject: str, body: str) -> bool:
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=5) as server:
                msg = f"Subject: {subject}\n\n{body}"
                server.sendmail("alert@devflow.com", [to_addr], msg)
            self.sent_emails.append({"to": to_addr, "subject": subject, "body": body, "sent_at": datetime.utcnow()})
            return True
        except Exception:
            return False


class WebhookNotifier:
    def __init__(self):
        self.calls = []

    async def send(self, url: str, payload: dict, secret: str = "") -> bool:
        async with httpx.AsyncClient() as client:
            headers = {}
            if secret:
                headers["X-Webhook-Secret"] = secret
            try:
                resp = await client.post(url, json=payload, headers=headers, timeout=10)
                result = resp.status_code == 200
            except httpx.RequestError:
                result = False
        self.calls.append({"url": url, "payload": payload, "sent_at": datetime.utcnow(), "success": result})
        return result


class AlertService:
    def __init__(self, in_app: InAppNotifier, email: EmailNotifier, webhook: WebhookNotifier):
        self.in_app = in_app
        self.email = email
        self.webhook = webhook
        self.alerts = []
        self.delivery_results = []

    async def trigger_alert(self, alert_config: dict) -> dict:
        triggered_at = datetime.utcnow()
        alert_id = len(self.alerts) + 1
        alert = {
            "id": alert_id,
            "config": alert_config,
            "triggered_at": triggered_at,
            "delivered": False,
        }
        self.alerts.append(alert)
        delivery = await self.dispatch_notifications(alert)
        alert["delivered"] = all(d["success"] for d in delivery)
        return alert

    async def dispatch_notifications(self, alert: dict) -> list:
        tasks = []
        config = alert["config"]
        results = []

        if "in_app" in config:
            for user_id in config["in_app"].get("user_ids", []):
                tasks.append(self._send_in_app(user_id, config["in_app"]["title"], config["in_app"]["content"]))

        if "email" in config:
            for recipient in config["email"].get("recipients", []):
                tasks.append(self._send_email(recipient, config["email"]["subject"], config["email"]["body"]))

        if "webhook" in config:
            for wh in config["webhook"].get("endpoints", []):
                tasks.append(self._send_webhook(wh["url"], wh.get("payload", {}), wh.get("secret", "")))

        if tasks:
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            for r in completed:
                if isinstance(r, Exception):
                    results.append({"success": False, "error": str(r)})
                else:
                    results.append(r)

        self.delivery_results.extend(results)
        return results

    async def _send_in_app(self, user_id: int, title: str, content: str) -> dict:
        success = await self.in_app.send(user_id, title, content)
        return {"channel": "in_app", "user_id": user_id, "success": success}

    async def _send_email(self, to_addr: str, subject: str, body: str) -> dict:
        success = await self.email.send(to_addr, subject, body)
        return {"channel": "email", "recipient": to_addr, "success": success}

    async def _send_webhook(self, url: str, payload: dict, secret: str) -> dict:
        success = await self.webhook.send(url, payload, secret)
        return {"channel": "webhook", "url": url, "success": success}

    def get_delivery_stats(self) -> dict:
        if not self.delivery_results:
            return {"total": 0, "success": 0, "failed": 0, "success_rate": 0.0}
        total = len(self.delivery_results)
        success_count = sum(1 for r in self.delivery_results if r.get("success"))
        failed_count = total - success_count
        rate = (success_count / total) * 100 if total > 0 else 0.0
        return {"total": total, "success": success_count, "failed": failed_count, "success_rate": rate}


class AlertTrigger:
    def __init__(self, alert_service: AlertService):
        self.alert_service = alert_service

    async def evaluate_and_trigger(self, metric_name: str, metric_value: float, threshold: float, alert_config: dict) -> dict:
        if metric_value > threshold:
            return await self.alert_service.trigger_alert(alert_config)
        return {"triggered": False, "reason": "threshold not exceeded"}


@pytest.fixture
def in_app_notifier():
    return InAppNotifier()


@pytest.fixture
def email_notifier():
    return EmailNotifier()


@pytest.fixture
def webhook_notifier():
    return WebhookNotifier()


@pytest.fixture
def alert_service(in_app_notifier, email_notifier, webhook_notifier):
    return AlertService(in_app_notifier, email_notifier, webhook_notifier)


@pytest.fixture
def alert_trigger(alert_service):
    return AlertTrigger(alert_service)


@pytest.fixture
def sample_alert_config():
    return {
        "in_app": {
            "user_ids": [1, 2, 3],
            "title": "CPU 使用率过高",
            "content": "CPU usage has exceeded 90% threshold"
        },
        "email": {
            "recipients": ["admin@devflow.com", "ops@devflow.com"],
            "subject": "[Alert] CPU 使用率过高",
            "body": "CPU usage has exceeded 90% threshold. Immediate action required."
        },
        "webhook": {
            "endpoints": [
                {"url": "https://hooks.example.com/alerts", "payload": {"event": "cpu_high", "severity": "critical"}, "secret": "whsec_test"},
                {"url": "https://hooks.example.com/log", "payload": {"event": "cpu_high", "source": "monitor"}, "secret": ""}
            ]
        }
    }


class TestInAppNotification:
    @pytest.mark.asyncio
    async def test_send_in_app_message(self, in_app_notifier):
        result = await in_app_notifier.send(1, "Test Title", "Test Content")
        assert result is True
        assert len(in_app_notifier.messages) == 1
        msg = in_app_notifier.messages[0]
        assert msg["user_id"] == 1
        assert msg["title"] == "Test Title"
        assert msg["content"] == "Test Content"
        assert "sent_at" in msg

    @pytest.mark.asyncio
    async def test_get_unread_messages(self, in_app_notifier):
        await in_app_notifier.send(1, "Title1", "Content1")
        await in_app_notifier.send(2, "Title2", "Content2")
        await in_app_notifier.send(1, "Title3", "Content3")
        unread = await in_app_notifier.get_unread(1)
        assert len(unread) == 2
        for msg in unread:
            assert msg["user_id"] == 1

    @pytest.mark.asyncio
    async def test_multiple_in_app_recipients(self, in_app_notifier):
        for uid in [10, 20, 30]:
            await in_app_notifier.send(uid, "Alert", "Critical")
        assert len(in_app_notifier.messages) == 3


class TestEmailNotification:
    @pytest.mark.asyncio
    async def test_send_email(self, email_notifier):
        result = await email_notifier.send("user@test.com", "Subject", "Body text")
        assert result is True
        assert len(email_notifier.sent_emails) == 1
        email = email_notifier.sent_emails[0]
        assert email["to"] == "user@test.com"
        assert email["subject"] == "Subject"
        assert email["body"] == "Body text"

    @pytest.mark.asyncio
    async def test_send_email_to_multiple_recipients(self, email_notifier):
        recipients = ["a@test.com", "b@test.com", "c@test.com"]
        for r in recipients:
            await email_notifier.send(r, "Alert", "Critical issue")
        assert len(email_notifier.sent_emails) == 3
        assert email_notifier.sent_emails[0]["to"] == "a@test.com"
        assert email_notifier.sent_emails[1]["to"] == "b@test.com"
        assert email_notifier.sent_emails[2]["to"] == "c@test.com"

    @pytest.mark.asyncio
    async def test_smtp_send_failure_returns_false(self, email_notifier):
        email_notifier.smtp_server = "nonexistent.example.com"
        email_notifier.smtp_port = 9999
        result = await email_notifier.send_via_smtp("user@test.com", "Sub", "Body")
        assert result is False


class TestWebhookNotification:
    @pytest.mark.asyncio
    async def test_send_webhook_success(self):
        notifier = WebhookNotifier()
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            result = await notifier.send("https://hooks.example.com/alert", {"key": "value"}, "secret123")
            assert result is True
            assert len(notifier.calls) == 1
            assert notifier.calls[0]["url"] == "https://hooks.example.com/alert"
            assert notifier.calls[0]["payload"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_send_webhook_with_secret_header(self):
        notifier = WebhookNotifier()
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            await notifier.send("https://hooks.example.com/alert", {}, "whsec_abc")
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["headers"]["X-Webhook-Secret"] == "whsec_abc"

    @pytest.mark.asyncio
    async def test_webhook_http_error_returns_false(self):
        notifier = WebhookNotifier()
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response
            result = await notifier.send("https://hooks.example.com/alert", {"key": "value"})
            assert result is False

    @pytest.mark.asyncio
    async def test_webhook_network_error_returns_false(self):
        notifier = WebhookNotifier()
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.RequestError("Connection refused")
            result = await notifier.send("https://hooks.example.com/alert", {"key": "value"})
            assert result is False


@pytest.mark.asyncio
class TestAlertTriggerLatency:
    async def test_alert_to_notification_delay_within_30s(self, alert_trigger, sample_alert_config):
        start = time.monotonic()
        result = await alert_trigger.evaluate_and_trigger("cpu_usage", 95.0, 90.0, sample_alert_config)
        elapsed = time.monotonic() - start
        assert elapsed <= 30.0, f"Alert to notification delay {elapsed:.2f}s exceeds 30s limit"
        assert result["id"] == 1
        assert result["delivered"] is True

    async def test_threshold_not_exceeded_no_alert(self, alert_trigger, sample_alert_config):
        result = await alert_trigger.evaluate_and_trigger("cpu_usage", 50.0, 90.0, sample_alert_config)
        assert result["triggered"] is False
        assert "threshold not exceeded" in result["reason"]


@pytest.mark.asyncio
class TestMultiChannelDelivery:
    async def test_all_three_channels_receive_notification(self, alert_service, sample_alert_config):
        alert = await alert_service.trigger_alert(sample_alert_config)
        assert alert["delivered"] is True
        channels_sent = set(r["channel"] for r in alert_service.delivery_results)
        assert "in_app" in channels_sent
        assert "email" in channels_sent
        assert "webhook" in channels_sent

    async def test_in_app_messages_sent_to_all_users(self, alert_service, in_app_notifier, sample_alert_config):
        await alert_service.trigger_alert(sample_alert_config)
        expected_users = sample_alert_config["in_app"]["user_ids"]
        sent_users = [m["user_id"] for m in in_app_notifier.messages]
        for uid in expected_users:
            assert uid in sent_users, f"User {uid} did not receive in-app notification"

    async def test_emails_sent_to_all_recipients(self, alert_service, email_notifier, sample_alert_config):
        await alert_service.trigger_alert(sample_alert_config)
        expected_recipients = sample_alert_config["email"]["recipients"]
        sent_recipients = [e["to"] for e in email_notifier.sent_emails]
        for r in expected_recipients:
            assert r in sent_recipients, f"Recipient {r} did not receive email"

    async def test_webhooks_called_for_all_endpoints(self, alert_service, sample_alert_config):
        alert_service.webhook.send = AsyncMock(return_value=True)
        await alert_service.trigger_alert(sample_alert_config)
        expected_count = len(sample_alert_config["webhook"]["endpoints"])
        assert alert_service.webhook.send.call_count == expected_count


@pytest.mark.asyncio
class TestDeliverySuccessRate:
    async def test_success_rate_meets_99_percent(self, alert_service, sample_alert_config):
        total_alerts = 100
        for _ in range(total_alerts):
            await alert_service.trigger_alert(sample_alert_config)
        stats = alert_service.get_delivery_stats()
        assert stats["total"] > 0
        rate = stats["success_rate"]
        assert rate >= 99.0, (
            f"Delivery success rate {stats['success_rate']:.2f}% is below 99% "
            f"(success={stats['success']}, failed={stats['failed']}, total={stats['total']})"
        )

    async def test_partial_failure_does_not_break_pipeline(self, alert_service, sample_alert_config):
        alert_service.webhook.send = AsyncMock(return_value=False)
        alert = await alert_service.trigger_alert(sample_alert_config)
        assert alert["delivered"] is False
        stats = alert_service.get_delivery_stats()
        assert stats["failed"] > 0
        assert stats["success"] > 0

    async def test_empty_config_produces_zero_stats(self, alert_service):
        config = {}
        alert = await alert_service.trigger_alert(config)
        assert alert["delivered"] is True
        stats = alert_service.get_delivery_stats()
        assert stats["total"] == 0
        assert stats["success_rate"] == 0.0

    async def test_success_rate_with_mixed_results(self, alert_service, sample_alert_config):
        call_count = {"in_app": 0, "email": 0, "webhook": 0}

        async def failing_webhook_send(url, payload, secret=""):
            call_count["webhook"] += 1
            return False

        alert_service.webhook.send = failing_webhook_send
        for _ in range(10):
            await alert_service.trigger_alert(sample_alert_config)
        stats = alert_service.get_delivery_stats()
        total_expected = 10 * 3 + 10 * 2 + 10 * len(sample_alert_config["webhook"]["endpoints"])
        assert stats["total"] == total_expected
        assert stats["failed"] > 0
        assert stats["success"] > stats["failed"]


class TestAlertTriggerEdgeCases:
    @pytest.mark.asyncio
    async def test_trigger_at_exact_threshold_no_alert(self, alert_trigger, sample_alert_config):
        result = await alert_trigger.evaluate_and_trigger("cpu_usage", 90.0, 90.0, sample_alert_config)
        assert result["triggered"] is False

    @pytest.mark.asyncio
    async def test_trigger_just_above_threshold(self, alert_trigger, sample_alert_config):
        result = await alert_trigger.evaluate_and_trigger("cpu_usage", 90.01, 90.0, sample_alert_config)
        assert result["triggered"] is not False
        assert result.get("id") == 1

    @pytest.mark.asyncio
    async def test_trigger_multiple_alerts_sequentially(self, alert_trigger, sample_alert_config):
        for val in [91.0, 92.0, 93.0, 94.0, 95.0]:
            result = await alert_trigger.evaluate_and_trigger("cpu_usage", val, 90.0, sample_alert_config)
            assert result["delivered"] is True
        assert alert_trigger.alert_service.get_delivery_stats()["total"] > 0
