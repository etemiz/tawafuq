"""Convert an article markdown to a styled standalone HTML page (+ print CSS).

Usage: python tools/md2html.py docs/articles/tawafuq-en-v2.md
Output: same path with .html. Images keep relative figs/ links.
Image paragraph + following italic caption paragraph are wrapped in
<figure><figcaption> for proper styling and page-break behavior.
"""
import re
import sys
from pathlib import Path

import markdown

CSS = """
:root { color-scheme: light; }
body {
  font-family: Georgia, 'Times New Roman', serif;
  max-width: 780px; margin: 0 auto; padding: 2.5rem 1.2rem 5rem;
  line-height: 1.62; color: #191919; background: #fffdf9;
  font-size: 1.05rem; text-align: justify; hyphens: auto;
}
h1 { font-family: 'Helvetica Neue', Arial, sans-serif; font-weight: 700;
     font-size: 1.9rem; line-height: 1.22; margin: 0 0 1.1rem;
     text-align: left; letter-spacing: -0.01em; }
h1 + p > em { display: block; text-align: left; color: #555;
              border-left: 3px solid #e4296b; padding-left: .9rem;
              font-size: .95rem; margin-bottom: 2rem; }
h2 { font-family: 'Helvetica Neue', Arial, sans-serif; font-weight: 700;
     font-size: 1.28rem; margin: 2.4rem 0 .8rem; text-align: left;
     color: #191919; }
h2::after { content: ""; display: block; width: 46px; height: 3px;
            background: #e4296b; margin-top: .35rem; }
h3 { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 1.05rem;
     margin-top: 1.6rem; text-align: left; }
p { margin: .8rem 0; }
strong { color: #000; }
figure { margin: 1.5rem 0 1.7rem; text-align: center;
         break-inside: avoid; page-break-inside: avoid; }
figure img { max-width: 96%; height: auto; max-height: 150mm;
             width: auto; border: 1px solid #e8e2d8;
             border-radius: 5px; background: #fff; }
figcaption { color: #665f56; font-size: .88rem; line-height: 1.45;
             text-align: center; margin: .5rem auto 0; max-width: 90%; }
table { border-collapse: collapse; margin: 1.3rem auto; font-size: .92rem;
        width: 86%; }
th, td { border: 1px solid #ddd6cc; padding: .42rem .65rem;
         text-align: left; }
th { background: #f4efe6; font-family: 'Helvetica Neue', Arial, sans-serif;
     font-size: .88rem; }
tr:nth-child(even) td { background: #faf7f1; }
code { background: #f3efe7; padding: .08rem .35rem; border-radius: 4px;
       font-size: .86em; }
pre { background: #f7f4ec; border: 1px solid #e5dfd4; border-radius: 6px;
      padding: .7rem .9rem; overflow-x: auto; }
pre code { padding: 0; background: none; }
blockquote { margin: 1.1rem 1.2rem; padding: .5rem 1rem; color: #444;
             background: #faf6ee; border-left: 4px solid #e4296b;
             font-size: .98rem; }
blockquote p { margin: .2rem 0; }
hr { border: none; border-top: 1px solid #e5dfd4; margin: 2.4rem 0; }
a { color: #b3144f; text-decoration: none; }
a:hover { text-decoration: underline; }
.keynums { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
           margin: 1.6rem 0 1.8rem; break-inside: avoid;
           page-break-inside: avoid; }
.keynums div { background: #faf6ee; border: 1px solid #e8e2d8;
               border-top: 3px solid #e4296b; border-radius: 6px;
               padding: .7rem .6rem .6rem; text-align: center; }
.keynums b { display: block; font-family: 'Helvetica Neue', Arial,
             sans-serif; font-size: 1.35rem; color: #191919;
             letter-spacing: -0.01em; }
.methodnotes { font-family: 'Helvetica Neue', Arial, sans-serif;
              font-size: .78rem; line-height: 1.55; color: #a09890;
              border-top: 1px solid #e8e2d8; padding-top: .9rem;
              margin-top: 2.2rem; text-align: left; hyphens: none; }
.keynums span { display: block; font-size: .78rem; color: #665f56;
                line-height: 1.35; margin-top: .3rem; }

@page { size: A4; margin: 17mm 16mm 19mm; }
@page { @bottom-center { content: counter(page) " / " counter(pages);
         font-size: 9pt; color: #999; font-family: Arial, sans-serif; } }
h1, h2, h3 { break-after: avoid; page-break-after: avoid; }
figure, table, blockquote, pre { break-inside: avoid;
               page-break-inside: avoid; orphans: 3; widows: 3; }
"""


def wrap_figures(html: str) -> str:
    # image and caption in the same paragraph (no blank line in md)
    pat = re.compile(
        r'<p><img alt="([^"]*)" src="([^"]*)" ?/>\s*(?:<br\s*/?>)?\s*'
        r'<em>(.*?)</em>\s*</p>', re.S)
    html = pat.sub(
        r'<figure><img alt="\1" src="\2"><figcaption>\3</figcaption></figure>',
        html)
    # images without captions
    pat2 = re.compile(r'<p><img alt="([^"]*)" src="([^"]*)" ?/></p>')
    html = pat2.sub(r'<figure><img alt="\1" src="\2"></figure>', html)
    return html


def main():
    src = Path(sys.argv[1])
    md = src.read_text(encoding="utf-8")
    html = markdown.markdown(md, extensions=["tables", "fenced_code"])
    html = wrap_figures(html)
    m = re.search(r"<h1>(.*?)</h1>", html, re.S)
    title = re.sub(r"<[^>]+>", "", m.group(1)) if m else src.stem
    out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
{html}
</body>
</html>"""
    dst = src.with_suffix(".html")
    dst.write_text(out, encoding="utf-8")
    print("wrote", dst)


if __name__ == "__main__":
    main()