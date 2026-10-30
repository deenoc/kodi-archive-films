# Archive Films — Kodi add-on

Browse and stream free, public-domain feature films from the [Internet Archive](https://archive.org/details/feature_films) on Kodi, using only the remote.

## Features

- **Popular, Recently added, Top rated** lists with posters, plot, year, runtime and rating
- **Genres** (17), **Decades** (1900s–2020s), **Collections** (Feature Films, Sci-Fi & Horror, Film Noir, Silent Films)
- **Search** by title, actor/director or genre, with a remembered search history
- Plays the best **H.264 MP4** (works on Android TV / Google TV dongles); loads **.srt/.vtt subtitles** when the film has them
- Long-press / context menu → **Choose version...** to pick a different file (e.g. a lighter 512 kb version on slow Wi-Fi)
- Settings: films per page (10–100)

No account, no API key, no dependencies beyond Kodi itself (Kodi 19 Matrix or newer).

## Install on the Google TV / Android TV dongle (no USB needed)

1. Kodi → **Settings → System → Add-ons** → turn on **Unknown sources**.
2. **Settings → File manager → Add source** → `<None>` → type
   `https://deenoc.github.io/kodi-archive-films/` → name it `archivefilms` → OK.
3. **Settings → Add-ons → Install from zip file** → `archivefilms` →
   `repository.archivefilms-1.0.0.zip`.
4. **Install from repository → Archive Films Repository → Video add-ons → Archive Films → Install**.
5. Open it from **Add-ons → Video add-ons → Archive Films**. Future versions update automatically.

## Publishing an update

1. Change the code and bump `version` in `plugin.video.archivefilms/addon.xml`.
2. `python3 build_repo.py`
3. Commit and push. GitHub Pages serves the new `repo/addons.xml`; Kodi updates on its next check.

## Project layout

```
index.html                  # what Kodi's file manager browses
repository.archivefilms/    # the Kodi repository add-on
repo/                       # generated: addons.xml, md5, add-on zips
build_repo.py               # rebuilds repo/ and the repository zip
plugin.video.archivefilms/
├── addon.xml               # id, version, Python 3 requirement
├── main.py                 # menus, listing, playback (router)
├── icon.png, fanart.jpg
└── resources/
    ├── settings.xml
    └── lib/ia.py           # Internet Archive API client + stream picker
```

## APIs used

- Search: `https://archive.org/advancedsearch.php`
- Item files: `https://archive.org/metadata/<identifier>`
- Posters: `https://archive.org/services/img/<identifier>`
- Streams: `https://archive.org/download/<identifier>/<file>`

## Debugging

Kodi log lines are prefixed with `[archivefilms]`. On Android, view the log via
**Settings → System → Logging → Enable debug logging**, or with the *Kodi Log Uploader* add-on.
