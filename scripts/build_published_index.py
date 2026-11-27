#!/usr/bin/env python3
"""Step 1 (tools box, has the tools CLI): python3 scripts/build_published_index.py --dump /tmp/dedup_raw.json
   then `tools workspace put --path /tmp/dedup_raw.json`.
   Step 2 (anywhere): python3 scripts/build_published_index.py --build /tmp/dedup_raw.json  -> queue/published_index.json"""
import json, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
S = "1ub02alNk9U-0k5WtWyjwhTFQY7SF22nNEPfjLRlTsvA"

def read(rng):
    o = subprocess.run(["tools","google-sheets","read-range","--account-id","priyans1532@gmail.com","--spreadsheet-id",S,"--range",rng,"--include","values","--json"],capture_output=True,text=True,check=True).stdout
    return json.loads(o)["values"]

if sys.argv[1] == "--dump":
    json.dump({"published": read("Published Shorts!A2:E600"), "ledger": read("Source Ledger!A2:F900")}, open(sys.argv[2], "w"))
else:
    from clipper.dedup import build_entries, INDEX_PATH
    raw = json.load(open(sys.argv[2]))
    e = build_entries(raw["published"], [(i, r) for i, r in enumerate(raw["ledger"], start=2)])
    INDEX_PATH.write_text(json.dumps({"generated_at_epoch": time.time(), "entries": e}))
    print("slugs", len(e))
