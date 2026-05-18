"""
DevFlow - FastAPI application entry point.
Thin wrapper that re-exports the backend application.
"""

import sys
from pathlib import Path

# Ensure backend/ is on the path so 'from app import ...' resolves correctly
_backend_path = str(Path(__file__).parent / "backend")
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from app.main import app as app  # noqa: E402

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
