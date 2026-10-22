#!/usr/bin/env python3
"""Extract text from a PDF file (or URL) to stdout, page-by-page.

Usage:
    .venv/bin/python tools/pdf_extract.py <file.pdf | http(s)://...> [first_page] [last_page]

Requires pymupdf (installed in .venv).
"""
import sys

import pymupdf


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2

    src = sys.argv[1]
    first = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    last = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    if src.startswith(("http://", "https://")):
        import io
        import urllib.request

        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            buf = io.BytesIO(r.read())
        doc = pymupdf.open(stream=buf.getvalue(), filetype="pdf")
    else:
        doc = pymupdf.open(src)

    n = doc.page_count
    last = last if last else n
    print(f"# pages: {n}", file=sys.stderr)

    for i in range(max(1, first), min(n, last) + 1):
        page = doc.load_page(i - 1)
        text = page.get_text("text")
        print(f"===== PAGE {i} =====")
        print(text)

    doc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
