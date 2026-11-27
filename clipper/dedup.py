"""Fail-closed duplicate-source gate for uploads.

The index (queue/published_index.json) is built from the tracker's Published Shorts
and Source Ledger tabs by scripts/build_published_index.py and holds one entry per
Twitch clip slug. Matching is exact on the slug (case-insensitive). No prefix or
substring matching, so unrelated slugs can never collide.
"""
import json, os, re, time
from pathlib import Path

INDEX_PATH = Path(os.environ.get("CLIPPER_DEDUP_INDEX", Path(__file__).resolve().parent.parent / "queue" / "published_index.json"))
MAX_AGE_S = int(os.environ.get("CLIPPER_DEDUP_MAX_AGE_S", 6 * 3600))
_SLUG = re.compile(r"clip/([A-Za-z0-9_-]+)")


def slug_of(text):
    m = _SLUG.search(text or "")
    return m.group(1).lower() if m else None


def dedup_failures(clip, index_path=None, now=None):
    """Return a list of block reasons. Empty list means the clip may upload."""
    p = Path(index_path or INDEX_PATH)
    if not p.exists():
        return ["dedup index missing: run scripts/build_published_index.py"]
    try:
        idx = json.loads(p.read_text())
        entries = idx["entries"]
        gen = float(idx["generated_at_epoch"])
    except Exception as e:  # corrupt index fails closed
        return ["dedup index unreadable: %s" % type(e).__name__]
    if (now or time.time()) - gen > MAX_AGE_S:
        return ["dedup index stale (older than %ds): rebuild before upload" % MAX_AGE_S]
    src = clip.get("source_url") or clip.get("url") or ""
    s = slug_of(src)
    if not s:
        return ["no Twitch clip slug in source_url: cannot dedup"]
    hit = entries.get(s)
    if hit:
        return ["duplicate source already in history: %s" % "; ".join(hit)]
    return []


BLOCK_STICKY = ("PUBLISHED", "DUPLICATE")  # never lifted by a later ledger row
BLOCK_REVERSIBLE = ("REJECT",)  # lifted only by a LATER ledger row for the same slug, e.g. "REASSESS: reason"


def build_entries(published_rows, ledger_rows):
    """published_rows: [[video_id, ..., source_url, ...]] (cells A:E). ledger_rows: [(row_number, [A..F])] in sheet order.
    Published tab entries always block. Ledger PUBLISHED/DUPLICATE always block. A ledger REJECT blocks only while it is
    the latest verdict for that slug; a later row (any other verdict, e.g. REASSESS, ELIGIBLE, SKIP) is a documented
    reassessment that reopens it. History is never edited, only appended."""
    entries, latest = {}, {}
    for r in published_rows:
        for c in r[:5]:
            s = slug_of(str(c))
            if s:
                entries.setdefault(s, []).append("PUBLISHED " + str(r[0]))
    for n, r in ledger_rows:
        verdict = (r[4] if len(r) > 4 else "").strip().upper()
        s = None
        for c in r[:6]:
            s = s or slug_of(str(c))
        if not s:
            continue
        if verdict.startswith(BLOCK_STICKY):
            entries.setdefault(s, []).append("LEDGER row %d %s" % (n, verdict[:40]))
        latest[s] = (n, verdict)
    for s, (n, v) in latest.items():
        if v.startswith(BLOCK_REVERSIBLE):
            entries.setdefault(s, []).append("LEDGER row %d %s" % (n, v[:40]))
    return entries
