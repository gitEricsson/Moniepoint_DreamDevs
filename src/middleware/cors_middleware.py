"""
middleware/cors_middleware.py
──────────────────────────────────────────────────────────────────────────────
Configures Cross-Origin Resource Sharing.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app: FastAPI) -> None:
    """Configures CORS to allow all origins for API consumption."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
