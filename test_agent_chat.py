import requests
import json

# 1. 登录获取token
login_resp = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"email": "test@devflow.local", "password": "Test123456"}
)
print("Login status:", login_resp.status_code)
token = login_resp.json()["data"]["tokens"]["access_token"]
print("Token:", token[:50] + "...")

# 2. 测试Agent chat
chat_resp = requests.post(
    "http://localhost:8000/api/agents/b4a42706-24aa-43b7-b92e-22ec20f77361/chat",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    },
    json={"message": "你好，请介绍一下你自己"}
)
print("\nChat status:", chat_resp.status_code)
print("Chat response:", json.dumps(chat_resp.json(), indent=2, ensure_ascii=False))
