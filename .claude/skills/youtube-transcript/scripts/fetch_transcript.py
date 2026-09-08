#!/usr/bin/env python3
"""Fetch a YouTube transcript (optionally a time window) and print it with timestamps.

Usage:
  fetch_transcript.py <url-or-id> [--start 6:25] [--end 7:40] [--lang zh-Hant,zh-Hans,zh,en] [--json]

Requires: pip install youtube-transcript-api   (pypi.org is reachable even on the
"trusted" network policy; youtube.com itself is NOT — the environment must allow it).
"""
import argparse, json, re, sys

def parse_ts(s):
    if s is None:
        return None
    parts = [float(p) for p in s.split(":")]
    secs = 0.0
    for p in parts:
        secs = secs * 60 + p
    return secs

def fmt_ts(sec):
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def video_id(s):
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", s):
        return s
    sys.exit(f"cannot find a video id in: {s}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--start", default=None, help="mm:ss or h:mm:ss")
    ap.add_argument("--end", default=None, help="mm:ss or h:mm:ss")
    ap.add_argument("--lang", default="zh-Hant,zh-TW,zh-Hans,zh-CN,zh,en",
                    help="comma-separated language preference order")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    a = ap.parse_args()

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api import (NoTranscriptFound, TranscriptsDisabled,
                                            RequestBlocked, IpBlocked, VideoUnavailable)
    except ImportError:
        sys.exit("youtube-transcript-api not installed: pip install youtube-transcript-api")

    vid = video_id(a.video)
    langs = [l.strip() for l in a.lang.split(",") if l.strip()]
    api = YouTubeTranscriptApi()
    try:
        tl = api.list(vid)
        try:
            tr = tl.find_transcript(langs)          # manual or auto captions in preferred langs
        except NoTranscriptFound:
            first = next(iter(tl))                  # any language, then translate if possible
            tr = first.translate(langs[0]) if first.is_translatable else first
        fetched = tr.fetch()
        meta = {"video_id": vid, "language": tr.language, "language_code": tr.language_code,
                "generated": tr.is_generated}
    except TranscriptsDisabled:
        sys.exit("captions are disabled on this video; ask the user to paste the transcript")
    except (RequestBlocked, IpBlocked) as e:
        sys.exit("YouTube blocked the request (network policy / IP block). "
                 "Environment must allow youtube.com. Detail: " + str(e).splitlines()[0])
    except VideoUnavailable:
        sys.exit("video unavailable (private, removed, or region-locked)")
    except Exception as e:  # connection errors etc.
        msg = str(e).splitlines()[0]
        hint = ""
        if "403" in msg or "Proxy" in msg or "Tunnel" in msg:
            hint = " -> YouTube blocked by the environment network policy; allow youtube.com and start a new session."
        sys.exit(f"fetch failed ({type(e).__name__}): {msg}{hint}")

    s0, s1 = parse_ts(a.start), parse_ts(a.end)
    rows = []
    for snip in fetched:
        t0, t1 = snip.start, snip.start + snip.duration
        if s0 is not None and t1 < s0:
            continue
        if s1 is not None and t0 > s1:
            continue
        rows.append({"start": round(t0, 2), "end": round(t1, 2), "text": snip.text.replace("\n", " ")})

    if a.json:
        print(json.dumps({**meta, "window": [a.start, a.end], "lines": rows}, ensure_ascii=False, indent=1))
        return
    print(f"# {vid} · {meta['language']} ({'auto' if meta['generated'] else 'manual'})"
          + (f" · {a.start or '0:00'}–{a.end or 'end'}" if (a.start or a.end) else ""))
    for r in rows:
        print(f"[{fmt_ts(r['start'])}] {r['text']}")
    if not rows:
        print("(no lines in that window)")

if __name__ == "__main__":
    main()
