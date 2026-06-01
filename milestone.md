# 🏔️ Project Milestones — Plain-Language Journey

This file is the **easy-to-read story** of the project: what we're building, what
we've achieved, and where we're headed — in everyday language, no jargon.

A new milestone is added here **each time a major step is completed**. For the
deep technical detail, see `session_journey.md` (decisions) and
`error_history_log.md` (bugs & fixes).

> 📚 **Want to understand the *science* behind these milestones?** See
> [Research/Foundations - Physics and Maths Primer.md](Research/Foundations%20-%20Physics%20and%20Maths%20Primer.md)
> — a beginner-friendly base in the physics & maths, built so you can confidently
> discuss this project with anyone.

---

## 🎯 The Goal (in one paragraph)

We're building an **early-warning system for landslides** along the **NH-44
highway through Ramban** (Jammu & Kashmir) — a stretch with a history of slope
failures, especially during monsoon. The big idea: radar satellites can measure
the ground shifting by *millimetres* from space. If a hillside is slowly
creeping, we want to catch it **before** it collapses.

**How it works, in one breath:** A radar satellite (Sentinel-1) flies over
Ramban every ~12 days. By comparing two passes, we measure how much the ground
moved in between. Stack many comparisons over months and you get a time-lapse of
the ground's motion — and from that, a yearly speed (millimetres/year) for every
spot on the hillside.

---

## ✅ Milestone 1 — Clean, Trustworthy Data  *(Phase 1 — completed 2026-05-28)*

**What we set out to do:** Get radar data over Ramban and, crucially, *throw away
the parts that lie*.

**Why it's hard:** Radar gets fooled by three things, and we had to defeat each:
- **Vegetation** — forests scramble the signal. → We deleted the unreliable pixels.
- **Weather** — water vapour in the air mimics ground movement. → We statistically
  detected and quarantined the contaminated images.
- **Timeline gaps** — the math needs an unbroken chain of dates, or it breaks
  silently. → We verified (with a network graph) that our data connects across
  the whole calendar, and patched the few weak links.

**What we ended up with:** 183 satellite image-pairs covering May–October 2025,
filtered down to a set where **every surviving measurement is real ground — not
trees, not clouds**. This is the clean fuel everything else runs on.

**Plain-language result:** We have a reliable record of how the ground around the
NH-44 corridor behaved through the 2025 monsoon.

---

## ✅ Milestone 2 — A Working "Movement Map" Engine  *(Phase 2 pathfinder — completed 2026-05-29)*

**What we set out to do:** Build the engine that turns the pile of image-pairs
into a single **velocity map** — how fast each point on the ground is moving per
year. We tested it on our cleanest patch of data first (a "pathfinder" run).

**What we found along the way (the honest version):**
1. **A weeks-old mystery bug, finally solved.** Crashes that had haunted the
   project turned out *not* to be a real software bug — we'd just been starting
   the program the wrong way, so it couldn't find its math libraries. A tiny fix
   ended a long headache.
