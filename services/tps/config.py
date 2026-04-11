"""TPS service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database — separate TPS database
    database_url: str = "postgresql+asyncpg://genalpha:genalpha_dev@localhost:5432/tps"

    # Encryption — comma-separated for key rotation (first key is active)
    fernet_keys: str = ""  # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    # Service auth
    tps_secret: str = "dev-tps-secret-change-in-production"

    # Per-app OAuth credentials (platform-level, same for all users)
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:3000/api/integrations/callback"
    github_scopes: str = "read:user user:email repo"

    model_config = {"env_prefix": "TPS_"}


settings = Settings()
