from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/whatswhat"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-key-change-in-production"
    resend_api_key: str = ""

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "whats-what/0.1"

    # Yelp
    yelp_api_key: str = ""

    # Eventbrite
    eventbrite_api_key: str = ""

    # Bandsintown
    bandsintown_app_id: str = "whats-what"

    # Spotify
    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
