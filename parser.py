# parser.py
from __future__ import annotations

import json
import re
from typing import Any, Iterator
from urllib.parse import parse_qs, urlparse

from models import Comment, Video

_DECODER = json.JSONDecoder()

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_COUNT_RE = re.compile(r"([\d][\d.,]*)\s*([KkMmBb])?")
_MULT = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}

_PATH_PREFIXES = {"shorts", "embed", "live", "v", "watch"}


def video_id(value: str) -> str:
    s = (value or "").strip()
    if _VIDEO_ID_RE.match(s):
        return s
    url = urlparse(s if "://" in s else "https://" + s)
    host = url.netloc.lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host

    if host.endswith("youtu.be"):
        candidate = url.path.lstrip("/").split("/")[0]
        if _VIDEO_ID_RE.match(candidate):
            return candidate

    qs = parse_qs(url.query)
    if "v" in qs and qs["v"]:
        candidate = qs["v"][0]
        if _VIDEO_ID_RE.match(candidate):
            return candidate

    parts = [p for p in url.path.split("/") if p]
    if parts and parts[0] in _PATH_PREFIXES and len(parts) > 1:
        candidate = parts[1]
        if _VIDEO_ID_RE.match(candidate):
            return candidate

    for part in reversed(parts):
        if _VIDEO_ID_RE.match(part):
            return part

    raise ValueError(f"cannot extract a video id from {value!r}")


def extract_json(html: str, marker: str) -> Any | None:
    idx = html.find(marker)
    if idx < 0:
        return None
    brace = html.find("{", idx + len(marker))
    if brace < 0:
        return None
    try:
        return _DECODER.raw_decode(html, brace)[0]
    except ValueError:
        return None


def initial_data(html: str) -> dict:
    for marker in ("var ytInitialData =", 'window["ytInitialData"] =', "ytInitialData ="):
        data = extract_json(html, marker)
        if isinstance(data, dict):
            return data
    return {}


def player_response(html: str) -> dict:
    for marker in (
        "var ytInitialPlayerResponse =",
        'window["ytInitialPlayerResponse"] =',
        "ytInitialPlayerResponse =",
    ):
        data = extract_json(html, marker)
        if isinstance(data, dict):
            return data
    return {}


def ytcfg(html: str) -> dict:
    for marker in ("ytcfg.set(", "ytcfg.set (", "var ytcfg ="):
        data = extract_json(html, marker)
        if isinstance(data, dict):
            return data
    return {}


def walk(obj: Any) -> Iterator[dict]:
    stack: list[Any] = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            yield cur
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)


def dig(obj: Any, *keys: str, default: Any = None) -> Any:
    cur = obj
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur


def find_first(obj: Any, key: str) -> Any:
    for node in walk(obj):
        if key in node and node[key] is not None:
            return node[key]
    return None


def text_of(node: Any) -> str:
    if not node:
        return ""
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return ""
    if "simpleText" in node:
        return node["simpleText"] or ""
    if "runs" in node:
        return "".join(r.get("text", "") for r in node.get("runs") or [])
    if "content" in node and isinstance(node["content"], str):
        return node["content"]
    if "text" in node and isinstance(node["text"], str):
        return node["text"]
    return ""


def parse_count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    match = _COUNT_RE.search(str(value))
    if not match:
        return 0
    number = match.group(1).replace(",", "")
    mult = _MULT.get((match.group(2) or "").upper(), 1)
    try:
        return int(float(number) * mult)
    except ValueError:
        return 0


def build_video(vid: str, url: str, data: dict, player: dict) -> Video:
    data = data or {}
    player = player or {}
    details = player.get("videoDetails") or {}
    micro = dig(player, "microformat", "playerMicroformatRenderer") or dig(
        data, "microformat", "playerMicroformatRenderer"
    ) or {}

    primary = find_first(data, "videoPrimaryInfoRenderer") or {}
    secondary = find_first(data, "videoSecondaryInfoRenderer") or {}

    title = details.get("title") or text_of(primary.get("title"))
    description = (
        details.get("shortDescription")
        or dig(secondary, "attributedDescription", "content")
        or text_of(secondary.get("description"))
        or ""
    )

    views = parse_count(details.get("viewCount"))
    if not views:
        views = parse_count(dig(primary, "viewCount", "videoViewCountRenderer", "viewCount"))

    thumbs = dig(details, "thumbnail", "thumbnails") or []
    thumbnail = thumbs[-1].get("url", "") if thumbs else ""

    return Video(
        id=vid,
        url=url,
        title=title or "",
        description=description or "",
        channel=details.get("author") or micro.get("ownerChannelName") or "",
        channel_id=details.get("channelId") or micro.get("externalChannelId") or "",
        views=views,
        duration=parse_count(details.get("lengthSeconds")),
        published=micro.get("publishDate") or micro.get("uploadDate") or text_of(primary.get("dateText")),
        thumbnail=thumbnail,
        keywords=list(details.get("keywords") or []),
    )


