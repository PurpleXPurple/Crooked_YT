# main.py
from __future__ import annotations

import argparse
import sys

import orjson

from fetcher import DEFAULT_KEY, DEFAULT_VERSION, FetchError, Fetcher, web_context
from models import Video
from parser import (
    build_video,
    comments_token,
    initial_data,
    parse_comments,
    player_response,
    video_id,
    ytcfg,
)
from transcript import caption_tracks, fetch_transcript

MAX_COMMENT_PAGES = 20


def _context(cfg: dict, lang: str) -> dict:
    version = cfg.get("INNERTUBE_CLIENT_VERSION") or DEFAULT_VERSION
    return web_context(client_version=version, lang=lang, region=cfg.get("GL") or "US")


def _api_key(cfg: dict) -> str:
    return cfg.get("INNERTUBE_API_KEY") or DEFAULT_KEY


def collect_comments(fetcher: Fetcher, api_key: str, context: dict, data: dict, limit: int) -> list:
    token = comments_token(data)
    if not token or limit <= 0:
        return []

    comments = []
    seen: set[str] = set()
    pages = 0

    while token and len(comments) < limit and pages < MAX_COMMENT_PAGES:
        try:
            payload = fetcher.next(api_key, context, token)
        except FetchError:
            break
        batch, token = parse_comments(payload)
        pages += 1
        if not batch and not token:
            break
        for comment in batch:
            key = comment.id or f"{comment.author}:{comment.text[:60]}"
            if key in seen:
                continue
            seen.add(key)
            comments.append(comment)
            if len(comments) >= limit:
                break

    return comments[:limit]


def pull(
    url: str,
    want_comments: int = 20,
    lang: str | None = None,
    with_transcript: bool = True,
    with_comments: bool = True,
    impersonate: str = "chrome",
    proxy: str | None = None,
    timeout: float = 30.0,
) -> Video:
    vid = video_id(url)
    canonical = f"https://www.youtube.com/watch?v={vid}"

    with Fetcher(impersonate=impersonate, timeout=timeout, proxy=proxy) as fetcher:
        html = fetcher.watch(vid)
        if "ytInitialData" not in html:
            raise FetchError("watch page did not contain ytInitialData (blocked or unavailable)")

        data = initial_data(html)
        player = player_response(html)
        cfg = ytcfg(html)
        api_key = _api_key(cfg)
        context = _context(cfg, lang or "en")

        video = build_video(vid, canonical, data, player)

        if with_comments:
            video.comments = collect_comments(fetcher, api_key, context, data, want_comments)

        if with_transcript:
            tracks = caption_tracks(player)
            if not tracks:
                try:
                    alt = fetcher.player(api_key, context, vid)
                    tracks = caption_tracks(alt) or caption_tracks(alt.get("playerResponse") or {})
                except FetchError:
                    tracks = []
            video.transcript = fetch_transcript(fetcher, tracks, lang)

    return video


def _hms(seconds: int) -> str:
    if seconds <= 0:
        return "?"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def render_text(video: Video, show_transcript: bool = True) -> str:
    out: list[str] = []
    out.append(f"Title:     {video.title}")
    out.append(f"Channel:   {video.channel}")
    out.append(f"Views:     {video.views:,}")
    out.append(f"Duration:  {_hms(video.duration)}")
    out.append(f"Published: {video.published}")
    out.append(f"URL:       {video.url}")

    if video.description:
        out.append("")
        out.append("Description")
        out.append("-" * 11)
        out.append(video.description)

    if video.comments:
        out.append("")
        out.append(f"Comments ({len(video.comments)})")
        out.append("-" * 11)
        for comment in video.comments:
            out.append(f"[{comment.likes}] {comment.author} · {comment.published} · {comment.replies} replies")
            out.append(comment.text)
            out.append("")

    if show_transcript and video.transcript:
        out.append("")
        out.append(f"Transcript ({len(video.transcript)} cues)")
        out.append("-" * 11)
        for cue in video.transcript:
            out.append(f"[{_hms(int(cue.start))}] {cue.text}")

    return "\n".join(out).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytp",
        description="Pull title, description, comments and transcript from a YouTube link.",
    )
    parser.add_argument("url", help="YouTube URL or bare 11-char video id")
    parser.add_argument("-o", "--output", help="write output to a file instead of stdout")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--comments", type=int, default=20, help="max comments to fetch (0 = none)")
    parser.add_argument("--lang", default=None, help="preferred caption language code, e.g. en, de, es")
    parser.add_argument("--no-comments", action="store_true")
    parser.add_argument("--no-transcript", action="store_true")
    parser.add_argument("--proxy", default=None, help="http(s) proxy URL")
    parser.add_argument("--impersonate", default="chrome", help="curl_cffi browser profile")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--indent", action="store_true", help="pretty-print JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    want_comments = 0 if args.no_comments else max(0, args.comments)

    try:
        video = pull(
            args.url,
            want_comments=want_comments,
            lang=args.lang,
            with_transcript=not args.no_transcript,
            with_comments=not args.no_comments,
            impersonate=args.impersonate,
            proxy=args.proxy,
            timeout=args.timeout,
        )
    except (FetchError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.format == "text":
        output = render_text(video, show_transcript=not args.no_transcript)
    else:
        option = orjson.OPT_INDENT_2 if args.indent else 0
        output = orjson.dumps(video.to_dict(), option=option | orjson.OPT_APPEND_NEWLINE).decode("utf-8")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output)
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())