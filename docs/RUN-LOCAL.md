# Running Alma locally — no Docker, no venv

The storefront and the backend run directly on the machine: Node for
`next dev`, a system Python 3.12+ for uvicorn. Nothing here needs a
container, and the backend's dependencies install fine into the
interpreter itself when an isolated environment is not wanted.

**Production is a different document.** `docs/DEPLOY.md` is the one with
the container, the Postgres, the TLS and the timers; nothing on this page
is meant to face the internet. The two differ on purpose: what makes a
laptop pleasant — SQLite in a file, no keys, one process — is exactly what
production refuses to start on (`config.check_production_ready`).

## Backend

```bash
python -m pip install -e backend            # Python 3.12+ (pyproject requires it)
cp backend/.env.example backend/.env.local  # dev defaults boot as-is
python -m uvicorn alma.api.app:app --port 8000   # run from backend/
```

`GET /ready` lists what it checked: the database, the ephemeris, the
places index, the model key and the billing credentials. On a fresh
checkout the last two are empty, so **it answers `ready: false`, and that
is the correct answer** — readiness means the service can do what it
promises, and without a model key nothing that sells works. Nothing is
blocked by it: every calculation runs, and `/health` (which is what the
container and the load balancer actually probe) stays `ok`.

`missing` names what to fill in. That detail is served only in a local
sandbox; in production the same route answers a single boolean, because a
list of unset secrets is a map for whoever is looking for a way in.

## Storefront

```bash
npm install
npm run dev        # port 3000
```

The API address defaults to `http://localhost:8000`. When that port is
taken (or the backend runs elsewhere), point the storefront at it once:

```
# .env.local in the repo root
NEXT_PUBLIC_ALMA_API=http://localhost:8100
```

and add the storefront's own origin to `ALMA_CORS_ORIGINS` in
`backend/.env.local` — the browser enforces this, not the server, and
the symptom of forgetting it is a working backend that the page cannot
reach.

## One Windows trap worth its own paragraph

Start `next dev` from the directory spelled with the **casing the disk
uses** (`Desktop`, not `desktop`). NTFS treats the two as the same
folder; webpack does not, and a dev server started from the wrong-case
path bundles two copies of Next's client runtime. The visible failure is
`invariant expected app router to be mounted` on every page — nowhere
near the actual cause. `Get-Item` on the folder shows the true casing.
