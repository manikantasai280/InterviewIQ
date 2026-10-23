from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str = "InterviewIQ API"
    app_version: str = "1.0.0"
    environment: str = "development"

    # Tells pydantic-settings to read values from a file called .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


# One shared instance that the rest of the app imports
settings = Settings()