2. **The first map was nonsense — and that was useful.** It showed the ground
   moving ±300 mm/year (physically impossible). We diagnosed it: we'd skipped a
   standard cleanup step. Each radar image had a built-in "tilt" (from the
   satellite's orbit and the atmosphere) that the math mistook for real motion.
   Once we removed that tilt, the numbers snapped into a believable range **and
   10× more usable pixels appeared.**
3. **A lesson we keep relearning:** when a result looks wrong, check the raw
   ingredients *before* adding more filters. Twice now, the real problem was
   upstream.

**Plain-language result:** The engine works. On our test patch it produces a
sensible movement map — most ground is stable, and the map is ready to hunt for
the few spots that are creeping. There's still some background "fuzziness"
(~30 mm/year of noise) we may tighten later, but the foundation is solid and
validated.

---

## ✅ Milestone 3 — From Movement to a First Hazard Map  *(Phase 3 pathfinder — completed 2026-05-29)*

**What we set out to do:** combine the *movement map* (Milestone 2) with the
*shape of the land* and a bit of *physics* to answer the real question: **is this
hillside close to failing?**

**How it works, plainly:**
- We took the terrain's **steepness** (slope) — steeper = more dangerous.
- We estimated where **water collects** (a "wetness index") — wetter ground is
  weaker.
- We ran a textbook slope-stability calculation (the **"Factor of Safety"**): if
  the forces pulling a slope down beat the forces holding it together, the number
  drops below 1 and the slope is, in theory, unstable.
- We did this for **two situations**: a **dry** slope and a **monsoon-soaked**
  slope — to bracket the seasonal danger.
- Finally, the headline step: we **fused the physics with the real measurements.**
  A slope flagged as theoretically unstable *and* one we actually measured
  creeping = the highest concern.

**What we found:**
- The terrain is genuinely steep (median slope ~28°).
- **Dry:** most slopes are stable (~13% unstable).
- **Monsoon-soaked:** the picture flips — ~73% of slopes become theoretically
  unstable. This is the qualitative warning the project is built to surface:
  water is the trigger.
- About **2,600 pixels** are flagged HIGH — unstable *and* measurably moving.
  The most trustworthy of these form coherent clusters (small zones ~0.2 km²);
  the rest are scattered single-pixel "specks" that are likely noise.

**Plain-language result:** **The full chain now works end-to-end — from raw radar
all the way to a hazard map.** This was the goal of building a thin "test slice"
first. And it did its job: it shows us the map currently flags *too much*, mostly
because our terrain data is coarse (80 m) and the movement signal still has some
noise. We now know *exactly* which links to strengthen next — which is far more
useful than guessing.

**Honest caveats:** the soil strength numbers are textbook assumptions, not
measured for Ramban; the terrain is coarse; and the "highest concern" pixels are
trustworthy mainly where they cluster, not as isolated specks. This is a *first
rough hazard map*, not a validated forecast.

---

## ✅ Milestone 4 — A Working Warning System (Demo)  *(Phase 4 Part A — completed 2026-05-29)*

**What we set out to do:** turn the hazard map into an **automated warning
system** you can actually show someone — software that *reasons* about the data
and raises alerts, instead of a human squinting at a map.

**How it works, plainly — three "agents" working together:**
- **Agent 1 (the InSAR Auditor)** reads our movement map and picks out the ground
  that's genuinely *creeping*.
- **Agent 2 (the Weather Trigger)** looks at a rainfall scenario — *dry*,
  *monsoon*, or *extreme* — and decides how water-logged (and therefore weak) the
  slopes are.
- **Agent 3 (the Cascading Reasoner)** combines the two: where a slope is *both*
  physically unstable *and* measurably moving, it raises an alert — grouping
  nearby danger pixels into **zones**, pinpointing each on the map, writing a
  plain-English reason, and flagging if a failure could send debris down to the
  valley (a "downstream risk").

**What we found — the weather trigger visibly drives the system:**
- **Dry day:** only **29** alert zones (~0.85 km²) — most slopes hold.
- **Monsoon:** jumps to **222** zones (~7.7 km²), 104 of them "critical" — the
  rain soaks the slopes and the danger lights up.

That jump *is* the whole point: it shows the system responding to the trigger,
exactly like a real early-warning tool should.

**What you can actually see:** for each scenario the system writes a
**self-contained dashboard** (`data/alerts/dashboard_<scenario>.html`) that opens
in any web browser — a colour-coded hazard map with numbered alert markers, and a
side panel where each alert explains itself in plain language (location, how fast
it's moving, why it's flagged, downstream risk). There's also a machine-readable
alert file and a written briefing for each scenario.

**Plain-language result:** **the full vision now runs end-to-end as a demo** — from
raw satellite radar all the way to an automatic, explainable landslide warning
that reacts to rainfall. It's an MVP: deterministic rules (not yet a fancy AI
"brain"), one satellite track, and assumptions baked in — but the complete story
is now showable, start to finish.

**Honest caveats:** the rules are fixed logic, not a learning AI; the rainfall is
a *what-if* scenario, not a live forecast yet; alerts only exist where we have
movement data (~14% of the area — *unmeasured ≠ safe*); and the "downstream risk"
flag is a rough rule of thumb pending real river-flow modelling.

