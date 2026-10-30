#!/usr/bin/env python3
"""Build the Kodi repository served by GitHub Pages.

Produces:
  repo/addons.xml + addons.xml.md5
  repo/<addon_id>/<addon_id>-<version>.zip (+ icon/fanart for Kodi's UI)
  repository.archivefilms-<version>.zip   (install this first, from the Kodi source)
  index.html                              (link list Kodi's file manager can browse)
Run after changing an add-on; bump its version in addon.xml so Kodi picks up the update.
"""
import hashlib
import os
import shutil
import xml.etree.ElementTree as ET
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
ADDONS = ["plugin.video.archivefilms", "repository.archivefilms"]
REPO = os.path.join(ROOT, "repo")
SKIP = ("__pycache__", ".DS_Store")


def zip_addon(addon_id, dest):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        base = os.path.join(ROOT, addon_id)
        for folder, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP]
            for name in sorted(files):
                if name in SKIP or name.endswith(".pyc"):
                    continue
                full = os.path.join(folder, name)
                zf.write(full, os.path.relpath(full, ROOT))


def main():
    shutil.rmtree(REPO, ignore_errors=True)
    os.makedirs(REPO)
    for f in os.listdir(ROOT):
        if f.startswith("repository.archivefilms-") and f.endswith(".zip"):
            os.remove(os.path.join(ROOT, f))

    xml_parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>']
    for addon_id in ADDONS:
        path = os.path.join(ROOT, addon_id, "addon.xml")
        version = ET.parse(path).getroot().get("version")
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        xml_parts.append(body[body.index("<addon"):].strip())
        out_dir = os.path.join(REPO, addon_id)
        os.makedirs(out_dir)
        zip_addon(addon_id, os.path.join(out_dir, "{}-{}.zip".format(addon_id, version)))
        for art in ("icon.png", "fanart.jpg"):
            src = os.path.join(ROOT, addon_id, art)
            if os.path.exists(src):
                shutil.copy(src, out_dir)
        if addon_id.startswith("repository."):
            repo_zip = "{}-{}.zip".format(addon_id, version)
            shutil.copy(os.path.join(out_dir, repo_zip), os.path.join(ROOT, repo_zip))
        print("built", addon_id, version)
    xml_parts.append("</addons>\n")

    addons_xml = "\n".join(xml_parts)
    with open(os.path.join(REPO, "addons.xml"), "w", encoding="utf-8") as fh:
        fh.write(addons_xml)
    with open(os.path.join(REPO, "addons.xml.md5"), "w") as fh:
        fh.write(hashlib.md5(addons_xml.encode("utf-8")).hexdigest())

    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write('<!DOCTYPE html>\n<html><head><meta charset="utf-8"><title>Archive Films Kodi repository</title></head>\n'
                 '<body>\n<a href="{0}">{0}</a>\n</body></html>\n'.format(repo_zip))
    open(os.path.join(ROOT, ".nojekyll"), "w").close()
    print("index ->", repo_zip)


if __name__ == "__main__":
    main()
