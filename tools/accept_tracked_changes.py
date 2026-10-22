#!/usr/bin/env python3
"""Accept all tracked changes in an ODT (LibreOffice change-tracking).

Accepting means: drop the <text:tracked-changes> block (deleted content lives
only there) and remove the in-body markers <text:change/>, <text:change-start/>,
<text:change-end/> (inserted text lives in the body and simply stays).

Usage: accept_tracked_changes.py <file.odt> <backup-path>
Writes the accepted file in place; the pre-accept copy goes to <backup-path>.
"""
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET

MARKER_RES = [
    r"<text:change(?:\s[^>]*)?/>",
    r"<text:change-(?:start|end)[^>]*/>",
]


def accept(xml):
    xml, n_block = re.subn(r"<text:tracked-changes>.*?</text:tracked-changes>",
                           "", xml, flags=re.S)
    n_markers = 0
    for pat in MARKER_RES:
        xml, n = re.subn(pat, "", xml)
        n_markers += n
    return xml, n_block, n_markers


def main():
    odt_path, backup_path = sys.argv[1], sys.argv[2]
    shutil.copy2(odt_path, backup_path)
    print(f"backup: {backup_path}")

    with zipfile.ZipFile(odt_path) as zin:
        entries = [(i, zin.read(i.filename)) for i in zin.infolist()]

    out = []
    for info, data in entries:
        if info.filename == "content.xml":
            xml = data.decode("utf-8")
            xml, n_block, n_markers = accept(xml)
            assert n_block == 1, f"tracked-changes blocks removed: {n_block}"
            assert "text:change" not in xml.replace("text:changed-region", "") \
                and "tracked-changes" not in xml, "markers remain"
            ET.fromstring(xml)  # well-formedness
            print(f"content.xml: removed 1 tracked-changes block, "
                  f"{n_markers} markers; XML well-formed")
            data = xml.encode("utf-8")
        out.append((info, data))

    with zipfile.ZipFile(odt_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in out:
            zout.writestr(info, data)

    with zipfile.ZipFile(odt_path) as z:
        assert z.testzip() is None
    print("zip integrity OK")


if __name__ == "__main__":
    main()
