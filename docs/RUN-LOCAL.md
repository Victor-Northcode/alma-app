# Running Alma locally — no Docker, no venv

The storefront and the backend run directly on the machine: Node for
`next dev`, a system Python 3.12+ for uvicorn. Nothing here needs a
container, and the backend's dependencies install fine into the
interpreter itself when an isolated environment is not wanted.

## Backend

```bash
python -m pip install -e backend            # Python 3.12+ (pyproject requires it)
cp backend/.env.example backend/.env.local  # dev defaults boot as-is
python -m uvicorn alma.api.app:app --port 8000   # run from backend/
```

`GET /ready` answers `ready: true` with the database, the ephemeris and
the places index all checked. `ANTHROPIC_API_KEY`, the sign-in providers
and the billing keys are listed as missing rather than failing anything:
every calculation works without them — what they gate is the writing,
accounts and money.

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
