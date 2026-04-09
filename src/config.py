from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Telegram
    telegram_bot_token: str

    # Raumzeit HKA
    raumzeit_base_url: str = "https://raumzeit.hka-iwi.de"
    raumzeit_login: str
    raumzeit_password: str

    # LLM Provider: claude | gemini | groq | mistral | openrouter
    llm_provider: str = "claude"
    llm_model: str = ""   # leer = Provider-Default

    # API Keys (nur der gewählte Provider wird benötigt)
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    mistral_api_key: str = ""
    openrouter_api_key: str = ""

    log_level: str = "INFO"


settings = Settings()
