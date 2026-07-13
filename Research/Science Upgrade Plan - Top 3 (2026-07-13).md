# Science Upgrade Plan — Top 3 (2026-07-13)

The three highest-value improvements to the **science and mathematics** of the pipeline, chosen
after the multi-AOI productization (§41) froze the plumbing. Selection criterion: *scientific
value per unit effort, given the data we already have* — each one attacks a weakness we have
**measured** (cited by §), not a hypothetical. Ordered by recommended execution order.

> House rules apply: implement one at a time, score against the inventories before/after
> (append to `RESULTS_AND_KPIS.md`, tag `[REAL]`), and record negative results as plainly as
> positive ones. None of these change data plumbing — they change equations and statistics.

---

## 1. Statistical rigor of the validation — bootstrap CIs + a dumb-baseline model ✅ DONE 2026-07-13 (§44)

> **Outcome:** `workflows/validation_stats.py`; both sites' CIs/p-values/ladders in §44; dashboards
> + README cite intervals. Acceptance met. The anticipated "unwelcome answer" arrived at VD: the
> model beats its components but not a tuned slope-only map on the corridor inventory — recorded
> honestly in §44, and it is the yardstick #2 and #3 will be judged against.

**What is weak now.** Every headline skill number is a *point estimate* on a small sample:
AUC 0.64 (Ramban, §16d/§21b), AUC 0.71 (VD, §32/§42-baseline) on n=41–46 inventory features vs
5,000 null points; the temporal test is 2/2 events at Δ=0 (§31/§38). No confidence intervals, no
significance statement, and no comparison against a *deliberately dumb* baseline. The first
question any reviewer will ask: **"is AUC 0.70 at n=46 distinguishable from chance — and from a
slope map alone?"** We currently cannot answer either.

**The math.**
- **Bootstrap CI:** resample the inventory features with replacement (B=10,000), recompute the
  distance-ROC AUC per replicate → percentile 95% CI. Same for recall@2 km. Report
  `AUC 0.71 [CI_lo–CI_hi]` everywhere a point estimate now stands.
- **Permutation p-value:** shuffle inventory vs null labels → distribution of AUC under H₀ →
  one-sided p for "beats chance".
- **Dumb baselines (the ablation ladder):** score, with identical protocol, (a) slope>threshold
  alone, (b) logistic regression on slope+TWI (no InSAR, no physics), (c) FS_saturated alone
  (physics, no InSAR), (d) creep alone (InSAR, no physics). The pipeline's claim becomes
  *incremental skill over each rung*, not raw AUC.

**Why this is #1.** It upgrades the *defensibility of every existing number* without touching the
pipeline, it is the cheapest of the three (pure post-processing on artifacts we already emit), and
it directly serves the pitch (strategy session 2026-07-13): "validated with CIs against ablation
baselines" is the sentence that separates this from typical LSM work. Risk of an unwelcome answer
is real (the CI at n=46 will be wide; a rung of the ladder may score close to us) — and reporting
that honestly is itself the project's brand.

**Sketch.** New `workflows/validation_stats.py`: reuses `backtest_inventory.py`'s distance/ROC
machinery; inputs = any `alerts_*.json` + inventory; outputs = CI/p-value/ablation table
(`data/inventory/validation_stats_<slug>.{json,md,png}`). No engine changes. Acceptance: CIs and
ablation AUCs for both sites in the ledger; README/dashboards cite intervals, not points.

---

## 2. Distributed saturation — replace the single AOI-wide m with a TWI-conditioned field ✅ DONE 2026-07-13 (§45)

> **Outcome — POSITIVE, adopted.** `kappa` config key + TWI-distributed m_i in the orchestrator;
> swept via `rainfall_selectivity_backtest.py --kappas`; both AOIs independently peaked at
> **kappa=0.06** (VD operational AUC 0.707→0.757 — **now beats the §44 slope-only ablation**;
> Ramban 0.640→0.676; both WATCH tiers held/improved, VD watch recall 0.913→0.957). Adopted in both
> registry configs (kappa=0 = §44, reversible). Honest caveats in §45: ALERT-AUC CIs overlap (gain is
> footprint economy + breaking the ablation tie, not a decisive AUC jump), ALERT recall trades down as
> the footprint tightens, and kappa is a spatial redistribution (it cannot change the §17 regional
> ALERT-day count). Acceptance met on the discrimination arm; recorded transparently.

**What is weak now.** The WHEN gate applies **one saturation value to the whole AOI**
(§17/§19): every zone sees the same m(t), so on a wet day the per-zone gate activates zones purely
by their m\* ranking, and in an extreme season the regional gate over-fires (59 ALERT days,
VD-2025 — the §17 limitation). Physically, saturation is *not* uniform: convergent, low-gradient
terrain wets first. We already compute exactly the index that encodes this — TWI — but use it only
as a downstream LLOF flag, not in the wetness itself.

**The math.** TOPMODEL's core result: local water-table deficit varies linearly with the
topographic index. Map it to our saturation fraction:

  m_i(t) = clip( m̄(t) + κ · (TWI_i − TWI̅) , 0, 1 )

