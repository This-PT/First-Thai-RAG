import re

COMBINING = "ั-ฺ็-๎"     # Thai marks that must stay with their base


def _safe_cut(text, i):
    """Move a cut point off a combining mark and onto a space if one is near."""
    while i < len(text) and re.match(f"[{COMBINING}]", text[i]):
        i += 1
    space = text.rfind(" ", max(0, i - 120), i)
    return space + 1 if space > 0 else i


def _hard_split(para, max_chars):
    out = []
    while len(para) > max_chars:
        cut = _safe_cut(para, max_chars)
        out.append(para[:cut].strip())
        para = para[cut:]
    if para.strip():
        out.append(para.strip())
    return out


def split_thai(text, max_chars=1200, overlap_paras=1):
    paras = [p for p in text.split("\n\n") if p.strip()]
    chunks, buf = [], []
    for para in paras:
        for piece in (_hard_split(para, max_chars) if len(para) > max_chars else [para]):
            if buf and sum(len(b) for b in buf) + len(piece) > max_chars:
                chunks.append("\n\n".join(buf))
                tail = buf[-overlap_paras:] if overlap_paras else []
                # only carry context forward if it is genuinely small
                buf = tail if sum(len(t) for t in tail) < max_chars // 3 else []
            buf.append(piece)
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks
