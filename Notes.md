# Notes

**Code review, hot takes, and what I would change.**

This is not the polished user-facing document. This is the honest one. If you are about to run, fork, or extend this project, read this first. It will save you time.

---

## The short version

The code works. It does what it says on the tin. But it is a first draft that ships, not a final draft. There are a handful of real bugs, several code smells, and a few opinions I would push back on if I were reviewing this as a pull request.

Nothing here is a dealbreaker. Everything here is worth knowing.

---

## What is genuinely good

Credit where it is due.

- **File separation is clean.** `fetcher.py` does the network, `parser.py` does the parsing, `transcript.py` does captions, `models.py` does shapes, `main.py` orchestrates. That is the right cut.
- **`models.py` uses `slots=True` and `default_factory=list`.** Both are the correct modern choices. No mutable default footgun.
- **Retry logic actually distinguishes retryable from non-retryable statuses.** `RETRY_STATUS` is a real set, not a vibe.
- **`FetchError` is a custom exception.** Callers can catch it specifically. Good hygiene.
- **`yield from` / generator walk in `parser.py`.** Clean, no recursion limit problems on deeply nested YouTube JSON.
- **The `raw_decode` trick for finding embedded JSON** is the right way. Regex would be a disaster here.

So the skeleton is solid. Now the meat.

---

## Real bugs

These are not opinions. These are things that will actually misbehave in the wild.

### 1. `keywords` will be a list of characters, not strings

In `parser.py`, `build_video` does:

```python
keywords=list(details.get("keywords") or [])
```

Sometimes `videoDetails.keywords` is a **string** like `"music,pop,2024"`, not a list. In that case `list("music,pop,2024")` gives you `['m', 'u', 's', 'i', 'c', ',', ...]`. Every character its own keyword.

**Fix:** detect the type and split on commas.

```python
raw = details.get("keywords")
if isinstance(raw, str):
    keywords = [k.strip() for k in raw.split(",") if k.strip()]
else:
    keywords = list(raw or [])
```

### 2. `_first_comment_id` can grab the wrong comment

It walks the whole thread looking for the first `commentId` it finds. But a `commentThreadRenderer` contains the top-level comment **and sometimes preview replies**. If a reply appears first in traversal order, you will key the whole thread on the wrong ID.

**Fix:** walk the specific path `commentThreadRenderer.commentViewModel` or `commentThreadRenderer.comment.commentRenderer.commentId`. Do not search the whole subtree blindly.

### 3. `collect_comments` can spin on empty pages

```python
while token and len(comments) < limit and pages < MAX_COMMENT_PAGES:
    ...
    batch, token = parse_comments(payload)
    pages += 1
    if not batch and not token:
        break
```

If YouTube returns a page with **no new comments but a continuation token**, this loop runs to `MAX_COMMENT_PAGES` doing nothing useful. It also does not detect "we got a token back but it is the same token we sent" — which does happen.

**Fix:** track the previous token and break if it repeats. Track consecutive empty batches and break after two.

### 4. `transcript_text` produces double spaces

```python
return " ".join(c.text for c in self.transcript)
```

Manual (human-written) captions often have cues that already end in a space, or cues whose text is `"Hello there "` with a trailing space. Joining with `" "` gives you double spaces everywhere.

**Fix:** strip each cue and smart-join.

```python
return " ".join(c.text.strip() for c in self.transcript if c.text.strip())
```

Or, better, join without a space and rely on the cue boundaries already being space-correct.

### 5. `comments_token` second fallback is dead-ish code

```python
for node in walk(data):
    if "commentsSection" in node or node.get("targetId") == "comments-section":
        token = dig(node, "continuationEndpoint", "continuationCommand", "token")
```

`continuationEndpoint` is almost never a direct child of the comments section node. It is nested inside a `continuationItemRenderer`, which the first loop already handles. This second loop rarely fires and gives false confidence.

**Fix:** delete it, or point it at the right path (`continuationItemRenderer`).

### 6. `--indent` silently does nothing with `--format text`

In `main.py`:

```python
if args.format == "text":
    output = render_text(video, ...)
else:
    option = orjson.OPT_INDENT_2 if args.indent else 0
    ...
```

If a user passes `--format text --indent`, they get no error and no effect. This is the kind of thing that makes people distrust a tool.

**Fix:** warn on stderr, or make them mutually exclusive with argparse.

### 7. `impersonate="chrome"` is version-sensitive

