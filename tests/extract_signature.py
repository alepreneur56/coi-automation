"""
extract_signature.py — one-shot helper.

Polls the admin inbox via Graph for the most recent message whose subject
contains 'SIGNATURE SAMPLE', strips everything before the signature (the
body should be empty anyway), and writes the raw HTML to signature.html.

Usage: .venv/bin/python tests/extract_signature.py [--timeout 600]
"""

import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from graph_client import GraphClient


def find_sample(graph):
    msgs = graph.list_inbox_since("2000-01-01T00:00:00Z", top=25)
    candidates = [
        m for m in msgs
        if "signature sample" in (m.get("subject") or "").lower()
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda m: m.get("receivedDateTime") or "")[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    graph = GraphClient()
    deadline = time.time() + args.timeout
    msg = None
    while time.time() < deadline:
        msg = find_sample(graph)
        if msg:
            break
        time.sleep(15)

    if not msg:
        print("TIMEOUT: no SIGNATURE SAMPLE email found")
        return 1

    html = (msg.get("body") or {}).get("content") or ""
    if not html.strip():
        print("Found the email but body is empty?")
        return 1

    out = os.path.join(config.BASE_DIR, "signature_raw.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"Found: {msg.get('subject')!r} from "
          f"{msg.get('from', {}).get('emailAddress', {}).get('address')}")
    print(f"Raw body saved to: {out}  ({len(html):,} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