---

## ✅ Milestone 5 — Seeing It in 3-D  *(Phase 4 Part B — completed 2026-05-29)*

**What we set out to do:** give the warning system a proper *face* — an
interactive, three-dimensional view of the terrain you can spin around, with the
danger zones standing out on the actual mountain shape.

**What we built:** a single web page (`data/alerts/dashboard_3d.html`) that opens
in any browser and shows the **Ramban terrain in 3-D** — the real ridges and
valleys of the Chenab gorge, drawn from the elevation data. On top of it:
- the ground we've **measured creeping**, as a toggle-able layer;
- the **alert zones**, as markers you can hover to read each one's plain-English
  reason (location, how fast it's moving, why it's flagged, downstream risk);
- **rainfall-scenario buttons** — click *Dry → Monsoon → Extreme* and watch the
  alert markers multiply across the slopes as the rain soaks in.

You can drag to orbit, scroll to zoom, and fly around the valley — the danger
sits on the real 3-D landscape instead of a flat map.

**How we built it (a deliberate choice):** instead of a heavy server app, it's a
**self-contained web page** — no new software to install, nothing that could
destabilise our carefully-built analysis environment, and it works by just
double-clicking the file. Same interactive 3-D experience, far less risk.

**Plain-language result:** the project now has a **complete, showable face** — not
just numbers and files, but a 3-D landscape you can explore, where the rainfall
slider visibly drives the danger. This is the piece that makes the whole thing
*demonstrable to anyone*, expert or not.

**Honest caveats (unchanged):** it visualises the same MVP data — one satellite
track, ~14% coverage, assumed soil strength, heuristic downstream flag. A
prettier picture doesn't add certainty; it makes the existing findings easier to
see and discuss.

---

## ✅ Milestone 6 — Packaged So It Runs Anywhere  *(Docker — completed 2026-05-30)*

**What we set out to do:** put the whole project inside a "shipping container" so it
runs *identically* on any computer — and, just as importantly, escape the
Windows-only glitches that had cost us the most time all project long.

**What we did, plainly:** we built a self-contained Linux box (a Docker *image*)
that carries the exact software the pipeline needs. The big data and the code stay
on your machine and are "plugged in" to the box when it runs, so the box itself
stays small and nothing big is ever copied around.

**What we found:** every stage we'd already built ran *first try* inside the box —
and the nastiest recurring crash (the one where the maths libraries couldn't be
found on Windows) simply **cannot happen** in there. We confirmed the full chain
reproduces the same results in the container.

**Plain-language result:** the project is now **portable and reproducible** — anyone
can rebuild the exact environment from one recipe. This is also the home turf for
the professional tool we adopt later (MintPy).

---

## ✅ Milestone 7 — Point It at Any Valley, and Widen the Map  *(AOI refactor + multi-stack — completed 2026-05-30)*

**What we set out to do:** two things. (1) Stop the pipeline being hard-wired to
Ramban so we can aim it at a *new* valley by editing a simple settings file. (2)
Widen the map by using *more than one* satellite viewing track instead of a single
test patch.

**What we did, plainly:**
- **A settings file (`config.yaml`)** now holds the area, the dates, and the rules —
  change it and the whole pipeline follows, with no code edits. The way we label
  each satellite track was rebuilt to read the satellite's own metadata instead of a
  Ramban-specific shortcut, so a new area won't silently break it.
- **A smarter "gap-bridging" step.** The maths needs an unbroken chain of dates; a
  few weak links must be "rescued" to bridge gaps. We made this *automatic* and, more
  importantly, *safe*: it only ever bridges a gap with a **clean-enough** link, and
  if the only available link is too noisy it **refuses** (that stretch is handled a
  different way instead of poisoning the result). We also taught it to prefer the
  link that keeps the **most usable ground**, after we caught it once choosing a
  "cleaner but emptier" link that quietly halved the coverage.
