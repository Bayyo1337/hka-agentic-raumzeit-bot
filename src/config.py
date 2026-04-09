from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_bot_token: str
    anthropic_api_key: str

    raumzeit_base_url: str = "https://raumzeit.hka-iwi.de"
    raumzeit_login: str    # HKA-Account-Login
    raumzeit_password: str  # HKA-Account-Passwort


settings = Settings()
