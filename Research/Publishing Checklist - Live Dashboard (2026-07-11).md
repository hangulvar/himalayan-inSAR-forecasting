# Publishing Checklist — Operational Alarm Dashboard → the public web (LinkedIn / X)

Target artifact: `data/alerts_vaishnodevi/mosaic_asc/operational_alarm_dashboard_vaishnodevi_2026.html`
(single self-contained ~88 KB file; everything inline, calendar PNG embedded as base64).
All "DONE" items live in the **generator** (`workflows/operational_alarm.py`), so every future
regeneration — including Ramban's dashboards — keeps them.

## ✅ DONE (implemented + browser-verified 2026-07-11)

- **Research-prototype disclaimer** — prominent amber strip under the tabs + repeated in the footer
  and the Guide's About card: *not an official warning system, not affiliated with SMVDSB/GSI/NDMA,
  static snapshot, do not use for safety decisions.* Non-negotiable for a public "alarm" page about
  a pilgrimage site.
- **Data attributions (license-required)** — footer + Guide card: "Contains modified Copernicus
  Sentinel-1 data (2025–26)" (ESA requirement), C3S ERA5-Land (Copernicus requirement), ALOS PALSAR
  RTC © JAXA/METI via ASF, GSI records, © OpenStreetMap contributors (ODbL).
- **Mobile rendering** — `<meta name="viewport">` added (was missing — page rendered desktop-zoomed
  on phones); wide tables scroll inside their card; verified at 375 px: no page-level horizontal
  scroll. Most LinkedIn/X clicks are mobile.
- **Social-link unfurl metadata** — Open Graph `og:type/title/description` + Twitter `summary` card.
- **Guide tab** (plain-language how-to-read, from the earlier UX pass) — essential for a lay audience.
- **Confusing artifacts fixed** — events table no longer prints `None` for the pre-season 2025 event
  (now "before this season's data window"); dead per-stack links fixed (derived from disk); footer is
  site-aware.

## 👤 USER-SIDE — before/at publish time

1. **Hosting (recommended: GitHub Pages or Netlify — free, static).** Copy the HTML as `index.html`
   into the site root. ⚠ The two per-stack map links ("Zoom in") are RELATIVE
   (`../ASC_path100_frame103/dashboard_operational.html`): either upload the
   `alerts_vaishnodevi/ASC_*/dashboard_*.html` files in the same relative structure, or accept the
   links 404 (they're secondary).
2. **After hosting, fill the two placeholder meta tags** (marked with an HTML comment in `<head>`):
   `og:url` (the final URL) and `og:image` (a hosted 1200×630 screenshot PNG — data: URIs don't work
   for unfurls). Then validate the unfurl with LinkedIn Post Inspector / X Card Validator.
3. **Author credit** — decide how you want to be identified (name / LinkedIn / GitHub repo link) and
   add one line to the footer or the About card in `operational_alarm.py`. Deliberately not
   pre-filled.
4. **Post framing (matters as much as the page):** present it as an *engineering/research portfolio
   piece* — "I built an explainable landslide-monitoring prototype from free satellite data" — NOT as
   a warning or prediction about the shrine. Avoid leading with the current WATCH state; lead with
   the method. Never imply SMVDSB/GSI endorsement.
5. **Staleness plan** — the page is a snapshot (rainfall lags ~5 days, radar 12-day cadence). Either
   state the snapshot date in the post, or re-upload after each `live_alarm.py` run (manual is fine;
   CI republish is a later nicety).
6. **Optional courtesy** — consider sharing with a GSI/SMVDSB contact before wide posting; the page
   names their programmes (factually, from public records).
7. **Nice-to-haves (not blockers):** favicon; a hosted OG screenshot that shows the banner + map
   cards; publishing the Ramban dashboard alongside (it inherits all of the above on next
   regeneration).

## Repo pointer

Findings ledger: `RESULTS_AND_KPIS.md` (the § references on the page). If the repo itself will be
linked publicly, skim it for anything you consider private first (it is already free of credentials
by design — `.env`/netrc are git-ignored).
