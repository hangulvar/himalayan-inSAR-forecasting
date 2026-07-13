# Monsoon Watch Runbook — now SCHEDULED (manual steps kept as the fallback)

> **⏰ Automated since 2026-07-13 (ERRC "Eliminate"):** the whole loop below runs by itself as the
> Windows scheduled task **"InSAR Monsoon Watch Cycle"** — every 2 days at 08:00, both sites
> (VD + Ramban), via `workflows/monsoon_cycle.ps1`. It starts Docker if needed, refreshes both
> alarms + the status board (`data/aoi_status.html`), logs to `logs/monsoon_cycle_<date>.log`, and
> **raises a Windows toast only when a human is needed** (a site enters ALERT, any state change, or
> a failed chain). Season-gated Apr–Oct; off-season runs exit silently.
>
> - Check it: `Get-ScheduledTaskInfo -TaskName 'InSAR Monsoon Watch Cycle'`
> - Run now: `Start-ScheduledTask -TaskName 'InSAR Monsoon Watch Cycle'`
> - Disable (post-monsoon): `Disable-ScheduledTask -TaskName 'InSAR Monsoon Watch Cycle'`
>
> Your remaining job on a toast: open the dashboard, and if it's an ALERT follow the escalation
> section below. The manual commands remain valid any time (everything is idempotent).

Quick reference for keeping the live alarm current while a site is in WATCH/ALERT
(§35/§38). Two steps: refresh rainfall, then check what changed. Takes under 2 minutes of your time
(the commands do the work). Run from the project root; Docker Desktop must be running.

## The two commands, in order

**Step 1 — fetch the latest rainfall** (needs the `mintpy` image, which has the CDS API client):

```powershell
docker compose run --rm mintpy python workflows/live_alarm.py
```

**Step 2 — regenerate the alarm + dashboard** (needs the `insar` image, which has plotting):

```powershell
docker compose run --rm insar python workflows/live_alarm.py
```

That's it. Same script, different image, because the rainfall-fetch and the alarm-plotting steps
need different Python environments (`live_alarm.py` auto-detects which stage it can run and skips
the other — see the `fetch=YES/no` / `alarm=YES/no` line in its own output).

> **Which site do these commands act on? (changed 2026-07-12, §41)** The commands follow the
> `active_config:` pointer in the root `config.yaml` — currently `config/vaishnodevi.yaml`, so the
> plain commands above are correct for the VD watch. If the pointer is ever switched, pin the site
> explicitly instead of trusting the pointer:
>
> ```powershell
> docker compose run --rm -e INSAR_CONFIG=config/vaishnodevi.yaml mintpy python workflows/live_alarm.py
> docker compose run --rm -e INSAR_CONFIG=config/vaishnodevi.yaml insar  python workflows/live_alarm.py
> ```
>
> The same pair with `config/ramban.yaml` refreshes the Ramban site — worth doing when the status
> board (below) shows its rainfall going stale.

## The health check — one command for all sites

Before or after the cycle, the status board shows every site's alarm level, how many days behind
its rainfall is, and the exact next command if something needs running (it is read-only and safe
any time; runs natively too):

```powershell
docker compose run --rm insar python workflows/aoi_status.py
```

Scan the card per site: `state: WATCH as-of <date> ...` and the rainfall `Nd behind` figure.
After a successful Step 1+2 the as-of date should advance to ~5 days behind today (the ERA5-Land
publication lag). If a stage shows unchecked, the card prints what to run. Browser version:
`data/aoi_status.html`.

## What to look for in the output

After Step 2, scan the terminal for these lines:

- **`as-of <date> (m=X.XX, regional <STATE>): N zones ACTIVE`** — the current alarm level
  (DORMANT / WATCH / ALERT) and how many hazard zones are live today.
- **`ALERT day(s): ...`** — if this is non-empty, the acute rainfall trigger has fired. That's the
  "check the dashboard now" signal.
- **`-> dashboard (as-of <date>, <STATE>): data/alerts_vaishnodevi/mosaic_asc/operational_alarm_dashboard_vaishnodevi_2026.html`**
  — the file to open.

## Which file/dashboard to open

**[data/alerts_vaishnodevi/mosaic_asc/operational_alarm_dashboard_vaishnodevi_2026.html](../data/alerts_vaishnodevi/mosaic_asc/operational_alarm_dashboard_vaishnodevi_2026.html)**
— open it in any browser (double-click, or drag into a tab). The banner at the top shows the
alarm state; the "WHICH ZONES" table shows which specific slopes are live today, ranked by
vulnerability, each coordinate a click-to-Google-Maps link. The Guide tab explains every term if
you need a refresher.

## When to escalate beyond "just look at it"

- **If the state reads ALERT** (not just WATCH): re-read the relevant field brief —
  `Research/Field Brief - Bhairon NE flank creep target (2026-07-07).md` or
  `Research/Vaishno_Devi_Watchlist/Field Brief - Bhavan overhang (2026-07-08).md` — and consider
  whether the field-check step (roadmap item) is now timely.
- **After any heavy rain/storm event:** also run the fast-failure tripwire, which checks for a
  sudden radar-coherence drop (a possible fresh rockfall/collapse signature):
  ```powershell
  docker compose run --rm insar python workflows/coherence_watch.py --polygons "Research/Vaishno_Devi_Watchlist/Vaishno_Devi_Bhavan_Overhang.kml" --out-name coherence_watch_bhavan_overhang
  docker compose run --rm insar python workflows/coherence_watch.py --polygons "data/alerts_vaishnodevi/mosaic_asc/bhairon_core_creep.kml" --out-name coherence_watch_bhairon_creep
  ```
  Look for `DROP-CONFIRMED` or `DROP-SINGLE-TRACK` in the output (vs the routine `OK`) —
  see `data/alerts_vaishnodevi/mosaic_asc/coherence_watch_*.md` for the full timelines.
- **Every ~2 weeks (separate from this 2–3 day loop):** check whether new Sentinel-1 radar scenes
  have landed in the archive — a bigger step (submit → download → QA → invert), covered by
  `SESSION_REVIEW.md` roadmap item #1, not this runbook.

## If something looks wrong

- **`fetch=no (needs mintpy image)`** printed by Step 1 — you ran it with the wrong image; re-check
  the command uses `mintpy` not `insar`.
- **No new rainfall days added** ("+0 day(s)") — normal; ERA5-Land publishes ~5 days behind, so a
  same-week re-run sometimes has nothing new yet. Not an error.
- Anything else: check `error_history_log.md` (searchable by symptom) before debugging from scratch.