`curl_cffi` accepts values like `chrome`, `chrome110`, `chrome120`, `chrome124`, `safari17_0`, etc. The bare `"chrome"` alias has shifted meaning across versions and has been removed or renamed at least once. If someone installs a different `curl_cffi` version, this default can break.

**Fix:** pin to a concrete target like `chrome124` and document that it may need updating.

### 8. Age-restricted videos silently return a mostly-empty `Video`

If YouTube serves a consent or age-gate page, `ytInitialData` may still be present (as a stub), so the `"ytInitialData" not in html` check passes. `build_video` then returns a `Video` with empty title, empty description, zero views. No error.

**Fix:** after building, check `if not video.title: raise FetchError("could not read video metadata (age-gated, private, or region-locked)")`.

---

## Code smells

Not bugs. Just things that will make future-you sigh.

- **`MAX_COMMENT_PAGES` is a module constant.** It should be a parameter on `pull()` and a CLI flag. Hardcoded limits age badly.
- **`pull()` does too much.** It validates, fetches, parses, orchestrates comments, orchestrates transcript, and returns. Split into `fetch_metadata`, `fetch_comments`, `fetch_transcript` — or move to a small class.
- **No logging.** `print(..., file=sys.stderr)` is the entire diagnostic story. A `logging.getLogger(__name__)` with a `--verbose` flag costs nothing and pays off immediately the first time something breaks in the wild.
- **Sleep-based backoff is fixed-step.** `1.2 * (attempt + 1)` is linear. Fine for three retries. Exponential with jitter is standard and just as easy.
- **`find_first` is O(n) per call and called repeatedly.** On a big page that is hundreds of thousands of dict nodes visited many times. A single pre-built index would be faster, but it is not a real bottleneck yet — just be aware.
- **`walk` uses a stack (LIFO).** That means traversal is depth-first and the order is reversed. For `find_first`, this changes which "first" you get. Usually fine, occasionally surprising. If you want "top-most first" semantics, use a deque and popleft.
- **No `__all__`** in any module. Small thing, but it documents the public surface and stops `from parser import *` from dragging internals into scope.
- **Comment dedup key can collide.** `comment.id or f"{author}:{text[:60]}"` — two genuinely distinct comments by the same author starting with the same 60 characters will be treated as one. Rare, but it happens with reply chains.

---

## Hot takes

Unpopular opinions, freely given.

### 1. Fighting InnerTube is a losing long-term bet

The whole comment-fetching approach rides on YouTube's internal, undocumented `youtubei/v1/next` endpoint. It works today. It has worked for years. It will break eventually, and when it does, it will not warn you — it will just start returning empty pages.

If you need comments to be reliable, use the official Data API v3 for those. Use this tool's InnerTube approach for everything else. Hybrid setups are less elegant but far more durable.

### 2. `ytInitialData` is the most fragile data source on the page

There are at least three different places the same data appears on a YouTube watch page:

- `ytInitialData`
- `ytInitialPlayerResponse`
- the `<script>`-injected JSON in the `<head>`

We pick the first two. But which one has the title, and which has the description, changes between page variants. The current code works around this. It will keep needing workarounds.

### 3. Scraping comments in full is almost never worth it

A 20-comment pull is fine. A 5000-comment pull takes minutes, gets rate-limited, and produces data that is 80% noise. If you genuinely need all comments, the official API is the answer. If you want "the vibe," the top 50 are enough. The default of 20 is honest.

### 4. The text output is not a report, it is a dump

Dumping every transcript cue on its own line for a 3-hour podcast produces thousands of lines. Nobody reads that. A `--merge-cues` mode that groups cues into paragraph-sized chunks by gap and punctuation would be dramatically more useful.

### 5. Five files is correct, but `main.py` is still too fat

`main.py` holds the CLI parser, `_context`, `_api_key`, `collect_comments`, `pull`, `_hms`, `render_text`, `build_parser`, and `main`. That is a lot of hats. `render_text` and `_hms` belong in a `render.py`. `pull` belongs in a `core.py`. The CLI belongs in `main.py`. Six files, still small, much clearer.

### 6. No tests is not a moral failing, it is a missing safety net

There is no test directory. There is no fixture. There is no recorded HTML to parse against. This means any refactor risks silent breakage. You do not need 100% coverage. You need one saved `watch.html` fixture and one test that says "the parser finds a title in it." That is a 30-line investment that pays back within a week.

