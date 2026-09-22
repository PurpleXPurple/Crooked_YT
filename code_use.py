#!/usr/bin/env python3
"""
code_use.py — A worked example of using the YouTube Link Parser.

This script shows how to use the project programmatically.
It pulls everything from a real video and prints a summary.

Run it:
    python code_use.py

Or change the URL below and run it again.
"""

from __future__ import annotations

import sys
from pathlib import Path

import orjson

from main import pull, render_text
from models import Video
from fetcher import FetchError


# ── Configuration ────────────────────────────────────────────────────────────

URL = "https://www.youtube.com/watch?v=RY5E2jBw2n0&t=7s"

# The video is in Arabic, so we ask for Arabic captions.
LANG = "ar"

# How many comments to pull. 0 disables comments.
COMMENTS = 15

# Where to save the output files.
OUTPUT_JSON = Path("output_RY5E2jBw2n0.json")
OUTPUT_TEXT = Path("output_RY5E2jBw2n0.txt")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _hms(seconds: int) -> str:
    """Turn seconds into a human-friendly time string."""
    if seconds <= 0:
        return "?"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _print_header(text: str) -> None:
    """Print a centered, padded section header."""
    width = 72
    print()
    print("=" * width)
    print(text.center(width))
    print("=" * width)


def _print_field(label: str, value: str, width: int = 24) -> None:
    """Print a 'Label: value' line with the label right-aligned."""
    print(f"{label:>{width}}: {value}")


def _wrap(text: str, width: int = 68, indent: str = "   ") -> str:
    """Wrap text to a given width, preserving word boundaries."""
    text = text.replace("\n", " ").strip()
    lines: list[str] = []
    while len(text) > width:
        cut = text.rfind(" ", 0, width)
        if cut <= 0:
            cut = width
        lines.append(indent + text[:cut])
        text = text[cut:].lstrip()
    if text:
        lines.append(indent + text)
    return "\n".join(lines)


# ── Main flow ────────────────────────────────────────────────────────────────

def main() -> int:
    _print_header("YouTube Link Parser — Worked Example")
    print(f"Target: {URL}")
    print(f"Language: {LANG}   Comments: {COMMENTS}")

    # ── 1. Pull everything ──────────────────────────────────────────────
    # `pull()` does the whole dance:
    #   fetch the watch page → parse hidden JSON → fetch comments → fetch transcript
    try:
        video = pull(
            URL,
            want_comments=COMMENTS,
            lang=LANG,
            with_transcript=True,
            with_comments=True,
            impersonate="chrome",
            timeout=30.0,
        )
    except FetchError as exc:
        print(f"\nFetch failed: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"\nBad URL: {exc}", file=sys.stderr)
        return 1

    # `video` is a `Video` dataclass. Every field is now available.

    # ── 2. Show a summary ──────────────────────────────────────────────
    _print_header("Video Summary")
    _print_field("Title", video.title)
    _print_field("Channel", video.channel)
    _print_field("Channel ID", video.channel_id or "—")
    _print_field("Views", f"{video.views:,}")
    _print_field("Duration", _hms(video.duration))
    _print_field("Published", video.published or "—")
    _print_field("Video ID", video.id)
    _print_field("Keywords", ", ".join(video.keywords[:5]) or "—")
    if video.keywords and len(video.keywords) > 5:
        print(f"{'':>{24}}  … and {len(video.keywords) - 5} more")

    # ── 3. Show the description (trimmed) ──────────────────────────────
    _print_header("Description (first 500 chars)")
    if video.description:
        snippet = video.description[:500]
        print(snippet + ("…" if len(video.description) > 500 else ""))
    else:
        print("(no description)")

    # ── 4. Show comments ───────────────────────────────────────────────
    _print_header(f"Comments ({len(video.comments)})")
    if not video.comments:
        print("(no comments returned)")
    else:
        for i, comment in enumerate(video.comments, 1):
            likes = f"[{comment.likes}]" if comment.likes else "[0]"
            replies = f" · {comment.replies} replies" if comment.replies else ""
            print(f"\n{i}. {likes} {comment.author}{replies}")
            print(f"   {comment.published}")
            print(_wrap(comment.text))

    # ── 5. Show the transcript (first and last cues) ────────────────────
    _print_header(f"Transcript ({len(video.transcript)} cues)")
    if not video.transcript:
        print("(no transcript returned)")
        print()
        print("Possible reasons:")
        print("  • The video genuinely has no captions.")
        print("  • YouTube served a stripped player response (consent/region).")
        print("  • The caption track is tagged with an unexpected language code.")
        print()
        print("Run debug_transcript.py to find out which one it is.")
    else:
        print("First 3 cues:")
        for cue in video.transcript[:3]:
            print(f"  [{_hms(int(cue.start))}] {cue.text[:70]}")
        print()
        print("Last 3 cues:")
        for cue in video.transcript[-3:]:
            print(f"  [{_hms(int(cue.start))}] {cue.text[:70]}")
        print()
        print(f"Full transcript length: {len(video.transcript_text):,} chars")

    # ── 6. Save outputs ────────────────────────────────────────────────
    _print_header("Saving output files")

    # JSON: the complete, structured data.  This is what you would load
    # into another program or store in a database.
    OUTPUT_JSON.write_bytes(
        orjson.dumps(video.to_dict(), option=orjson.OPT_INDENT_2)
    )
    print(f"  JSON  → {OUTPUT_JSON.resolve()}")

    # Text: a human-readable report.  Useful for reading or pasting.
    OUTPUT_TEXT.write_text(
        render_text(video, show_transcript=True),
        encoding="utf-8",
    )
    print(f"  Text  → {OUTPUT_TEXT.resolve()}")

    # ── 7. Show how to access individual pieces ────────────────────────
    _print_header("Accessing data programmatically")

    print(f"  video.title                  → {video.title!r}")
    print(f"  video.views                  → {video.views}")
    print(f"  len(video.comments)          → {len(video.comments)}")
    print(f"  len(video.transcript)        → {len(video.transcript)}")

    if video.comments:
        print(f"  video.comments[0].author     → {video.comments[0].author!r}")
        print(f"  video.comments[0].likes      → {video.comments[0].likes}")
        print(f"  video.comments[0].text       → {video.comments[0].text[:60]!r}…")
    else:
        print(f"  video.comments[0]            → (no comments returned)")

    if video.transcript:
        print(f"  video.transcript[0].start    → {video.transcript[0].start}")
        print(f"  video.transcript[0].text     → {video.transcript[0].text[:60]!r}…")
        print(f"  len(video.transcript_text)   → {len(video.transcript_text):,} chars")
    else:
        print(f"  video.transcript[0]          → (no transcript returned)")

    _print_header("Done")
    print("The full JSON and text files are in the current directory.")
    print("Open them, parse them, feed them to another tool — they are yours.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())