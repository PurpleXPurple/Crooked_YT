# YouTube Link Parser + Transcript Puller

**Paste a link. Get everything back.**

A tiny Python tool that takes a YouTube link and hands you clean, structured data: the title, description, comments, and the full transcript. One link in, clean data out.

---

## What is this, in plain words?

Imagine you found a YouTube video and you wanted to save everything about it — the name, the description under it, what people said in the comments, and every word spoken in the video.

Normally you would have to copy and paste all of that by hand. That is slow. That is boring. That is exactly the kind of thing a computer should do for you.

This project does it for you. You give it a link. It gives you back a neat little package of everything.

That is it. That is the whole thing.

---

## Who is this for?

- **Curious people** who want to save video info without clicking around.
- **Students** building a dataset or doing research.
- **Developers** who want a small, clean, dependency-light tool they can read in one sitting.
- **Tinkerers** who want something they can actually understand and modify.

If you can open a terminal and type a command, you can use this.

---

## What does it actually grab?

| Thing | What it means |
|---|---|
| **Title** | The name of the video. |
| **Description** | The text the creator wrote below the video. |
| **Comments** | What people said. Top comments, and you can ask for more. |
| **Transcript** | Every word spoken in the video (the captions/subtitles), with timestamps. |

Plus a few bonuses: channel name, view count, duration, publish date, thumbnail URL, and keywords.

---

## Show me it working

Here is the simplest possible thing you can do:

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

That prints a big pile of JSON to your screen. JSON is just a way of writing data that both humans and computers can read. If you want it to look prettier:

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --indent
```

If you would rather read it like a normal document:

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --format text
```

