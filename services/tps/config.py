"""TPS service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://genalpha:genalpha_dev@localhost:5432/genalpha"
    fernet_key: str = ""  # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    tps_secret: str = "dev-tps-secret-change-in-production"

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:3000/api/integrations/github/callback"
    github_scopes: str = "read:user user:email repo"

    model_config = {"env_prefix": "TPS_"}


settings = Settings()
