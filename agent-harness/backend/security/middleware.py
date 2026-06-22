from fastapi import Request, HTTPException
from backend.security.spire_client import SPIREIdentity
from backend.security.opa_client import OPAClient, OPARequest


async def auth_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    spiffe_id = request.headers.get("X-SPIFFE-ID")
    if not spiffe_id or not SPIREIdentity.is_valid(spiffe_id):
        raise HTTPException(status_code=401, detail="Missing or invalid SPIFFE ID")

    opa = OPAClient(
        opa_url=request.app.state.config.opa_url
    )
    allowed = await opa.check_permission(
        OPARequest(
            action=f"{request.method}:{request.url.path}",
            subject=spiffe_id,
            resource=request.url.path,
        )
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied")

    request.state.spiffe_id = spiffe_id
    return await call_next(request)
