"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import auth, webhooks, inventory, waste, recipes, reports

app = FastAPI(title="Inventory SaaS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(inventory.router)
app.include_router(waste.router)
app.include_router(recipes.router)
app.include_router(reports.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
