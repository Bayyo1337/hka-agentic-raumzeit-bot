"""
Interaktive Terminal-Konsole und Rich-Dashboard für den Raumzeit-Bot.
"""

import asyncio
import logging
import sys
import json
import litellm
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table

from src.config import settings
from src import agent
from src import tools as raumzeit
from src import db

log = logging.getLogger("src.bot")
console = Console()

def make_dashboard() -> Panel:
    """Erstellt das Status-Panel für das Terminal."""
    from src.state import _BOT_START, _maintenance
    table = Table.grid(expand=True)
    table.add_column(style="cyan", justify="right")
    table.add_column(style="white")

    uptime = datetime.now() - _BOT_START
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    
    current_llm = agent.current_provider()
    level_int = logging.getLogger("src.bot").getEffectiveLevel()
    level_name = logging.getLevelName(level_int)
    
    table.add_row("Uptime: ", f"{h}h {m}min {s}s")
    table.add_row("LLM: ", f"[bold green]{current_llm}[/bold green]")
    table.add_row("Logs: ", f"[bold yellow]{level_name}[/bold yellow]")
    table.add_row("Status: ", "Bereit für Anfragen" if not _maintenance[0] else "[bold red]Wartung[/bold red]")
    
    return Panel(table, title="[bold blue]Raumzeit Bot Dashboard[/bold blue]", border_style="blue")


async def terminal_loop(app, stop_event: asyncio.Event):
    """Schleife für Konsolenbefehle."""
    from src.bot import set_log_level, _run_index_build, _run_lecturer_build
    while not stop_event.is_set():
        try:
            # Nutze to_thread für blockierende Eingabe
            cmd_line = await asyncio.to_thread(input, "raumzeit> ")
            if not cmd_line.strip():
                continue
            
            parts = cmd_line.split()
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd == "exit":
                log.info("Fahre Bot herunter...")
                stop_event.set()
                break
            elif cmd == "status":
                console.print(make_dashboard())
            elif cmd == "loglevel":
                if args:
                    if set_log_level(args[0]):
                        log.info("Loglevel auf %s gesetzt", args[0].upper())
                    else:
                        console.print(f"[red]Ungültiges Loglevel: {args[0]}[/red]. Erlaubt: debug, info, warning, error")
                else:
                    console.print("[yellow]Verwendung:[/yellow] loglevel <debug|info|warning|error>")
            elif cmd == "sync":
                asyncio.create_task(_run_index_build())
                asyncio.create_task(_run_lecturer_build())
            elif cmd == "test":
                await _handle_test_cmd(args)
            elif cmd == "help":
                _print_help()
            else:
                console.print(f"[red]Unbekannter Befehl: {cmd}[/red]. Nutze 'help'.")
        except (EOFError, KeyboardInterrupt):
            stop_event.set()
            break
        except Exception as e:
            log.error("Fehler in Konsole: %s", e)


async def _handle_test_cmd(args: list[str]):
    if not args:
        console.print("[yellow]Verwendung:[/yellow] test <run|generate <N>|list>")
        return
    
    sub = args[0].lower()
    if sub == "list":
        cases = await db.get_all_test_cases()
        if not cases:
            console.print("Keine Testfälle in der Datenbank.")
        else:
            for i, c in enumerate(cases, 1):
                console.print(f"{i:2d}. {c}")
    
    elif sub == "generate":
        try:
            n = int(args[1]) if len(args) > 1 else 5
        except ValueError:
            console.print("[red]Ungültige Zahl.[/red]")
            return
        console.print(f"Generiere {n} Test-Anfragen via LLM...")
        prompt = f"Generiere eine JSON-Liste mit {n} realistischen, abwechslungsreichen Nutzeranfragen an einen HKA-Stundenplan-Bot. Inkludiere Edge-Cases wie Wochenende, vage Zeitangaben ('nächste Woche'), Tippfehler oder Abfragen nach Räumen/Dozenten. Format: {{\"queries\": [\"query1\", \"query2\", ...]}}"
        try:
            res = await litellm.acompletion(
                model=agent._resolve_model(),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            queries = data.get("queries", [])
            new_count = 0
            for q in queries:
                if await db.save_test_case(q):
                    new_count += 1
            console.print(f"[green]Erfolg:[/green] {new_count} neue Testfälle gespeichert.")
        except Exception as e:
            console.print(f"[red]Fehler bei der Generierung:[/red] {e}")
    elif sub == "run":
        cases = await db.get_all_test_cases()
        if not cases:
            console.print("[yellow]Keine Testfälle vorhanden. Nutze 'test generate'.[/yellow]")
            return

        console.print(f"Starte sequentiellen Test mit {len(cases)} Anfragen (1s Pause)...")
        results = []

        for i, q in enumerate(cases, 1):
            try:
                start_time = datetime.now()
                # Agent direkt aufrufen
                reply, in_tok, out_tok, _ = await agent.run(q, [], user_label="StressTest")
                duration = (datetime.now() - start_time).total_seconds()
                results.append((q, "OK", in_tok + out_tok, f"{duration:.2f}s", reply[:50].replace("\n", " ")))
            except Exception as e:
                results.append((q, "ERROR", 0, "0s", str(e)))

            if i < len(cases):
                await asyncio.sleep(1) # Drosselung für API Limits

        test_table = Table(title="Stresstest Ergebnisse", show_lines=True)
        test_table.add_column("Anfrage", style="cyan")
        test_table.add_column("Status", justify="center")
        test_table.add_column("Tokens", justify="right")
        test_table.add_column("Dauer", justify="right")
        test_table.add_column("Antwort-Vorschau", style="dim")
        
        for q, status, tokens, dur, preview in results:
            color = "green" if status == "OK" else "red"
            test_table.add_row(q, f"[{color}]{status}[/{color}]", str(tokens), dur, preview)
        
        console.print(test_table)


def _print_help():
    console.print("\n[bold cyan]Verfügbare Konsolenbefehle:[/bold cyan]")
    console.print("  [bold green]status[/bold green]          - Zeigt das aktuelle Bot-Dashboard an")
    console.print("  [bold green]loglevel <level>[/bold green] - Ändert die Detailtiefe der Logs (debug, info, warning, error)")
    console.print("  [bold green]sync[/bold green]            - Startet den Neuaufbau der Kurs- und Dozenten-Indizes")
    console.print("  [bold green]test <subcommand>[/bold green] - Stresstest-Tool (generate <N>, run, list)")
    console.print("  [bold green]help[/bold green]            - Zeigt diese Hilfe an")
    console.print("  [bold green]exit[/bold green]            - Beendet den Bot sicher\n")
