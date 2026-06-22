import logging

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from backend.shared.config import config

logger = logging.getLogger(__name__)


def setup_telemetry() -> None:
    try:
        resource = Resource.create({
            "service.name": config.otel_service_name,
            "service.version": "0.1.0",
        })
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=f"{config.otel_endpoint}/v1/traces")
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
    except Exception:
        logger.warning("Telemetry setup failed — continuing without tracing", exc_info=True)
