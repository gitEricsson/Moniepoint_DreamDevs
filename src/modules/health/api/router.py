from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health", summary="Standard API health check")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}
