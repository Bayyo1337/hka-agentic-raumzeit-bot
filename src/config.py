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
    llm_provider: str = "groq"
    llm_model: str = ""   # leer = Provider-Default

    # API Keys (nur der gewählte Provider wird benötigt)
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    mistral_api_key: str = ""
    openrouter_api_key: str = ""

    # Zugriffskontrolle
    # Komma-getrennte Telegram User-IDs, die den Bot nutzen dürfen.
    # Leer = alle erlaubt (nur für Entwicklung!)
    allowed_user_ids: str = ""
    # Komma-getrennte Telegram User-IDs mit Admin-Rechten
    admin_user_ids: str = ""
    # Max. Anfragen pro User pro Stunde (0 = kein Limit)
    rate_limit_per_hour: int = 20

    log_level: str = "INFO"

    @property
    def allowed_ids(self) -> set[int]:
        if not self.allowed_user_ids.strip():
            return set()
        return {int(x.strip()) for x in self.allowed_user_ids.split(",") if x.strip()}

    @property
    def admin_ids(self) -> set[int]:
        if not self.admin_user_ids.strip():
            return set()
        return {int(x.strip()) for x in self.admin_user_ids.split(",") if x.strip()}


settings = Settings()
