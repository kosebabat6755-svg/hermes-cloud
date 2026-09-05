#!/usr/bin/env python3
"""Push changed files under HERMES_HOME to the state branch every ~2 min.

v2 — fixes v1's fatal flaw: contents-API PUT with branch=state 404s forever
when the state branch doesn't exist (and hash-marker files live on that same
missing branch, so the "unchanged?" check also 404s → looks unchanged-free
and pushes nothing... and any push that DID fire would have failed silently).

v3 (2026-09-04): size cap 8MB→50MB (state.db hit the old cap and was silently skipped —
     chat history lost on every reset), + push sqlite -wal/-shm sidecars so the newest
     messages survive, + loud SKIP-SIZE logging instead of silent drops.

v2 approach (pure API, no git binary needed):
  1. Ensure state branch exists: GET ref/heads/state; if 404, create it
     from the current main head SHA (empty-ish starting point is fine).
  2. Maintain an in-memory + remote manifest of pushed file hashes
     (state/hermes-home/.manifest.json committed to the state branch).
  3. For changed/new files: blob → tree (based on latest state head) →
     commit → move ref. Batched per cycle = ONE commit per cycle, not
     per file (keeps commit noise low).
Skips .env, caches, big files. Secrets never touch the branch.
"""
import os, sys, time, base64, json, urllib.request, urllib.error, hashlib

REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]
BRANCH = "state"
STATE_ROOT = os.environ["HERMES_HOME"]
INTERVAL = int(os.environ.get("STATE_PUSH_INTERVAL", "2"))
API = f"https://api.github.com/repos/{REPO}"
PREFIX = "hermes-home"          # state branch will hold: hermes-home/<rel>
MANIFEST = ".manifest.json"

