from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str = "InterviewIQ API"
    app_version: str = "1.0.0"
    environment: str = "development"
    # Database (no default on purpose: the app must get this from .env)
    database_url: str
    # Authentication
    secret_key: str
    access_token_expire_minutes: int = 60
        # Gemini AI
    gemini_api_key: str
    gemini_model: str = "gemini-3.5-flash-lite"

    # Tells pydantic-settings to read values from a file called .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


# One shared instance that the rest of the app imports
settings = Settings()