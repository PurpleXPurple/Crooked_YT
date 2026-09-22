# models.py
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class Comment:
    id: str = ""
    author: str = ""
    text: str = ""
    likes: int = 0
    published: str = ""
    replies: int = 0
    is_reply: bool = False


@dataclass(slots=True)
class TranscriptCue:
    start: float
    duration: float
    text: str


@dataclass(slots=True)
class Video:
    id: str
    url: str
    title: str = ""
    description: str = ""
    channel: str = ""
    channel_id: str = ""
    views: int = 0
    duration: int = 0
    published: str = ""
    thumbnail: str = ""
    keywords: list[str] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    transcript: list[TranscriptCue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def transcript_text(self) -> str:
        return " ".join(c.text for c in self.transcript)