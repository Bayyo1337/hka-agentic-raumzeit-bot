from src.domain.models import TimetableResult


def escape_markdown(text: str) -> str:
    return text.replace("\\", "\\\\").replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")


def render_timetable(result: TimetableResult) -> str:
    if not result.events:
        return "Keine Termine gefunden."
    lines = ["**Stundenplan**"]
    for event in result.events:
        start = event.start.strftime("%H:%M")
        end = event.end.strftime("%H:%M")
        room = f" · {escape_markdown(event.room)}" if event.room else ""
        lines.append(f"{start}-{end} · {escape_markdown(event.name)}{room}")
    return "\n".join(lines)


def chunk_telegram_text(text: str, *, limit: int = 4096) -> tuple[str, ...]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    if len(text) <= limit:
        return (text,)
    chunks: list[str] = []
    remaining = text
    while remaining:
        split_at = min(limit, len(remaining))
        if split_at < len(remaining):
            newline = remaining.rfind("\n", 0, split_at)
            if newline > 0:
                split_at = newline
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    return tuple(chunks)

