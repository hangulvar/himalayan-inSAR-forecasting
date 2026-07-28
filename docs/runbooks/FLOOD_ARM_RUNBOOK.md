# Flood Arm Runbook (F0 + F1)

How to run, re-run, interpret and switch off the flash-flood arm.
Plan of record: `docs/references/FLOOD_EXPANSION_PLAN_2026-07-28.md`. Numbers: ledger §69–§71.

---

## 0. What this arm does and does not do

| It answers | It does NOT answer |
|---|---|
| Where water concentrates (channels, catchments) | How deep the water gets |
| Which creep zones sit near a channel | Where the water spreads (inundation extent) |
| How hard it is raining on each catchment, staged | Discharge in m³/s |

It publishes a **staged level per catchment** (`FLOOD-DORMANT / FLOOD-WATCH / FLOOD-ALERT`) and
the exceedance `E_f` behind it. It is **EXPERIMENTAL**: thresholds are inherited from the burst
arm (§64) and have never been calibrated against flood ground truth, because none exists.

**It cannot change the validated landslide product.** It writes only to `data/flood/` and feeds
only its own dashboard card. `tests/test_flood_invariants.py` proves that by hashing 116
protected artifacts.

---

## 1. Turning it on / off

The arm is gated by an optional `flood:` block in each AOI's registry file:

```yaml
flood:
  channel_upstream_km2: 0.5       # what counts as a channel (= the validated LLOF threshold)
  channel_buffer_m: 120           # a zone this close to a channel is "flood-exposed"
  min_catchment_coverage_pct: 95  # refuse to grade a catchment truncated by the DEM edge
```

**Delete the block and the arm is completely off** — both scripts exit 0 and write nothing, and
the dashboard renders exactly as it did before the feature existed. That is a tested property
(`R2`), not a claim.

---

## 2. Normal operation (nothing to do)

`live_alarm.py` runs `flood_gate.py` automatically before each dashboard render, non-fatally.
If GEE is down, the run prints `flood gate SKIPPED (...)` and everything else proceeds.

## 3. Running it by hand

```bash
docker compose run --rm insar python workflows/flood_gate.py
```

For the other site, or a past season:

```bash
docker compose run --rm -e INSAR_CONFIG=config/vaishnodevi.yaml insar python workflows/flood_gate.py
```

**F0 only needs re-running when the hazard footprint changes** (new zones ⇒ new catchments):

```bash
docker compose run --rm insar python workflows/flood_domain.py --merit
```

`--merit` adds the optional MERIT-Hydro corroboration (needs GEE, non-fatal, currently
**inconclusive** at these catchment sizes — see §71 and §6 below).

---

## 4. Reading the output

`data/flood/flood_gate_summary{sfx}.json`:

| field | meaning |
|---|---|
| `latest`, `latest_date`, `level_counts` | **CURRENT state** — the newest day. This is what the card headlines. |
| `season_peak` | the worst half-hour anywhere this season. **Context, not current state.** |
| `alert_days_per_catchment` | how many ALERT-grade days each catchment actually had |
| `durations_h` per catchment | the window range screened (starts at that catchment's t_c) |
| `aborted` / `abort_reason` | a refusal, never a silent DORMANT |

> **Read `latest` for "what now?" and `season_peak` for "how bad has it been?".** Conflating them
> reports a four-month-old cloudburst as today's emergency — the §70 bug.

---

## 5. Failure modes and what they mean

| Symptom | Meaning | Action |
|---|---|---|
| `ABORT — catchment touches the edge of the DEM's valid data` | The catchment runs off the frame, so its area is an under-estimate | Expected for edge zones; not gradeable. Do not "fix" by lowering the coverage threshold. |
| `ABORT — no rainfall steps returned` | GEE returned nothing for this catchment | Was the §70 sub-pixel-null bug (fixed by `sampling_scale_m`). If it recurs, probe the bbox at several scales BEFORE changing code. |
| `ABORT — all N rainfall steps are non-finite (void, not dry)` | The rainfall record is missing, not zero | Correct behaviour. Never publish DORMANT for this. |
| `flood gate SKIPPED (...)` in a live_alarm run | GEE/network down | None — the card just goes stale or absent, by design. |
| `regime: B (mainstem river)` | The nearest channel is a big river | Out of scope by plan §2. Not a bug. |

---

## 6. Known limitations (state these when showing the arm to anyone)

1. **No flood ground truth exists** → thresholds are inherited, not calibrated. EXPERIMENTAL.
2. **Only 3 of 22 zones are channel-adjacent** at the 120 m buffer — the arm addresses a minority
   of sites today.
3. **Most catchments span ~1 IMERG pixel (~11 km)** — a "catchment mean" is effectively that one
   pixel. Sampling finer (§70) prevents nulls; it adds no information.
4. **t_c is a Kirpich proxy** (0.07–0.12 h here), used only to set where the duration range
   starts, never published as a hydrograph quantity.
5. **MERIT-Hydro corroboration is INCONCLUSIVE** at Regime-A scale: an 80 m and a 90 m channel
   raster do not align well enough at headwater outlets, and near mainstems the snap window jumps
   basins. Routing consistency is pinned by tests instead (BFS catchment == accumulation, and the
   shared §67 criterion).
6. **Not an inundation model.** See the table in §0 and say so out loud.

---

## 7. If a protected artifact changes

`tests/test_flood_invariants.py` R1 fails loudly. **One legitimate cause:** a `live_alarm.py` run
refreshes the CURRENT season's daily-arm files. If every changed path is one of those, that is
the daily arm doing its job — confirm nothing else moved, then delete
`data/flood/_baseline_freeze.json` to re-freeze. Anything else: restore from backup and find what
wrote it before re-freezing.

## 8. Housekeeping

`data/flood/_cache/*.npy` (~80 MB per stack) is regenerable D8 accumulation — delete any time.
`data/flood/_rain/` holds per-catchment half-hourly caches; **delete these if the sampling scale
ever changes**, because a series must not mix sampling methods.
