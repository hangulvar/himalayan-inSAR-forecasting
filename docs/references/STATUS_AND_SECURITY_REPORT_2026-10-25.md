# Status & Security Report — 25 Oct 2026

*Written after ~40 days of inactivity (last session: 15 Sep 2026). Branch `aoi-vaishnodevi`.
Every number below was produced by a command run on 25 Oct; the ledger home for the headline ones
is `RESULTS_AND_KPIS.md` §88.*

---

## 0. The short version

- **Everything still works.** All 16 test suites pass: **243 of 243 checks**, on your current
  setup *and* on a tested upgrade. Nothing in `data/` changed (the 116-file freeze check is intact).
- **I found and fixed 4 security holes**, all in the local control panel, plus 3 smaller defects.
  The two that mattered: any website you visited while the panel was running could (a) start its
  Docker jobs, by slipping past the §86 fix, or (b) make your PC try to log in to a stranger's
  file server. Both are closed, each with a test proven to fail on the old code.
- **The PHP flaws in the news ("PHP2Shell", CVE-2026-109618/109619) cannot affect this project.**
  There is no PHP in it. The lesson that does transfer, "the code that reads web requests is
  where the danger is", is exactly where I looked hardest.
- **The real "keep it up to date" item has a deadline:** Python 3.10, which both your conda env and
  your Docker image run, **stops getting security fixes on 31 Oct 2026, 6 days from now.** I built
  and tested a replacement (Python 3.12). It has **0 known vulnerabilities, vs 117 in your current
  env**, and passes every test.
- **The data is stale.** Live rainfall and alarms for Ramban and Vaishno Devi stop on
  **8 Aug, 78 days ago.** Radar is older still: Ramban's library ends **6 May**. Meanwhile
  **28 new radar passes (Ramban) and 12 (Vaishno Devi)** have landed, and NISAR has gone from 7 to
  **22 ready-made interferograms** over your sites.
- **Your top three, in order:** (1) approve the Python upgrade; (2) start Docker and press
  "Refresh cycle" once; (3) say go or no-go on the Ramban radar rebuild (~300 of your 8,000
  credits).

---

## 1. Catching up: where you left off

**Sessions 37–38 (7–15 Sep): Triund.** A fourth site (Triund, Dhauladhar) was set up, and a
terrain-and-rockfall screening was built for a trek dated 26 Sep: a dashboard, GPS files (GPX/KMZ),
offline maps with a satellite layer, and a one-page printable field card (§87). Two lessons came
out of it:
- the three rainfall products disagree **3.5×** on the same days over the same patch of ground;
- a patch shipped that blanked most of the dashboard. A new guard (`check_dashboard_render.py`)
  now actually *runs* the page before it is republished.

**August, briefly:**
- the flash-flood arm was built and validated against fatal events (§69–§75);
- Vaishno Devi's hazard map was found to score **worse than a coin flip**. That was recorded
  honestly and not tuned away (§79–§80);
- NISAR's L-band radar was shown to see through the vegetation that blinds Sentinel-1 on your own
  slopes (§81–§83);
- an affected-area layer (§84), control-panel fixes (§85), and a first security audit (§86).

**Unchanged honest limits:**
- Vaishno Devi's map is below chance (§80);
- the NISAR monsoon comparison is still unmeasured (§82);
- the inventory records *reports*, not landslides (§60/§83);
- radar noise is about 30 mm/yr (§78);
- the Triund screening has no accuracy score, by design (§87).

---

## 2. What changed while you were away (time, not code)

