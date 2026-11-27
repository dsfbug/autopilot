"""Dedup gate tests (stdlib only; run: python tests/test_dedup.py). Never uploads."""
import json, sys, tempfile, time, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from clipper.dedup import dedup_failures  # noqa: E402
from clipper.upload import dispatcher  # noqa: E402

BASE = "PatientSweetMilkArgieB8-usdfKujw8E2OZHUm"
E = {BASE.lower(): ["PUBLISHED MASsCMKvArU", "PUBLISHED 9akYc1VqTCw"], "knottyclumsypepperpogchamp-ymfyotajgbsmpt5": ["PUBLISHED qydGh2Bqr6A"]}

def mk(entries, age=0, raw=None):
    p = Path(tempfile.mkdtemp()) / "i.json"
    p.write_text(raw if raw is not None else json.dumps({"generated_at_epoch": time.time() - age, "entries": entries}))
    return p

def u(s): return {"source_url": "https://www.twitch.tv/x/clip/" + s}

class B(unittest.TestCase):
    def test_reject_blocks_until_reassessed(self):
        from clipper.dedup import build_entries
        L = lambda n, v, u: (n, [u, "c", "d", "l", v, "r"])
        U = "https://www.twitch.tv/a/clip/OldRej-1"
        self.assertIn("oldrej-1", build_entries([], [L(2, "REJECT", U)]))
        self.assertNotIn("oldrej-1", build_entries([], [L(2, "REJECT", U), L(9, "REASSESS: length rule was mine", U)]))
        self.assertIn("oldrej-1", build_entries([], [L(2, "REJECT", U), L(9, "REASSESS", U), L(12, "REJECT", U)]))
    def test_published_never_lifted(self):
        from clipper.dedup import build_entries
        U = "https://www.twitch.tv/a/clip/Pub-1"
        e = build_entries([["VID1", "", "", U]], [(2, [U, "", "", "", "REASSESS", ""])])
        self.assertIn("pub-1", e)
        e = build_entries([], [(2, [U, "", "", "", "PUBLISHED x", ""]), (3, [U, "", "", "", "REASSESS", ""])])
        self.assertIn("pub-1", e)
    def test_skip_hold_eligible(self):
        from clipper.dedup import build_entries
        U = "https://www.twitch.tv/a/clip/Sk-1"
        self.assertNotIn("sk-1", build_entries([], [(2, [U, "", "", "", "SKIP", ""])]))
        self.assertNotIn("sk-1", build_entries([], [(2, [U, "", "", "", "HOLD", ""])]))

class T(unittest.TestCase):
    def test_exact(self): self.assertTrue(dedup_failures(u(BASE), mk(E)))
    def test_case_query(self): self.assertTrue(dedup_failures(u(BASE.lower() + "?filter=clips&range=7d"), mk(E)))
    def test_no_prefix_substring_false_positive(self):
        for s in (BASE[:25], BASE + "ZZ", "Different" + BASE, BASE[3:]):
            self.assertEqual(dedup_failures(u(s), mk(E)), [])
    def test_new_allowed(self): self.assertEqual(dedup_failures(u("BrandNewSlugNotSeen-abc"), mk(E)), [])
    def test_missing_index(self): self.assertTrue(dedup_failures(u("Abc"), Path(tempfile.mkdtemp()) / "no.json"))
    def test_stale_index(self): self.assertTrue(dedup_failures(u("Abc"), mk(E, age=7 * 3600)))
    def test_corrupt_index(self): self.assertTrue(dedup_failures(u("Abc"), mk(E, raw="{not json")))
    def test_no_source(self):
        self.assertTrue(dedup_failures({}, mk(E)))
        self.assertTrue(dedup_failures({"source_url": "https://youtube.com/watch?v=1"}, mk(E)))
    def test_upload_path_invokes_gate(self):
        called = []
        mod = type("M", (), {"upload_clip": staticmethod(lambda *a, **k: called.append(1) or "VID")})
        with mock.patch("clipper.dedup.INDEX_PATH", mk(E)), mock.patch.object(dispatcher, "_ensure_formatted", lambda c, cfg: c), \
             mock.patch("clipper.gates.gate_failures_for_upload", lambda c, cfg: []), \
             mock.patch.object(dispatcher, "get_channel_platform", lambda ch, cfg: "youtube"), \
             mock.patch.object(dispatcher, "_get_module", lambda p: mod):
            dup = u(BASE)
            self.assertIsNone(dispatcher.upload_clip(dup, {}, privacy="public"))
            self.assertFalse(called)
            self.assertEqual(dup["_upload_error_reason"], "publish_gate_failed")
            self.assertEqual(dispatcher.upload_clip(u("NewOne-1"), {}, privacy="public"), "VID")
            self.assertTrue(called)

if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