### 7. The default `chrome` impersonation is fine until it is not

See the bug section. But more broadly: whatever browser profile you pick, YouTube fingerprints it. Rotating between two or three profiles on retry is more robust than a single "best" one.

### 8. `orjson` and `selectolax` are hard dependencies for marginal gains here

This tool makes ~5 HTTP requests per run and parses maybe 2 MB of HTML. `json` would be fine. `BeautifulSoup` would be fine. The speed difference is real but irrelevant at this scale. The real reason to use `orjson`/`selectolax` is that they are pleasant to use, which is a fine reason — just do not pretend it is performance.

---

## Improvements, ranked

If you have an hour, do these in order.

### Tier 1 — correctness (do first)

1. Fix the `keywords` string/list bug in `parser.py`.
2. Fix `_first_comment_id` to walk the correct path.
3. Add a no-progress break in `collect_comments`.
4. Strip cues in `transcript_text`.
5. Raise `FetchError` when `video.title` is empty after parsing.

### Tier 2 — usability (do next)

6. Add `--max-comment-pages` flag.
7. Move `render_text` and `_hms` into `render.py`.
8. Make `--indent` warn or error when `--format text` is set.
9. Add `--merge-cues` for readable transcripts.
10. Add a `--verbose` flag that wires up `logging`.

### Tier 3 — robustness (worth the time)

11. Add exponential backoff with jitter.
12. Rotate impersonation profiles on retry.
13. Detect consent/age-gate pages and raise clearly.
14. Save partial comments on failure instead of discarding everything.
15. Add one saved HTML fixture and one parser test.

### Tier 4 — nice to have

16. `pyproject.toml` with declared dependencies and a `ytp` console script.
17. A `--json-schema` mode that emits the shape of the output.
18. Support for translated caption tracks via `tlang`.
19. Optional parallel fetch of comments and transcript (they do not depend on each other).
20. A `--cookies` flag for age-restricted videos.

---

## What I would do differently

If I were starting from scratch, three changes.

**First, add a `core.py`.** Keep `main.py` as a thin CLI wrapper. `core.pull()` should be importable without dragging in argparse.

**Second, split the parser into two layers.** One layer that navigates YouTube's JSON generically (`find_first`, `walk`, `dig`, `text_of`), and one layer that knows YouTube's specific shape (`build_video`, `parse_comments`). The generic layer is reusable and testable. The specific layer is the one that breaks when YouTube changes.

**Third, save a fixture.** One real watch page. One test. The whole point of this project is "it works even when YouTube changes." Without a fixture, you cannot tell whether a change broke you or you broke yourself.

---

## What I would not change

A few things are right and worth defending.

- **No async.** For a single-video CLI tool, asyncio is a tax with no dividend. If someone wants to batch-process 10,000 videos, they can wrap `pull()` in a thread pool. Do not infect the happy path with `async def` for the 1% case.
- **No Selenium, no Playwright.** The whole point is "no browser." Do not add one for a feature that works without it.
- **Five (or six) files, not fifty.** Small tools should look small. The moment this becomes a package with a `src/` layout and an `internal/` folder is the moment it stops being readable.
- **`slots=True` on dataclasses.** Keep it. Memory matters when you have 5000 comments in a list.
- **Custom `FetchError`.** Keep it. Catching `RuntimeError` is a smell.

---

## A note on fragility, again

Every tool that reads YouTube without the official API is a tool that breaks sometimes. This is not pessimism, it is the cost of the approach.

What matters is how gracefully it breaks and how quickly you can fix it.

This code is well set up for that:

- All network concerns in `fetcher.py`.
- All structure concerns in `parser.py`.
- All caption concerns in `transcript.py`.

When YouTube changes something, you open one file, find the field, update it. That is the whole maintenance story. It is a good story. Keep it that way when you extend it.

---

## The honest summary

This is a strong first draft. The bones are right. The names are right. The separation is right. It will work for most videos most of the time.

It is not production-grade. It has real bugs, no tests, and one or two fragile assumptions about YouTube's page structure that will need revisiting.

If you are using it for yourself — a script, a notebook, a one-off — you are fine. Go.

If you are using it in a product or a pipeline — fix Tier 1 first, add a fixture, and be ready to patch `parser.py` every few months. That is the deal you make when you scrape YouTube without an API key.

Still a good deal. Just know the terms.

---

**Built by Deepseek 4.1 Flash. Reviewed by the same, with the gloves off.**