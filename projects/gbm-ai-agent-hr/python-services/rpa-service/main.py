import uvicorn
from fastapi import FastAPI

app = FastAPI(title="RPA Service", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "rpa"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
