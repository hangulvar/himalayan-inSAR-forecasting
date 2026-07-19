# 📚 Documentation Index

One page to answer "what do I read, and in which order?" — created in the 2026-07-17
restructure that gathered all *reading* material under `docs/`. The **functional** docs
(the ones the session ritual writes to) stay at the project root, on purpose:

| Root doc (functional — do not move) | Role |
|---|---|
| `SESSION_REVIEW.md` | 🚦 Start here every session — LIVE state + STABLE guide |
| `RESULTS_AND_KPIS.md` | Committed append-only ledger of every headline KPI/finding |
| `milestone.md` | Plain-language story of progress |
| `error_history_log.md` | Every bug + root cause + fix — check before debugging |
| `session_journey.md` | Slim per-session decisions + dead-ends (git-ignored, local) |
| `README.md` | Project overview, repo layout, full run guide |
| `CLAUDE.md` | Behavioural rules for AI-assisted dev (git-ignored, local) |

## Reading order for a newcomer

1. `SESSION_REVIEW.md` (root) — where the project stands today.
2. `milestone.md` (root) — the story so far, no jargon.
3. [guides/Foundations - Physics and Maths Primer.md](guides/Foundations%20-%20Physics%20and%20Maths%20Primer.md) — ALL the science, beginner-friendly (+ interview prep, honest limitations).
4. [guides/InSAR_hazard_forecasting_Context.md](guides/InSAR_hazard_forecasting_Context.md) — the original vision and full expansion roadmap.
5. `RESULTS_AND_KPIS.md` (root) — the evidence, newest §§ first.

## docs/ map

### guides/ — learning material
- **Foundations - Physics and Maths Primer.md** — the science base (Phases 1–4 + forecasting/rainfall/validation). Updated each completed phase by `/wrap-session`.
- **InSAR_hazard_forecasting_Context.md** — original project vision + strategic roadmap (mirrors SESSION_REVIEW STABLE §4).
- **proj_pipeline_AOI.md** — future-AOI shortlist and pipeline notes.

### runbooks/ — how to operate
- **NEW_AOI_PLAYBOOK.md** — deterministic recipe for onboarding a new AOI (automated steps + the manual M1–M4). Referenced by `workflows/aoi_status.py`'s next-step hints.
- **Publishing Checklist - Live Dashboard (2026-07-11).md** — what to check before publishing the dashboard publicly.

*Day-to-day ops need no runbook anymore:* the scheduled cycle (`workflows/monsoon_cycle.ps1`)
runs unattended, and `control_panel.bat` (root) gives one-click refresh + a results hub.

### briefs/ — site-specific field material
- **Field Brief - Bhairon NE flank creep target (2026-07-07).md** — the printable field-check brief for the NE-flank CORE target.
- **Vaishno_Devi_Watchlist/** — Bhavan overhang brief, soil parameter research brief, GSI/geotech PDFs, the overhang KML.
- **LandslideInventory/** — GSI landslide reports/compendium PDFs + the Batote–Ganpat susceptibility note (inventory provenance; exclusion notes live in `RESULTS_AND_KPIS.md`).

### references/ — literature & standing plans
- **Joshimath InSAR.pdf** — the study that seeded the methodology.
- **STRENGTHENING_PLAN_2026-07-18.md** — the ACTIVE data+science plan (Tier 0–4: S1-handover
  triage, in-monsoon rain science, NISAR L-band pilot, validation depth, structural items);
  successor to the archived Science Upgrade Plan.
- **RAMBAN_REBUILD_MANIFEST_2026-07-19.md** — the dry-run-verified 3-pair submission
  manifest for the unblocked Ramban cadence rebuild (frame-renumbering finding, ~30-credit
  cost, one-command submit + the post-landing rebuild loop).

### archive/ — superseded, kept for the record
- **Monsoon Watch Runbook (2026-07-11).md** — manual loop, superseded by the scheduled cycle + control panel.
- **Science Upgrade Plan - Top 3 (2026-07-13).md** — all three items complete (§44–§46).
- **local/** — git-ignored scratch research notes (old meteorology/LLM-synthesis material, pre-streamline SESSION_REVIEW snapshot). Never cite these as sources.

## Old → new path mapping (2026-07-17)

Historical documents (`RESULTS_AND_KPIS.md` §-entries, `session_journey.md`,
`error_history_log.md`) still cite the old paths — that history is append-only and was
deliberately not rewritten. Translate with this table:

| Old path | New path |
|---|---|
| `NEW_AOI_PLAYBOOK.md` | `docs/runbooks/NEW_AOI_PLAYBOOK.md` |
| `InSAR_hazard_forecasting_Context.md` | `docs/guides/InSAR_hazard_forecasting_Context.md` |
| `workflows/proj_pipeline_AOI.md` | `docs/guides/proj_pipeline_AOI.md` |
| `Research/Foundations - Physics and Maths Primer.md` | `docs/guides/Foundations - Physics and Maths Primer.md` |
| `Research/Monsoon Watch Runbook (2026-07-11).md` | `docs/archive/Monsoon Watch Runbook (2026-07-11).md` |
| `Research/Publishing Checklist - Live Dashboard (2026-07-11).md` | `docs/runbooks/Publishing Checklist - Live Dashboard (2026-07-11).md` |
| `Research/Science Upgrade Plan - Top 3 (2026-07-13).md` | `docs/archive/Science Upgrade Plan - Top 3 (2026-07-13).md` |
| `Research/Field Brief - Bhairon NE flank creep target (2026-07-07).md` | `docs/briefs/Field Brief - Bhairon NE flank creep target (2026-07-07).md` |
| `Research/Vaishno_Devi_Watchlist/…` | `docs/briefs/Vaishno_Devi_Watchlist/…` |
| `Research/LandslideInventory/…` | `docs/briefs/LandslideInventory/…` |
| `Research/Joshimath InSAR.pdf` | `docs/references/Joshimath InSAR.pdf` |
| `Research/Archive/…` | `docs/archive/local/…` |
| `ramban_aoi.geojson` (root) | `config/aoi/ramban_aoi.geojson` |
| `vaishnodevi_aoi.geojson` (root) | `config/aoi/vaishnodevi_aoi.geojson` |
| `vaishnodevi_route.geojson` (root) | `config/aoi/vaishnodevi_route.geojson` |
| `.env.template` / `.netrc.template` / `.cdsapirc.template` (root) | `config/templates/…` |
