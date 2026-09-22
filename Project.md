# YouTube Link Parser + Transcript Puller

> [!info] Project type: Tool / Script
> A Python tool that takes a YouTube link and pulls out the title, description, comments, and transcript. Simple to use, strong under the hood.

---

## Messy first thoughts

So the idea is simple. You paste a YouTube link. The tool grabs everything — title, description, comments, transcript. All of it. The stack is curl_cffi for requests (it can act like a real browser, so YouTube does not block it), selectolax for fast HTML parsing, orjson for fast JSON. Pure Python style. It is advanced stuff inside, but the user just pastes a link and gets clean data. That's it.

---

## Clean version

### What it is
A small Python tool. One job: take a YouTube link, return clean data.

### What it gets

| Data | What it means |
|------|---------------|
| Title | The video name |
| Description | The text below the video |
| Comments | Top comments, maybe all |
| Transcript | Full subtitle text |

### Tech stack

| Library | Why we use it |
|---------|---------------|
| curl_cffi | HTTP requests. Can fake a real browser. Beats YouTube blocks. |
| selectolax | Very fast HTML parser. |
| orjson | Very fast JSON reader and writer. |
| Pure Python | Easy to install. Easy to read. |

> [!tip] Why this stack?
> All four are fast and light. No heavy frameworks. No browser needed. Just clean Python.

---

### How it works (simple flow)

1. User gives a YouTube link.
2. Tool sends a request with **curl_cffi**.
3. Tool parses the page with **selectolax**.
4. Tool reads hidden JSON with **orjson**.
5. Tool returns title, description, comments, transcript.

> [!warning] YouTube changes things
> YouTube updates its page often. The parser may break. Keep it easy to fix.

---

### Design goals

- **Advanced inside** — handles real-world YouTube blocks.
- **User friendly outside** — one link in, clean data out.
- **Small** — pure Python. No big setup.
- **Fast** — curl_cffi + selectolax + orjson.

---

### Project structure idea

```
youtube_puller/
├── main.py          # CLI entry
├── fetcher.py       # curl_cffi requests
├── parser.py        # selectolax + orjson
├── transcript.py    # transcript logic
└── models.py        # simple data classes
```

---

### Links

- [[Web Scraping Basics]]
- [[Python Project Ideas]]
- [[YouTube Data API vs Scraping]]
- [[Fast Python Libraries]]

### Tags
#project #python #youtube #scraping #transcript #tool

---

### Review questions

1. What does curl_cffi do that normal `requests` cannot?
2. Why use selectolax instead of BeautifulSoup?
3. What four things does this tool pull from a YouTube link?

---

> [!summary] Summary
> A small Python tool that takes a YouTube link and returns the title, description, comments, and transcript. It uses curl_cffi for smart requests, selectolax for fast parsing, orjson for fast JSON, and stays pure Python. Advanced inside, simple outside. One link in, clean data out.