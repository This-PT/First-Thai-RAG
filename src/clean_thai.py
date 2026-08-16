"""Clean text extracted from Thai PDFs so it is usable for RAG.

    python clean_thai.py text.txt --inspect    # see what is in the file
    python clean_thai.py text.txt              # writes text.clean.txt
    python clean_thai.py text.txt --force      # delete unmapped glyphs instead of failing

Every invisible character is written as a \\uXXXX escape on purpose: this file
survives being copied and pasted, which literal private-use characters do not.
"""
import re
import unicodedata

FFFD = "�"          # replacement char: the PDF had no mapping for a glyph
SARA_AM = "ำ"       # ำ
NIKHAHIT = "ํ"      # ํ
SARA_AA = "า"       # า

# Legacy DTP glyphs land in the private-use area U+F700-U+F71A.
PUA_MAP = {
    "": "่", "": "้", "": "๊",
    "": "๋", "": "์",
    "": "่", "": "้", "": "๊",
    "": "๋", "": "์",
    "": "่", "": "้", "": "๊",
    "": "๋", "": "์",
    "": "ญ",                              # ญ, no descender
    "": "ั", "": "ิ", "": "ี",
    "": "ึ", "": "ื",
    "": "่", "": "้", "": "๊",
    "": "๋", "": "์",
    "": "ฐ",                              # ฐ, no base
}
PUA_RE = re.compile("[-]")               # anything else in private use
INVISIBLE = ["­", "​", "‌", "﻿", " "]
BULLETS = ["ï", "•", "●"]             # symbol-font list markers
QUOTES = {"“": '"', "”": '"', "‘": "'", "’": "'"}


def fix_replacement_chars(text, strict=True):
    """Repair U+FFFD, which marks a glyph the PDF carried no ToUnicode entry for.

    In this document it is always part of sara am, which the font stores as
    นิคหิต + สระอา. Recompose it. Anything left over is real data loss, so
    raise rather than delete it silently.
    """
    text = re.sub(NIKHAHIT + FFFD + "?" + SARA_AA, SARA_AM, text)
    text = text.replace(SARA_AM + FFFD, SARA_AM)
    text = re.sub(FFFD + SARA_AA, SARA_AM, text)
    if FFFD in text:
        i = text.index(FFFD)
        if strict:
            raise ValueError(
                f"{text.count(FFFD)} unmapped glyph(s) not part of sara am; "
                f"first near: {text[max(0, i - 25):i + 25]!r}"
            )
        text = text.replace(FFFD, "")
    return text


def normalize_chars(text):
    for bad, good in PUA_MAP.items():
        text = text.replace(bad, good)
    text = PUA_RE.sub("", text)
    for ch in INVISIBLE + BULLETS:
        text = text.replace(ch, "")
    for bad, good in QUOTES.items():
        text = text.replace(bad, good)
    text = text.replace(NIKHAHIT + SARA_AA, SARA_AM)
    return unicodedata.normalize("NFC", text)


def to_paragraphs(text, drop_patterns=()):
    """A tab or 2+ spaces at line start marks a new paragraph in this layout."""
    drop = [re.compile(p) for p in drop_patterns]
    paras, buf = [], []

    def flush():
        if buf:
            paras.append(" ".join(buf))
            buf.clear()

    for raw_line in text.split("\n"):
        starts_para = bool(re.match(r"[\t ]{2,}|\t", raw_line))
        line = re.sub(r"[\t ]+", " ", raw_line).strip()
        if not line:
            flush()
            continue
        if any(p.fullmatch(line) for p in drop):
            continue
        if starts_para:
            flush()
        if buf and buf[-1].endswith("-"):
            buf[-1] = buf[-1][:-1] + line              # rejoin hyphen split
        else:
            buf.append(line)
    flush()
    return paras


# Noise to delete: page markers, running header, bare page numbers, section marks
DEFAULT_DROP = [
    r"--- page \d+ ---",
    r"100 ปี สงครามโลกครั้งที่ 1 ?\d*",
    r"\d{1,3}",
    r"~\d+~",
]


def clean(text, drop_patterns=DEFAULT_DROP, strict=True):
    text = fix_replacement_chars(text, strict=strict)
    return "\n\n".join(to_paragraphs(normalize_chars(text), drop_patterns))


def inspect(text):
    """Report every non-ASCII character outside the standard Thai block."""
    import collections
    counts = collections.Counter(
        ch for ch in text
        if not ch.isascii() and not ("฀" <= ch <= "๿")
    )
    for ch, n in counts.most_common(40):
        try:
            name = unicodedata.name(ch)
        except ValueError:
            name = "<private use / unnamed>"
        print(f"U+{ord(ch):04X}  x{n:<6} {name}")
    print(f"tabs: {text.count(chr(9))}   lines: {text.count(chr(10)) + 1}")


if __name__ == "__main__":
    import pathlib
    import sys

    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    src = pathlib.Path(args[0] if args else "text.txt")
    raw = src.read_text(encoding="utf-8")

    if "--inspect" in sys.argv:
        inspect(raw)
    else:
        out = src.with_name(src.stem + ".clean.txt")
        cleaned = clean(raw, strict="--force" not in sys.argv)
        out.write_text(cleaned, encoding="utf-8")
        print(f"wrote {out}  ({len(cleaned)} chars, "
              f"{cleaned.count(chr(10) * 2) + 1} paragraphs)")
