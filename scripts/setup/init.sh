#!/usr/bin/env bash
set -euo pipefail

# ─── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; exit 1; }
step() { echo -e "\n${BOLD}$*${NC}"; }

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════╗"
echo "║    hka-agentic-raumzeit-bot  –  Setup    ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ─── 1. uv ─────────────────────────────────────────────────────────────────────
step "1/4  Prüfe uv …"
if ! command -v uv &>/dev/null; then
    warn "uv nicht gefunden – wird installiert …"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # shellcheck disable=SC1091
    source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
fi
ok "uv $(uv --version)"

# ─── 2. .env ───────────────────────────────────────────────────────────────────
step "2/4  Konfiguration (.env) …"

if [[ -f .env ]]; then
    warn ".env existiert bereits."
    read -rp "        Neu befüllen? [j/N] " overwrite
    [[ "$overwrite" =~ ^[jJyY]$ ]] || { ok ".env wird übernommen."; }
fi

if [[ ! -f .env ]] || [[ "$overwrite" =~ ^[jJyY]$ ]]; then
    cp .env.example .env

    read_secret() {
        local prompt="$1" var="$2" current
        current=$(grep "^${var}=" .env | cut -d= -f2-)
        read -rsp "  ${prompt}: " val; echo
        [[ -z "$val" ]] && val="$current"
        # replace in-place (macOS + Linux compat)
        sed -i.bak "s|^${var}=.*|${var}=${val}|" .env && rm -f .env.bak
    }

    echo -e "  ${YELLOW}Telegram Bot Token${NC}  – von @BotFather"
    read_secret "TELEGRAM_BOT_TOKEN" "TELEGRAM_BOT_TOKEN"

    echo -e "\n  ${YELLOW}KI-Provider wählen:${NC}"
    echo "    1) claude     – Anthropic Claude  (kostenpflichtig)"
    echo "    2) gemini     – Google Gemini 2.0 Flash  ✅ KOSTENLOS"
    echo "    3) groq       – Groq / Llama 3.3 70B     ✅ KOSTENLOS"
    echo "    4) mistral    – Mistral Small             ✅ KOSTENLOS"
    echo "    5) openrouter – OpenRouter (teils kostenlos)"
    read -rp "  Auswahl [1-5, Standard: 1]: " provider_choice
    case "$provider_choice" in
        2) provider="gemini";      key_var="GEMINI_API_KEY";      key_url="aistudio.google.com/apikey" ;;
        3) provider="groq";        key_var="GROQ_API_KEY";        key_url="console.groq.com/keys" ;;
        4) provider="mistral";     key_var="MISTRAL_API_KEY";     key_url="console.mistral.ai/api-keys" ;;
        5) provider="openrouter";  key_var="OPENROUTER_API_KEY";  key_url="openrouter.ai/keys  (Default: Llama 3.3 70B free)" ;;
        *) provider="claude";      key_var="ANTHROPIC_API_KEY";   key_url="console.anthropic.com" ;;
    esac
    sed -i.bak "s|^LLM_PROVIDER=.*|LLM_PROVIDER=${provider}|" .env && rm -f .env.bak
    echo -e "\n  ${YELLOW}${key_var}${NC}  – ${key_url}"
    read_secret "$key_var" "$key_var"

    echo -e "\n  ${YELLOW}HKA Login${NC}           – dein Hochschul-Account (z.B. muster)"
    read_secret "RAUMZEIT_LOGIN" "RAUMZEIT_LOGIN"

    echo -e "  ${YELLOW}HKA Passwort${NC}"
    read_secret "RAUMZEIT_PASSWORD" "RAUMZEIT_PASSWORD"

    ok ".env gespeichert (Provider: ${provider})."
fi

# ─── 3. Abhängigkeiten ─────────────────────────────────────────────────────────
step "3/4  Installiere Abhängigkeiten (uv sync) …"
uv sync --quiet
ok "Alle Pakete installiert."

# ─── 4. Verbindungstest ────────────────────────────────────────────────────────
step "4/4  Teste Verbindungen …"
uv run python scripts/check.py || fail "Verbindungstest fehlgeschlagen – prüfe deine Credentials in .env"

# ─── Start ─────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}${BOLD}Alles bereit! Bot startet …${NC}\n"
uv run python -m src.bot
