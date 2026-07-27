import jwt
import datetime
import requests
import json

# Correct settings from .env
SECRET_KEY = "devflow-secret-key"
JWT_ALGORITHM = "HS256"

# Haimei user ID from database
HAI_MEI_USER_ID = "2e623e32-de01-4afc-b66b-039e36186f3f"

# Generate a proper JWT token matching the auth_service format
token = jwt.encode({
    "sub": HAI_MEI_USER_ID,
    "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=86400),
    "iat": datetime.datetime.now(datetime.timezone.utc),
    "type": "access",
}, SECRET_KEY, algorithm=JWT_ALGORITHM)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
base = "http://localhost:8000/api/v1"

# Test with /me endpoint
r = requests.get(f"{base}/auth/me", headers=headers)
print(f"Auth/me: {r.status_code} - {r.text[:300]}")

# Execute steps
projects = [
    ("45935b53-92bc-4a72-8fdf-adebda719acf", "Aeternova", 10),
    ("fe5eae09-6ca1-4029-abbf-fb30e008167b", "GBM AI Agent HR", 10),
    ("6e466502-63dc-4b5f-b3e8-a2172308662d", "DevFlow", 9),
]

for pid, name, step in projects:
    print(f"\n=== {name} Step {step} ===")
    r = requests.post(f"{base}/workflow/{pid}/step{step}/execute", headers=headers)
    print(f"  Execute: {r.status_code} - {r.text[:500]}")

# Step 2 uses POST /step2 not /step2/execute
for pid, name, step in [
    ("05d1ed55-21ff-4a82-a190-2bd528cc10e5", "Legacy-1", 2),
    ("a55b0e32-2aa1-4367-b681-59d4aa99eda9", "Legacy-2", 2),
]:
    print(f"\n=== {name} Step {step} ===")
    r = requests.post(f"{base}/workflow/{pid}/step2", headers=headers, json={})
    print(f"  Execute: {r.status_code} - {r.text[:500]}")

print("\n=== DONE ===")
