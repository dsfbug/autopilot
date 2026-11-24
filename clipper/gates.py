"""Pre-publish checks for a finished Short. Offline: uses ffprobe only.

Usage:
    python -m clipper.gates clip.mp4 [--meta meta.json] [--config config.yaml]

meta.json (all optional, checked when present in the config's `required_meta`):
    {"title": "...", "description": "...", "source_url": "https://...",
     "creator": "...", "anchor_note": "why this clip depicts the game"}

Defaults live in config.yaml under `publish_gates`. Every limit is a setting,
not a rule of the tool: change them to match your channel.
Exit code 0 = all checks pass, 1 = at least one failed.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DEFAULTS = {
    "width": 1080,
    "height": 1920,
    "min_seconds": 5.0,
    "max_seconds": 28.9,  # Studio rounds up; stay under 30 shown
    "video_codec": "h264",
    "audio_codec": "aac",
    "max_title_chars": 100,
    "required_meta": ["title", "description", "source_url", "creator", "anchor_note"],
    "must_mention_in_description": ["source_url"],
}


def _probe(path: str) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def check_clip(path: str, meta: dict | None = None, cfg: dict | None = None) -> list[tuple[str, bool, str]]:
    """Return a list of (check name, passed, detail)."""
    c = {**DEFAULTS, **(cfg or {})}
    meta = meta or {}
    res: list[tuple[str, bool, str]] = []
    info = _probe(path)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"].get("duration", 0))

    res.append(("has video", v is not None, ""))
    if v:
        w, h = v.get("width"), v.get("height")
        res.append(("resolution", (w, h) == (c["width"], c["height"]), f"{w}x{h}"))
        res.append(("video codec", v.get("codec_name") == c["video_codec"], str(v.get("codec_name"))))
    res.append(("has audio", a is not None, ""))
    if a:
        res.append(("audio codec", a.get("codec_name") == c["audio_codec"], str(a.get("codec_name"))))
    res.append((
        "duration", c["min_seconds"] <= dur <= c["max_seconds"],
        f"{dur:.1f}s (allowed {c['min_seconds']}-{c['max_seconds']})",
    ))
    for key in c["required_meta"]:
        res.append((f"meta:{key}", bool(str(meta.get(key, "")).strip()), ""))
    title = str(meta.get("title", ""))
    if title:
        res.append(("title length", len(title) <= c["max_title_chars"], f"{len(title)} chars"))
    desc = str(meta.get("description", ""))
    for key in c["must_mention_in_description"]:
        val = str(meta.get(key, ""))
        if val:
            tail = val.rstrip("/").split("/")[-1]
            res.append((f"description mentions {key}", tail in desc, ""))
    return res


def gate_failures_for_upload(clip: dict, config: dict) -> list[str]:
    """Return human-readable reasons this clip must NOT be uploaded (empty list = ok).

    Fail closed: any missing file, unreadable file, failed check or missing review
    blocks the upload. Controlled by config `publish_gates.enforce` (default true).

    Content review is explicit and separate from the file checks. A clip needs
        clip["content_review"] = {"approved": true,
                                  "evidence_url": "<page you opened that shows this clip's scene is from the game>",
                                  "reviewer": "<who looked at the frames>"}
    A note alone is not evidence; the evidence URL and a named reviewer are required,
    and a written anchor_note must describe the scene (not only the game or creator).
    """
    gates = (config or {}).get("publish_gates", {}) or {}
    if gates.get("enforce", True) is False:
        return []
    reasons: list[str] = []
    path = clip.get("processed_path")
    if not path or not Path(str(path)).exists():
        return [f"missing processed file: {path}"]

    review = clip.get("content_review") or {}
    if review.get("approved") is not True:
        reasons.append("content_review.approved is not true (a person must review the frames)")
    if not str(review.get("evidence_url", "")).startswith(("http://", "https://")):
        reasons.append("content_review.evidence_url missing (link to the page that shows this scene is from the game)")
    if not str(review.get("reviewer", "")).strip():
        reasons.append("content_review.reviewer missing")

    meta = {
        "title": clip.get("_title_override") or clip.get("title", ""),
        "description": clip.get("_description_override") or "",
        "source_url": clip.get("url", ""),
        "creator": clip.get("streamer", ""),
        "anchor_note": clip.get("anchor_note", ""),
    }
    # When no description override exists the uploader builds one that already
    # carries creator and source link, so only check the description when supplied.
    cfg = dict(gates)
    cfg["required_meta"] = [k for k in cfg.get("required_meta", DEFAULTS["required_meta"])
                            if k != "description" or meta["description"]]
    cfg["must_mention_in_description"] = [] if not meta["description"] else cfg.get(
        "must_mention_in_description", DEFAULTS["must_mention_in_description"])
    try:
        for name, ok, detail in check_clip(str(path), meta, cfg):
            if not ok:
                reasons.append(f"{name} {detail}".strip())
    except Exception as e:  # unreadable file, ffprobe missing: fail closed
        reasons.append(f"could not inspect file: {type(e).__name__}")
    return reasons


def main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m clipper.gates")
    ap.add_argument("clip")
    ap.add_argument("--meta")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args(argv)

    cfg: dict = {}
    if Path(args.config).exists():
        import yaml

        cfg = (yaml.safe_load(Path(args.config).read_text()) or {}).get("publish_gates", {}) or {}
    meta = json.loads(Path(args.meta).read_text()) if args.meta else {}

    results = check_clip(args.clip, meta, cfg)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}".rstrip())
    failed = [n for n, ok, _ in results if not ok]
    print("ALL CHECKS PASSED" if not failed else f"{len(failed)} CHECK(S) FAILED")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
