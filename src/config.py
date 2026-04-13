import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

_log = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Telegram
    telegram_bot_token: str

    # Raumzeit HKA
    raumzeit_base_url: str = "https://raumzeit.hka-iwi.de"
    raumzeit_login: str
    raumzeit_password: str

    # LLM Provider: claude | gemini | groq | mistral | openrouter
    llm_provider: str = ""
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
    rate_limit_per_hour: int = 0
    # Max. Tokens pro User gesamt (0 = kein Limit)
    max_tokens_per_user: int = 0

    log_level: str = "INFO"

    def _parse_ids(self, raw: str, field: str) -> set[int]:
        if not raw.strip():
            return set()
        result = set()
        for x in raw.split(","):
            x = x.strip()
            if not x:
                continue
            try:
                result.add(int(x))
            except ValueError:
                _log.warning("Ungültige User-ID in %s: %r (übersprungen)", field, x)
        return result

    @property
    def allowed_ids(self) -> set[int]:
        return self._parse_ids(self.allowed_user_ids, "ALLOWED_USER_IDS")

    @property
    def admin_ids(self) -> set[int]:
        return self._parse_ids(self.admin_user_ids, "ADMIN_USER_IDS")


settings = Settings()