- **Three tracks instead of one.** We processed three ascending satellite tracks and
  **combined** them into one area-wide danger map. The rule is honest about physics:
  because each track views the slope from a different angle, we don't blur their
  speeds together — instead a spot is flagged if **any** track sees danger, and spots
  confirmed by **two or more** tracks are highlighted as the most trustworthy.

**What we found:** the wider map flags more of the corridor (as expected with more
coverage), and crucially it now has **corroboration** — dozens of danger spots are
independently confirmed by multiple satellite views.

**Plain-language result:** the system is no longer a one-valley, one-track demo. It
can be **aimed at a new area from a settings file**, and it now produces an
**area-wide, cross-checked** danger map. Two descending tracks are still waiting —
they need a more advanced maths trick that the professional tool (next milestone)
provides for free.

**Honest caveats:** still the same assumed soil strengths and coarse (80 m) terrain;
the descending tracks aren't in yet; and "combining views" is done at the
danger-flag level, not yet as a full 3-D motion reconstruction.

---

## ✅ Milestone 8 — Bringing In the Industry-Standard Tool  *(MintPy: image + first run + cross-check, 2026-05-31)*

**What we set out to do:** begin adopting **MintPy** — the peer-reviewed, field-
standard package the experts use — to harden our home-built movement engine and,
later, to scrub out the atmosphere's interference (which sets our current accuracy
limit).

**What we did, plainly:** we built MintPy its own self-contained box (kept separate
so it can't disturb our working pipeline), and we set up the **weather-data
credentials** it will use to download atmospheric readings and subtract them — you
added your access token, and we ran a tiny test that confirmed the download works
end-to-end. We also arranged things so the credentials are remembered automatically
and never get committed anywhere public.

**Then we actually ran it:** MintPy successfully turned our radar pairs into a
movement map for the test patch — the key proof that the field-standard tool accepts
our data and pipeline. We compared its answer to our home-built engine: they **agree
in direction, but only weakly so far**. That's *expected*, not a worry — we ran MintPy
with its atmosphere-scrubbing still switched **OFF** (the very next step), so both
maps are still atmosphere-dominated and handled differently. Two fiddly setup snags
(a file-timestamp quirk on the synced drive, and a clash with too-new Python/maths
libraries) were diagnosed and fixed along the way.

**Where this leaves us:** the professional tool now demonstrably **works on our
data**. Next we switch **on** the atmosphere-scrubbing (using the weather credentials
we set up) and re-compare — the run expected to actually *sharpen* the numbers — then
bring in the two remaining satellite tracks.

**Plain-language result:** a real milestone — the field-standard tool runs on our
Ramban data end-to-end and produces a movement map. The current headline results are
unchanged; we've proven the path to sharper, more defensible numbers and know exactly
what to turn on next.

---

## ✅ Milestone 9 — Scrubbing Out the Atmosphere  *(MintPy ERA5 correction, 2026-05-31)*

**What we set out to do:** switch **on** the part of MintPy that physically removes the
atmosphere's interference — the single biggest thing limiting how small a movement we
can trust — and prove it actually sharpens our numbers.

**How it works, plainly:** the air (water vapour, temperature, pressure) slightly delays
the radar signal on each pass, and that delay *masquerades* as ground movement. Until now
we fought it statistically — spotting and discarding suspicious images. MintPy does
something better: for each satellite pass it pulls that day's **global weather record
(ERA5)**, calculates exactly how much delay the air added, and **subtracts it** — keeping
the image instead of throwing it away. We first ran a tiny test to confirm the weather
download works against the new data service, then ran the full correction on our test
patch (it fetched 15 days of weather automatically).

**What we found (a clear, honest win):**
- Compared to our independent home-built engine, agreement **nearly doubled** once the
  atmosphere was removed (a correlation of ~0.28 jumped to ~0.55 on the same ground).
  That jump is the proof that the earlier disagreement *was* mostly atmosphere, not real
  motion.
- MintPy's own background "fuzziness" **dropped from ~39 to ~21 mm/year** — better than
  our custom engine's ~31 — exactly what you'd expect when you physically remove the haze
  rather than just blur it out.
- Two completely independent movement engines now **agree with each other** (~0.55–0.59),
  which is the kind of cross-check that turns "a result" into "a trustworthy result."

**Plain-language result:** the professional atmosphere-scrubbing **works on our data and
demonstrably sharpens it.** This is the most important accuracy upgrade in the project so
far — it lifts the ceiling on how slow a creep we can believe.

**Honest caveats:** this is proven on **one** satellite patch so far, and the sharper
numbers haven't yet been pushed through the hazard/warning maps (those still use the
home-built movement map). The two remaining "descending" tracks are next.

