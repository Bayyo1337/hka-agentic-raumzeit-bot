import os
import json
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()
ENV_FILE = Path(".env")
ENV_EXAMPLE = Path(".env.example")

def main():
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]Raumzeit KI-Agent - Onboarding[/bold cyan]\n"
        "Willkommen beim Setup-Assistenten! Dieses Skript hilft dir,\n"
        "den Bot für den ersten Start zu konfigurieren.",
        border_style="cyan"
    ))

    # Existierende .env laden, falls vorhanden
    env_data = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env_data[k.strip()] = v.strip()

    def ask(key, prompt_text, is_password=False, default=None):
        current = env_data.get(key, "")
        if current and not default:
            default = current
        
        display_prompt = prompt_text
        if current and is_password:
            display_prompt += " [dim](bereits gesetzt, Enter zum Beibehalten)[/dim]"
        elif current:
            display_prompt += f" [dim](aktuell: {current})[/dim]"

        val = Prompt.ask(display_prompt, password=is_password, default=default)
        if val:
            env_data[key] = val
        return val

    console.print("\n[bold yellow]1. Telegram Konfiguration[/bold yellow]")
    ask("TELEGRAM_BOT_TOKEN", "Telegram Bot Token (von @BotFather)")
    ask("admin_user_ids", "Deine Telegram User-ID (Admin-Rechte, kommagetrennt)")

    console.print("\n[bold yellow]2. HKA Raumzeit Zugangsdaten[/bold yellow]")
    ask("RAUMZEIT_LOGIN", "HKA Kürzel (z.B. abcd1011)")
    ask("RAUMZEIT_PASSWORD", "HKA Passwort", is_password=True)

    console.print("\n[bold yellow]3. KI Provider & Modell[/bold yellow]")
    console.print("[dim]Wähle deinen bevorzugten Provider. Gemini und Mistral sind oft kostenlos verfügbar.[/dim]")
    
    provider_choices = ["mistral", "gemini", "groq", "claude", "openrouter"]
    current_p = env_data.get("LLM_PROVIDER", "mistral")
    provider = Prompt.ask("Wähle einen Provider", choices=provider_choices, default=current_p)
    env_data["LLM_PROVIDER"] = provider

    key_map = {
        "mistral": "MISTRAL_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY"
    }
    
    target_key = key_map[provider]
    ask(target_key, f"API Key für {provider.capitalize()}")

    # .env schreiben
    console.print("\n[bold green]Speichere Konfiguration...[/bold green]")
    
    # Template als Basis nutzen, um Kommentare zu erhalten
    template_lines = []
    if ENV_EXAMPLE.exists():
        with open(ENV_EXAMPLE, "r", encoding="utf-8") as f:
            template_lines = f.readlines()
    
    final_lines = []
    processed_keys = set()
    
    for line in template_lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=")[0].strip()
            if key in env_data:
                final_lines.append(f"{key}={env_data[key]}\n")
                processed_keys.add(key)
                continue
        final_lines.append(line)
        
    # Neue Keys hinzufügen, die nicht im Template waren
    for key, value in env_data.items():
        if key not in processed_keys:
            final_lines.append(f"{key}={value}\n")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(final_lines)

    console.print(Panel.fit(
        "[bold green]Setup erfolgreich abgeschlossen![/bold green]\n\n"
        "Du kannst den Bot nun starten mit:\n"
        "[bold cyan]make run[/bold cyan]",
        border_style="green"
    ))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Setup abgebrochen.[/red]")
