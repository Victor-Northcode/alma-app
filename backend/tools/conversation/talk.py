"""Talk to Alma over the live backend. One guest account per (up to 3) turns."""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import uuid

BASE = "http://127.0.0.1:8018"
BIRTH = {
    "birth_date": "1990-06-14",
    "birth_time": "09:25",
    "latitude": 55.7558,
    "longitude": 37.6173,
    "timezone": "Europe/Moscow",
    "place_label": "Moscow, Russia",
    "name": "Test",
    "is_self": True,
}


def call(method: str, path: str, body=None, token=None, anon=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("content-type", "application/json")
    if token:
        req.add_header("authorization", f"Bearer {token}")
    if anon:
        req.add_header("x-alma-anon", anon)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}


def new_account():
    anon = uuid.uuid4().hex
    st, s = call("GET", "/v1/auth/session", anon=anon)
    tok = s["token"]
    st, p = call("POST", "/v1/profiles", BIRTH, token=tok)
    if st >= 300:
        print("profile failed", st, p, file=sys.stderr)
        sys.exit(1)
    return tok


def run(cases, out_path):
    """cases: list of dicts {id, turns:[{msg, locale}]}"""
    log = []
    for case in cases:
        tok = new_account()
        thread = None
        for turn in case["turns"]:
            body = {"message": turn["msg"], "locale": turn.get("locale", "en")}
            if thread and not turn.get("fresh"):
                body["thread_id"] = thread
            t0 = time.time()
            st, r = call("POST", "/v1/chat", body, token=tok)
            dt = round(time.time() - t0, 1)
            entry = {
                "case": case["id"],
                "sent": turn["msg"],
                "locale": turn.get("locale", "en"),
                "status": st,
                "seconds": dt,
            }
            if st == 200:
                thread = r["thread_id"]
                m = r["message"]
                entry["body"] = m["body"]
                entry["cited"] = m["cited_factors"]
                entry["answered_from_chart"] = m["answered_from_chart"]
            else:
                entry["error"] = r
            log.append(entry)
            print(json.dumps(entry, ensure_ascii=False)[:400], flush=True)
    with open(out_path, "a") as f:
        for e in log:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    cases = json.load(open(sys.argv[1]))
    run(cases, sys.argv[2])
