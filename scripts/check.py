"""
Verbindungstest für alle drei Dienste.
Wird von init.sh via `uv run python scripts/check.py` aufgerufen.
"""

import asyncio
import os
import sys
from pathlib import Path

# .env laden bevor src-imports
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx

GREEN = "\033[0;32m"; RED = "\033[0;31m"; NC = "\033[0m"

ok   = lambda msg: print(f"  {GREEN}✓{NC}  {msg}")
fail = lambda msg: print(f"  {RED}✗{NC}  {msg}")


async def check_raumzeit() -> bool:
    base = os.getenv("RAUMZEIT_BASE_URL", "https://raumzeit.hka-iwi.de")
    login = os.getenv("RAUMZEIT_LOGIN", "")
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
                name = data["result"].get("username", "?")
                ok(f"Telegram      –  @{name}")
                return True
            fail(f"Telegram      –  {data.get('description', 'Ungültiger Token')}")
            return False
    except Exception as e:
        fail(f"Telegram      –  {e}")
        return False


async def check_anthropic() -> bool:
    import anthropic
    key = os.getenv("ANTHROPIC_API_KEY", "")
    try:
        client = anthropic.AsyncAnthropic(api_key=key)
        msg = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        if msg.content:
            ok("Anthropic API –  Verbindung ok")
            return True
        fail("Anthropic API –  leere Antwort")
        return False
    except Exception as e:
        fail(f"Anthropic API –  {e}")
        return False


async def main():
    print()
    results = await asyncio.gather(
        check_raumzeit(),
        check_telegram(),
        check_anthropic(),
    )
    print()
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