def gh(method, path, payload=None):
    req = urllib.request.Request(f"{API}/{path}", method=method,
        data=json.dumps(payload).encode() if payload else None,
        headers={"Authorization": f"Bearer {TOKEN}",
                 "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

SKIP_DIRS = {"__pycache__", ".cache", "node_modules", "request_dumps", "tmp", "crashes"}
SKIP_FILES = {".env", "gateway.log", "nohup.out"}
PUSHABLE_EXT = {".db", ".db-wal", ".db-shm", ".json", ".yaml", ".yml", ".md", ".txt", ".jsonl", ".skill"}
SIZE_CAP = 50 * 1024 * 1024  # 50MB — state.db crossed the old 8MB cap and was silently
                             # skipped for hours = the "chat history reverts at reset" bug (2026-09-04)

def iter_files():
    for root, dirs, files in os.walk(STATE_ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f in SKIP_FILES or not any(f.endswith(e) for e in PUSHABLE_EXT):
                continue
            p = os.path.join(root, f)
            try:
                sz = os.path.getsize(p)
                if sz > SIZE_CAP:
                    print(f"[pusher] SKIP-SIZE {f} ({sz} bytes > {SIZE_CAP})", flush=True)
                    continue
                with open(p, "rb") as fh:
                    yield os.path.relpath(p, STATE_ROOT).replace(os.sep, "/"), fh.read()
            except OSError:
                continue

def ensure_branch():
    st, _ = gh("GET", f"git/ref/heads/{BRANCH}")
    if st == 200:
        return
    # create from current default head
    st, main = gh("GET", "git/ref/heads/main")
    parent = main["object"]["sha"] if st == 200 else None
    if parent:
        st, c = gh("GET", f"git/commits/{parent}")
        tree = c["tree"]["sha"]
        st, nc = gh("POST", "git/commits", {"message": "init state branch", "tree": tree, "parents": [parent]})
        st, _ = gh("POST", "git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": nc["sha"]})
    else:
        # empty repo fallback: bare commit
        st, tree = gh("POST", "git/trees", {"tree": []})
        st, nc = gh("POST", "git/commits", {"message": "init state branch", "tree": tree["sha"], "parents": []})
        st, _ = gh("POST", "git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": nc["sha"]})
    print(f"[pusher] created {BRANCH} branch ({st})")

def get_manifest(head):
    st, d = gh("GET", f"contents/{PREFIX}/{MANIFEST}?ref={BRANCH}")
    if st == 200:
        try:
            return json.loads(base64.b64decode(d["content"]).decode())
        except Exception:
            return {}
    return {}

def push_cycle():
    ensure_branch()
    st, ref = gh("GET", f"git/ref/heads/{BRANCH}")
    if st != 200:
        print("[pusher] cannot resolve state branch head"); return 0
    head = ref["object"]["sha"]
    st, c = gh("GET", f"git/commits/{head}")
    base_tree = c["tree"]["sha"]
    manifest = get_manifest(head)

    # collect changed files
    changes = []
    for rel, data in iter_files():
        digest = hashlib.sha256(data).hexdigest()
        if manifest.get(rel) == digest:
            continue
        st, blob = gh("POST", "git/blobs", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
        if st in (200, 201):
            changes.append((rel, blob["sha"], digest))
    if not changes:
        return 0

    # build tree entries on top of base_tree (fetch base tree items to avoid clobber)
    st, bt = gh("GET", f"git/trees/{base_tree}?recursive=1")
    items = []
    if st == 200:
        for it in bt.get("tree", []):
            if it["type"] == "blob" and it["path"].startswith(PREFIX + "/"):
                items.append({"path": it["path"], "mode": "100644", "type": "blob", "sha": it["sha"]})
    path_set = {i["path"] for i in items}
    for rel, bsha, digest in changes:
        p = f"{PREFIX}/{rel}"
        if p in path_set:
            for i in items:
                if i["path"] == p:
                    i["sha"] = bsha
        else:
            items.append({"path": p, "mode": "100644", "type": "blob", "sha": bsha})
        manifest[rel] = digest

    # manifest itself as a blob
    mdata = json.dumps(manifest).encode()
    st, mblob = gh("POST", "git/blobs", {"content": base64.b64encode(mdata).decode(), "encoding": "base64"})
    mp = f"{PREFIX}/{MANIFEST}"
    if mp in path_set:
        for i in items:
            if i["path"] == mp:
                i["sha"] = mblob["sha"]
    else:
        items.append({"path": mp, "mode": "100644", "type": "blob", "sha": mblob["sha"]})

    st, tree = gh("POST", "git/trees", {"tree": items, "base_tree": base_tree})
    if st not in (200, 201):
        print(f"[pusher] tree fail: {st} {json.dumps(tree)[:200]}", file=sys.stderr); return 0
    st, commit = gh("POST", "git/commits",
                    {"message": f"state-sync: {len(changes)} files", "tree": tree["sha"], "parents": [head]})
    if st not in (200, 201):
        print(f"[pusher] commit fail: {st}", file=sys.stderr); return 0
    st, _ = gh("PATCH", f"git/refs/heads/{BRANCH}", {"sha": commit["sha"], "force": False})
    if st in (200, 201):
        print(f"[pusher] pushed {len(changes)} files → {BRANCH} @ {commit['sha'][:8]}")
        return len(changes)
    print(f"[pusher] ref update fail ({st}) — race? retry next cycle", file=sys.stderr)
    return 0

def main():
    print(f"[pusher] v2 watching {STATE_ROOT} → {BRANCH} every {INTERVAL}m", flush=True)
    time.sleep(45)
    idle = 0
    while True:
        try:
            n = push_cycle()
            idle = 0 if n else idle + 1
            if idle and idle % 15 == 0:
                print(f"[pusher] idle x{idle} (nothing new)", flush=True)
        except Exception as e:
            print(f"[pusher] cycle error: {e}", file=sys.stderr, flush=True)
        time.sleep(INTERVAL * 60)

if __name__ == "__main__":
    main()
