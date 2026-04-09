from fastapi import FastAPI
from routers import user_router

app = FastAPI()

API_PREFIX = "/api/v1"

app.include_router(user_router, prefix=API_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok"}
