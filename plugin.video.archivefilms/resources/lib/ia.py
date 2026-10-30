"""Small client for the public Internet Archive APIs (no login, no keys)."""
import json
import re
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE = "https://archive.org"
UA = "Kodi-ArchiveFilms/1.0 (plugin.video.archivefilms)"
TIMEOUT = 25

FIELDS = ["identifier", "title", "year", "description", "subject",
          "runtime", "avg_rating", "creator", "language"]

# Only full-length movies; skip trailers and stub items.
FILM_FILTER = "mediatype:movies"


class ArchiveError(Exception):
    pass


def fetch_json(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # network, HTTP or JSON errors
        raise ArchiveError(str(exc))


def search(query, sort="downloads desc", page=1, rows=40):
    """Run an advancedsearch query. Returns (docs, total)."""
    q = "({}) AND {}".format(query, FILM_FILTER)
    params = [("q", q), ("rows", rows), ("page", page), ("output", "json")]
    params += [("fl[]", f) for f in FIELDS]
    if sort:
        params.append(("sort[]", sort))
    data = fetch_json("{}/advancedsearch.php?{}".format(BASE, urlencode(params)))
    resp = data.get("response") or {}
    return resp.get("docs", []), int(resp.get("numFound", 0))


def metadata(identifier):
    return fetch_json("{}/metadata/{}".format(BASE, quote(identifier)))


def thumb_url(identifier):
    return "{}/services/img/{}".format(BASE, quote(identifier))


def file_url(identifier, name):
    return "{}/download/{}/{}".format(BASE, quote(identifier), quote(name))


# --- stream selection -------------------------------------------------------

VIDEO_EXT = (".mp4", ".m4v", ".mkv", ".webm", ".ogv", ".avi", ".mpeg", ".mpg")
SUB_EXT = (".srt", ".vtt")


def _size(f):
    try:
        return int(f.get("size") or 0)
    except ValueError:
        return 0


def _rank(f):
    """Higher is better. Prefer H.264 MP4 (plays everywhere, incl. Android TV)."""
    name = f.get("name", "").lower()
    fmt = (f.get("format") or "").lower()
    if not name.endswith(VIDEO_EXT):
        return None
    if "sample" in name or "trailer" in name:
        return None
    score = 0
    if name.endswith(".mp4") or name.endswith(".m4v"):
        score += 100
    if "h.264" in fmt:
        score += 50
    if "hd" in fmt.split() or "h.264 hd" in fmt:
        score += 10
    if "512kb" in fmt or "512kb" in name:
        score -= 30  # low-res derivative, last resort
    if name.endswith((".ogv", ".avi", ".mpeg", ".mpg")):
        score -= 40
    return score


def best_streams(meta):
    """Return (video_files, subtitle_files) ranked best-first."""
    files = meta.get("files") or []
    videos = []
    for f in files:
        r = _rank(f)
        if r is not None:
            videos.append((r, _size(f), f))
    videos.sort(key=lambda t: (t[0], t[1]), reverse=True)
    subs = [f for f in files if f.get("name", "").lower().endswith(SUB_EXT)]
    return [v[2] for v in videos], subs


# --- text helpers -----------------------------------------------------------

def as_text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(v) for v in value)
    text = re.sub(r"<br\s*/?>", "\n", str(value), flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    for a, b in (("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"),
                 ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " ")):
        text = text.replace(a, b)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [s.strip() for s in str(value).split(";") if s.strip()]


def parse_year(value):
    m = re.search(r"(1[89]\d\d|20\d\d)", as_text(value))
    return int(m.group(1)) if m else 0


def parse_runtime(value):
    """'1:32:10', '92 min', '01:32' -> seconds."""
    text = as_text(value).lower()
    if not text:
        return 0
    m = re.match(r"^(\d+):(\d{1,2})(?::(\d{1,2}))?", text)
    if m:
        a, b, c = m.groups()
        if c is not None:
            return int(a) * 3600 + int(b) * 60 + int(c)
        return int(a) * 60 + int(b)
    m = re.search(r"(\d+)\s*min", text)
    if m:
        return int(m.group(1)) * 60
    return 0
