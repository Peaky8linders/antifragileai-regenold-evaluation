---
inclusion: always
---

# Railway — always redeploy after main

⚠ **CORRECTED 2026-08-13.** This file previously described a CI path that does
not exist in this repo and pointed every URL at the SIBLING repo's service.
Both were inherited text from `regenold-eu-ai-act-rag`. Verified:
`.github/` does not exist here at all, and `gh run list` returns nothing —
**there are no workflows and no runs in this repo.**

## This repo's service

```
project      e19dc6ef-b463-4a54-9662-4a5085ae00c9
service      0086ff18-f642-46c8-8127-57c913ca1c53
environment  2f6298dd-881c-4848-81eb-5017a8a64c32
```

The sibling repo `regenold-eu-ai-act-rag` deploys **separately** to
`https://regenold-eu-ai-act-rag-production.up.railway.app`. That is NOT this
service — do not verify a deploy from here against that URL, and do not assume a
change here is live there (or vice versa). They sync by cherry-pick.

## Policy

Whenever code is **merged or pushed to `main`**, ensure Railway deploys the
latest commit. **Do not assume a silent auto-deploy happened** — that is the
whole point of this file, and it is now doubly true because the CI path below
does not exist here.

## CI path — ❌ NOT PRESENT IN THIS REPO

The sibling repo runs `.github/workflows/railway-redeploy.yml`
(`railway redeploy --yes --from-source`, GitHub secret `RAILWAY_TOKEN`). **This
repo has no `.github/` directory**, so a push to `main` here triggers no GitHub
Actions redeploy. Either Railway's own GitHub integration is deploying this
service on push, or nothing is — confirm in the dashboard before believing a
merge shipped. Setup reference: `docs/partners/regenold/RAILWAY_DEPLOY.md`.

## Manual / local path — the reliable one

`scripts/redeploy-railway.ps1` wraps
`npx @railway/cli redeploy --yes --from-source` and reads
`RAILWAY_SERVICE_ID` / `RAILWAY_ENVIRONMENT` / `RAILWAY_PROJECT_ID` from the
environment. Set them explicitly — the script has no defaults, so without them
the CLI targets whatever is linked, which may be the wrong service.

```powershell
$env:RAILWAY_TOKEN      = "<token from https://railway.com/account/tokens>"
$env:RAILWAY_PROJECT_ID = "e19dc6ef-b463-4a54-9662-4a5085ae00c9"
$env:RAILWAY_SERVICE_ID = "0086ff18-f642-46c8-8127-57c913ca1c53"
$env:RAILWAY_ENVIRONMENT= "2f6298dd-881c-4848-81eb-5017a8a64c32"
.\scripts\redeploy-railway.ps1
```

## Verify after deploy

Use **this** service's public domain (Railway dashboard → the service →
Settings → Networking). The script's closing line still prints the sibling's
URL; that is a known wart.

```powershell
curl https://<this-service-domain>/healthz
curl https://<this-service-domain>/healthz/llm   # ⚠ /healthz/llm LIES — see CLAUDE.md
```

`/healthz/llm` is documented as unreliable; verify the LLM path with a real
`POST` to `/api/v1/regenold/eu-ai-act/ask`.

## Agent checklist (end of ship PR)

1. Merge/push to `main`.
2. Run `scripts/redeploy-railway.ps1` with the four env vars above. There is no
   CI fallback in this repo.
3. Probe `/healthz`, then spot-check `/api/v1/regenold/eu-ai-act/ask` with a real
   POST if behaviour changed.
