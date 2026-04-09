from fastapi import APIRouter

user_router = APIRouter(prefix="/users")


@user_router.get("/")
def list_users(limit: int = 10):
    return []


@user_router.get("/{user_id}")
def get_user(user_id: int):
    return {}


@user_router.post("/")
async def create_user(name: str, email: str):
    return {}