And if you want to save it to a file so you can open it later:

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o my_video.json
```

That is the basics. For everything else — comments limits, languages, proxies — see [USAGE.md](USAGE.md).

---

## Why does this exist?

YouTube is one of the biggest libraries of human speech and human opinion ever assembled. And yet there is no easy, no-nonsense way to say *"give me everything about this one video in a format I can actually use."*

The official YouTube Data API is fine, but it needs API keys, has quotas, and does not give you the transcript. Browser automation tools like Selenium or Playwright work, but they are heavy — they literally launch a whole browser just to read one page.

This project takes the middle path. It talks to YouTube the way a browser does (so it does not get blocked), but it does not launch a browser. It is small, fast, and honest about what it does.

### Design goals

- **Small.** Pure Python. Five files. No frameworks. You can read the whole thing.
- **Fast.** Every library was picked because it is quick.
- **Advanced inside, simple outside.** The hard parts (browser impersonation, hidden JSON, paginated comments) are hidden. You just pass a link.
- **Easy to fix.** YouTube changes its page often. The parser is written so that when it breaks, you can find the broken part quickly.
- **Approachable.** Named clearly. No magic. No clever tricks for the sake of being clever.

---

## How it works (the friendly version)

Think of it like a relay race with five runners.

1. **You give it a link.** Any YouTube link. Watch links, shorts, `youtu.be` links — all fine.
2. **It fetches the page** using a library called `curl_cffi`. This library can *pretend to be a real browser*, which matters because YouTube blocks plain requests.
3. **It finds the hidden data.** YouTube does not send you a clean answer. It sends you a giant HTML page with a lump of JSON buried inside it. The tool digs that lump out.
4. **It reads the JSON** with a very fast JSON library called `orjson`, then picks out the title, description, comment token, caption tracks, and so on.
5. **It fetches the comments and transcript** by asking YouTube's internal API for more data, then hands you the whole package.

---

## The tech stack (and why each piece was chosen)

| Library | What it does | Why this one |
|---|---|---|
| **curl_cffi** | Makes HTTP requests. | It can impersonate real browsers, so YouTube does not block it the way it blocks normal `requests`. |
| **selectolax** | Parses HTML. | It is one of the fastest HTML parsers in Python. Faster than BeautifulSoup by a wide margin. |
| **orjson** | Reads and writes JSON. | It is dramatically faster than the built-in `json` module. |
| **Pure Python** | Everything else. | No build steps. No compiled extensions to fight with. Installs in seconds. |

No Selenium. No Playwright. No headless Chrome. No `pip install` that takes five minutes and fails halfway through.

---

## Folder structure

Here is what lives where.

```
youtube_puller/
├── main.py           # The entry point. Runs the CLI, ties everything together.
├── fetcher.py        # All network calls live here. This is the "talk to YouTube" file.
├── parser.py         # Turns YouTube's messy HTML/JSON into clean Python objects.
├── transcript.py     # Everything about captions and subtitles.
└── models.py         # The data shapes: Video, Comment, TranscriptCue.
```

That is the whole project. Five files, each with one job.

- **`main.py`** — If you are a user, this is the one you run. If you are a developer, this is where the flow starts.
- **`fetcher.py`** — If YouTube starts blocking you, look here. This is where impersonation, retries, proxies, and timeouts are set.
- **`parser.py`** — If YouTube changes its page and the tool stops finding the title or comments, this is where you will fix it.
- **`transcript.py`** — If captions break or you want a different language, this is your file.
- **`models.py`** — The shape of the output. If you want to add a new field to what gets returned, you add it here first.

---

## Glossary — every term, in plain English

Not everyone speaks "developer." Here is a little dictionary so nothing in this README or in the code feels like a mystery.

**API**
A way for one program to ask another program for data. Like a waiter taking your order to the kitchen.

**Caption track**
A single subtitle file for a video. A video can have many — one per language.

**CLI**
"Command Line Interface." The black box where you type commands. Opposite of a window with buttons.

**curl_cffi**
A Python library that makes web requests. Its special trick is that it can make the request *look like it came from a real Chrome or Firefox browser*, which makes websites less likely to block it.

**HTML**
The language web pages are written in. It is the raw text you never see when browsing.

**InnerTube**
YouTube's internal API. It is what the YouTube website itself uses to load comments, recommendations, and other dynamic parts. Not officially documented, but very useful.

**JSON**
"JavaScript Object Notation." A way of writing data as text. Looks like `{"name": "value"}`. Both humans and computers can read it.

**orjson**
A very fast JSON library for Python. Reads and writes JSON much faster than the standard library.

**Parse**
To take messy input (like HTML) and pull out the useful parts in a structured way.

**Proxy**
A middleman server that sits between you and the internet. Useful if your own connection is being blocked or rate-limited.

**Rate limit**
A cap a website puts on how often you can ask it for things. Go too fast, and you get blocked temporarily.

**selectolax**
A fast HTML parser for Python. It lets you say "find me all the `<title>` tags" or "get the text inside this element" quickly.

**Transcript / Captions / Subtitles**
All roughly the same thing here. The words spoken in the video, with timestamps, usually auto-generated by YouTube.

**ydl / yt-dlp**
Another popular YouTube tool. It is great at downloading videos. This project is not a downloader — it just pulls metadata, comments, and text.

**Video ID**
The 11-character code that identifies a video. In `youtube.com/watch?v=dQw4w9WgXcQ`, the ID is `dQw4w9WgXcQ`.

---

## Quick reference — the fields you get back

| Field | Type | What it holds |
|---|---|---|
| `id` | string | The 11-character video ID. |
| `url` | string | The canonical watch URL. |
| `title` | string | The video's title. |
| `description` | string | The description text. |
| `channel` | string | The channel name. |
| `channel_id` | string | The channel's ID. |
| `views` | number | View count. |
| `duration` | number | Length in seconds. |
| `published` | string | Publish date. |
| `thumbnail` | string | URL to the highest-quality thumbnail. |
| `keywords` | list | Tags the creator added. |
| `comments` | list | `Comment` objects. |
| `transcript` | list | `TranscriptCue` objects. |

Each **Comment** has: `id`, `author`, `text`, `likes`, `published`, `replies`, `is_reply`.

Each **TranscriptCue** has: `start` (seconds), `duration` (seconds), `text`.

---

## Installation

```bash
pip install curl_cffi selectolax orjson
```

That is all. Python 3.10 or newer.

---

## A note on fragility (and why that is fine)

YouTube changes its website constantly. Any tool that reads YouTube without using the official API will break sometimes. That is not a bug — that is the nature of the game.

This project is designed with that in mind:

- Everything that touches YouTube's structure lives in **one file** (`parser.py`).
- Everything that touches the network lives in **another file** (`fetcher.py`).

So when YouTube shakes things up, you are not hunting through a thousand lines of code. You open one file, find the field that changed, fix it, done.

---

## How this was built

**Coded by:** Deepseek 4.1 Flash.

The whole project — the structure, the library choices, the parser logic, the CLI, the models — was written by Deepseek 4.1 Flash. It was built to be read as much as it was built to be run. Every file has a clear job, every name says what it does, and nothing is clever for the sake of being clever.

It is the kind of code a person can actually open, understand, and improve. That was the point.

---

## Related reading

- [USAGE.md](USAGE.md) — Full CLI reference, Python API examples, and troubleshooting.
- Web Scraping Basics
- Python Project Ideas
- YouTube Data API vs Scraping
- Fast Python Libraries

---

## License

Do whatever you want with it. It is yours.

---

**One link in. Clean data out.** That is the whole promise.