where m̄(t) is the current AOI-mean wetness (the existing rainfall proxy), TWI̅ the AOI-mean index,
and κ a single new calibration constant (units 1/TWI) — sweep κ against the inventories exactly
like the m-sweep (§16d/§32) so it is *earned per site*, not assumed. FS stays linear in m_i
(unchanged engine), but each zone now crosses FS=1 on its own hydrologically-informed schedule:
wet-hollow zones alarm earlier, dry-ridge zones later.

**Why this is #2.** It attacks the biggest *operational* weakness (uniform WHEN, §17's over-firing)
with data already on disk, adds exactly one interpretable parameter, and plugs into the existing
m\*/per-zone-gate algebra without breaking any of it (κ=0 reproduces today's behavior — a built-in
regression gate). It is also the honest cheap step *before* sub-daily IMERG (roadmap #5): spatial
differentiation first, temporal sharpening second.

**Sketch.** `geomechanical_engine.py` emits TWI already; `per_zone_gate.py`/`operational_alarm.py`
gain a `kappa` config key (default 0 = today); `rainfall_selectivity_backtest.py` sweeps κ.
Acceptance: κ>0 must *improve* (or at least not degrade) AUC/recall AND reduce extreme-season
ALERT days; if it does neither, record the negative and keep κ=0.

---

## 3. Nonlinear matric suction — a van Genuchten curve instead of linear cohesion interpolation

**What is weak now.** The dry→wet strength loss is modeled as cohesion varying **linearly** in m
between c_dry=18.5 and c_wet=5 kPa (§20). Real unsaturated soils lose matric suction *nonlinearly*:
suction (and its apparent cohesion) collapses rapidly over a narrow saturation range set by the
soil-water retention curve. The linear model therefore **misplaces every per-zone critical
saturation m\*** — the exact quantity the WHEN gate ranks zones by (§19) — and §42 proved the
product is highly sensitive to precisely these strength assumptions. §20 itself flags this as
"the next refinement".

**The math.** Van Genuchten (1980) retention + Vanapalli's suction-cohesion:

  Effective saturation  S_e = [1 + (α·ψ)ⁿ]^(−(1−1/n))  →  invert for suction ψ(m)
  Apparent cohesion     c_app(m) = c' + ψ(m) · tanφ_b · S_e   (φ_b ≈ φ'·S_e as the simple form)
  c(m) = c_wet + c_app(m),  anchored so c(0)=c_dry and c(1)=c_wet (preserves both §20 end-members)

Two new parameters (α, n) from published curves for silty colluvium — a *literature pass with
provenance*, like the soil block (M2); sensitivity-sweep them with the §42 harness before trusting.
FS is no longer linear in m, so `per_zone_gate`'s closed-form m\* = (1−FS_dry)/(FS_sat−FS_dry)
becomes a 1-D root-find per zone (bisection on FS(m)=1 — trivial numerically, monotone in m).

**Why this is #3 (not #1).** Highest physics value — it corrects the *shape* of the hazard's
response to wetness, which reorders zone activation timing and could move the two-tier operating
points — but it carries the most new-parameter risk (α, n are borrowed until lab data exists,
Part E) and its end-to-end effect must be judged through #1's statistics to be credible. Doing it
after #1 and #2 means its impact is measured with CIs, against a hydrologically sensible m-field.

**Sketch.** `factor_of_safety()` gains an optional suction-curve mode (config block
`suction: {alpha, n}`; absent = today's linear model — regression-safe); `per_zone_gate` m\* via
bisection; §42 sweep extended over (α, n). Acceptance: end-members reproduce exactly; scored
back-tests + temporal catches re-run; operating points re-swept (§32 method) if the FS(m) shape
shifts them.

---

## Explicitly considered and NOT in the top 3

- **Coherence-weighted SBAS inversion + Bperp DEM-error term** (Berardino 2002 / Fattahi 2013):
  real math upgrades to Phase 2 (we even cache Bperp now, §43) — but the MintPy/ERA5 cross-check
  (§9/§13) already bounds the inversion's credibility, and the noise floor is dominated by
  troposphere + vegetation, not inversion weighting. Revisit when chains lengthen or NISAR lands.
- **Phase-linking / DS methods**: the biggest noise-floor lever but a heavy dependency step
  (new processor); NISAR-era work (§4 Area 1/2).
- **D-infinity flow routing for LLOF**: improves a *flag*, not the core hazard; cheap but low
  leverage until the failure-class gap (roadmap #4) is addressed.
- **Sub-daily IMERG per-zone WHEN** (roadmap #5): valuable, but #2 gives spatial differentiation
  first with zero new data dependencies; IMERG is the follow-on, not the substitute.

## Execution order and effort

| # | upgrade | new params | effort | primary § it attacks |
|---|---|---|---|---|
| 1 | Validation statistics + ablation ladder | none | ~1 session | §16d/§31/§32 (defensibility) |
| 2 | TWI-distributed saturation m_i | κ (swept) | ~1–2 sessions | §17/§19 (uniform WHEN, over-firing) |
| 3 | van Genuchten suction curve | α, n (literature + swept) | ~2 sessions | §19/§20/§42 (m\* placement) |

Each stage ends with the standard regression battery + a ledger entry; a negative result keeps the
old model and records why.