---

## ✅ Milestone 10 — Testing the Descending Tracks, and Refusing Bad Data  *(MintPy DESC evaluation, 2026-05-31)*

**What we set out to do:** add the two **descending** satellite views (the radar looking
from the other side) to the three ascending ones. Having both directions is what would let
us split the motion into true up/down vs sideways — the big interpretation upgrade.

**What we found — and the honest call we made:** both descending tracks turned out to be
**too poor to trust**, and after a careful, fair test we **rejected them** rather than let
bad data into the results:
- **Track A (frame484)** was so scrambled by vegetation/terrain that there wasn't a single
  reliable anchor point anywhere in the scene — only ~1% of it was usable. Unusable.
- **Track B (frame479)** *looked* promising (it processed almost completely), but its
  movement numbers were physically impossible — thousands of points "moving" faster than
  10 cm/year. We traced this to the data being broken into time-gaps the maths can't bridge
  reliably. We tried the textbook fix (analyse only the unbroken monsoon stretch on its
  own) — and it got **worse**, because a shorter time window magnifies noise. That told us
  the noise is in the *data*, not the method.

**Why this is a win, not a setback:** the ascending tracks over the same ground are **2–5×
cleaner**. A real movement signal wouldn't look five times noisier just because you view it
from the other side — so the descending numbers are noise, and including them would have
*degraded* a good result. Knowing when to **throw data away** is exactly the discipline that
separates a credible tool from a pretty one.

**Plain-language result:** the area-wide product stands on the **three ascending tracks**
(plus the atmosphere-sharpened cross-check from Milestone 9). The up/down-vs-sideways
decomposition is **deferred** until we can get better descending data (a longer, unbroken
series, or point-like reflectors on rock and infrastructure).

---

## ✅ Milestone 11 — From a Hazard Map to a Failure *Forecast* (the method)  *(Inverse-velocity, 2026-05-31)*

**What we set out to do:** take the biggest conceptual step — stop only saying *where* a slope
is dangerous and start estimating *when* it might fail — using the movement history we already
have, no new data.

**How it works, plainly:** there's a classic landslide-forecasting trick (the "inverse-velocity"
method). As a slope accelerates toward collapse, plot **1 ÷ its speed** over time and it falls in
a straight line; the moment that line hits zero is the projected failure time. The beauty is it
needs nothing new — just the per-point movement timeline we already produce. We built this as an
automatic screen over every flagged danger zone.

**A bug we caught on ourselves (and why it matters):** the first version confidently announced
"7 zones will fail in 11–51 days." We didn't believe it — and we were right: those zones were
actually drifting the *wrong way* (toward the satellite, not downslope), and the method had been
fooled by noise. We'd (a) blurred each small zone with its calm neighbours and (b) let the maths
cherry-pick the few noisy dips that looked like acceleration. We tightened it so a zone must be
*genuinely and consistently* sliding downhill before any failure date is even computed. After the
fix: **zero false alarms.**

**What we found (the honest answer):** across all three ascending tracks and every danger zone —
**nothing is accelerating.** The flagged slopes are creeping *steadily*, not speeding up toward
imminent failure, over our ~3.5-month window. That's the correct, cautious result: steady creep
is normal until a trigger (like a big storm), and clear run-away acceleration is rare and needs a
longer record to see. **"Steady" is not "safe"** — the screen is deliberately conservative
(better to miss than to cry wolf).

**Plain-language result:** the project now has the **forecasting machinery** in place, validated
and noise-hardened. It currently (honestly) returns "no imminent acceleration," and it will
automatically start projecting failure dates the moment the data shows one — as the time series
grows, or if a real event begins.

---

