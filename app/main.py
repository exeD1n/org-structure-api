from fastapi import FastAPI

from app.api.departments import router as departments_router
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="Organization Structure API",
    version="1.0.0",
    description="API for departments and employees with tree structure.",
)

app.include_router(departments_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
