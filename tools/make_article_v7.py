#!/usr/bin/env python3
"""Build docs/articles/tawafuq-art-v7.odt from tawafuq-art-v6.odt.

Two kinds of changes, no image or claim/number edits:
  A. Grammar/copy fixes in content.xml (exact-once replacements, span-aware).
  B. Styling: brand-colored title/subtitle with a rule, section headings get a
     thin bottom border + keep-with-next, step headings recolored to the brand
     brown, body unified to 11pt Liberation Serif, justified, 140% line
     height, orphan/widow control, hanging indents for the dash bullets,
     challenge line styled as a centered callout, per-type table cells moved
     to the same 9.5pt header/body styles as the other tables, and a centered
     page-number footer on the master page.

Every replacement is asserted to occur exactly once. Validated at the end:
zip integrity, XML well-formedness, odfpy load, digit-token multiset identical
to v6 (no number touched), and Pictures byte-identical to v6.
"""
import hashlib
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

SRC = "docs/articles/tawafuq-art-v6.odt"
DST = "docs/articles/tawafuq-art-v7.odt"

# ---------------------------------------------------------------- A. grammar
GRAMMAR = [
    ("Imagine 3 red dots appeared",
     "Imagine 3 red dots appear"),
    ("This may not look when you think about 1 page but",
     "This may not look like much when you think about 1 page, but"),
    ("let alone test one",
     "let alone tested one"),
    ('<text:span text:style-name="T2">which has</text:span>',
     '<text:span text:style-name="T2">that has</text:span>'),
    ("We open source the code on GitHub",
     "We open-source the code on GitHub"),
    ('spent probably around ~<text:span text:style-name="T4">3</text:span>0 USD',
     "spent probably around 30 USD"),
    ('that cost about ~100 USD. <text:s/><text:span text:style-name="T4">Then GLM',
     'that cost about 100 USD. <text:span text:style-name="T4">Then GLM'),
    ('• Faithful polymaths <text:span text:style-name="T12">to </text:span>'
     'jumping other domains <text:span text:style-name="T12">than faith. </text:span><text:s/>',
     "• Faithful polymaths for jumping to domains beyond faith. "),
    ("source of inter domain evaluation ",
     "source of inter-domain evaluation "),
    ("above average truthful",
     "above-average truthful"),
    ("but combination should work",
     "but the combination should work"),
    ("We started with Quran but",
     "We started with the Quran, but"),
    ("don’t oppose Quran",
     "don’t oppose the Quran"),
    ("The above two is for LLM fine tuning.",
     "The above two are for LLM fine-tuning."),
    ("logarithmic scale. Each step",
     "a logarithmic scale. Each step"),
    ("What this means for a muslim:",
     "What this means for a Muslim:"),
    ("habits that fake alignment",
     "habits that could fake alignment"),
    ("withdrew that, because",
     "withdrew that because"),
    ("where do you begin with?",
     "where do you begin?"),
    ("We refuse IJASAT",
     "We reject IJASAT"),
    ("they refuse 2 verses",
     "they reject 2 verses"),
    ("change Quran’s text",
     "change the Quran’s text"),
    ("comparisons—not from",
     "comparisons — not from"),
    ("And imagine realizing the same thing",
     "And imagine realizing that the same thing"),
    ("Quran looks like a great starting point",
     "The Quran looks like a great starting point"),
    ('Accepting <text:span text:style-name="T12">Q</text:span>uran as ground truth',
     "Accepting the Quran as ground truth"),
    ("As claims get closer to Quranic truth they must be scoring higher",
     "As claims get closer to Quranic truth, they must score higher"),
    ("can be compared with each other and truth",
     "can be compared with every other, and truth"),
    ("It also affects your vibes, every heavy metal",
     "It also affects your vibes. Every heavy metal"),
    ("health related questions",
     "health-related questions"),
    ("but friends were busy",
     "but they were busy"),
    ("GPT. <text:s/>Emin Temiz did not audit",
     "GPT. Emin Temiz did not audit"),
    ('manually. <text:s/><text:span text:style-name="T14">He</text:span>',
     'manually. <text:span text:style-name="T14">He</text:span>'),
    ('human. <text:s/><text:span text:style-name="T15">In this study',
     'human. <text:span text:style-name="T15">In this study'),
    (">human aligned</text:a>",
     ">human-aligned</text:a>"),
    ("LLMs</text:a> which try to include",
     "LLMs</text:a> that try to include"),
    ("from datasets or anything",
     "from datasets, and anything"),
    ("it or knowledge around it could be included",
     "it or the knowledge around it could be included"),
]