| What | Last refreshed | Today | Gap / note |
|---|---|---|---|
| Ramban live rainfall + alarm | as-of 8 Aug | DORMANT, E=0.936 at last run | **78 days stale** |
| Vaishno Devi live rainfall + alarm | as-of 8 Aug | WATCH, E=1.123 at last run | **78 days stale** |
| Tosh rainfall | as-of 8 Aug | no alarm (no hazard map yet, by design) | 78 days |
| Triund weather half | 15 Sep | — | 40 days; **its decision date (26 Sep) has passed** |
| Ramban radar library | through 6 May | **28 new passes at ASF**, newest 23 Oct | ~5.5 months |
| Vaishno Devi radar library | through 5 Aug | **12 new passes**, newest 23 Oct | ~2.7 months |
| Radar-watch file (feeds the dashboard pill) | 14 Aug | refreshed in scratch only, not overwritten | auto-refreshes on the next cycle |
| NISAR over both sites | 124 products, 7 interferograms | **282 products, 22 interferograms** | see below |
| HyP3 credits | ~7,900 (8 Aug) | **8,000**, login verified | full monthly allotment |
| Earth Engine login | — | **works** | verified read-only |
| Copernicus login (feeds daily rainfall) | — | **not verified** | lives in the MintPy container, so it needs Docker |

**NISAR gate check.** The plan said: wire NISAR in when there are ≥8 acquisitions on one
track/frame *and* the products are final.
- **Volume: met.** Ascending track 156 has **11** distinct dates; descending track 135 has **12**.
- **Final products: not met.** All 22 interferograms are still provisional (`PR`).

**Season context.** The monsoon is over. The alarm season starts on **1 April** (pre-monsoon slides
count; Digdol was 7 Apr 2026), so the every-2–3-days rainfall routine isn't needed again until
then. Winter is instead the best time for radar work: clear skies and stable ground give the
cleanest signal.

---

## 3. Testing: what I ran and what it showed

| Check | Result |
|---|---|
| Full battery, current env, before any change | **16/16 suites, 238/238** |
| Full battery, current env, after all changes | **16/16, 243/243** (5 new security tests) |
| Full battery, trial Python 3.12 env | **16/16, 243/243**, no warnings |
| Each new test, run against the OLD code | **fails**, as it must (proves the test can see the bug) |
| Control-panel suite, 5 back-to-back runs | **24/24 every time** (it used to flake; see finding 6) |
| Real end-to-end: launched the actual panel, drove it in a real browser | button click → **9/9 steps** ran; all **17** results-hub links streamed back byte-complete; Ramban's live dashboard rendered (**538 elements, 0 console errors**) |
| Triund dashboard render check | **634 elements**, OK |
| Live ASF / NISAR / logins under the upgraded clients | **identical results** to the current env |
| Data freeze (116 protected artifacts byte-identical) | **intact**: nothing in `data/` changed |

**Not done, and why:** the container battery. Docker was off, and by your standing rule I don't
start it. The native runs cover the same 16 suites, but the container run should be repeated once
Docker is up (one command, in §6).

---

## 4. Security audit

### 4a. What I found and fixed

