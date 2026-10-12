# Final audit

## Issues found and corrected

| Finding | Correction |
|---|---|
| Analysis could render more React hooks after its loading/error early return, crashing when a snapshot finished loading. | Moved data-derived memoized work ahead of the conditional returns and made it safe for missing data. |
| Blank or omitted analysis fields reached endpoint code and raised `ValueError`, producing a server error; validation errors could also echo serialization details. | Validate both names at request parsing, return a clean 400 for invalid `/api/analyze` requests, and omit raw validation details from responses. |
| A price-route ticker check rejected a valid test fixture; the CORS test depended on a removed Starlette attribute. | Kept the restrictive ticker alphabet and corrected the fixture/test to exercise supported input and current middleware configuration. |
| The PDF test closed its Playwright context before using the page. | Keep browser lifetime around page creation/rendering and verify PDF output. |
| Legacy synthetic market-price fallback could make fabricated values appear live. | Removed the fake fallback and its unused sample-data module; offline analysis now uses dated snapshots. |
| The README was stale and contained broken character encoding; unused report dependencies, patch scripts, and unused imports remained. | Replaced the README, removed confirmed unused dependencies/files/imports, and pinned direct package versions. |
| Vite 5 was within several published vulnerable ranges. | Pinned Vite 6.4.3, which is compatible with the current React plugin. |
| CORS was broader than the exhibition's local frontend required; input bounds and analysis abuse limits were incomplete. | Restrict CORS to explicit origins, reject wildcards, sanitize/bound user text, validate ticker paths, and add a per-client `/api/analyze` sliding-window limit. |

## Security checks

- API credentials are backend-only. `.env` files are ignored except `.env.example`; frontend configuration contains only public URLs. A source and built-bundle scan found no credential values.
- CORS defaults to `localhost:5173` and `127.0.0.1:5173`; configure the exact deployed frontend origin explicitly.
- `/api/analyze` is limited per client IP and process. Multi-worker hosting should add a shared proxy/Redis limit.
- No `console.log` calls remain in frontend source. Backend request/error output uses the configured logger.

## Remaining dependency advisory

`npm audit` reports **5 high severity advisories** in the current Tailwind CSS 3.4.19 development dependency tree (including `chokidar`, `micromatch`, `braces`, and `fast-glob`); `npm audit --omit=dev` reports zero production advisories. npm offers a fix by upgrading to Tailwind CSS 4, a major version that changes the CSS integration; that migration needs a separate visual compatibility pass. Vite 6.4.3 removed the Vite/esbuild advisories. Do not expose the development server publicly.

## Final run status

- Backend: `python -m pytest -q --tb=short` — **75 passed**.
- Frontend: `npm run build` — **passed** with Vite 6.4.3.
- Production dependency audit: `npm audit --omit=dev` — **0 vulnerabilities**. Full audit — **5 high** in Tailwind CSS 3 development dependencies, as described above.
- `python scripts/warm_cache.py` — **18/18 stock histories warmed; benchmark ready**. Yahoo returned insufficient history for some sector indexes; those indexes are discarded rather than fabricated.
- Final preflight — **4/6 passed**: internet, Yahoo, warm cache, and 9/9 snapshots pass. Gemini key is not configured; ports **5173 and 8000 are occupied**. The preflight exits nonzero until those two environment conditions are addressed.
- Secret scan — **0 credential-like matches** in source and built JavaScript bundles. The local `backend/.env` has no Gemini key configured.
- Frontend source scan — **no `console.*` calls found**.
- Production browser check — the bundled HAL/Mazagon Dock snapshot rendered its dated offline badge in **1.01 seconds**.