# ------------------------------------------------------- B1. style elements
def pstyle(name, para_props, text_props):
    return (f'<style:style style:name="{name}" style:family="paragraph" '
            f'style:parent-style-name="Standard">{para_props}{text_props}</style:style>')

BODY_PP = ('<style:paragraph-properties fo:margin-top="0in" '
           'fo:margin-bottom="0.0591in" style:contextual-spacing="false" '
           'fo:line-height="140%" fo:text-align="justify" '
           'style:justify-single-word="false" fo:orphans="2" fo:widows="2"/>')
HEAD_RULE = (' fo:keep-with-next="always" fo:border-bottom="0.5pt solid #d9bcbc" '
             'fo:padding-bottom="0.03in"')

STYLE_REPLACEMENTS = [
    # title: bigger, brand color, more air above
    (pstyle("P1",
            '<style:paragraph-properties fo:margin-top="0.2362in" fo:margin-bottom="0.1181in" '
            'style:contextual-spacing="false" fo:text-align="center" style:justify-single-word="false"/>',
            '<style:text-properties fo:font-size="26pt" fo:font-weight="bold" '
            'style:font-weight-asian="bold" style:font-weight-complex="bold"/>'),
     pstyle("P1",
            '<style:paragraph-properties fo:margin-top="0.55in" fo:margin-bottom="0.1181in" '
            'style:contextual-spacing="false" fo:text-align="center" style:justify-single-word="false"/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="28pt" '
            'fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold"/>')),
    # subtitle lines: brand color
    (pstyle("P2",
            '<style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0.1965in" '
            'style:contextual-spacing="false" fo:text-align="center" style:justify-single-word="false"/>',
            '<style:text-properties fo:font-size="13pt" fo:font-style="italic"/>'),
     pstyle("P2",
            '<style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0.1965in" '
            'style:contextual-spacing="false" fo:text-align="center" style:justify-single-word="false"/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="13pt" '
            'fo:font-style="italic"/>')),
    (pstyle("P3",
            '<style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0.1965in" '
            'style:contextual-spacing="false" fo:text-align="center" style:justify-single-word="false"/>',
            '<style:text-properties fo:font-size="13pt" fo:font-style="italic" officeooo:rsid="00044c01"/>'),
     pstyle("P3",
            '<style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0.1965in" '
            'style:contextual-spacing="false" fo:text-align="center" style:justify-single-word="false" '
            'fo:border-bottom="0.75pt solid #d9bcbc" fo:padding-bottom="0.1in"/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="13pt" '
            'fo:font-style="italic" officeooo:rsid="00044c01"/>')),
    # section headings: keep-with-next + thin brand rule underneath
    (pstyle("P4",
            '<style:paragraph-properties fo:margin-top="0.1965in" fo:margin-bottom="0in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="16pt" '
            'fo:font-weight="bold" officeooo:rsid="0012ffda" officeooo:paragraph-rsid="0012ffda" '
            'style:font-weight-asian="bold" style:font-weight-complex="bold"/>'),
     pstyle("P4",
            '<style:paragraph-properties fo:margin-top="0.1965in" fo:margin-bottom="0in" '
            'style:contextual-spacing="false"' + HEAD_RULE + '/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="16pt" '
            'fo:font-weight="bold" officeooo:rsid="0012ffda" officeooo:paragraph-rsid="0012ffda" '
            'style:font-weight-asian="bold" style:font-weight-complex="bold"/>')),
    (pstyle("P10",
            '<style:paragraph-properties fo:margin-top="0.1965in" fo:margin-bottom="0.0783in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="16pt" '
            'fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold"/>'),
     pstyle("P10",
            '<style:paragraph-properties fo:margin-top="0.1965in" fo:margin-bottom="0.0783in" '
            'style:contextual-spacing="false"' + HEAD_RULE + '/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="16pt" '
            'fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold"/>')),
    (pstyle("P17",
            '<style:paragraph-properties fo:margin-top="0.1965in" fo:margin-bottom="0in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="16pt" '
            'fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold"/>'),
     pstyle("P17",
            '<style:paragraph-properties fo:margin-top="0.1965in" fo:margin-bottom="0in" '
            'style:contextual-spacing="false"' + HEAD_RULE + '/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="16pt" '
            'fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold"/>')),
    (pstyle("P22",
            '<style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0.0591in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="16pt" '
            'fo:font-weight="bold" officeooo:rsid="00075029" officeooo:paragraph-rsid="00100b9d" '
            'style:font-weight-asian="bold" style:font-weight-complex="bold"/>'),
     pstyle("P22",
            '<style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0.0591in" '
            'style:contextual-spacing="false"' + HEAD_RULE + '/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="16pt" '
            'fo:font-weight="bold" officeooo:rsid="00075029" officeooo:paragraph-rsid="00100b9d" '
            'style:font-weight-asian="bold" style:font-weight-complex="bold"/>')),
    (pstyle("P24",
            '<style:paragraph-properties fo:margin-top="0.1965in" fo:margin-bottom="0in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="16pt" '
            'fo:font-weight="bold" officeooo:paragraph-rsid="00100b9d" '
            'style:font-weight-asian="bold" style:font-weight-complex="bold"/>'),
     pstyle("P24",
            '<style:paragraph-properties fo:margin-top="0.1965in" fo:margin-bottom="0in" '
            'style:contextual-spacing="false"' + HEAD_RULE + '/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="16pt" '
            'fo:font-weight="bold" officeooo:paragraph-rsid="00100b9d" '
            'style:font-weight-asian="bold" style:font-weight-complex="bold"/>')),
    # step headings: gray -> brand brown, keep-with-next
    (pstyle("P14",
            '<style:paragraph-properties fo:margin-top="0.1575in" fo:margin-bottom="0in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:color="#333333" loext:opacity="100%" fo:font-size="12.5pt" '
            'fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold"/>'),
     pstyle("P14",
            '<style:paragraph-properties fo:margin-top="0.1575in" fo:margin-bottom="0in" '
            'style:contextual-spacing="false" fo:keep-with-next="always"/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="12.5pt" '
            'fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold"/>')),
    (pstyle("P20",
            '<style:paragraph-properties fo:margin-top="0.1575in" fo:margin-bottom="0in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:color="#333333" loext:opacity="100%" fo:font-size="12.5pt" '
            'fo:font-weight="bold" officeooo:rsid="0008aa85" officeooo:paragraph-rsid="0008aa85" '
            'style:font-weight-asian="bold" style:font-weight-complex="bold"/>'),
     pstyle("P20",
            '<style:paragraph-properties fo:margin-top="0.1575in" fo:margin-bottom="0in" '
            'style:contextual-spacing="false" fo:keep-with-next="always"/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="12.5pt" '
            'fo:font-weight="bold" officeooo:rsid="0008aa85" officeooo:paragraph-rsid="0008aa85" '
            'style:font-weight-asian="bold" style:font-weight-complex="bold"/>')),
    # intro body P5: 11pt justified like the rest of the body
    ('<style:style style:name="P5" style:family="paragraph" style:parent-style-name="Standard">'
     '<style:text-properties officeooo:rsid="0012ffda" officeooo:paragraph-rsid="0012ffda"/></style:style>',
     pstyle("P5", BODY_PP,
            '<style:text-properties fo:font-size="11pt" officeooo:rsid="0012ffda" '
            'officeooo:paragraph-rsid="0012ffda"/>')),
    # figure paragraphs keep with their captions
    (pstyle("P7",
            '<style:paragraph-properties fo:text-align="center" style:justify-single-word="false"/>',
            '<style:text-properties fo:font-size="10pt"/>'),
     pstyle("P7",
            '<style:paragraph-properties fo:text-align="center" style:justify-single-word="false" '
            'fo:keep-with-next="always"/>',
            '<style:text-properties fo:font-size="10pt"/>')),
    # body P11 justified + airy
    (pstyle("P11",
            '<style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0.0591in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:font-size="11pt"/>'),
     pstyle("P11", BODY_PP, '<style:text-properties fo:font-size="11pt"/>')),
    # dash bullets: justified, hanging indent
    (pstyle("P15",
            '<style:paragraph-properties fo:margin-top="0.0311in" fo:margin-bottom="0.0311in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:font-size="11pt"/>'),
     pstyle("P15",
            '<style:paragraph-properties fo:margin-top="0.0311in" fo:margin-bottom="0.0311in" '
            'style:contextual-spacing="false" fo:line-height="140%" fo:text-align="justify" '
            'style:justify-single-word="false" fo:orphans="2" fo:widows="2" '
            'fo:margin-left="0.18in" fo:text-indent="-0.18in"/>',
            '<style:text-properties fo:font-size="11pt"/>')),
    # challenge line: centered brand callout
    (pstyle("P16",
            '<style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0.0591in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:font-size="11pt" officeooo:rsid="0008aa85" '
            'officeooo:paragraph-rsid="000dbabd"/>'),
     pstyle("P16",
            '<style:paragraph-properties fo:margin-top="0.12in" fo:margin-bottom="0.12in" '
            'style:contextual-spacing="false" fo:text-align="center" style:justify-single-word="false"/>',
            '<style:text-properties fo:color="#5b1f1f" loext:opacity="100%" fo:font-size="11pt" '
            'fo:font-style="italic" officeooo:rsid="0008aa85" officeooo:paragraph-rsid="000dbabd"/>')),
    (pstyle("P18",
            '<style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0.0591in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:font-size="11pt" officeooo:paragraph-rsid="00151fc7"/>'),
     pstyle("P18", BODY_PP,
            '<style:text-properties fo:font-size="11pt" officeooo:paragraph-rsid="00151fc7"/>')),
    (pstyle("P19",
            '<style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0.0591in" '
            'style:contextual-spacing="false"/>',
            '<style:text-properties fo:font-size="11pt" officeooo:rsid="00151fc7" '
            'officeooo:paragraph-rsid="00151fc7"/>'),
     pstyle("P19", BODY_PP,
            '<style:text-properties fo:font-size="11pt" officeooo:rsid="00151fc7" '
            'officeooo:paragraph-rsid="00151fc7"/>')),
    # 12pt stragglers -> unified 11pt justified body
    ('<style:style style:name="P21" style:family="paragraph" style:parent-style-name="Standard">'
     '<style:text-properties officeooo:paragraph-rsid="000ee8e2"/></style:style>',
     pstyle("P21", BODY_PP,
            '<style:text-properties fo:font-size="11pt" officeooo:paragraph-rsid="000ee8e2"/>')),
    ('<style:style style:name="P23" style:family="paragraph" style:parent-style-name="Standard">'
     '<style:text-properties officeooo:paragraph-rsid="001cbc50"/></style:style>',
     pstyle("P23", BODY_PP,
            '<style:text-properties fo:font-size="11pt" officeooo:paragraph-rsid="001cbc50"/>')),
    ('<style:style style:name="P25" style:family="paragraph" style:parent-style-name="Standard">'
     '<style:text-properties officeooo:paragraph-rsid="001d6c34"/></style:style>',
     pstyle("P25", BODY_PP,
            '<style:text-properties fo:font-size="11pt" officeooo:paragraph-rsid="001d6c34"/>')),
]

