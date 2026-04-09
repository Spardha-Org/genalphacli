from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "hello"}


@app.get("/users")
def list_users(limit: int = 10, offset: int = 0):
    """List all users."""
    return []


@app.get("/users/{user_id}")
def get_user(user_id: int):
    """Get a user by ID."""
    return {}


@app.post("/users")
async def create_user(name: str, email: str, age: int = 25):
    """Create a new user."""
    return {}


@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    return {}
