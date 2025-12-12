"""Rendering helpers for teleprompter-friendly markup."""
from __future__ import annotations

import re

from markupsafe import Markup, escape

PARAGRAPH_BREAK = re.compile(r"\n\n+")
BOLD = re.compile(r"\*\*(.+?)\*\*")
CUE = re.compile(r"\[\[(.+?)\]\]")
PAUSE = re.compile(r"\{\{\s*pause:(\d+(?:\.\d+)?)\s*\}\}")


def render_script(text: str) -> Markup:
    """Convert lightweight markup to safe HTML for the teleprompter."""
    paragraphs = []
    for block in PARAGRAPH_BREAK.split(text.strip()):
        if not block:
            continue
        safe = escape(block)
        safe = BOLD.sub(r"<strong>\1</strong>", safe)
        safe = CUE.sub(r"<span class=\"cue\">\1</span>", safe)

        def render_pause(match: re.Match[str]) -> str:
            seconds = match.group(1)
            return f"<span class=\"pause\" data-duration=\"{seconds}\">⏸ {seconds}s</span>"

        safe = PAUSE.sub(render_pause, safe)
        paragraphs.append(f"<p>{safe}</p>")

    return Markup("\n".join(paragraphs))
