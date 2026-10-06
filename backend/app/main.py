from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes.auth import router as auth_router
from app.api.routes.workspaces import router as workspaces_router

settings = get_settings()

app = FastAPI(title="Task Board API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(workspaces_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