NEW_P26 = pstyle("P26", BODY_PP, '<style:text-properties fo:font-size="11pt"/>')

FOOTER_STYLE = ('<style:style style:name="Footer" style:family="paragraph" '
                'style:parent-style-name="Standard" style:class="extra">'
                '<style:paragraph-properties fo:text-align="center" '
                'style:justify-single-word="false"/><style:text-properties '
                'fo:color="#666666" loext:opacity="100%" fo:font-size="9pt"/></style:style>')


def replace_once(xml, old, new, label):
    n = xml.count(old)
    assert n == 1, f"{label}: found {n} occurrences, expected 1\n---\n{old[:200]}"
    return xml.replace(old, new)


def main():
    with zipfile.ZipFile(SRC) as zin:
        entries = [(i, zin.read(i.filename)) for i in zin.infolist()]

    content = next(d for i, d in entries if i.filename == "content.xml").decode("utf-8")
    styles = next(d for i, d in entries if i.filename == "styles.xml").decode("utf-8")

    # A. grammar
    for old, new in GRAMMAR:
        content = replace_once(content, old, new, f"grammar: {old[:60]!r}")

    # B1. style element rewrites
    for old, new in STYLE_REPLACEMENTS:
        content = replace_once(content, old, new, f"style: {old[30:60]!r}")

    # B2. new body style P26, inserted right after P25's element
    p25_el = next(new for old, new in STYLE_REPLACEMENTS if 'style:name="P25"' in new)
    content = replace_once(content, p25_el, p25_el + NEW_P26, "insert P26")

    # B3. non-table Standard paragraphs -> P26 (table cells keep theirs)
    parts = re.split(r"(<table:table .*?</table:table>)", content, flags=re.S)
    n_std = 0
    for k in range(0, len(parts), 2):
        n_std += parts[k].count('<text:p text:style-name="Standard"')
        parts[k] = parts[k].replace('<text:p text:style-name="Standard"',
                                    '<text:p text:style-name="P26"')
    assert n_std == 34, f"Standard->P26 reassignments: {n_std}, expected 34"
    content = "".join(parts)

    # B4. per-type table TB90: header row -> P12, body rows -> P13
    tb = re.search(r'<table:table table:name="TB90".*?</table:table>', content, re.S)
    block = tb.group(0)
    first_row_end = block.index("</table:table-row>")
    head, rest = block[:first_row_end], block[first_row_end:]
    assert head.count('<text:p text:style-name="Standard"') == 6
    assert rest.count('<text:p text:style-name="Standard"') == 30
    head = head.replace('<text:p text:style-name="Standard"', '<text:p text:style-name="P12"')
    rest = rest.replace('<text:p text:style-name="Standard"', '<text:p text:style-name="P13"')
    content = content.replace(block, head + rest)

    # B5. styles.xml: widow/orphan default, footer style, footer layout, master page
    styles = replace_once(
        styles,
        '<style:style style:name="Standard" style:family="paragraph" style:class="text"/>',
        '<style:style style:name="Standard" style:family="paragraph" style:class="text">'
        '<style:paragraph-properties fo:orphans="2" fo:widows="2"/></style:style>',
        "Standard widows")
    styles = replace_once(styles, "</office:automatic-styles>",
                          FOOTER_STYLE + "</office:automatic-styles>", "Footer style")
    styles = replace_once(
        styles, "<style:footer-style/>",
        '<style:footer-style><style:header-footer-properties svg:height="0.25in" '
        'fo:margin-top="0.08in"/></style:footer-style>', "footer-style")
    styles = replace_once(
        styles,
        '<style:master-page style:name="Standard" style:page-layout-name="Mpm1" '
        'draw:style-name="Mdp1"/>',
        '<style:master-page style:name="Standard" style:page-layout-name="Mpm1" '
        'draw:style-name="Mdp1"><style:footer><text:p text:style-name="Footer">'
        '<text:page-number text:select-page="current">1</text:page-number>'
        "</text:p></style:footer></style:master-page>", "master page footer")

    # ------------------------------------------------------------- write out
    out = []
    for info, data in entries:
        if info.filename == "content.xml":
            data = content.encode("utf-8")
        elif info.filename == "styles.xml":
            data = styles.encode("utf-8")
        out.append((info, data))

    with zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in out:
            zout.writestr(info, data)

    # ------------------------------------------------------------- validate
    with zipfile.ZipFile(DST) as z:
        assert z.testzip() is None
        for name in ("content.xml", "styles.xml"):
            ET.fromstring(z.read(name))
    print("zip + XML well-formed: OK")

    from odf.opendocument import load
    from odf import teletype
    from odf.text import P, H

    def paras(path):
        doc = load(path)
        return [teletype.extractText(el) for el in
                list(doc.text.getElementsByType(P)) + list(doc.text.getElementsByType(H))]

    v6, v7 = paras(SRC), paras(DST)
    assert len(v6) == len(v7) == 268, (len(v6), len(v7))
    d6 = re.findall(r"\d+(?:[.,]\d+)*", " ".join(v6))
    d7 = re.findall(r"\d+(?:[.,]\d+)*", " ".join(v7))
    assert sorted(d6) == sorted(d7), "digit tokens changed!"
    print("odfpy load: OK | 268 paragraphs | digit tokens identical to v6")

    def pics(path):
        with zipfile.ZipFile(path) as z:
            return {n: hashlib.sha256(z.read(n)).hexdigest()
                    for n in z.namelist() if n.startswith("Pictures/")}

    assert pics(SRC) == pics(DST), "Pictures differ!"
    print("Pictures byte-identical to v6: OK")

    print("\nchanged paragraphs (grammar pass):")
    for i, (a, b) in enumerate(zip(v6, v7)):
        if a != b:
            print(f"  [{i}]")
            print(f"    v6: {a[:140]}")
            print(f"    v7: {b[:140]}")


if __name__ == "__main__":
    main()
