"""
DevFlow 启动脚本
启动整个项目: 后端 (FastAPI) + 前端 (Vite)

用法:
  python start_project.py

访问地址:
  - 前端: http://localhost:3000
  - 后端API: http://localhost:8082
  - API文档: http://localhost:8082/docs
"""
import subprocess, time, urllib.request, json, os, sys, signal

bdir = os.path.join(os.path.dirname(__file__), "backend")
os.chdir(bdir)
os.environ["DATABASE_URL"] = "sqlite:///./devflow_test.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["APP_PORT"] = "8082"
os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["DEBUG"] = "false"
os.environ["REDIS_URL"] = ""

procs = []

try:
    # Start backend
    be = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8082", "--log-level", "error"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    procs.append(be)

    # Wait for backend
    for i in range(30):
        try:
            r = urllib.request.urlopen("http://127.0.0.1:8082/health", timeout=2)
            if r.status == 200: break
        except: pass
        time.sleep(1)
    else:
        print("Backend failed to start"); sys.exit(1)
    print("Backend: http://localhost:8082 (healthy)")

    # Start frontend
    fdir = os.path.join(os.path.dirname(__file__), "frontend")
    fe = subprocess.Popen(
        ["npx.cmd", "vite", "--port", "3000", "--host"],
        cwd=fdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    procs.append(fe)
    time.sleep(4)
    print("Frontend: http://localhost:3000")

    print("\nBoth services running. Press Ctrl+C to stop.")
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nShutting down...")
finally:
    for p in procs:
        p.terminate()
        try: p.wait(timeout=5)
        except: p.kill()
