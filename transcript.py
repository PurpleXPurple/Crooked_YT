# transcript.py
from __future__ import annotations

import html as html_lib
import re

import orjson
from selectolax.lexbor import LexborHTMLParser

from models import TranscriptCue

_XML_CUE_RE = re.compile(
    r"<text[^>]*\bstart=\"([\d.]+)\"[^>]*?(?:\bdur=\"([\d.]+)\")?[^>]*>(.*?)</text>",
    re.DOTALL,
)


def caption_tracks(player: dict) -> list[dict]:
    tracks = (
        ((player or {}).get("captions") or {})
        .get("playerCaptionsTracklistRenderer", {})
        .get("captionTracks")
    )
    return list(tracks or [])


def pick_track(tracks: list[dict], lang: str | None = None) -> dict | None:
    if not tracks:
        return None
    if lang:
        target = lang.lower()
        for track in tracks:
            code = (track.get("languageCode") or "").lower()
            vss = (track.get("vssId") or "").lstrip(".").lower()
            name = ((track.get("name") or {}).get("simpleText") or "").lower()
            if code == target or vss == target or name == target:
                return track
        for track in tracks:
            code = (track.get("languageCode") or "").lower()
            if code.startswith(target) or target.startswith(code):
                return track
    for track in tracks:
        if track.get("kind") != "asr":
            return track
    return tracks[0]


def _track_url(track: dict, fmt: str | None = None) -> str:
    url = track.get("baseUrl") or track.get("url") or ""
    if url.startswith("//"):
        url = "https:" + url
    if fmt:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}fmt={fmt}"
    return url


def _cues_from_json3(body: bytes) -> list[TranscriptCue]:
    try:
        data = orjson.loads(body)
    except Exception:
        return []
    cues: list[TranscriptCue] = []
    for event in data.get("events") or []:
        segs = event.get("segs")
        if not segs:
            continue
        text = "".join(seg.get("utf8", "") for seg in segs)
        text = text.replace("\n", " ").strip()
        if not text:
            continue
        cues.append(
            TranscriptCue(
                start=round((event.get("tStartMs") or 0) / 1000.0, 3),
                duration=round((event.get("dDurationMs") or 0) / 1000.0, 3),
                text=text,
            )
        )
    return cues


def _cues_from_xml(body: str) -> list[TranscriptCue]:
    cues: list[TranscriptCue] = []
    try:
        tree = LexborHTMLParser(body)
        for node in tree.css("text"):
            attrs = node.attributes
            raw = node.text() or ""
            text = html_lib.unescape(raw).replace("\n", " ").strip()
            if not text:
                continue
            cues.append(
                TranscriptCue(
                    start=round(float(attrs.get("start") or 0.0), 3),
                    duration=round(float(attrs.get("dur") or 0.0), 3),
                    text=text,
                )
            )
    except Exception:
        cues = []

    if cues:
        return cues

    for match in _XML_CUE_RE.finditer(body):
        text = html_lib.unescape(re.sub(r"<[^>]+>", "", match.group(3) or ""))
        text = text.replace("\n", " ").strip()
        if not text:
            continue
        cues.append(
            TranscriptCue(
                start=round(float(match.group(1) or 0.0), 3),
                duration=round(float(match.group(2) or 0.0), 3),
                text=text,
            )
        )
    return cues


def fetch_transcript(fetcher, tracks: list[dict], lang: str | None = None) -> list[TranscriptCue]:
    track = pick_track(tracks, lang)
    if not track:
        return []

    url = _track_url(track, "json3")
    if url:
        try:
            body = fetcher.get_bytes(url)
            cues = _cues_from_json3(body)
            if cues:
                return cues
        except Exception:
            pass

    raw_url = _track_url(track)
    if raw_url:
        try:
            body = fetcher.get_text(raw_url)
            cues = _cues_from_xml(body)
            if cues:
                return cues
        except Exception:
            pass

    return []