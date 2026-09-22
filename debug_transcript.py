#!/usr/bin/env python3
"""debug_transcript.py — find out why a video has no captions."""

import orjson

from fetcher import DEFAULT_KEY, DEFAULT_VERSION, Fetcher, web_context
from parser import initial_data, player_response, video_id, ytcfg
from transcript import caption_tracks

URL = "https://www.youtube.com/watch?v=RY5E2jBw2n0&t=7s"
LANG = "ar"

vid = video_id(URL)
print(f"video id: {vid}")

with Fetcher(impersonate="chrome", timeout=30.0) as f:
    html = f.watch(vid)
    print(f"watch page size: {len(html):,} chars")

    pr = player_response(html)
    print(f"ytInitialPlayerResponse keys: {list(pr.keys())[:8]}")

    tracks = caption_tracks(pr)
    print(f"\ntracks from watch page: {len(tracks)}")
    for t in tracks:
        print(f"  - lang={t.get('languageCode')!r} "
              f"vss={t.get('vssId')!r} "
              f"kind={t.get('kind')!r} "
              f"name={(t.get('name') or {}).get('simpleText')!r}")
        print(f"    baseUrl: {t.get('baseUrl', '')[:120]}")

    if not tracks:
        cfg = ytcfg(html)
        key = cfg.get("INNERTUBE_API_KEY") or DEFAULT_KEY
        ver = cfg.get("INNERTUBE_CLIENT_VERSION") or DEFAULT_VERSION
        ctx = web_context(client_version=ver, lang=LANG, region="US")
        print(f"\nFallback: calling InnerTube player (key={key[:12]}…)")
        alt = f.player(key, ctx, vid)
        print(f"  playabilityStatus: "
              f"{alt.get('playabilityStatus', {}).get('status')!r}")
        print(f"  reason: "
              f"{alt.get('playabilityStatus', {}).get('reason')!r}")
        tracks = caption_tracks(alt) or caption_tracks(alt.get("playerResponse") or {})
        print(f"  tracks from InnerTube: {len(tracks)}")
        for t in tracks:
            print(f"    - lang={t.get('languageCode')!r} "
                  f"vss={t.get('vssId')!r} "
                  f"kind={t.get('kind')!r}")

    if tracks:
        t = tracks[0]
        url = t.get("baseUrl") or ""
        if url.startswith("//"):
            url = "https:" + url
        print(f"\nfetching first track as json3…")
        try:
            body = f.get_bytes(url + "&fmt=json3")
            data = orjson.loads(body)
            events = data.get("events", [])
            print(f"  events: {len(events)}")
            for e in events[:3]:
                print(f"    {e.get('tStartMs')}ms → "
                      f"{''.join(s.get('utf8','') for s in e.get('segs', []))!r}")
        except Exception as exc:
            print(f"  json3 fetch failed: {exc}")

        print(f"\nfetching first track as XML…")
        try:
            body = f.get_text(url)
            print(f"  XML length: {len(body):,}")
            print(f"  first 300 chars: {body[:300]!r}")
        except Exception as exc:
            print(f"  XML fetch failed: {exc}")