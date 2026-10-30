"""Archive Films - browse Internet Archive public-domain films in Kodi."""
import json
import os
import sys
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "lib"))
import ia  # noqa: E402

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
PLUGIN_URL = sys.argv[0]
HANDLE = int(sys.argv[1])
FANART = os.path.join(ADDON.getAddonInfo("path"), "fanart.jpg")
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
HISTORY_FILE = os.path.join(PROFILE, "search_history.json")

ALL_FILMS = "collection:(feature_films OR SciFi_Horror OR Film_Noir OR silent_films)"

SORTS = {
    "popular": "downloads desc",
    "recent": "addeddate desc",
    "rated": "avg_rating desc",
    "az": "titleSorter asc",
    "oldest": "year asc",
    "newest": "year desc",
}

GENRES = [
    ("Action", "action"), ("Adventure", "adventure"), ("Comedy", "comedy"),
    ("Crime", "crime"), ("Documentary", "documentary"), ("Drama", "drama"),
    ("Family", "family"), ("Fantasy", "fantasy"), ("Horror", "horror"),
    ("Musical", "musical"), ("Mystery", "mystery"), ("Romance", "romance"),
    ("Science Fiction", "science fiction"), ("Thriller", "thriller"),
    ("War", "war"), ("Western", "western"), ("Animation", "animation"),
]

COLLECTIONS = [
    ("Feature Films", "feature_films"),
    ("Sci-Fi & Horror", "SciFi_Horror"),
    ("Film Noir", "Film_Noir"),
    ("Silent Films", "silent_films"),
]

DECADES = list(range(1900, 2030, 10))


def url_for(**kwargs):
    return "{}?{}".format(PLUGIN_URL, urlencode(kwargs))


def rows_per_page():
    try:
        return max(10, min(100, int(ADDON.getSetting("rows") or 40)))
    except ValueError:
        return 40


def notify(msg, icon=xbmcgui.NOTIFICATION_INFO):
    xbmcgui.Dialog().notification(ADDON_NAME, msg, icon, 4000)


def folder(label, icon="DefaultFolder.png", plot="", **query):
    li = xbmcgui.ListItem(label=label)
    li.setArt({"icon": icon, "thumb": icon, "fanart": FANART})
    if plot:
        _set_video_info(li, {"plot": plot})
    xbmcplugin.addDirectoryItem(HANDLE, url_for(**query), li, isFolder=True)


def _set_video_info(li, info):
    """Kodi 20+ InfoTagVideo, falling back to setInfo on Kodi 19."""
    try:
        tag = li.getVideoInfoTag()
    except AttributeError:
        li.setInfo("video", info)
        return
    if "title" in info:
        tag.setTitle(info["title"])
    if info.get("plot"):
        tag.setPlot(info["plot"])
    if info.get("year"):
        tag.setYear(info["year"])
    if info.get("duration"):
        tag.setDuration(info["duration"])
    if info.get("genre"):
        tag.setGenres(info["genre"])
    if info.get("director"):
        tag.setDirectors(info["director"])
    if info.get("rating"):
        tag.setRating(info["rating"])
    if info.get("mediatype"):
        tag.setMediaType(info["mediatype"])


# --- menus --------------------------------------------------------------------

def root():
    folder("Popular", "DefaultMovies.png", action="list", q=ALL_FILMS, sort="popular")
    folder("Recently added", "DefaultRecentlyAddedMovies.png", action="list", q=ALL_FILMS, sort="recent")
    folder("Top rated", "DefaultMovieTitle.png", action="list",
           q=ALL_FILMS + " AND num_reviews:[5 TO 100000]", sort="rated")
    folder("Genres", "DefaultGenre.png", action="genres")
    folder("Decades", "DefaultYear.png", action="decades")
    folder("Collections", "DefaultSets.png", action="collections")
    folder("Search", "DefaultAddonsSearch.png", action="search_menu")
    xbmcplugin.endOfDirectory(HANDLE)


def genres():
    for label, subject in GENRES:
        folder(label, "DefaultGenre.png", action="list",
               q='{} AND subject:("{}")'.format(ALL_FILMS, subject), sort="popular")
    xbmcplugin.endOfDirectory(HANDLE)


def decades():
    for start in DECADES:
        folder("{}s".format(start), "DefaultYear.png", action="list",
               q="{} AND year:[{} TO {}]".format(ALL_FILMS, start, start + 9), sort="popular")
    xbmcplugin.endOfDirectory(HANDLE)


def collections():
    for label, coll in COLLECTIONS:
        folder(label, "DefaultSets.png", action="list", q="collection:({})".format(coll), sort="popular")
    xbmcplugin.endOfDirectory(HANDLE)


# --- search -------------------------------------------------------------------

def _load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return []


