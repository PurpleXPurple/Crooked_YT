# Usage

## Requirements

- Python 3.10+
- `curl_cffi`
- `selectolax`
- `orjson`

Install:

```bash
pip install curl_cffi selectolax orjson
```

## Quick start

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Default output is JSON to stdout.

## Common examples

Save JSON to a file:

```bash
python main.py "https://youtu.be/dQw4w9WgXcQ" -o video.json
```

Pretty-print JSON:

```bash
python main.py "https://youtu.be/dQw4w9WgXcQ" --indent
```

Human-readable text report:

```bash
python main.py "https://youtu.be/dQw4w9WgXcQ" --format text
```

Limit comments:

```bash
python main.py "https://youtu.be/dQw4w9WgXcQ" --comments 50
```

Skip comments:

```bash
python main.py "https://youtu.be/dQw4w9WgXcQ" --no-comments
```

Skip transcript:

```bash
python main.py "https://youtu.be/dQw4w9WgXcQ" --no-transcript
```

Prefer a transcript language:

```bash
python main.py "https://youtu.be/dQw4w9WgXcQ" --lang en
```

Use a proxy:

```bash
python main.py "https://youtu.be/dQw4w9WgXcQ" --proxy "http://127.0.0.1:8080"
```

Change browser impersonation:

```bash
python main.py "https://youtu.be/dQw4w9WgXcQ" --impersonate chrome124
```

## CLI options

| Option | Default | Description |
|---|---:|---|
| `url` | required | YouTube URL or bare 11-character video ID |
| `-o`, `--output` | stdout | Write output to a file |
| `--format` | `json` | Output format: `json` or `text` |
| `--comments` | `20` | Max comments to fetch. `0` disables comments |
| `--lang` | auto | Preferred caption/UI language, e.g. `en`, `de`, `es` |
| `--no-comments` | off | Skip comment fetching |
| `--no-transcript` | off | Skip transcript fetching |
| `--proxy` | none | HTTP(S) proxy URL |
| `--impersonate` | `chrome` | curl_cffi browser profile |
| `--timeout` | `30.0` | Request timeout in seconds |
| `--indent` | off | Pretty-print JSON output |

## Output: JSON

The JSON shape follows `Video.to_dict()`.

```json
{
  "id": "dQw4w9WgXcQ",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "Video title",
  "description": "Video description",
  "channel": "Channel name",
  "channel_id": "UC...",
  "views": 123456,
  "duration": 213,
  "published": "2009-10-25",
  "thumbnail": "https://...",
  "keywords": ["keyword1", "keyword2"],
  "comments": [
    {
      "id": "Ug...",
      "author": "Commenter",
      "text": "Comment text",
      "likes": 42,
      "published": "1 year ago",
      "replies": 3,
      "is_reply": false
    }
  ],
  "transcript": [
    {
      "start": 0.0,
      "duration": 2.5,
      "text": "First line of transcript"
    }
  ]
}
```

## Output: text

`--format text` produces a readable report:

```text
Title:     Video title
Channel:   Channel name
Views:     123,456
Duration:  3:33
Published: 2009-10-25
URL:       https://www.youtube.com/watch?v=dQw4w9WgXcQ

Description
-----------
Video description

Comments (20)
-------------
[42] Commenter · 1 year ago · 3 replies
Comment text

Transcript (120 cues)
--------------------
[0:00] First line of transcript
```

## Python API

```python
from main import pull

video = pull(
    "https://youtu.be/dQw4w9WgXcQ",
    want_comments=10,
    lang="en",
    with_transcript=True,
    with_comments=True,
)

print(video.title)
print(video.channel)
print(video.views)
print(video.transcript_text)
print(video.to_dict())
```

`pull()` returns a `Video` object. Use:

- `video.to_dict()` for JSON-serializable data
- `video.transcript_text` for plain transcript text
- `video.comments` for `Comment` objects
- `video.transcript` for `TranscriptCue` objects

## Notes

- Comments are fetched through YouTube's InnerTube `next` endpoint.
- Transcripts prefer `json3`; XML captions are used as fallback.
- If comments are disabled or unavailable, `comments` will be empty.
- If no captions exist, `transcript` will be empty.
- `MAX_COMMENT_PAGES` in `main.py` limits comment pagination. Increase it if you need more than the default depth.

## Troubleshooting

`error: HTTP 429`

YouTube is rate-limiting. Wait, retry, or use `--proxy`.

`watch page did not contain ytInitialData`

The video may be private, deleted, age-restricted, region-blocked, or YouTube changed its page structure. Try `--proxy` or a different `--impersonate` profile.

No comments returned

Comments may be disabled, hidden, or not present in the initial payload.

No transcript returned

Captions may be disabled. Try `--lang` with a specific language code.

`curl_cffi` install fails

Upgrade pip first:

```bash
pip install -U pip
pip install curl_cffi
```

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Success |
| `1` | Fetch or parse error |