| # | Finding (plain words) | How bad | Who could trigger it | Status |
|---|---|---|---|---|
| 1 | **The §86 "refuse other websites" check had a gap.** It let through requests labelled `Origin: null`, which is exactly what a sandboxed frame on any web page sends. | Medium | Any website you visit while the panel is running. It could start the 3 allow-listed Docker jobs: unwanted compute, not arbitrary commands. | **Fixed** + test |
| 2 | **The file route could be made to reach out over the network.** A request for `/file///some-host/share/x` became a Windows network path, and the panel *opened* it before refusing. Windows then tries to log in to that host, which can hand over a crackable hash of your Windows password. Measured: it hung **21 s** on an address that never answers. | Medium | Any website, via a hidden image tag. The hash only leaks if your network allows outbound file-sharing (port 445 / WebDAV). | **Fixed** + test |
| 3 | **The file route read whole files into memory** (logged in §66 as LOW, open since July). One request for a multi-GB raster could exhaust the panel. | Low–medium | Any website, via an image tag | **Fixed** (streams in chunks) + test |
| 4 | **The 3-D dashboard loaded Plotly from a CDN with no tamper check**, and the panel serves that page with the same powers as its job API. | Low (needs a compromised CDN) | — | **Fixed**: integrity hash, verified in a real browser both ways (the real file loads; a tampered hash is blocked). Plus a guard test that fails if any future CDN script lacks a hash. |
| 5 | Junk request values (`log_from=abc`, a bad `Content-Length`) crashed the request with no reply, and a negative length held a server thread. | Robustness only (a browser can't send these) | Local programs | **Fixed** + test |
| 6 | **The panel refused requests before reading their body**, so Windows sometimes reset the connection instead of delivering the "refused" reply. **2–3% of refused requests** (measured on the old code too, so it predates today), which made the §86 tests flaky. | Robustness (still a refusal) | — | **Fixed**: 0 resets in 600 |
| 7 | One docstring had `\f`/`\c` sequences: Python 3.12 warns, a future version will reject it, and today it silently holds a form-feed character. | Upgrade blocker | — | **Fixed** (raw string) |

### 4b. Still open

| # | Item | What it costs you | My recommendation |
|---|---|---|---|
| 8 | **Python 3.10 end-of-life on 31 Oct.** Google's client library already warns that it has dropped 3.10. | No more security fixes after this week | Upgrade (§5, item 1) |
| 9 | **Vulnerable libraries: 117 known advisories in the native env, across 19 packages.** Most sit in the Jupyter stack (jupyterlab, tornado, mistune…), which **no pipeline script imports**, and in Pillow (50, pulled in by matplotlib's PNG writer). The ones on real data paths: **GDAL 3.10.3 (7 advisories; it reads every downloaded raster)** and the network stack (urllib3, cryptography, certifi) under the ASF/Earth Engine clients. The Docker lock file carries GDAL, Pillow, urllib3 and certifi too. | Exposure when parsing downloaded files | The tested upgrade clears **all of it**: 0 advisories across 92 packages |
| 10 | Docker base image `micromamba:1.5.10` is from 2024 (§66). Its operating-system packages **couldn't be scanned** without Docker. | Unknown | Bump it in the same rebuild |
| 11 | `.env` holds **4 API keys the code never reads** (Planetary Computer, Sentinel Hub, Mapbox, OpenWeather), in plain text, inside a **OneDrive-synced** folder | Keys sit in Microsoft's cloud for no benefit | Delete those 4 lines; rotate any key that is still live |
| 12 | Node.js v22.14.0 (early 2025), used only by the dashboard render check | Low | Update when convenient |
| 13 | Two page generators (`aoi_status.py`, `agentic_orchestrator.py`) don't escape text | Informational: only our own code's text reaches them today | Escape first if outside text (news, ASF metadata) is ever routed into them |

### 4c. What held up (checked, not assumed)
- **No real secret has ever been committed**, on any branch. The nine "password" hits in history
  are all `YOUR_…` placeholders.
- No `shell=True` / `eval` / `pickle` / unsafe YAML.
- Archive handling is safe: zip members are written by bare filename; the GACOS tarball is read in
  memory and never extracted to disk.
- Static scan (bandit): **0 high, 3 medium, and all 3 are false positives.**
- §86's other guards still hold: the localhost-only `Host` check, the traversal guard, and the
  allow-listed actions.

---

## 5. Your blockers, in the order I'd tackle them

**1. Approve the Python 3.12 upgrade.** *This week; the deadline is 31 Oct.*
- Why it's yours: it changes your working env and the Docker images.
- Cost: about an hour, mostly waiting for the image build. Risk is low: the trial env already
  passes 243/243 and the live ASF/Earth Engine checks.
- Not yet proven on the trial: real downloads and Earth Engine data pulls. The first real refresh
  exercises those.
- **Recommendation: yes.** Recipe in §8.

**2. Start Docker, then press "Refresh cycle → All sites" once in the control panel.** *This week.*
- This closes out the 2026 season for Ramban and Vaishno Devi (8 Aug → ~20 Oct) and refreshes
  the radar pill and the status board.
- It is also the only way to verify the Copernicus rainfall login.
- Afterwards, run the container battery (§6, Phase A).

**3. Go / no-go on the Ramban radar rebuild.** *Next 2 weeks.*
- 28 new passes, roughly **28 pairs ≈ ~300 credits of 8,000**. Credits aren't the constraint.
  The real cost is a multi-session, you-present rebuild in MintPy (the field-standard radar
  processing package), across the Sentinel-1A → 1D satellite handover.
- Fold in the deferred §61 re-score at the same time.
- **Recommendation: go.** Winter has the best signal, and Ramban's map is the one that beats
  chance in its back-test (Vaishno Devi's does not, §80).

**4. Rule on two Vaishno Devi history rows.** *5 minutes each.*
- Bhawan rockfall: the GSI report says **30 Aug 2008** in its body and **30 Dec 2008** in its
  heading. Which one?
- Himkoti rockfall with casualties: **undated, before Jul 2017**. Keep it as "pending", or do you
  have a date?

**5. NISAR monsoon pilot: run it on provisional data now, or wait for final products?**
- It's one command, it **aborts honestly** if the data gaps are still there, and downloads are
  free (~1.8 GB each).
- **Recommendation: run it, labelled provisional.** Don't wire NISAR into the live product until
  final versions exist.

**6. Tosh: soil pass, inventory, and radar go/no-go.** *This winter; this has now been the
recommended next step for 4 sessions running.*
- A radar velocity baseline needs 2–3 months of data. To be ready for monsoon 2027, the radar
  decision should be made by about February.

**7. Clean `.env`.** *5 minutes.* Remove the 4 unused keys (finding 11) and rotate any that are
still live.

**8. Triund: archive the screening as historical, or set a new date.** The 26 Sep decision it was
built for has passed. The SP Kangra permission question only matters if there's a new trek.

**9. Low priority:** submit the GACOS web form (the helper prints the values), update Node.js, and
the Vaishno Devi radar rebuild (12 passes, ~120 credits) after Ramban.

---

## 6. Refresh plan: what to refresh, in what order

**Phase A, now (~1 hour, mostly waiting).** Start Docker yourself. Then:
- `control_panel.bat` → **Run refresh cycle (All sites)**. This fetches ERA5-Land rainfall,
  regenerates the alarms, refreshes the radar-watch file and the status board, and verifies the
  Copernicus login.
- Then run the container battery:
  ```
  docker compose run --rm insar bash -c 'for t in tests/test_*.py; do python "$t" || echo "FAILED $t"; done'
  ```

**Phase B, with the upgrade.**
- Rebuild both images.
- Rebuild the 3-D dashboards (panel → Rebuild 3-D dashboard). That also picks up the Plotly
  tamper pin; the existing `dashboard_3d.html` files keep the unpinned tag until rebuilt.

**Phase C, this winter (multi-session).**
- Ramban radar rebuild (28 passes), then Vaishno Devi (12).
- After each: 3-D dashboard, then the back-test re-score.
- Use the dry-run first (`submit_hyp3_jobs.py` without `--submit`). Each site's `search_end`
  must be extended past 23 Oct, because both windows currently end before the new passes.

**Phase D.** NISAR monsoon pilot:
```
nisar_coherence_pilot.py --season monsoon
```

**Phase E.** Verify any Aug–Oct 2026 landslides at Ramban and Vaishno Devi against 2+ independent
sources, so the 2026 season can be scored. This is a research session, under the
verified-ground-truth rule in CLAUDE.md.

**Don't refresh:**
- the 2–3-day rainfall routine, until **1 Apr 2027**;
- Triund's weather half, unless there's a new trek date.

---

## 7. Future scope

**This winter**
- The upgrade and image rebuild.
- Radar rebuilds.
- Tosh to monsoon-2027 readiness.
- **NISAR's descending track now has 12 dates.** That reopens the up/down vs east/west motion split
  (Area 2) that Sentinel-1's descending data was too noisy for.

**Next**
- Susceptibility model as a *corroborator*, never the headline (§83, `PIVOT_ANALYSIS`). The
  headline number is its accuracy *with elevation removed*.
- Flood arm phase F2: creep × flood undercutting.
- Per-zone rainfall from the 0.1° IMERG grid.
- Wire NISAR in live once final products exist (`NISAR_INGESTION_DESIGN.md`).

**Later**
- Hybrid LLM: rules decide, the LLM only narrates.
- A hosted dashboard.
- A Content-Security-Policy, which is now easier because the only CDN script is pinned.

**Hygiene (optional, manual):**
- re-run the pip-audit scan each quarter;
- pin the Docker base image by digest.

---

## 8. Appendix

**What changed in the repo today (uncommitted):**
- `workflows/control_panel.py`: findings 1, 2, 3, 5, 6.
- `workflows/build_3d_dashboard.py`: finding 4 (integrity pin + provenance comment).
- `workflows/watch_triage.py`: finding 7 (`r"""`).
- `tests/test_control_panel.py`: **+5 tests**: null Origin, network path, streaming, malformed
  input, CDN pin.
- Docs: this report, `docs/INDEX.md`, `RESULTS_AND_KPIS.md` §88, `error_history_log.md`,
  `SESSION_REVIEW.md` LIVE block.

**Outside the repo:** a trial conda env, `C:\Users\varun\.conda\envs\insar_trial_py312` (1.6 GB).
Delete it with:
```
conda env remove -p C:\Users\varun\.conda\envs\insar_trial_py312
```

**Upgrade recipe** (versions are the ones the trial actually tested):

| | current | tested |
|---|---|---|
| Python | 3.10.20 | **3.12.15** |
| GDAL | 3.10.3 | **3.13.3** |
| rasterio | 1.4.3 | **1.5.2** |
| numpy | 2.2.6 | **2.5.4** |
| scipy | 1.15.2 | **1.18.1** |
| geopandas | 1.1.3 | **1.2.0** |
| shapely | 2.1.2 | **2.2.0** |
| pyproj | 3.7.1 | **3.8.0** |
| matplotlib | 3.10.9 | **3.11.2** |
| hyp3_sdk | 7.7.6 | **7.7.8** |
| asf_search | 12.2.2 | **14.1.0** |
| earthengine-api | 1.7.29 | **1.7.49** |

1. **Native:** in `environment.yml`, set `python=3.12` and `gdal=3.13.*`, and drop `jupyterlab`
   (dev-only, and the source of most advisories; install it separately if you want notebooks).
   Recreate the env with conda 24.x. Your user-level conda is **4.12 (2022)**, whose solver
   your error log records hanging, so use `C:\ProgramData\anaconda3\Scripts\conda.exe`.
2. **Docker `insar` image:** in `docker/environment.docker.yml`, set `python=3.12.*`,
   `gdal=3.13.*`, `rasterio=1.5.*`, `geopandas=1.2.*`, `shapely=2.2.*`, `numpy=2.5.*`,
   `scipy=1.18.*`, `matplotlib-base=3.11.*`. Bump the `FROM` tag in `docker/Dockerfile` and the
   pip pins (`hyp3_sdk==7.7.8`, `asf_search==14.1.0`). Rebuild, run the battery in the
   container, then regenerate `docker/conda-linux-64.lock`.
3. **MintPy image:** stays on Python 3.11 + numpy<2 (that pin exists for a real MintPy bug, and
   3.11 is supported until Oct 2027). Just rebuild it to pick up patched libraries.

**Sources for the external facts:**
- PHP2Shell: [Canadian Centre for Cyber Security AL26-026](https://cyber.gc.ca/en/alerts-advisories/al26-026-critical-vulnerabilities-impacting-php-cve-2026-109618-cve-2026-109619),
  [Sophos](https://www.sophos.com/blog/proof-of-concept-exploit-released-for-php-vulnerabilities-109618-109619).
- Python 3.10 end of life:
  [HeroDevs guide](https://www.herodevs.com/blog-posts/python-3-10-end-of-life-october-2026-security-and-migration-guide),
  [Anaconda support policy](https://www.anaconda.com/docs/reference/policies-practices/python-version-support).