def _save_history(items):
    try:
        os.makedirs(PROFILE, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as fh:
            json.dump(items[:20], fh)
    except Exception as exc:
        xbmc.log("[archivefilms] could not save history: {}".format(exc), xbmc.LOGWARNING)


def _search_query(term):
    safe = term.replace('"', "").strip()
    return '{} AND (title:("{}") OR subject:("{}") OR creator:("{}"))'.format(ALL_FILMS, safe, safe, safe)


def search_menu():
    folder("[B]New search...[/B]", "DefaultAddonsSearch.png", action="search")
    for term in _load_history():
        folder(term, "DefaultAddonsSearch.png", action="list", q=_search_query(term), sort="popular")
    if _load_history():
        folder("[I]Clear search history[/I]", "DefaultIconError.png", action="clear_history")
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def search():
    term = xbmcgui.Dialog().input("Search films (title, actor, genre)")
    if not term or not term.strip():
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    term = term.strip()
    hist = [t for t in _load_history() if t.lower() != term.lower()]
    _save_history([term] + hist)
    list_films(_search_query(term), "popular", 1)


def clear_history():
    _save_history([])
    notify("Search history cleared")
    xbmc.executebuiltin("Container.Refresh")
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


# --- listing & playback -------------------------------------------------------

def list_films(query, sort, page):
    rows = rows_per_page()
    try:
        docs, total = ia.search(query, SORTS.get(sort, SORTS["popular"]), page, rows)
    except ia.ArchiveError as exc:
        xbmc.log("[archivefilms] search failed: {}".format(exc), xbmc.LOGERROR)
        notify("Could not reach archive.org", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    xbmcplugin.setContent(HANDLE, "movies")
    if not docs:
        notify("No films found")

    for doc in docs:
        ident = doc.get("identifier")
        if not ident:
            continue
        title = ia.as_text(doc.get("title")) or ident
        year = ia.parse_year(doc.get("year"))
        label = "{} ({})".format(title, year) if year else title
        li = xbmcgui.ListItem(label=label)
        thumb = ia.thumb_url(ident)
        li.setArt({"thumb": thumb, "poster": thumb, "icon": thumb, "fanart": FANART})
        rating = 0.0
        try:
            rating = float(doc.get("avg_rating") or 0) * 2  # archive uses 0-5 stars
        except (TypeError, ValueError):
            pass
        _set_video_info(li, {
            "title": title,
            "year": year,
            "plot": ia.as_text(doc.get("description")),
            "genre": ia.as_list(doc.get("subject"))[:4],
            "director": ia.as_list(doc.get("creator"))[:2],
            "duration": ia.parse_runtime(doc.get("runtime")),
            "rating": rating,
            "mediatype": "movie",
        })
        li.setProperty("IsPlayable", "true")
        li.addContextMenuItems([
            ("Choose version...", "PlayMedia({})".format(url_for(action="play", id=ident, choose=1))),
        ])
        xbmcplugin.addDirectoryItem(HANDLE, url_for(action="play", id=ident), li, isFolder=False)

    if page * rows < total:
        pages = (total + rows - 1) // rows
        folder("[B]Next page ({}/{}) >>[/B]".format(page + 1, pages), "DefaultFolder.png",
               action="list", q=query, sort=sort, page=page + 1)

    for method in (xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_TITLE,
                   xbmcplugin.SORT_METHOD_VIDEO_YEAR, xbmcplugin.SORT_METHOD_VIDEO_RATING):
        xbmcplugin.addSortMethod(HANDLE, method)
    xbmcplugin.endOfDirectory(HANDLE)


def play(identifier, choose=False):
    try:
        meta = ia.metadata(identifier)
    except ia.ArchiveError as exc:
        xbmc.log("[archivefilms] metadata failed: {}".format(exc), xbmc.LOGERROR)
        notify("Could not reach archive.org", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    videos, subs = ia.best_streams(meta)
    if not videos:
        notify("No playable video in this item", xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    chosen = videos[0]
    if choose and len(videos) > 1:
        labels = []
        for f in videos:
            size = ia._size(f)
            size_txt = " - {:.0f} MB".format(size / 1048576.0) if size else ""
            labels.append("{} [{}]{}".format(f.get("name"), f.get("format", "?"), size_txt))
        idx = xbmcgui.Dialog().select("Choose version", labels)
        if idx < 0:
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            return
        chosen = videos[idx]

    stream = ia.file_url(identifier, chosen["name"])
    xbmc.log("[archivefilms] playing {}".format(stream), xbmc.LOGINFO)
    li = xbmcgui.ListItem(path=stream)
    md = meta.get("metadata") or {}
    _set_video_info(li, {
        "title": ia.as_text(md.get("title")) or identifier,
        "plot": ia.as_text(md.get("description")),
        "year": ia.parse_year(md.get("year") or md.get("date")),
        "mediatype": "movie",
    })
    li.setArt({"thumb": ia.thumb_url(identifier), "fanart": FANART})
    if chosen["name"].lower().endswith((".mp4", ".m4v")):
        li.setMimeType("video/mp4")
        li.setContentLookup(False)
    if subs:
        li.setSubtitles([ia.file_url(identifier, s["name"]) for s in subs])
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def router(paramstring):
    params = dict(parse_qsl(paramstring.lstrip("?")))
    action = params.get("action")
    if action is None:
        root()
    elif action == "genres":
        genres()
    elif action == "decades":
        decades()
    elif action == "collections":
        collections()
    elif action == "search_menu":
        search_menu()
    elif action == "search":
        search()
    elif action == "clear_history":
        clear_history()
    elif action == "list":
        try:
            page = int(params.get("page", 1))
        except ValueError:
            page = 1
        list_films(params.get("q", ALL_FILMS), params.get("sort", "popular"), page)
    elif action == "play":
        play(params["id"], choose=params.get("choose") == "1")
    else:
        root()


if __name__ == "__main__":
    router(sys.argv[2] if len(sys.argv) > 2 else "")
