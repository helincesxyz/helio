from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from helio.service.routers import learning, risk, state, status, strategy, verify


def create_app() -> FastAPI:
    app = FastAPI(
        title="Helio",
        description=(
            "Local-only risk/strategy/learning service for Claude Code to call while "
            "orchestrating OKX trades via the OKX Agent Trade Kit MCP server. "
            "Never exposes or accepts OKX credentials."
        ),
        version="0.1.0",
    )

    # Only the local Vite dev server may call this from a browser context.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(risk.router)
    app.include_router(strategy.router)
    app.include_router(learning.router)
    app.include_router(state.router)
    app.include_router(verify.router)
    app.include_router(status.router)

    return app


app = create_app()
