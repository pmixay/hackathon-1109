# CLAUDE.md

Notes for Claude Code sessions in this repository.

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
