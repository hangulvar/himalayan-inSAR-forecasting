# 🚦 SESSION REVIEW — Start Here

**This is the first file to read when starting a new session.** It is a living
dashboard, **overwritten at the end of each working session** to always reflect
the *current* state — not a historical log. (For history, see
`session_journey.md`.)

_Last updated: 2026-06-07 (Session 12, branch `mvp-expansion`). **Current state:** the full MVP
(radar → audited data → SBAS velocity → physics hazard → explainable rainfall-driven warning, plus a
3-D UI) is COMPLETE, Dockerized, point-anywhere, and multi-stack. **Session 12 (newest) — the validation
became *scored* and *crossed chance*:** (1) **φ=36° hazard re-run** (`run_multistack.py --force`, Docker):
the GSI-calibrated friction angle de-flags ~12–16 % of marginal zones — frame106 222→**192**, union HIGH
px 5,268→**4,418**, union monsoon zones 405→**357**, while the **≥2-look core stays 26** (fewer false
positives, same hard core) — KPIs **§16a**. (2) **First SCORED back-test** (`backtest_inventory.py` +
null-point control: 5,000 random AOI points + distance-ROC/**AUC**): on the φ=36° mosaic **AUC=0.409** —
real *localized* skill (lift **1.61×@100 m**) but **below chance at 2 km** (lift 0.77×) because we flag a
lot of area → the §14 "71 %@2 km" was *indicative, not scored*; honest detection buffer **≤250 m** (**§16b**).
(3) **Selectivity levers** (`--min-looks`, V_slope mosaic re-run under φ=36): the **≥2-look core lifts
discrimination** (AUC 0.461, spec@2 km 0.10→0.64) but trades recall; **V_slope ≈ LOS** for inventory
discrimination (**§16c**). (4) **★ Rainfall-realistic saturation — the headline** (`rainfall_selectivity_backtest.py`,
saturation sweep): the monsoon mosaic assumes m=1 everywhere, but the regional rainfall model reaches m=1
only **11/214 days** (median m≈0.26). Lowering m to a realistic level concentrates the alert on the steepest
marginal slopes → **AUC rises monotonically 0.407 → 0.550** (m=1.0→0.25), the **first config to beat chance**;
at **m=0.40** lift **5.57×@100 m, >1× out to 1 km**; spec@2 km 0.10→0.61. **Honest nuance:** the regional ID
curve is a *temporal* gate (when to issue) and can't move a *spatial* score — the gain comes from the
saturation *level* (**§16d**). Wired m=0.40 in as the standing `operational` scenario (union 88 zones,
AUC 0.537, **§16e**). **Then built the TWO-FACTOR operational warning — WHERE × WHEN:** `operational_alarm.py`
(**§17**) gates the operational footprint by the regional curve graded by exceedance E (DORMANT/WATCH/ALERT),
cutting the raw **112/214-day trigger → 27 ALERT days (4.1× fewer)** while catching the **20 Apr cloudburst at
Δ=0** (4/4 events in a WATCH+ window) — resolving the §12c over-firing. **And rolled the ERA5-corrected
velocity through the hazard** (`hazard_era5_compare.py`, frame106, **§18**): self-check passed; ERA5 flags
~half the creep/HIGH but only ~18 % overlap → single-look creep is processing-sensitive (trust the multi-look
core). **Session 11** had reviewed TRAIN + run the MintPy tropo-method comparison (ERA5 −31 % scatter,
**§13**), ingested the GSI inventory (138 AOI slides, **§14**), and calibrated φ 32°→36° (**§15**). Detail: §2 / §5._

---

## 1. Read these documents, in this order

| # | Document | Why read it | How much |
|---|---|---|---|
| 1 | **SESSION_REVIEW.md** (this file) | Current state, open questions, next step | All — it's short |
| 2 | **`RESULTS_AND_KPIS.md`** | **Committed** ledger of every headline KPI/finding (mock + real), with provenance | Skim; read **§16/§16a–d** (newest) |
| 3 | `README.md` | Project overview, repo layout, full-pipeline run guide, known env issues | Skim |
| 4 | `milestone.md` | Plain-language story of progress (Milestones 1–23) | Top to current |
| 5 | `session_journey.md` | Detailed decisions & reasoning; **read the top (newest) entry** | Newest 1–2 entries |
| 6 | `error_history_log.md` | Every bug + root cause + fix — **check before debugging anything** | Scan headings |
| 7 | `docker/README.md` | How to build/run the pipeline in the Linux container | As needed |
| 8 | `Research/Foundations - Physics and Maths Primer.md` | The science (Phases 1–4 + forecasting/rainfall/**validation CF6**) | As needed |
| 9 | `InSAR_hazard_forecasting_Context.md` | Original vision / full expansion roadmap | Reference |

**Also re-read `CLAUDE.md`** — behavioural rules + the post-phase documentation ritual (§5).

> **Committed vs local-only (verified 2026-06-07 via `git ls-files`):** `CLAUDE.md` and
> `session_journey.md` are **git-ignored / untracked** (local-only working notes), as is most of `data/`.
> ⚠️ **`SESSION_REVIEW.md` (this file) and `milestone.md` are actually TRACKED in git** — older notes
> (incl. CLAUDE.md §5 and the `RESULTS_AND_KPIS.md` header) call them "git-ignored", but that is **wrong**:
> they were committed early and `.gitignore` never listed them. So a fresh *clone* DOES get this dashboard +
> the milestones, alongside the always-committed `README.md`, `RESULTS_AND_KPIS.md`, `error_history_log.md`,
> the Foundations primer, and `InSAR_hazard_forecasting_Context.md` — but NOT `session_journey.md`/`CLAUDE.md`.
> The user commits manually; uncommitted work from this session is in §7. *(If you'd rather these two be
> local-only, they need `git rm --cached` + a `.gitignore` line — your call; not done automatically.)*

---

## 2. Where we are right now

🎉 **The full end-to-end MVP is COMPLETE and demonstrable, including a 3-D UI**, runs in a
reproducible Linux Docker container, and the spatial validation is now **scored and beats chance**.

- **Phase 1 (clean data): COMPLETE** → `data/qa_masks/`
- **Phase 2 (SBAS velocity): 3 ASC stacks inverted**; 2 DESC dumped (too noisy) → `data/velocity/`
- **Phase 3 (geomechanical engine): per ASC stack, now at φ=36°** → `data/hazard/`
- **Phase 4A (agentic warning): per-stack + AOI union** → `data/alerts/<stack>/`, `data/alerts/mosaic_asc/`
- **Phase 4B (interactive 3-D explorer): COMPLETE** (frame106) → `data/alerts/dashboard_3d.html`
- **Infra 0a (Docker): COMPLETE & VERIFIED**; **Infra 0b (AOI-parameterization): COMPLETE**
  (config.yaml + `workflows/config.py`, metadata-driven `stacks.py`, gated connectivity-rescue,
  multi-stack driver + union mosaic).
- **MintPy migration: STEPS 1–4 DONE** — `insar-mintpy:latest` (py3.11+numpy<2); frame106 ERA5
  tropo correction (r +0.28→+0.55, velocity std 39→21 mm/yr); both DESC evaluated + DUMPED (quality-first).
  Tropo-method comparison (§13): ERA5 −31 % scatter; empirical topo-only barely moves it.
- **Forecasting + validation layer:** inverse-velocity TTF (all steady, short series); real ERA5-Land
  rainfall + Caine/regional ID thresholds coupled into the orchestrator (`FS_real=(1−m)·FS_dry+m·FS_sat`);
  GEE CHIRPS + GPM IMERG fetched; the 20-Apr-2025 cloudburst date correction (§12g).
- **Session 12 — SCORED validation → rainfall-realistic product → two-factor operational warning (§16a–e, §17, §18):**
  - **§16a φ=36° re-run:** zones −12 to −16 % vs φ=32°; ≥2-look core unchanged (26).
  - **§16b first scored back-test:** null-point control (5,000 random AOI pts, seed 20260606) + distance-ROC
    + AUC, in `backtest_inventory.py`. φ=36° mosaic **AUC=0.409**; lift 1.61×@100 m; below chance ≥0.5 km.
  - **§16c selectivity levers:** ≥2-look core AUC **0.461** (spec@2 km 0.64), V_slope ≈ LOS; no dominant
    product (recall ⇄ specificity trade). Added `--min-looks` + `--out-prefix`; V_slope mosaic re-run at φ=36°.
  - **§16d ★ rainfall-realistic saturation:** `rainfall_selectivity_backtest.py` sweep → **AUC 0.407→0.550**
    (m=1.0→0.25), beats chance; **m=0.40** lift 5.57×@100 m, >1× to 1 km. Shared scorer `roc_from_distances`
    extracted from `backtest_inventory.py` (verified behaviour-preserving: reproduces AUC 0.409 exactly).
  - **§16e operational scenario:** m=0.40 wired as a first-class scenario (orchestrator + multistack); union
    88 zones, scored **AUC=0.537** (reproduces §16d). The demos now lead with this beats-chance product.
  - **§17 ★ temporal gate** (`operational_alarm.py`): regional curve graded by exceedance E → DORMANT/WATCH/
    ALERT over the fixed operational footprint. **112/214-day raw trigger → 27 ALERT days (4.1× fewer)**;
    20 Apr cloudburst = ALERT Δ=0; 4/4 events caught by WATCH+, 3/4 by ALERT. Two-factor warning = WHERE×WHEN.
  - **§18 ERA5 velocity through hazard** (`hazard_era5_compare.py`, frame106): self-check passed; ERA5 flags
    ~half the creep (3,752→1,615) / HIGH zones (192→72), ~18 % overlap → single-look creep is processing-
    sensitive (trust the multi-look core). Demonstrative single-stack; not in the mosaic.
  - **Operational dashboard** (`operational_alarm.py` → `operational_alarm_dashboard.html`): self-contained
    two-factor warning UI — current-state banner (as-of any `--as-of` day; default peak-E) + WHERE/WHEN
    panels + season calendar. The new headline demo. (Note: GSI Bhukosh dropped — the CSV already suffices
    for the *spatial* test; it only lacked per-landslide *dates*, and we have 4 dated events already.)
  - **§19 per-zone gating** (`per_zone_gate.py`): each operational zone's critical saturation
    **m\*=(1−FS_dry)/(FS_sat−FS_dry)**; on a regional WATCH/ALERT day the active set = zones with m\* ≤ daily
    m(t), ranked by vulnerability, capped at the validated footprint. Resolves the §17 AOI-wide limitation.
  - **§20 ★ matric-suction dry/wet cohesion split** (`geomechanical_engine.py`): c_dry=18.5 (suction) /
    c_wet=5 kPa → FS_dry 1.58→**2.15** (FS_sat unchanged). FS stays linear in m. **Operating point re-tuned
    m=0.40→0.55**, footprint 88→20 zones, and **AUC 0.537→0.614 (0.615 scored) — the project's best**; per-zone
    m\* now 0.378–0.547. **This supersedes the m=0.40 numbers in §16d–§19.** 20 Apr cloudburst still all-active.

**Active branch: `mvp-expansion`** — all post-MVP work happens here, not `master`.

**Data state after Session 12:** all 3 ASC stacks re-run at φ=36° (LOS **and** V_slope mosaics refreshed).
Union LOS: HIGH=**4,418** (≥2-look **251**), monsoon zones=**357** (≥2-look **26**). V_slope (φ=36°): HIGH=4,568
(≥2-look 331), monsoon zones 362. Per-m sweep mosaics in `data/alerts/mosaic_asc/alerts_sat{025..100}.json`.
Scored artefacts in `data/inventory/` (`backtest_*`, `rainfall_selectivity_*`).

**The demos:** ⭐ **`data/alerts/mosaic_asc/operational_alarm_dashboard.html`** is the headline demo — now
**WHERE × WHEN × WHICH ZONES**: current-state banner + WHERE footprint + WHEN alarm calendar + a **per-zone
ranked "live zones today" panel** (§19, breathes 95/95 on 26 Aug, 85/95 on 27 Apr; `--as-of <date>`). Also
`data/alerts/dashboard_3d.html` (3-D), per-stack `dashboard_operational.html`. Validation story:
`data/inventory/rainfall_selectivity.png` + `backtest_roc.png`; alarm calendar `data/rainfall/operational_alarm.png`.

**The container:** `docker compose build` then e.g.
`docker compose run --rm insar python workflows/agentic_orchestrator.py`. Code + `data/` bind-mounted at `/app`.

---

## 3. CRITICAL environment gotcha (read before running anything)

**Two ways to run, pick one — don't mix:**

- **In Docker (preferred):** `docker compose run --rm insar python …`. numpy/BLAS work natively;
  activation automatic; the Windows bug class below cannot occur. Needs Docker Desktop (WSL2) running.
  **NOTE: matplotlib `savefig` crashes NATIVELY (exit 127) — run anything that plots in Docker** (the
  scored back-test + the sweep both plot, so always run them in the container).
- **Native Windows (legacy):** run compute scripts with the **conda env activated**, or rely on the
  in-script DLL bootstrap. Launching `python.exe` by full path *without* activation → numpy can't find
  its BLAS DLLs → **`0xC06D007F`** (DLL-load failure, not a numerical bug). Keep `logging` ASCII.

- Env (native): `insar_qa_env` at `C:\Users\varun\.conda\envs\insar_qa_env\`.
- HyP3 credits: ~6,170 (≈ enough for one more AOI's full Phase-1 pull). Disk: ~73 GB used in `data/`.
- Minor: a cosmetic `np.trapz`→`trapezoid` numpy-2.x DeprecationWarning in the scored arm — not breaking.

---

## 4. Open questions — "deepen trust" or "scale/deploy"

The core vision is fully built and now **scored above chance**. Remaining work:

0. **Infrastructure & portability:** Infra 0a/0b DONE. Still: fold the <150 m perpendicular-baseline
   gate into rescues; AOI guidance (a better polygon improves *targeting*, not the ~30 mm/yr noise floor).
   **New-AOI replication readiness (asked this session):** infra replicability HIGH (config-driven,
   Dockerized, multi-stack); scientific transferability MEDIUM — a new AOI needs (a) ~2–3 months of S1
   acquisitions for a velocity baseline, (b) site soil calibration (φ=36° is Ramban-specific), (c) a local
   inventory for validation. For *this* monsoon: start the S1 stack now; adopt the §16d m≈0.40 product.
1. **Accuracy backlog:** roll the ERA5-corrected velocity through the hazard/alert chain (proven on
   frame106, not yet rolled through); 12.5 m ALOS DEM; soil cohesion + **matric-suction dry/wet split**;
   uncertainty quantification (velocity error bars → FS/alerts).
2. **Visualization:** combined interactive 3-D dashboard over the UNION mosaic; ASC/DESC vertical+EW
   decomposition (DEFERRED — needs better DESC: longer connected series / PS / phase-linking).
3. **Make it live / smarter:** live rainfall ingestion (CHIRPS/GPM auto, replace manual fetch); real
   flow-routing for LLOF (replace TWI proxy); hybrid LLM ("rules decide, LLM narrates").
4. **Deploy/polish:** hosted Streamlit version of the 3-D dashboard.
5. **Housekeeping:** README run-sequence note for `backtest_inventory.py` (scored arm) +
   `rainfall_selectivity_backtest.py`.
6. **NISAR (next-season step-change):** launched Jul 2025; L-band global since Aug 2025; 100k+ products on
   ASF Feb 2026; **calibrated forward processing at 1–3 day latency from Jul 2026**. L-band recovers
   coherence over vegetation (our worst enemy) + ships geocoded interferograms via ASF (feeds this
   pipeline). Track ASF availability; start ingestion to build an L-band baseline for the Jul-2026 window.

---

## 5. Recommended next step

The validation + operational thread is now **complete end-to-end**: φ=36° → scored back-test → selectivity
levers → rainfall-realistic operating point (§16) → **two-factor operational warning** (§17) → ERA5-velocity
hazard reality-check (§18) → **per-zone gating** (§19). Headline: **a provably-better-than-chance forecast
(AUC 0.55, lift 5.6×@100 m) gated by a selective temporal alarm that catches the 20 Apr cloudburst at Δ=0,
now resolved per zone**. All follow-ups DONE:

1. ✅ **DONE (§16e) — m≈0.40 `operational` standing product** (scenario in orchestrator + multistack; union
   88 zones, AUC=0.537).
2. ✅ **DONE (§17) — regional curve as the *temporal gate*** (`workflows/operational_alarm.py`): E-graded
   DORMANT/WATCH/ALERT over the fixed operational footprint. **Cuts the raw 112/214-day trigger → 27 ALERT
   days (4.1× fewer)**; 20 Apr cloudburst = ALERT Δ=0; 4/4 events caught by WATCH+, 3/4 by ALERT. Resolves
   the §12c over-firing.
3. ✅ **DONE (§18) — ERA5 velocity rolled through the hazard** (`workflows/hazard_era5_compare.py`, frame106):
   self-check passed; ERA5 flags ~half the creep (3,752→1,615 px) / HIGH zones (192→72), but only ~18 %
   overlap → **single-look creep is processing-sensitive; trust the multi-look core.** Demonstrative
   single-stack (`*_hazard_class_era5.tif`); not in the mosaic.
4. ✅ **DONE (operational dashboard)** — `operational_alarm_dashboard.html` (WHERE×WHEN, current-state banner).
5. ✅ **DONE (§19) — per-zone gating** (`workflows/per_zone_gate.py`): per-zone critical saturation m\*; the
   active set breathes **53–95 of 95** zones by day, ranked by vulnerability, capped at the validated
   footprint. Resolves the §17 AOI-wide limitation via intrinsic vulnerability (rain is ~uniform at scale).

6. ✅ **DONE — per-zone ranking wired into the dashboard** (`operational_alarm.py` reads `per_zone_*`,
   renders the "WHICH ZONES — live as of <date>" ranked panel; banner live-count is per-zone-gated).
   Dashboard is now WHERE × WHEN × WHICH ZONES.
7. ✅ **DONE (§20) — matric-suction dry/wet cohesion split** (Area 7 #4, the last big soil assumption):
   c_dry=18.5 / c_wet=5 kPa; FS_dry 1.58→2.15 (FS_sat unchanged); operating point re-tuned **m=0.40→0.55**,
   **AUC 0.537→0.615 — the project's best**. Supersedes the m=0.40 numbers in §16d–§19.

**New top remaining quick wins (all need external data/compute — NOT self-contained):** (a) **12.5 m DEM**
(sharper slope → FS; ASF Vertex download); (b) **roll ERA5 velocity through all stacks** (per-stack MintPy
ERA5 runs); (c) **nonlinear (van Genuchten) suction curve** — §20 is a first-order *linear* split; (d) lab
confirmation of c_dry/c_wet (the "18.5 kg/cm²" unit). **GSI Bhukosh DROPPED** (the CSV suffices for the
spatial test; it only lacked per-landslide dates). **The self-contained operational thread (§16–§20) is now
COMPLETE.** For a **new AOI before monsoon**: point `config.yaml` at the new polygon + start the S1/HyP3 pull
now (velocity needs a time series) — offer stands
to wire `config.yaml` and dry-run everything that doesn't need the HyP3 order.

**Exception to MVP-first (always):** fix correctness/data-integrity bugs immediately; defer quality-only
improvements until shown to matter.

> **⏸ Deferred manual setups (user-side, both DOCUMENTED in `README.md` Step 7):** **(1) GACOS** tropo
> cross-check (gacos.net, drop `.ztd`, MintPy `method=gacos`); **(2) GSI Bhukosh** verified-date inventory
> (register + portal download — NGDR `geodataindia.gov.in` / Bhukosh). Both firewalled/login-gated from the
> agent. When either lands in the repo, the agent does the rest.

---

## 6. Expansion roadmap — areas of exploration toward a robust forecasting tool

§4 is the *near-term hardening backlog*; this is the broader strategic menu (mirrored in
`InSAR_hazard_forecasting_Context.md` for durability). Each **AREA is self-contained**.

**Where the MVP is weakest today:** ~30 mm/yr velocity noise floor; single-look (no true 3-D motion);
assumed/uniform soil strength (φ now site-calibrated) + dry/sat end-members + TWI-proxy downstream flag;
manual (not live) rainfall; a static-vs-worst-case hazard map; recall-limited validation on one small AOI.

- **Area 1 — Noise reduction:** MintPy ERA5 (done on frame106, roll through), GACOS cross-check, DEM-error +
  coherence-weighted inversion, phase-linking/DS methods (recover vegetated slopes), <150 m Bperp rule.
- **Area 2 — Signal strengthening:** ASC/DESC → vertical+EW (needs better DESC), PS points on rock/infra,
  longer series → seasonal vs steady-creep split.
- **Area 3 — Map → FORECAST:** inverse-velocity TTF (built), regional ID thresholds (built/verified),
  calibrated spatially-varying soil + distributed saturation, real flow-routing for LLOF.
- **Area 4 — Validation & uncertainty:** scored back-test **DONE (§16, AUC)**; next = uncertainty
  quantification + a susceptibility model (LR/RF) cross-check + GSI Bhukosh verified-date temporal test.
- **Area 5 — Multi-sensor corroboration (GEE):** CHIRPS/IMERG/ERA5-Land rainfall, SMAP/ASCAT soil moisture,
  SoilGrids strength, DEM upgrades, WorldCover/NDVI veg masks, Sentinel-2/Landsat optical change, NASA GLC.
- **Area 6 — Operationalize:** live rainfall ingestion, hybrid LLM, hosted + union 3-D dashboard.
- **Area 7 (physics borrows):** #1 snowmelt/freeze-thaw (done), #2 V_slope (done), #3 regional ID + K_sn,
  #4 matric-suction/Bishop FS refinement (pending).
- **Data upgrade — NISAR (NASA-ISRO, L+S band):** the top future SAR upgrade (L-band beats vegetation
  decorrelation, our worst enemy); operational window from Jul 2026 (§4.6).

**Suggested priority:** (1) make m≈0.40 the default + regional curve as temporal gate; (2) roll ERA5
velocity through; (3) live rainfall; (4) NISAR ingestion as it matures; (5) uncertainty + susceptibility.

**Robustness in one line:** corroborate InSAR creep with optical change, real rainfall, soil moisture, and a
validated inventory — never trust a single sensor or a single physics assumption.

---

## 7. End-of-session checklist

**Session 12 (2026-06-07) — documentation ritual COMPLETE.**

**Session-12 new files (mostly committed):** `workflows/rainfall_selectivity_backtest.py` (§16d),
`workflows/operational_alarm.py` (§17 gate + dashboard + per-zone panel), `workflows/hazard_era5_compare.py`
(§18), `workflows/per_zone_gate.py` (§19). **Modified (committed-track):** `workflows/backtest_inventory.py`
(scored arm + `roc_from_distances` + `np.trapezoid`); `workflows/agentic_orchestrator.py` +
`workflows/run_multistack.py` (`operational` m=0.40 scenario, §16e); `RESULTS_AND_KPIS.md` (**§16a–e, §17–§19**);
`README.md` (all new run-notes); `Research/Foundations - Physics and Maths Primer.md` (**CF6/CF7/CF8** + Part D
Q + Part E). **Journals:** `session_journey.md` (Session 12, **Pushes 1–10**) is local-only/untracked;
`milestone.md` (**M23, M24, M25**) **and this file are TRACKED** (see §1 box).

**Already committed this session:** `c71b09f` (§16d), `10d3a21` (§16e/§17/§18), `9c66aec` (dashboard),
`6759c14` (§19 per-zone). **Latest uncommitted delta — the dashboard-integration commit + the §20
matric-suction split (re-baselined the operating point to m=0.55):**
```
git add workflows/operational_alarm.py workflows/geomechanical_engine.py workflows/agentic_orchestrator.py \
        workflows/per_zone_gate.py RESULTS_AND_KPIS.md README.md "Research/Foundations - Physics and Maths Primer.md"
git commit -m "Matric-suction dry/wet cohesion split (FS_dry 1.58->2.15) re-tunes op point m=0.40->0.55, AUC 0.61 best (§20); + per-zone dashboard panel"
```
(`SESSION_REVIEW.md` + `milestone.md` are also tracked — the M25/M26 journal updates; include or omit per your call.)

**Git-ignored data outputs (NOT committable):** `data/hazard/*` (incl. `*_hazard_class_era5.tif`,
`hazard_era5_compare.*`) + `data/alerts/*` (incl. `alerts_operational.json`, `operational_alarm_dashboard.html`,
`per_zone_*`, per-stack `dashboard_operational.html`) + `data/mosaic*/`; `data/alerts/mosaic_asc/alerts_sat*.json`;
`data/rainfall/operational_alarm_*`; `data/inventory/` (`backtest_*`, `rainfall_selectivity_*`).

**`error_history_log.md`:** NO new entry — no code bugs this session (only a cosmetic `np.trapz` deprecation,
now fixed; and one self-inflicted false-alarm in a verification check — "WHICH ZONES" appears in both the
dashboard header and the panel, so a naive substring `find()` matched the wrong one — not a product bug).

**Git state (user commits manually).** The §16a–d batch is **already committed** (`c71b09f`, `0230706`,
`40012e9`). Remaining uncommitted delta = §16e operational scenario + §17 temporal gate + §18 ERA5 hazard +
housekeeping/docs:
```
git add workflows/agentic_orchestrator.py workflows/run_multistack.py workflows/backtest_inventory.py \
        workflows/operational_alarm.py workflows/hazard_era5_compare.py \
        RESULTS_AND_KPIS.md README.md "Research/Foundations - Physics and Maths Primer.md"
git commit -m "Operational two-factor warning: m=0.40 scenario + regional-curve temporal gate (§16e,§17) + ERA5 hazard check (§18)"
```
(`SESSION_REVIEW.md` + `milestone.md` are also tracked — include or omit per your call; `session_journey.md`
+ `CLAUDE.md` are untracked.)

**Recommended first action next session (see §5):** the operational dashboard "live today?" banner is now
DONE. Remaining high-value, fully-doable items: **(a) per-zone temporal gating** (sub-daily/point IMERG rain
so ALERT varies per zone instead of AOI-wide — the main §17 limitation); **(b) 12.5 m DEM** (sharper slope →
FS; needs an ASF Vertex download); **(c) roll ERA5 velocity through *all* stacks** (needs a per-stack MintPy
ERA5 run; DESC dumped). **GSI Bhukosh DROPPED** — the `Research/LandslideInventory` CSV already suffices for
the spatial test (138 AOI pts, scored §16); it only lacked per-landslide *dates* (92 % year=0) for a *temporal*
test, and we already have 4 dated events (§17). **Start Docker Desktop first** (anything that plots → container).
