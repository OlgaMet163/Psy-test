from __future__ import annotations


def build_progress_bar(
    percent: float, level_id: str | None = None, length: int = 12
) -> str:
    length = max(8, length)
    filled = int(round((percent / 100) * length))
    filled = min(length, max(0, filled))
    color = _resolve_bar_color(level_id, percent)
    color_map = {"green": "🟩", "yellow": "🟨", "red": "🟥"}
    fill_symbol = color_map[color]
    bar = fill_symbol * filled + "⬜️" * (length - filled)
    return f"<code>{bar}</code>"


def _resolve_bar_color(level_id: str | None, percent: float) -> str:
    if level_id in {"very_high", "high"}:
        return "green"
    if level_id in {"medium", "moderate", "im"}:
        return "yellow"
    if level_id in {"low", "very_low"}:
        return "red"
    # fallback by percent
    if percent >= 66:
        return "green"
    if percent >= 34:
        return "yellow"
    return "red"
