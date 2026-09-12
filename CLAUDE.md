# CLAUDE.md

Notes for Claude Code sessions in this repository.

## App workflow (`app/`)

- The real front end lives in `app/static/` (vanilla HTML/CSS/JS, no build
  step) and is driven only by `dashboard.json` (contract: `app/CONTRACT.md`).
  `app/backend/` is a thin layer over the team's calculation engine
  `src/kosmo`: every number comes from `kosmo.calculate_all_scenarios`,
  scores from `kosmo.score_variants` with `config/weights.json`, exports from
  `kosmo.export_bundle`. Never re-implement formulas in `app/`; if a screen
  needs a new number, add it to the engine (`src/kosmo`) and expose it in
  `payload.py`. Shared inputs: `config/portfolio.json`, `config/weights.json`,
  `config/alternatives.json`, `config/custom_mode.json`.
- After any change to the app or the engine: `python -m pytest -q` (engine
  tests plus `app/tests`), `python app/build.py`, then `node app/screenshot.mjs`
  (set `FONT_DIR` when Google Fonts is unreachable) and send the PNGs from
  `app/screenshots/` in the chat. Commit `app/static/data/dashboard.json`
  together with the code.
- `docs/mockup/` is the approved design reference. Style changes go to
  `app/static/styles.css` first; mirror them into the mockup only when the
  reference itself is supposed to change.

## Mockup workflow (`docs/mockup/`)

- The dashboard mockup is one file, `docs/mockup/kosmo-portfolio.html` (all
  screens), with PNG renders in `docs/mockup/renders/`.
- After any mockup change, re-render every screen and commit the HTML together
  with the PNGs:

  ```
  node docs/mockup/render.mjs docs/mockup/kosmo-portfolio.html docs/mockup/renders
  node docs/mockup/render.mjs docs/mockup/fonts.html docs/mockup/renders --fullpage fonts
  ```

- Do not publish design artifacts or canvases. Send the rendered PNG files
  directly in the chat instead.
- The sandbox browser may not reach Google Fonts. Cache the woff2 files locally
  and pass `FONT_DIR` to the render script (see `docs/mockup/README.md`).

## Conventions

- Documentation is in Russian; keep it that way.
- Files under `cases/case02/` come from the organizers and are read-only.
- Figures in the mockup come from `tools/case02_enumerate.py` and the candidate
  table in `docs/case02-team-plan.md` §4. Combinations are named by their lot
  composition and modes, never as versions.
