# fetcher.py
from __future__ import annotations

import time

import orjson
from curl_cffi import requests

WATCH_URL = "https://www.youtube.com/watch?v={}"
PLAYER_URL = "https://www.youtube.com/youtubei/v1/player?key={}&prettyPrint=false"
NEXT_URL = "https://www.youtube.com/youtubei/v1/next?key={}&prettyPrint=false"

DEFAULT_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
DEFAULT_VERSION = "2.20240401.00.00"

RETRY_STATUS = {408, 429, 500, 502, 503, 504}


class FetchError(RuntimeError):
    pass


def web_context(client_version: str = DEFAULT_VERSION, lang: str = "en", region: str = "US") -> dict:
    return {
        "client": {
            "clientName": "WEB",
            "clientVersion": client_version,
            "hl": lang,
            "gl": region,
            "timeZone": "UTC",
            "utcOffsetMinutes": 0,
        },
        "user": {"lockedSafetyMode": False},
        "request": {"useSsl": True},
    }


class Fetcher:
    def __init__(
        self,
        impersonate: str = "chrome",
        timeout: float = 30.0,
        retries: int = 3,
        proxy: str | None = None,
    ) -> None:
        self.timeout = timeout
        self.retries = max(1, retries)
        proxies = {"http": proxy, "https": proxy} if proxy else None
        self.session = requests.Session(
            impersonate=impersonate,
            timeout=timeout,
            proxies=proxies,
            allow_redirects=True,
        )
        self.session.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )
        try:
            self.session.cookies.set("SOCS", "CAI", domain=".youtube.com")
            self.session.cookies.set("CONSENT", "YES+cb", domain=".youtube.com")
        except Exception:
            pass

    def close(self) -> None:
        try:
            self.session.close()
        except Exception:
            pass

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _request(self, method: str, url: str, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        last: Exception | None = None
        for attempt in range(self.retries):
            try:
                resp = self.session.request(method, url, **kwargs)
                if resp.status_code in RETRY_STATUS:
                    last = FetchError(f"HTTP {resp.status_code} for {url}")
                    time.sleep(1.2 * (attempt + 1))
                    continue
                if resp.status_code >= 400:
                    raise FetchError(f"HTTP {resp.status_code} for {url}")
                return resp
            except FetchError:
                raise
            except Exception as exc:
                last = exc
                time.sleep(1.2 * (attempt + 1))
        raise FetchError(f"request failed: {url}: {last}")

    def watch(self, video_id: str, lang: str = "en", region: str = "US") -> str:
        resp = self._request(
            "GET",
            WATCH_URL.format(video_id),
            params={"hl": lang, "gl": region, "persist_hl": "1", "bpctr": "9999999999"},
        )
        return resp.text

    def get_text(self, url: str) -> str:
        resp = self._request("GET", url)
        return resp.text

    def get_bytes(self, url: str) -> bytes:
        resp = self._request("GET", url)
        return resp.content

    def innertube(self, endpoint: str, api_key: str, body: dict) -> dict:
        url = f"https://www.youtube.com/youtubei/v1/{endpoint}?key={api_key}&prettyPrint=false"
        resp = self._request(
            "POST",
            url,
            data=orjson.dumps(body),
            headers={"Content-Type": "application/json"},
        )
        try:
            return orjson.loads(resp.content)
        except Exception as exc:
            raise FetchError(f"bad JSON from {endpoint}: {exc}") from exc

    def next(self, api_key: str, context: dict, continuation: str) -> dict:
        return self.innertube("next", api_key, {"context": context, "continuation": continuation})

    def player(self, api_key: str, context: dict, video_id: str) -> dict:
        return self.innertube(
            "player",
            api_key,
            {
                "context": context,
                "videoId": video_id,
                "contentCheckOk": True,
                "racyCheckOk": True,
            },
        )