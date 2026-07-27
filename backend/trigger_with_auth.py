import jwt
import datetime
import requests
import json

JWT_SECRET = "devflow-jwt-secret-key-change-in-production"

# Generate a JWT token
token = jwt.encode({
    "sub": "admin",
    "role": "admin",
    "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
}, JWT_SECRET, algorithm="HS256")

headers = {"Authorization": f"Bearer {token}"}
base = "http://localhost:8000/api/v1"

# Test token
r = requests.get(f"{base}/workflow/45935b53-92bc-4a72-8fdf-adebda719acf/status", headers=headers)
print(f"Status check: {r.status_code} - {r.text[:200]}")

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
