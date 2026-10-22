"""Insert the intro dice illustrations into the v5 ODT.

The user's tracked edits in the intro left three placeholders:
  "AI: insert an image here that contains 10 dice, 3 ones ..."
  "AI: insert an image here that contains 10 dice, 4 ones ..."
  "AI: insert an image that maps dice and box to words and Quran."

This script accepts the pending tracked changes (there are no deletions),
removes the three standalone dice-emoji lines that stood in for the red dots,
and replaces each placeholder with the matching figure and a caption.

Run: .venv/bin/python tools/insert_intro_dice_figs.py
Backup: logs/article-v5-patch/tawafuq-art-v5.odt.pre-intro-dice
"""
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ODT = ROOT / "docs" / "articles" / "tawafuq-art-v5.odt"
FIGS = ROOT / "docs" / "articles" / "figs"
BACKUP = ROOT / "logs" / "article-v5-patch" / "tawafuq-art-v5.odt.pre-intro-dice"

FIGURES = [
    {
        "placeholder": "AI: insert an image here that contains 10 dice, 3 ones in a "
                       "rectangular box and ones are in vertical alignment. Box appears "
                       "tall, not wide.",
        "png": "intro_dice_3.png",
        "name": "Figintro_dice_3",
        "width": "3.35in",
        "height": "4.436in",
        "caption": "Three ones in a vertical column inside a tall box — the other dice "
                   "land at random.",
    },
    {
        "placeholder": "AI: insert an image here that contains 10 dice, 4 ones in a "
                       "rectangular box and ones are in vertical alignment. Box appears "
                       "tall, not wide.",
        "png": "intro_dice_4.png",
        "name": "Figintro_dice_4",
        "width": "3.35in",
        "height": "4.436in",
        "caption": "Four ones in a vertical column — now the pattern is hard to call luck.",
    },
    {
        "placeholder": "AI: insert an image that maps dice and box to words and Quran.",
        "png": "intro_dice_mapping.png",
        "name": "Figintro_dice_mapping",
        "width": "6.4961in",
        "height": "3.537in",
        "caption": "The mapping: the box is the page, the dice are the words, and a red "
                   "one is the name of God.",
    },
]

FRAME = (
    '<text:p text:style-name="P9"><draw:frame text:anchor-type="as-char" '
    'draw:z-index="{z}" draw:name="{name}" draw:style-name="gr1" '
    'draw:text-style-name="P10" svg:width="{width}" svg:height="{height}">'
    '<draw:image xlink:href="Pictures/{png}" xlink:type="simple" xlink:show="embed" '
    'xlink:actuate="onLoad" draw:mime-type="image/png"><text:p/></draw:image>'
    '</draw:frame></text:p>'
    '<text:p text:style-name="P11">{caption}</text:p>'
)


def accept_changes(xml):
    xml = re.sub(r"<text:tracked-changes>.*?</text:tracked-changes>", "",
                 xml, flags=re.S)
    xml = re.sub(r"<text:change-(?:start|end)[^>]*/>", "", xml)
    return xml


def main():
    assert not BACKUP.exists(), f"backup already exists: {BACKUP}"
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ODT, BACKUP)

    with zipfile.ZipFile(ODT) as zin:
        entries = [(i, zin.read(i.filename)) for i in zin.infolist()]

    names = {i.filename for i, _ in entries}
    content = next(d for i, d in entries if i.filename == "content.xml").decode("utf-8")
    content = accept_changes(content)

    emoji = '<text:p text:style-name="P6">🎲</text:p>'
    assert content.count(emoji) == 3, content.count(emoji)
    content = content.replace(emoji, "")

    for z, fig in enumerate(FIGURES, start=10):
        old = f'<text:p text:style-name="P7">{fig["placeholder"]}</text:p>'
        assert content.count(old) == 1, (fig["name"], content.count(old))
        new = FRAME.format(
            z=z, name=fig["name"], width=fig["width"], height=fig["height"],
            png=fig["png"], caption=fig["caption"])
        content = content.replace(old, new)

    manifest_name = "META-INF/manifest.xml"
    manifest = next(d for i, d in entries if i.filename == manifest_name).decode("utf-8")
    for fig in FIGURES:
        path = f'Pictures/{fig["png"]}'
        assert path not in names, path
        entry = (f' <manifest:file-entry manifest:full-path="{path}" '
                 f'manifest:media-type="image/png"/>\n')
        manifest = manifest.replace("</manifest:manifest>", entry + "</manifest:manifest>")
        names.add(path)

    out = ODT.with_suffix(".odt.tmp")
    with zipfile.ZipFile(out, "w") as zout:
        for info, data in entries:
            if info.filename == "content.xml":
                data = content.encode("utf-8")
            elif info.filename == manifest_name:
                data = manifest.encode("utf-8")
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zout.writestr(zi, data)
        for fig in FIGURES:
            zi = zipfile.ZipInfo(f'Pictures/{fig["png"]}', date_time=(2026, 10, 21, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(zi, (FIGS / fig["png"]).read_bytes())
    out.replace(ODT)
    print("patched", ODT)
    print("backup", BACKUP)


if __name__ == "__main__":
    main()
