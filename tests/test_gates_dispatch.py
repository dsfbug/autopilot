"""Fail-closed tests for the upload chokepoint. Never uploads: youtube.upload_clip is stubbed."""
import copy
import sys
from pathlib import Path
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json as _j, os as _o, tempfile as _t, time as _tm  # dedup has its own tests; give these gate tests a fresh empty index
_ip = Path(_t.mkdtemp()) / "idx.json"; _ip.write_text(_j.dumps({"generated_at_epoch": _tm.time(), "entries": {}})); _o.environ["CLIPPER_DEDUP_INDEX"] = str(_ip)
from clipper.upload import dispatcher  # noqa: E402

CFG = yaml.safe_load(Path(__file__).resolve().parent.parent.joinpath("config.yaml").read_text())
import subprocess as _sp
_FX = Path(_t.mkdtemp())

def _mk(name, size, secs):
    f = _FX / name
    _sp.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=%s:rate=30:duration=%s" % (size, secs),
             "-f", "lavfi", "-i", "sine=frequency=440:duration=%s" % secs, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(f)], check=True)
    return str(f)

# Self-contained temporary fixtures (generated, not dependent on /downloads); optional CLI paths still override.
CLIP_FILE = sys.argv[1] if len(sys.argv) > 1 else _mk("good_final.mp4", "1080x1920", 20)
BAD_FILE = sys.argv[2] if len(sys.argv) > 2 else _mk("bad_final.mp4", "640x360", 40)

GOOD = {
    "id": "t1", "processed_path": CLIP_FILE + "", "title": "Tminnzy pressed the wrong button 💀",
    "streamer": "Tminnzy", "url": "https://www.twitch.tv/tminnzy/clip/PatientSweetMilkArgieB8-usdfKujw8E2OZHUm",
    "anchor_note": "Clear Skies mission subtitle",
    "content_review": {"approved": True, "evidence_url": "https://gameta.gg/gta6/missions/clear-skies/", "reviewer": "frames checked by a person"},
}


def run(clip, cfg=CFG):
    called = []
    with mock.patch("clipper.upload.youtube.upload_clip", side_effect=lambda *a, **k: called.append(1) or "STUB_ID"):
        out = dispatcher.upload_clip(clip, cfg, privacy="private")
    return out, bool(called), clip.get("_upload_error_message")


def case(name, mutate, expect_upload):
    c = copy.deepcopy(GOOD); mutate(c)
    out, called, msg = run(c)
    ok = (called == expect_upload)
    print(("PASS" if ok else "FAIL"), name, "| reached uploader:", called, "|", (msg or "")[:110])
    return ok


r = [
    case("good clip passes through", lambda c: None, True),
    case("no content_review", lambda c: c.pop("content_review"), False),
    case("review not approved", lambda c: c["content_review"].update(approved=False), False),
    case("review without evidence url", lambda c: c["content_review"].pop("evidence_url"), False),
    case("review without reviewer", lambda c: c["content_review"].pop("reviewer"), False),
    case("missing anchor_note", lambda c: c.pop("anchor_note"), False),
    case("missing creator", lambda c: c.pop("streamer"), False),
    case("missing source url", lambda c: c.pop("url"), False),
    case("file does not exist", lambda c: c.update(processed_path="/nope/x_final.mp4"), False),
    case("wrong size and length", lambda c: c.update(processed_path=BAD_FILE), False),
]
off = copy.deepcopy(CFG); off["publish_gates"]["enforce"] = False
c = copy.deepcopy(GOOD); c.pop("content_review")
out, called, _ = run(c, off)
print("PASS" if called else "FAIL", "enforce:false lets it through (explicit opt-out) | reached uploader:", called); r.append(called)
sys.exit(0 if all(r) else 1)