def comments_token(data: dict) -> str | None:
    for node in walk(data):
        if node.get("sectionIdentifier") != "comment-item-section":
            continue
        for item in node.get("contents") or []:
            token = dig(
                item,
                "continuationItemRenderer",
                "continuationEndpoint",
                "continuationCommand",
                "token",
            )
            if token:
                return token
    for node in walk(data):
        if "commentsSection" in node or node.get("targetId") == "comments-section":
            token = dig(node, "continuationEndpoint", "continuationCommand", "token")
            if token:
                return token
    return None


def _continuation_items(payload: dict) -> list[dict]:
    items: list[dict] = []
    for endpoint in payload.get("onResponseReceivedEndpoints") or []:
        for key in ("appendContinuationItemsAction", "reloadContinuationItemsCommand"):
            block = endpoint.get(key)
            if isinstance(block, dict):
                items.extend(block.get("continuationItems") or [])
    if not items:
        items = list(dig(payload, "continuationContents", "itemSectionContinuation", "contents") or [])
    return items


def _next_token(items: list[dict]) -> str | None:
    for item in reversed(items):
        token = dig(
            item,
            "continuationItemRenderer",
            "continuationEndpoint",
            "continuationCommand",
            "token",
        )
        if token:
            return token
    return None


def _entity_map(payload: dict) -> dict[str, dict]:
    entities: dict[str, dict] = {}
    for mutation in dig(payload, "frameworkUpdates", "entityBatchUpdate", "mutations") or []:
        entity = dig(mutation, "payload", "commentEntityPayload")
        if not entity:
            continue
        key = entity.get("key") or dig(entity, "properties", "commentId") or ""
        if key:
            entities[key] = entity
    return entities


def _first_comment_id(node: Any) -> str:
    for candidate in walk(node):
        cid = candidate.get("commentId")
        if isinstance(cid, str) and cid:
            return cid
    return ""


def _comment_from_entity(entity: dict, is_reply: bool = False) -> Comment:
    props = entity.get("properties") or {}
    author = entity.get("author") or {}
    toolbar = entity.get("toolbar") or {}
    likes = toolbar.get("likeCountNotliked")
    if likes in (None, ""):
        likes = toolbar.get("likeCountLiked")
    return Comment(
        id=props.get("commentId") or entity.get("key") or "",
        author=author.get("displayName") or "",
        text=dig(props, "content", "content") or "",
        likes=parse_count(likes),
        published=props.get("publishedTime") or "",
        replies=parse_count(toolbar.get("replyCount")),
        is_reply=bool(props.get("replyLevel")) or is_reply,
    )


def _comment_from_legacy(renderer: dict) -> Comment:
    return Comment(
        id=renderer.get("commentId") or "",
        author=text_of(renderer.get("authorText")),
        text=text_of(renderer.get("contentText")),
        likes=parse_count(dig(renderer, "voteCount", "simpleText")),
        published=text_of(renderer.get("publishedTimeText")),
        replies=parse_count(renderer.get("replyCount")),
        is_reply=bool(renderer.get("replyLevel")),
    )


def parse_comments(payload: dict) -> tuple[list[Comment], str | None]:
    items = _continuation_items(payload)
    entities = _entity_map(payload)
    comments: list[Comment] = []
    seen: set[str] = set()

    for item in items:
        thread = item.get("commentThreadRenderer")
        if thread:
            cid = _first_comment_id(thread)
            entity = entities.get(cid)
            if entity:
                comment = _comment_from_entity(entity)
            else:
                legacy = find_first(thread, "commentRenderer")
                if not legacy:
                    continue
                comment = _comment_from_legacy(legacy)
            if comment.id and comment.id in seen:
                continue
            if comment.id:
                seen.add(comment.id)
            if comment.text or comment.author:
                comments.append(comment)

        reply = item.get("commentRenderer")
        if reply:
            comment = _comment_from_legacy(reply)
            if comment.id and comment.id in seen:
                continue
            if comment.id:
                seen.add(comment.id)
            if comment.text or comment.author:
                comments.append(comment)

    if not comments and entities:
        for entity in entities.values():
            comment = _comment_from_entity(entity)
            if comment.id and comment.id in seen:
                continue
            if comment.id:
                seen.add(comment.id)
            comments.append(comment)

    return comments, _next_token(items)