## ✅ Milestone 12 — Real Rain Instead of Guesswork  *(Live rainfall + trigger thresholds, 2026-05-31)*

**What we set out to do:** stop *assuming* the rain. Until now the danger map was driven by
made-up weather ("a dry day," "a monsoon day with 120 mm"). We replaced that with the **actual
rainfall that fell** over the area, and the **standard scientific rule** for when rain triggers
landslides.

**How it works, plainly:** we pulled the real day-by-day rainfall for the Ramban area across the
whole 2025 wet season (May–October) from a global weather record. Then we applied the textbook
**"intensity–duration" rule**: heavy rain over a short time is far more dangerous than the same
total spread over weeks, so there's a known line — *this much rain, this fast* — above which
slopes have historically failed. We checked every stretch of the season against that line.

**What we found (a sharp, real answer):** the season dropped **1,233 mm**, but the
landslide-triggering rain was **one single day — 26 August 2025** — when ~**134 mm** fell in a
day (183 mm over two days), punching above the danger line. The rest of the monsoon, though wet,
stayed below it. This is exactly the correction real data gives you: not a vague "monsoon is
dangerous," but a **specific date** to focus on — and the obvious next thing to check against
records of what actually happened on the ground around then.

**Honest caveats:** the rainfall record we used is modelled and tends to *under*-count the
intense bursts that mountains squeeze out of storms — so a rain-gauge-based product (the planned
cross-check) would likely flag *more* trigger days, not fewer. And we used a conservative *global*
danger line; a Himalaya-specific one would be more exact. We also haven't yet fed this real
wetness back into the slope-stability sums (that's the very next step) — but the daily wetness is
already computed and waiting.

**Plain-language result:** the warning system is now driven by **what the sky actually did**, and
it pinpoints the real trigger moment of the season. The mock weather scenarios are on their way
out.

---

## ✅ Milestone 13 — The Warning Now Breathes with the Weather  *(Rainfall coupling + hazard timeline, 2026-05-31)*

**What we set out to do:** feed the *real* rainfall (Milestone 12) straight into the slope-safety
sums, so the danger map is driven by what the sky actually did — and, better still, show how the
danger **changes day by day** across the season instead of as three frozen "what-if" maps.

**How it works, plainly:** the slope-safety score depends on how water-logged the ground is. We
already had two reference maps — bone-dry and fully-soaked — and it turns out the in-between is a
simple straight-line blend, so for any day's real wetness we can mix the two to get that day's true
safety map (no expensive recompute). We then walked through every day of the 2025 wet season,
mixed the map for that day's wetness, and counted the danger zones.

**What we found (a living hazard curve):** the number of danger zones **rises as the monsoon soaks
in, peaks at 222 right on 26 August** — the real cloudburst day — then **fades as the ground dries
out** over the following weeks, with a little bump when late-September rain returns. Before the
monsoon it sits around 30–65 zones. So instead of a flat "monsoon = dangerous," we now have a
**timeline of danger that tracks the actual weather**, and we can point to the exact day it peaked.

**Plain-language result:** the warning system is no longer fed made-up weather at all — it runs on
the real rainfall, and it now has a **time dimension**: you can watch the hazard build and recede
with the season. There's a ready-to-open dashboard for the real trigger day (26 Aug) and a
season-long hazard chart.

**Honest caveats:** on the peak day the ground is fully soaked, so that single map matches the old
"monsoon" one — the new value is that it's tied to the *real* event and, crucially, the *timeline*.
The wetness is still a *relative* index (not a calibrated soil-moisture measurement), and it feeds a
slope calculation that still uses textbook soil strengths — both on the upgrade list.

---

## ✅ Milestone 14 — The First Reality Check  *(Back-test against documented landslides, 2026-06-01)*

**What we set out to do:** stop marking our own homework. Compare what the system flags against
**records of landslides that actually happened** on the Ramban highway — the step that separates a
plausible-looking map from a *trusted* one.

**What we found (two answers, both honest):**
- **Place — promising.** The danger zones our system flags **line up with the notorious, decades-old
  landslide black-spots** of the NH-44 (Panthyal, Khooni Nallah, Digdol, Maroog, Cafeteria Morh…):
  8 of 9 documented spots sit within ~2 km of a flagged zone. So the map points at the *right
  ground*. (Caveat: we flag a lot of ground, so this is encouraging but not yet proof — a full
  scored test needs the official Geological Survey of India inventory, ~302 mapped Ramban slides.)
- **Timing — caught a real problem.** Our rainfall-trigger picked **26 August**, but the big
  documented 2025 failures on this stretch were in **late April and early May** — months apart. The
  back-test thus did its job: it **revealed that our weather trigger is mistimed** for this corridor.
  Two clear reasons: our analysis window only starts 1 May (so it misses the April disaster), and the
  global weather dataset we used *under-counts* the intense mountain cloudbursts that actually set
  off the May slide.

**Why this is exactly what we wanted:** a validation step that only ever said "looks great" would be
useless. This one flagged a genuine weakness and **told us precisely how to fix it** — start the
clock in April and switch to a rain-gauge-based product (and a Himalaya-specific trigger curve) — then
re-test. Honest science moves forward by finding its own gaps.

**Plain-language result:** the hazard **map** is spatially credible (it flags the known black-spots),
but the **timing** of the rainfall trigger is **not yet validated** — and we now know the two concrete
changes that should fix it. That's a real step from "rough map" toward "validated forecast."

**Honest caveats:** the locations we compared against are *approximate* (from news + documentation,
not field-surveyed coordinates); the rigorous spatial score awaits the official GSI inventory.

---

## ✅ Milestone 15 — Which Way Is the Hill Actually Sliding?  *(Slope-parallel velocity, 2026-06-01)*

**What we set out to do:** our radar only measures motion *along its own line of sight* — a slanted
direction set by where the satellite sits, not "downhill." A creeping slope actually slides *down the
hill*, so we wanted to convert the slanted radar speed into the **true downslope speed**, using the
shape of the land (steepness + which way each slope faces).

**How it works, plainly:** for every point we know two directions — the way the radar looks, and the
way the hill falls. The radar only "feels" the part of the motion that lines up with its view. So we
divide the measured speed by how well the two directions line up, to recover the full downslope speed.
Where the hill happens to slide *across* the radar's view, the radar is nearly blind to it.

**What we found — two honest, useful results:**
- **A blind-spot map.** Between **a quarter and 42%** of the measured ground has its downhill direction
  pointing almost sideways to the radar — so its movement is **under-counted or invisible** from this
  one satellite track. We can now show *exactly where* we're flying blind, instead of pretending the
  map is uniform. (This is the well-known limit of using a single viewing direction.)
- **Sharper creep.** Converting to true downslope speed **magnifies the motion by about 1.4–1.6×**
  (because the radar was only catching part of it), which sharpens both the creep map and the
  failure-timing method. On two tracks it even revealed extra creeping ground the line-of-sight view
  had under-counted.

**Plain-language result:** we now read the hillside's motion in the direction that actually matters —
**downhill** — and we're honest about where one satellite track can't see. It's the cheap, single-view
stand-in for the full up/down-vs-sideways reconstruction that's still waiting on better descending data.

**A bonus we didn't expect:** when we rebuilt the whole area-wide map this "downhill" way, the number of
danger spots **confirmed by two independent satellite views jumped by over a third** (291 → 399). The
reason is neat: by translating each view's slanted reading into the *same* common "downhill" language,
the two views start describing the same motion — so they agree far more often. Downhill-projection
doesn't just sharpen the numbers, it makes our most-trustworthy (multiply-confirmed) flags more numerous.
This is wired in as an optional mode; the original map is kept untouched alongside it.

---

## ✅ Milestone 16 — Adding Snowmelt and the Cold — and What It Taught Us  *(Snowmelt/freeze-thaw drivers, 2026-06-01)*

**What we set out to do:** the previous reality-check (Milestone 14) caught our rainfall trigger firing
in **August**, while the real 2025 disasters were in **April–May** — the Himalayan **snowmelt season**.
The obvious suspect: we were only counting *rain*, ignoring the water from **melting snow** and the
slope-weakening of repeated **freeze–thaw**. So we added both, and started the clock in **April**.

**What we did, plainly:** we pulled the real day-by-day **snowmelt** and **temperature** for the area
(same weather service we already use), added the meltwater to the rainfall as the total water soaking
the slope, and flagged days that swing across freezing. Then we re-ran the danger map and the
reality-check.

**What we found — an honest, instructive result (not the fix we hoped, but a sharper diagnosis):**
- The snowmelt is **real but small** — about 59 mm for the whole season (against 1,350 mm of rain),
  mostly in early April. That's nowhere near the heavy-downpour line that the standard trigger needs,
  so it **didn't create a new trigger day**, and the April–May events were **still missed** by the
  trigger.
- Freeze–thaw, measured as the area's *average* temperature, **never crossed freezing** in our season
  — because the warm valley floor drowns out the cold high slopes in the average. (Catching
  high-mountain freeze–thaw properly needs temperature *by elevation*, which we noted for later.)
- **But** when we let the real spring weather drive the *danger map* (not just the trigger), the map
  **does light up in spring** — up to 136 danger zones in late April — so the hazard picture is right;
  it's specifically the *rainfall trigger* that's mistimed.

**Why this is genuinely valuable:** it **narrows down the real culprit.** The April–May failures
weren't missed because we forgot snowmelt — they were missed because the global weather record we use
**badly under-counts the intense mountain cloudbursts** that actually set off those slides (it logged
barely 9 mm on a day the news reported mudslides). So the fix is now crystal-clear and pinpointed:
switch to a **rain-gauge-based rainfall product** with a **Himalaya-specific trigger line**. Honest
science is as much about ruling things *out* as ruling them in — and the snowmelt/freeze-thaw machinery
is now built and ready for the day we feed it sharper, elevation-aware data.

**Plain-language result:** we added the two missing natural drivers and started the clock in April; the
danger map now breathes with the real spring weather, and we've **precisely identified** why the
*trigger* still misses the spring events — pointing straight at the next, well-defined fix.

---

## 🧭 Where We're Headed Next

Almost the entire original "what's next" list is now **done**: a 3-D face (Milestone 5),
clean packaging (6), point-it-anywhere + a wider 3-track map (7), the pro tool installed
and cross-checked (8), its **atmosphere-scrubbing switched on and shown to sharpen the
numbers (9)**, an honest **evaluation (and rejection) of the descending tracks (10)**, the
**failure-forecasting method built and noise-hardened (11)**, **real rainfall + trigger
thresholds replacing the mock weather (12)**, **real rain driving a time-resolved hazard (13)**,
and a first **reality-check back-test against documented landslides (14)**. What remains is mostly
*deepening trust* and *going live*:

- **Fix the trigger timing the back-test exposed.** Start the analysis window in April and switch to
  a rain-gauge product (CHIRPS/GPM) + a Himalaya-specific trigger curve, then re-run the back-test;
  and bring in the official GSI inventory (~302 mapped slides) for a properly-scored spatial test.
- **Better descending data for a true 3-D motion split.** Today's two descending tracks
  were rejected as too noisy (Milestone 10); the up/down-vs-sideways reconstruction waits
  on a longer unbroken series or point-like (persistent-scatterer) reflectors.
- **Finer terrain.** Swap the coarse (80 m) elevation for 12.5 m so the steepness —
  and therefore the danger calculation — is sharper and flags less spurious risk.
- **One combined 3-D face.** Extend the 3-D explorer to show the whole area-wide,
  multi-track map (today's 3-D view is the single test patch).
- **Make it live.** Real weather forecasts instead of *what-if* scenarios, real
  river-flow modelling for the downstream-risk flag, and a genuine reasoning AI in
  place of the fixed rules.

**Bottom line:** the entire vision — raw radar → movement → physics → explainable,
rainfall-driven warning — works **end to end**, now **portable, point-anywhere, and
multi-track**. Everything ahead is deepening trust (the pro tool, finer data, the
remaining tracks) and going live, not inventing new pieces.

---
