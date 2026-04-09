"""
Verbindungstest für alle konfigurierten Dienste.
Wird von init.sh via `uv run python scripts/check.py` aufgerufen.
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx

GREEN = "\033[0;32m"; RED = "\033[0;31m"; YELLOW = "\033[1;33m"; NC = "\033[0m"
ok   = lambda msg: print(f"  {GREEN}✓{NC}  {msg}")
fail = lambda msg: print(f"  {RED}✗{NC}  {msg}")
info = lambda msg: print(f"  {YELLOW}i{NC}  {msg}")


async def check_raumzeit() -> bool:
    base     = os.getenv("RAUMZEIT_BASE_URL", "https://raumzeit.hka-iwi.de")
    login    = os.getenv("RAUMZEIT_LOGIN", "")
    password = os.getenv("RAUMZEIT_PASSWORD", "")
    try:
        async with httpx.AsyncClient(base_url=base, timeout=10) as c:
            r = await c.post(
                "/private/api/v1/authentication",
                json={"login": login, "password": password},
            )
            r.raise_for_status()
            token = r.json().get("accessToken", "")
            if token:
                ok(f"Raumzeit API  –  JWT erhalten ({len(token)} Zeichen)")
                return True
            fail("Raumzeit API  –  kein accessToken in Antwort")
            return False
    except Exception as e:
        fail(f"Raumzeit API  –  {e}")
        return False


async def check_telegram() -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://api.telegram.org/bot{token}/getMe")
            data = r.json()
            if data.get("ok"):
                ok(f"Telegram      –  @{data['result'].get('username', '?')}")
                return True
            fail(f"Telegram      –  {data.get('description', 'Ungültiger Token')}")
            return False
    except Exception as e:
        fail(f"Telegram      –  {e}")
        return False


async def check_llm() -> bool:
    provider = os.getenv("LLM_PROVIDER", "claude").lower()

    key_map = {
        "claude":      ("ANTHROPIC_API_KEY",  "console.anthropic.com"),
        "gemini":      ("GEMINI_API_KEY",      "aistudio.google.com/apikey"),
        "groq":        ("GROQ_API_KEY",        "console.groq.com/keys"),
        "mistral":     ("MISTRAL_API_KEY",     "console.mistral.ai/api-keys"),
        "openrouter":  ("OPENROUTER_API_KEY",  "openrouter.ai/keys"),
    }

    if provider not in key_map:
        fail(f"LLM           –  Unbekannter Provider: '{provider}'")
        return False

    env_var, url = key_map[provider]
    api_key = os.getenv(env_var, "").strip()

    if not api_key:
        fail(f"LLM ({provider:10s}) –  {env_var} fehlt in .env  →  {url}")
        return False

    # Kurzer Ping mit litellm
    try:
        import litellm
        litellm.drop_params = True
        model_map = {
            "claude":     "claude-haiku-4-5-20251001",
            "gemini":     "gemini/gemini-2.0-flash",
            "groq":       "groq/llama-3.3-70b-versatile",
            "mistral":    "mistral/mistral-small-latest",
            "openrouter": "openrouter/google/gemini-2.0-flash-exp:free",
        }
        os.environ[env_var] = api_key
        model = os.getenv("LLM_MODEL") or model_map[provider]
        resp = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        if resp.choices:
            ok(f"LLM ({provider:10s}) –  {model}  ✓")
            return True
    except litellm.RateLimitError:
        # 429 = Key gültig, aber Rate Limit erreicht → kein Blocker
        ok(f"LLM ({provider:10s}) –  Key gültig (Rate Limit, kurz warten)")
        return True
    except Exception as e:
        fail(f"LLM ({provider:10s}) –  {e}")
        return False

    return False


async def main():
    print()
    results = await asyncio.gather(
        check_raumzeit(),
        check_telegram(),
        check_llm(),
    )
    print()
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
