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

## ✅ Milestone 17 — A Himalaya-Tuned Trigger Line (and a Gauge-Rain Pipe)  *(Regional I–D curve + GEE CHIRPS, 2026-06-02)*

**What we set out to do:** Milestone 16 pinned the blame for the missed April–May 2025 disasters on two
things: a **trigger line copied from a *global* average** (far too cautious for these mountains), and a
weather record that **under-counts mountain cloudbursts**. This milestone tackles both: swap in a
**Himalaya-specific trigger line**, and build the pipe to bring in **rain-gauge-based** rainfall.

**What we did, plainly:**
- We looked up the **published rainfall trigger line for the Northwest Himalaya** (from a 2025 study of
  real Indian landslides) and a **cross-check study for our exact road**, the NH-44 Udhampur–Banihal
  stretch that runs through Ramban. Both agree the danger line here is about **15–19 mm of rain in a day**
  — versus the global textbook value of about **100 mm/day** we'd been using. Roughly **five times** too
  cautious. We made the trigger line a simple switch, so we can run either the old global line or the new
  regional one.
- We built the plumbing to pull **CHIRPS** — a rainfall product that blends satellite estimates with
  *ground rain-gauge readings* — for our area, day by day, from Google Earth Engine. It drops into the
  exact same slot our old weather data used, so everything downstream just works.

**What we found (a real, measurable result — with an honest catch):**
- Just switching to the **regional trigger line** — *without any new rainfall yet* — flips the
  reality-check from **0 of 2** documented spring events caught to **2 of 2**. So a big part of the
  problem really was the over-cautious global line, exactly as diagnosed.
- **The honest catch:** the regional line is *so* sensitive that it now flags **112 of 214 days** as
  "trigger" days. When more than half the season is a trigger, "we caught the event" almost can't fail —
  it's **sensitive but not yet *selective***. A genuinely useful warning needs the sharper gauge rainfall
  (to test whether the one *acute* 8 May cloudburst really stands out) plus a "how rare is this?" rule so
  it stops crying wolf. That's the clearly-marked next step.

**We then built the "how rare is this?" filter and learned something decisive.** It scores each day by
*how far above* the danger line the rain sits (just touching = 1; a true cloudburst = much higher), and
lets us dial up the strictness. The result, in plain terms: as we make it stricter, the season's noise
drops fast — but **the two real spring slides drop out too**, because in our current weather record they're
barely on the line (27 Apr) or **even below it (8 May)**. The big 26 Aug cloudburst, by contrast, towers
**7×** over the line. So with the weather data we have, you simply **cannot be both quiet and catch the
spring events**. The obvious next suspect was the rain data itself — so we **finished the Google sign-in
and actually pulled CHIRPS**.

**And here's the honest twist — CHIRPS made the case *worse*, which is itself the finding.** The
gauge-blended product turned out to be **drier** than our old weather record over this area, and on the two
event days it recorded *less* rain, not more: **0 mm on 27 April and ~4 mm on 8 May**. So **two completely
independent rainfall products now agree there was barely any heavy rain at the map-grid scale on the days
those slopes actually failed.** That flips the whole story: the spring disasters probably **weren't caused
by a big rainstorm our data missed** — more likely a *very local* downpour smaller than the ~5–9 km map
squares, or the slow build-up of **snowmelt-soaked ground** (which our danger map already shows lighting up
in spring), or even the heavy **road-and-tunnel construction** at those exact spots, or simply fuzzy dates
from news reports. We chased the leading suspect to ground and ruled it out — a clean, honest negative that
**redirects** the next search (finer/faster rain like 30-minute satellite data, or treating spring as a
slow-saturation problem) instead of chasing the wrong fix.

**Why this matters:** we tuned the trigger line to these mountains (a documented, citeable, swappable
choice), built and ran the gauge-rainfall pipe end-to-end, and used it to **test — and disprove — the
leading explanation** for the missed spring slides. That's three solid outcomes: a better trigger line, a
reusable rainfall pipe (it'll take the next data source unchanged), and a *ruled-out* suspect. The science
stays honest: we report the win (the line), the catch (over-triggering), and the negative (gauge rain
didn't help) — and we now know to look elsewhere for the spring trigger.

**Plain-language result:** the warning now has a **Himalaya-tuned trigger line** instead of a global
hand-me-down, and we **plugged in proper rain-gauge data and checked** — only to find it's *drier* here, so
the missed spring slides weren't a "missed rainstorm" after all. A clean, honest dead-end that points the
search toward finer/faster rain data or treating spring as a slow snowmelt-soaking problem.

---

## ✅ Milestone 18 — The Last Rainfall Check: Was It a Quick Cloudburst?  *(GPM IMERG sub-daily test, 2026-06-02)*

**What we set out to do:** Milestone 17 left one rainfall idea untested. Daily rain totals can *hide* a
short, violent cloudburst — 30 minutes of torrential rain can trigger a slope yet barely move the *daily*
number. So we brought in **GPM IMERG**, a satellite product that measures rain **every 30 minutes**, to ask:
on the days those spring slopes failed, was there a brief, intense burst the daily products simply averaged
away?

**What we did, plainly:** we pulled the half-hourly rain rate over the area for the two-week spring window
(and, as a sanity check, the big 26 August storm), and measured the most intense burst at every timescale
from 30 minutes to a day — then compared it to the Himalaya danger line. To be kind to the cloud-computing
budget, we only pulled the days that matter and saved them so re-runs cost nothing.

**What we found — the question is now firmly settled:**
- The **26 August** check lit up exactly as it should (rain *twelve times* over the danger line) — proving
  the method works.
- But on the actual spring failure days: **27 April was completely dry**, and **8 May had only a mild burst
  that stayed *under* the danger line** at every short timescale (it only grazed it over 3 hours). No
  cloudburst.
- Curiously, there *was* a real burst on **20 April that crossed the line — yet nothing was reported to have
  failed that day** — another hint that rain alone doesn't explain these slides.

**Why this matters:** we have now checked the rain **three independent ways** — a weather-model record, a
rain-gauge-blended product, and a 30-minute satellite — and **all three agree there was no triggering
downpour on the days the spring slopes failed.** That's a strong, honest conclusion: the spring disasters
were **almost certainly not caused by rain we failed to see.** The likely real causes are slower or
non-weather ones — **ground left soggy by melting snow** (which our danger map already flags in spring), the
heavy **road-and-tunnel construction** at those exact spots, or **imprecise dates** in the news reports. We
closed a question properly instead of leaving it hanging.

**Plain-language result:** rain is now **ruled out** as the hidden cause of the spring slides — confirmed
from three independent angles. The investigation turns to soggy-ground (snowmelt) and ground-disturbance
explanations, with a cleaner, better-dated landslide record as the next thing to fetch.

---

## ✅ Milestone 19 — If Not Rain, Then What? The "Slowly Primed Slope" Picture  *(Spring conditioning, 2026-06-02)*

**What we set out to do:** with a sudden downpour ruled out (Milestone 18), we checked the two *slow* ways a
spring slope gets dangerous: **freeze–thaw** (water in cracks freezing and thawing, prying rock apart night
after night) and **soggy ground** (snowmelt and earlier rain leaving the slope wet long before it fails). Both
can be read from data we already have — the daily temperatures and the elevation map — so it cost nothing new.

**What we did, plainly:** the area's *average* temperature never dips below freezing (the warm valley floor
drags the average up), which is why our earlier freeze–thaw check came back empty. The fix: use the elevation
map to estimate temperature **at each height** (it gets ~6.5 °C colder per kilometre up) and count freeze–thaw
days **band by band**. We also tracked how *wet* the ground already was, day by day, through spring.

**What we found:**
- **Freeze–thaw kicks in around 2,500 m** and gets stronger higher up — but the road and the failure sites
  themselves sit low in the **warm valley (~1,540 m), with zero freeze–thaw**. So freeze–thaw is busy
  loosening the **higher slopes above the road**, not the road itself.
- The ground was **moderately wet** on both failure days (about a **third** as wet as the season's peak on
  27 April, a fifth on 8 May) from snowmelt and earlier rain — **even though almost no rain fell that day.**

**Why this matters:** it paints a coherent picture — the spring slopes were **slowly primed** (damp ground +
freeze–thaw working the upper slopes) rather than hit by a single storm. That fits everything else we found.
**Honest limit:** "primed" explains why a slope was *vulnerable*, but it still doesn't name the exact thing
that let go on those specific dates — so the next job is a **better, verified landslide record** (real dates
and locations) and a look at the **road/tunnel construction** at those spots.

**Plain-language result:** the spring slides looked like **slowly-primed slopes** (soggy ground + freeze–thaw
up high) — a consistent picture that pointed the last questions at the landslide record and the construction.
*(But see Milestone 20 — checking the record next changed this answer.)*

---

## ✅ Milestone 20 — Checking the Record Flipped the Answer (a date was wrong)  *(Inventory date correction, 2026-06-02)*

**What we set out to do:** start fetching the official Indian landslide record (GSI Bhukosh) to *verify* our
findings with real, field-mapped dates and locations — the gold-standard check we'd been pointing toward.

**The honest surprise — we'd had a date wrong.** The official portal needs a manual login (and is blocked
from the tool's side), so we first verified the events against **peer-reviewed papers + news**. That revealed
the **real deadly April event was a cloudburst on 20 April 2025** — three people killed at Seri Bagna, the
highway washed away at five places, with **torrential rain (~100 mm in an hour locally)**. Our list had
"27 April" (a news article written a week later) and **completely missed 20 April** — the actual disaster.

**Why this matters — it reversed our conclusion (for the better):** we had earlier concluded the spring
slides "weren't triggered by rain." But once we used the **correct date**, the picture flipped: **20 April
WAS a violent rain event, and our system actually flags it** — both the Himalaya-tuned trigger line and the
30-minute satellite rain catch it. In other words, *the warning system would have fired for the deadly
event* — we'd just been checking it against the wrong day. The fuller, truer story is now **soaked slopes
PLUS a cloudburst** working together, and the model sees both. (The smaller 8 May event still looks minor;
and ordinary *daily-average* rain maps under-count these pinpoint cloudbursts, so you need the 30-minute data
to see them.)

**The real lesson (worth more than the result):** *a single wrong date in the record had inverted our
finding.* We let the evidence overturn our own earlier conclusion — and it's a textbook argument for getting
the **verified official landslide record (GSI Bhukosh)**, which is exactly the next step.

**Plain-language result:** correcting one wrong date turned "rain didn't cause the spring slides" into "the
deadly 20 April slide *was* a cloudburst — and our system catches it." A humbling, honest course-correction,
and quietly a validation win.

---

## ✅ Milestone 21 — Three Ways to Scrub the Haze: Which Works Best?  *(Tropospheric-correction comparison, 2026-06-03)*

**What we set out to do:** our biggest measurement weakness is a ~30 mm/yr "fuzziness" floor caused mostly by
the **atmosphere** (the air bends the radar signal differently on each pass). A reader pointed us to a
well-known toolkit (**TRAIN**) for cleaning this up. It's written in MATLAB (a different language from our
tools), so rather than bolt it on, we did the *experiment it's famous for* — **compare the cleaning
methods** — using tools we already have (MintPy, in Python).

**What we did, plainly:** we ran the same data three ways and measured how "quiet" each result is and how
well it agrees with our own independently-built engine:
1. **No cleaning** (baseline).
2. **Weather-model cleaning** — download the actual weather (ERA5) for each radar pass and subtract the delay it caused.
3. **Cheap shortcut cleaning** — just assume the haze tracks *elevation* and fit that from the data (no weather download).

**What we found:**
- The **weather-model (ERA5)** method is the clear winner: it cut the fuzziness by **31%** (from ~30 to
  ~21 mm/yr) and made our two independent engines agree much better.
- The **cheap shortcut** barely reduced the fuzziness — though it *did* improve agreement a bit. The reason
  is neat: the haze has two parts, one that tracks **elevation** (which the shortcut removes) and one that's
  **random weather swirl** (which it can't). Here the *random* part dominates — so only the real weather
  model can clean it.

**Why this matters:** it **confirms, with numbers, that the weather-model correction we already adopted is
the right call** — and shows *why* the cheaper trick isn't enough here. That's exactly the kind of
"we tried the alternatives and measured them" evidence that reviewers expect, and it directly strengthens
the part of the project that was weakest (the noise floor) — without adding a new language or toolchain.

**Plain-language result:** of three haze-cleaning recipes, the **real-weather one wins (−31% noise)**; the
cheap elevation-only shortcut can't touch the random weather swirl that dominates here. A tidy, measured win
for the part of the project that needed it most.

---

## ✅ Milestone 22 — The Real Landslide Record Arrives, and the Physics Gets Calibrated  *(GSI inventory + soil-strength calibration, 2026-06-03)*

**What we set out to do:** two long-standing gaps were "validate against a *real* mapped landslide record"
and "stop using textbook guesses for the soil strength." A reader (you) supplied official **Geological
Survey of India** documents, which let us close both in one go.

**What we did, plainly:**
- **A real landslide map.** One of the PDFs is the GSI **field-validated landslide inventory** — a table of
  actual slides with their exact coordinates. We pulled out every record inside our study area: **138
  field-mapped landslides** (83 in Ramban itself), saved as a clean spreadsheet + map file. This finally
  replaces the ~11 rough points we'd scraped from news reports.
- **A reality check.** We asked: do our flagged danger zones line up with where slides *actually* are?
  **71% of the 138 real slides sit within 2 km of a flagged zone** (median just 0.84 km). A solid match
  against ground truth — with the honest note that we still need to also prove we *don't* flag safe ground
  (the next refinement).
- **Calibrated the strength numbers.** A second GSI document measured the *actual* soil strength on these
  very slopes — friction angle **36–39°** (we'd been assuming a generic 32°), with the crucial finding that
  the soil **loses a lot of strength when wet.** We updated our physics to the real friction value. The
  effect: the danger threshold for a wet slope shifts from ~22° to ~25° steepness, so we **stop flagging the
  gentlest slopes** (fewer false alarms) while the genuinely steep ones stay flagged.

**Why this matters:** these are the two things reviewers ask for first — *validation against real data* and
*physics grounded in measurements, not assumptions.* We now have both, from the authoritative national
agency. The same documents also give an independent "official" danger map (which scored well, 84% accurate)
to cross-check ours against, and explicitly blame **road/tunnel construction** for some failures — backing
up our earlier finding about the 20 April disaster.

**Plain-language result:** we swapped guesswork for the **official landslide record** (real slides, real
soil strength) — our danger map lines up with **71%** of mapped slides, and the physics now uses
**measured** soil strength instead of a textbook number.

---

## ✅ Milestone 23 — Grading the Map Honestly — and the Weather Setting That Made It Beat a Coin-Toss  *(Scored back-test + rainfall-realistic saturation, 2026-06-07)*

**What we set out to do:** Milestone 22 said our map sits near **71%** of real slides "within 2 km" — but
also flagged the honest catch: *we flag a lot of ground, so being "near" a slide might just be luck.* This
session graded the map **fairly** for the first time, and that grading pointed us straight to a fix.

**What we did, plainly:**
- **A fair exam, not an open-book one.** We sprinkled **5,000 random points** across the study area as a
  "what would pure luck score?" control, then asked: are real landslides genuinely *closer* to our danger
  zones than random spots are? We graded across many distances at once and rolled it into a single score
  (think of an exam mark from 0 to 1, where **0.5 = a coin-toss**).
- **The blunt result.** At the headline soil setting (worst-case "everything soaked"), the map scored
  **0.41 — *below* a coin-toss.** It *does* pinpoint slides impressively at very close range (a real slide
  is **1.6× more likely** than a random spot to sit within 100 m of a zone), but because it paints so much
  of the map as "danger," that close-range skill drowns at the 2 km range we'd been quoting. So the
  honest read: **the 71% headline was indicative, not a real grade.**
- **The fix — use a *realistic* weather setting, not the worst case.** Our map had been drawn assuming the
  ground is *fully soaked everywhere* — but the real rainfall record says the ground only gets that wet on
  **11 days out of 214**; a typical day is about a quarter-soaked. When we redrew the danger map at a
  **realistic wetness** instead of the worst case, only the genuinely steep, marginal slopes stay flagged —
  and the grade **jumped from 0.41 to 0.55 — above the coin-toss line**, the *first time the project has
  beaten chance.* Close-range pinpointing leapt too: a real slide is now **5.6× more likely** than random
  to sit within 100 m of a zone.

**Why this matters:** this is the difference between "a rough map that looks plausible" and "a map that
*provably* knows where slides are better than guessing." It also handed us a free dial: **how wet to assume
the ground is** trades *catching more slides* against *crying wolf less*. The sweet spot (~quarter-to-
40%-soaked) is where the map is sharpest.

**One honest nuance we wrote down:** the regional "rain trigger line" decides *when* to raise an alarm (a
**timing** tool); it can't by itself improve a *map*. The map got better purely from the **wetness level**
we drew it at. Keeping those two straight is what makes the result trustworthy rather than over-sold.

**Plain-language result:** graded fairly against a random-luck control, our worst-case map scored **0.41
(below a coin-toss)** — but redrawn at a **realistic wetness** it scores **0.55 (beats chance)** and is
**5.6× better than luck at 100 m**. First provably-better-than-random forecast on the project.

---

## ✅ Milestone 24 — Teaching the Alarm *When* to Ring (not just *where* to point)  *(Temporal gate + an ERA5 reality check, 2026-06-07)*

**What we set out to do:** Milestone 23 gave us a danger **map** (the *where*) that finally beats a
coin-toss. But a map isn't a warning — a warning also needs a *when*. We had a rain "trigger line" for the
NW Himalaya, but on its own it cried wolf: it tripped on **112 of 214 days** (half the season). This step
joined the two — *where* × *when* — into a single, honest alarm, and then stress-tested our cleanest
radar against the hazard.

**What we did, plainly:**
- **Made the alarm a two-part decision.** *Where* = the validated 88-zone map (Milestone 23). *When* =
  the rain trigger, but **graded by how *far above* the danger line each day sits** (not just "above /
  below"). A day barely over the line → **WATCH** (footprint armed, keep an eye out); a day *well* over →
  **ALERT** (raise the alarm).
- **The result is genuinely usable.** The full-blown ALERT now fires on just **27 days (13% of the
  season)** instead of 112 — about **4× less crying wolf** — yet it still lights up on exactly the right
  windows: the deadly **20 April cloudburst is a Δ=0 ALERT**, and the late-August monsoon peak. Of the four
  recorded disasters, **all four** fall inside an armed (WATCH-or-higher) window, and **three of four** hit
  a full ALERT. The two that only reach WATCH (27 Apr, 8 May) are exactly the ones whose rain was too
  localized for our coarse weather data to "see" — an honesty we keep on the record, not paper over.
- **A reality check on our best radar.** We have a premium, "atmosphere physically scrubbed" velocity for
  one satellite track. We ran it through the danger map and compared. Reassuring: it agrees with our
  everyday method on the big picture. Sobering: it flags only **half as many** creeping pixels, and they
  **barely overlap** with the everyday method's. The lesson we wrote down: *which exact pixels are
  "creeping" on a single track is not rock-solid — trust the spots that several tracks agree on.*

**Why this matters:** a map that says "these slopes are dangerous" plus a calendar that says "and today is
a dangerous day" is the shape of a real early-warning system. We now have both — and, just as importantly,
we've measured and stated where each half is still soft (coarse rain misses local cloudbursts; single-track
creep isn't pixel-stable).

**Plain-language result:** the alarm now rings **4× less often** (27 vs 112 days) but still catches the
deadly **20 April cloudburst on the exact day** and all four recorded disasters within an armed window — a
real *where × when* warning, with its soft spots measured rather than hidden.

---

## ✅ Milestone 25 — *Which* slopes, today — and one screen an operator can act on  *(Per-zone gating + the operator dashboard, 2026-06-07)*

**What we set out to do:** Milestone 24 told us *when* the whole area is dangerous, but treated all the
flagged slopes alike — on an alarm day, every zone lit up together. A real operator needs the next level
down: *which* of these slopes should I send a crew to **first, today?**

**What we did, plainly:**
- **Gave every slope its own "breaking point."** Because our stability sum is a straight line in how wet
  the ground is, each flagged slope has a **critical wetness** — the soak level at which *that* slope tips
  past failure. We worked it out for all of them. Some fail the moment the ground is barely damp (the most
  dangerous — **44 of them**); others only let go when it's very wet.
- **Made the alarm pick out the slopes in play *today*.** On a given day, the active list is just the
  slopes whose breaking point the day's wetness has reached — **53 on the drier alarm days, up to all 95 on
  the wettest** — always ranked worst-first, and never spilling beyond the slopes we already validated (so
  it can't drift back into crying wolf). On the 20 April cloudburst day, with the ground already soaked from
  snowmelt, **all 95 were in play** — correctly.
- **Put it all on one screen.** The dashboard now shows, together: a **headline banner** (is today calm,
  watch, or alarm, and how many slopes are live), **WHERE** (the validated danger map), **WHEN** (the season
  alarm calendar), and **WHICH SLOPES** (today's ranked priority list with each slope's location, breaking
  point, and movement speed). You can dial it to any date.

**Why this matters:** this is the difference between "the region is dangerous today" and "**these twelve
slopes, in this order, are the ones to inspect today.**" That's the form a disaster-management officer can
actually use — and it falls straight out of physics and data we already had, no new satellite passes needed.

**Plain-language result:** the warning now names **which specific slopes** are in play each day — a worst-
first list that breathes from ~50 to 95 as the ground wets and dries — all on one operator-ready screen.

---

## ✅ Milestone 26 — The "dry soil is stronger" fix — better physics, and our best score yet  *(Matric-suction dry/wet strength split, 2026-06-08)*

**What we set out to do:** our stability sum had used **one** soil-stickiness number whether the ground was
bone-dry or soaked. But everyone who's built a sandcastle knows **damp sand holds together and dry or
flooded sand doesn't** — soil gains real, temporary "glue" from being slightly moist (a suction effect),
and loses it as it saturates. The official field report measured exactly this ("good dry strength… rapid
loss when wet"). This milestone finally builds that into the physics.

**What we did, plainly:**
- **Gave dry soil its real strength, and wet soil its real weakness.** We now use a **high** stickiness for
  dry ground (the measured dry value, with the moisture "glue") and a **low** one for saturated ground (the
  glue gone). The maths still behaves nicely — the danger smoothly slides from the dry number to the wet
  number as the ground wets — so nothing downstream had to be rebuilt.
- **The honest consequence: our old "danger setting" was too jumpy.** Because dry slopes are genuinely
  stronger than we'd been assuming, the wetness level we draw the daily map at had to move **up** (from
  ~40%-soaked to ~55%-soaked) to pick out the truly marginal slopes. The worst-case (fully-soaked) map is
  **unchanged** — the fix only affects the in-between days, exactly where it should.
- **And it actually scored *better*.** Re-graded against the random-luck control at the new setting, the map
  reaches **0.61 — the best mark the project has ever gotten** (up from 0.55). More realistic physics turned
  out to be *more* discriminating, not less. The deadly 20 April cloudburst is still caught (the snowmelt had
  already soaked the ground that day, so every flagged slope was in play).

**Why this matters:** this was the last big "we're just guessing" knob in the soil model. Replacing it with
measured, physically-honest behaviour both **removed an assumption** *and* **improved the score** — the rare
case where doing the rigorous thing also makes the result look better. One caveat we wrote down: the dry
strength number in the report is in odd units, so we used the physically-sensible reading and flagged it for
a lab check.

**Plain-language result:** teaching the model that **damp soil is stronger than dry-or-soaked soil** (real,
measured behaviour) replaced the last big soil guess — and *raised* the danger map's grade to **0.61, the
project's best**, with the worst-case map untouched.

---

## ✅ Milestone 27 — Sharper eyes on the terrain (a 6× finer elevation map)  *(12.5 m ALOS DEM, 2026-06-08)*

**What we set out to do:** every steepness number — the single biggest driver of landslide danger — came
from a **coarse 80 m elevation map**, which smooths hills and **under-reads how steep slopes really are**.
A finer elevation map was the long-standing fix. You downloaded the **12.5 m** one (≈6× finer per side).

**What we did, plainly:**
- **Measured steepness on the fine map, then summarised onto our working grid.** We can't make the radar
  itself finer (it genuinely sees the ground in 80 m patches), but we *can* read the slope at the full 12.5 m
  detail and then take each 80 m cell's **average true steepness** — which is sharper and more honest than
  measuring steepness on the blurred 80 m map. Typical slope rose from 28° to **31°**, and the steepest from
  56° to **66°** — real terrain the coarse map had been hiding.
- **Re-graded, and got a new best.** Sharper slopes mean a few more genuinely-steep places get flagged, so
  the "danger setting" nudged again (to ~50%-soaked), and the map's grade ticked up once more to **0.64 — the
  project's best yet** (from 0.61). Three honest upgrades in a row, each removing a shortcut *and* improving
  the score.

**Why this matters:** steepness is the #1 ingredient in the physics, and we'd been feeding it a blurred
picture. Now the slope numbers come from genuinely fine terrain. One honest caveat: the danger list is now
**short and focused** (about a dozen top slopes) — high-confidence but deliberately not exhaustive.

**Plain-language result:** swapping the blurry 80 m terrain for a **6× finer 12.5 m** one un-hid the real
steepness (typical 28→31°, steepest 56→66°) and pushed the danger map's grade to **0.64 — a new best**.

---

## ✅ Milestone 28 — A second, wider "watch list" next to the short "act-now" list  *(Two-tier WATCH product, 2026-06-10)*

**What we set out to do:** our best map (Milestone 27) is deliberately **short — about a dozen top slopes**.
That's great for "where do I send a crew *today*," but a short list also **misses** slopes that only let go
after the ground gets *really* soaked. The honest gap was **recall** — how many of the real slides we'd catch.
We wanted a companion list that casts a wider net, without watering down the trustworthy short list.

**What we did, plainly:**
- **Added a "wetter day" setting.** The act-now map assumes a *moderately* wet slope. The new **WATCH** map
  assumes a *sustained-monsoon-soaked* slope — so more marginal hillsides cross into "could fail." That widens
  the list from **12 places to 132**.
- **Graded both honestly against the real landslide record.** The wide WATCH list catches **about 2.5× more**
  of the documented slides (roughly 1-in-4 → nearly 2-in-3) — exactly the recall safety-net we wanted. The
  trade is that, taken as a whole, it's no better than a coin-toss at telling danger from luck (that's the
  price of casting a wide net). **But** the slopes inside it that **two different satellite passes both flag**
  stay genuinely better than chance — a trustworthy inner ring inside the wide net.
- **Kept the two jobs separate.** Short **ALERT** list = act now (precise). Wide **WATCH** list = keep an eye
  on more places (thorough). We *didn't* touch the validated act-now map or its rainfall timing — WATCH sits
  beside it as an option, not a replacement. We also checked that going *even* wetter (the worst-case monsoon
  map, 393 places) barely catches more slides for triple the noise — so the "sustained-monsoon" setting is the
  sweet spot.

**Why this matters:** a real warning system needs both a *focused* list (don't cry wolf) and a *thorough* one
(don't miss the quiet ones). Now we have both, each graded honestly, and the operator can choose the posture.

**Plain-language result:** a new **WATCH** list of **132 slopes** sits beside the focused **12-slope ALERT**
list — catching **~2.5× more** real slides (recall ~0.25 → ~0.63), with a two-pass-confirmed inner ring that
still beats chance (grade 0.59).

---

## ✅ Milestone 29 — "How sure are we this slope is *really* moving?"  *(Uncertainty from the velocity noise floor, 2026-06-10)*

**What we set out to do:** the satellite's speed reading isn't perfect — it has a built-in "fuzziness" of
roughly 15–25 mm/yr from the atmosphere getting in the way. So a slope we clock at −18 mm/yr might just be
noise, while one at −45 is almost certainly really creeping. Until now every flagged slope was treated as
equally certain. We wanted to put a **confidence number** on each one.

**What we did, plainly:**
- **Measured the fuzziness per radar track.** For each satellite track we measured how much the speed map
  jitters where the ground is steady — that's the noise level (≈14–24 mm/yr here).
- **Turned each slope's speed into a probability.** A slope moving far faster than the noise gets a high
  confidence ("this is real"); one barely past the cut-off gets a low one. A slope seen by **two** different
  satellite passes that *both* call it moving gets a big boost — two independent witnesses (two "70% sure"
  looks combine to "91% sure"). This finally puts a number on our long-standing rule of trusting slopes
  confirmed by more than one pass.
- **Asked an honest question: does "more confident" mean "more likely a real landslide site"?** We tested it
  against the landslide record — and the honest answer is **no, not really.** Keeping only the
  highest-confidence slopes didn't improve the match to known slides.

**Why this matters (and the honest twist):** "confident the slope is *moving*" and "this is a known
*landslide* spot" turn out to be **two different questions.** A slope can be unmistakably creeping yet not sit
on a mapped slide — and vice versa. So the new confidence number is for **triage** — don't send a crew to
chase what might be atmospheric noise — and it sits *alongside* (not instead of) our location-accuracy grade
and our rainfall-timing alarm. It's another independent way to avoid trusting any single signal.

**Plain-language result:** every flagged slope now carries a **"how sure are we it's really moving"** score
(0–1), with a real boost when two satellite passes agree — and we showed honestly that this measurement
confidence is a *separate* thing from being near a known landslide.

---

## ✅ Milestone 30 — A *sorted* watch list, not a *filtered* one  *(WATCH triage ranking, 2026-06-10)*

**What we set out to do:** our wide "watch" list (132 slopes — the thorough net that tries not to miss
anything) was just an unsorted pile. Staring at 132 equal dots isn't useful. We wanted the scariest ones at
the top — without throwing any away.

**The temptation we avoided:** we already had a tool that *narrows* the short "act-now" list down to the
slopes that matter today. The obvious move was to point it at the watch list too. But that would shrink the
very thing that makes the watch list valuable — its *width* (the whole point is to not miss anything). It's
like casting a wide fishing net and then throwing fish back to make it tidier. So we deliberately chose to
**sort, not filter.**

**What we did, plainly:** we gave every slope on the watch list a single **priority score** that multiplies
two things we'd already measured — **how fragile it is** (how little rain it takes to fail) × **how sure we
are it's really moving** (the confidence score from the last milestone). A slope shoots to the top only if
it's *both* fragile *and* convincingly moving — exactly what you'd want to look at first. Slopes seen by two
satellite passes get a boost, so corroborated ones rise. **Nothing is dropped** — all 132 stay; they're just
ordered worst-first.

**Why this matters:** a "keep an eye on everything" list is only useful if a human can actually start
somewhere. Now the top of the list is the handful of slopes that are both fragile and confidently moving,
while the 96 "only fails in a downpour" slopes settle to the bottom — still listed, just not shouting.

**Plain-language result:** the 132-slope watch list is now **sorted worst-first** by a "fragile × really-
moving" priority — the operator reads the top few instead of all 132 — with every slope kept.

---

## ✅ Milestone 31 — Pointing the tool at a second mountain  *(Vaishno Devi AOI, Phase 1, 2026-07-03)*

**What we set out to do:** prove the "point it anywhere" promise for real. The new target: the **Vaishno
Devi pilgrimage route** — the full climb from Katra town up to the shrine and on to the Bhairav temple —
to find which parts of the track and the mountain-side infrastructure sit under slopes that are slowly
creeping.

**How we drew the new area:** instead of hand-drawing a box, we pulled the route's real landmarks (Katra,
the trek start, the shrine, the Bhairav temple, even the ropeway between them) from OpenStreetMap and wrapped
a box around them with a couple of kilometres of margin — enough to include the slopes *above* the path
(the ones that could fail onto it) and the town at the bottom.

**A lucky discovery:** the satellite "picture frames" that cover Ramban turn out to cover Katra too — the
two sites are neighbours on the same orbital tracks. That means the radar archive we already downloaded
for Ramban *also* photographs the new mountain, giving us history for free.

**What happened:** we ordered 49 radar-pair computations from the NASA/ASF cloud (~490 of our 8,000
credits). 48 came back perfect; 1 failed on their side. The failure exposed a small blind spot in our
ordering script — it counted failed orders as "done", so re-running would never re-order them. One-line fix,
re-ran, and it re-ordered exactly the missing one. Then the quality audit ran over everything and told us,
honestly: the **deep-winter radar pairs are mostly ruined by snow and atmosphere** (expected in the high
Himalaya), but the **spring chains — the ones that matter heading into the monsoon — are clean and fully
connected**.

**One important piece of plumbing:** because the two sites share picture frames, their results would have
overwritten each other. We taught every step of the pipeline to keep **separate output folders per site**
(Ramban keeps its original folders untouched; the new site gets its own `_vaishnodevi` folders). The two
mountains now coexist in one project.

**Plain-language result:** the raw radar ingredients for the Vaishno Devi route are **downloaded, audited,
and ready** — next step is turning them into a motion map, then a hazard map for the track. (Honest caveat:
the soil-strength number we'll use at first is borrowed from Ramban, and there's no local landslide list yet
to score against — the new site starts as "framework-validated", not "site-validated".)

---

## ✅ Milestone 32 — The shrine route gets its first hazard map  *(Vaishno Devi Phases 2–4, 2026-07-03)*

**What we set out to do:** turn the freshly-audited radar ingredients (Milestone 31) into the same product
Ramban has — a motion map, then a physics hazard map, then ranked alert zones — for the pilgrimage route.

**What broke first (and why that's good news):** pointing the machinery at a second mountain immediately
exposed three hidden "only works for Ramban" assumptions — a quality bar set higher than a short radar
series can ever reach, a high-resolution elevation tile that only covers Ramban, and one function whose
callers were never updated after an earlier upgrade. All three fixed; the pipeline is now genuinely
site-agnostic, and each fix came from a *real* failure rather than a guess.

**What we got:** the two clean spring radar chains (May–June 2026, two different satellite tracks) became
velocity maps, then a hazard map, then alert zones — landing in the new site's own folders, with Ramban's
untouched. Under today's standing "realistic wet-season" assumption the route corridor shows **27 alert
zones (4 critical)**; the wider watch net has 72; a worst-case fully-soaked monsoon scenario has 185. Most
importantly, **411 spots are flagged by both satellite tracks independently** — that double-confirmed core
is where to look first.

**The honest caveat, in plain words:** this map is built from only ~7 weeks of radar — its "is it moving?"
measurements are several times noisier than Ramban's year-long series — and it borrows Ramban's soil
calibration, with no local landslide list yet to score against. Treat it as a **first reconnaissance map**,
strongest where the two tracks agree, and improving every 12 days as new acquisitions extend the chain
through the monsoon.

**Plain-language result:** the Vaishno Devi route now has a working end-to-end hazard product — velocity →
physics → ranked alert zones with dashboards — in its own folders beside Ramban's. Next: draw the actual
pilgrim track on top and name which segments sit in or below the flagged zones.

---

## ✅ Milestone 33 — Drawing the pilgrim track on the hazard map  *(Route exposure, 2026-07-03)*

**What we set out to do:** answer the question this whole second site exists for — *which parts of the
actual walking route, and which buildings and cable-cars, sit near the slopes our radar+physics flags?*

**What we did, plainly:** we pulled the real mapped geometry of the route from OpenStreetMap — the classic
track, the two newer route variants (Himkoti and Hathimata), the Bhawan–Bhairon ropeway, the helipads and
the shrine buildings — walked along it in 40-metre steps, and measured the distance from every step to the
nearest flagged slope, using the same honest 250-metre yardstick our Ramban validation earned.

**What the map says (first reconnaissance read):**
- **One 680 m stretch of path above the Bhairon top** is the single place where the route comes near
  ground that **both satellite tracks independently agree is creeping** — the most trustworthy flag we
  have; look there first.
- Under the standing realistic-wet-season setting, **no part of the track sits inside a flagged zone** —
  the flagged slopes are off-track. Reassuring, with the usual young-data caveats.
- The **two modern route variants pass through the wider "keep an eye on it" net** (~5 km combined), and
  the **shrine complex, Bhairon temple and the ropeway** all sit within a couple hundred metres of
  watch-level slopes. The classic track only shows up in the everything-soaked worst case.
- **Katra town and the trek start are clear.**

**Plain-language result:** the route now has a ranked, mapped exposure list — one double-confirmed hotspot
to inspect, the modern variants and the shrine complex on the monitoring list, the classic track only in the
worst case, and the town clear. Every 12 days of new radar sharpens it.

---

## ✅ Milestone 34 — The shrine corridor gets a live weather-aware alarm  *(VD two-factor warning, 2026-07-06)*

**What we set out to do:** yesterday's route map answers *where* to look; a warning system also needs
*when*. Ramban already had this "two-factor" design — a fixed hazard map that only *arms* when real
rainfall crosses a danger line. We pointed the same machinery at the new site.

**What we did, plainly:** fetched the real 2026 rain-and-snowmelt season for the Katra hills (April through
June so far), converted it to a daily ground-wetness estimate, and ran it through the alarm: which days
crossed the regional rain-danger line, and which of the 33 flagged slopes would have been "live" on each day.

**What the alarm says today:** **all quiet (DORMANT).** The season's 13 danger-line days were all in one
April wet spell, and none rose far enough above the line to rate an actual ALERT; on 30 June no flagged
slope was wet enough to be active. As the monsoon builds, one command refreshes the whole picture.

**Just as important — honesty plumbing:** we made it *impossible* for the new site's dashboard to wear the
old site's medals. Vaishno Devi has no landslide history-list yet, so its dashboard now plainly says "not
yet back-tested at this site" instead of borrowing Ramban's accuracy scores (which the old template would
have quietly done). Each site also finally shows its **own name** in its dashboards.

**Plain-language result:** the Vaishno Devi corridor now has a **live, weather-gated warning dashboard** —
currently reading all-quiet — that refreshes with one command and tells the truth about what has and hasn't
been validated at this site.

---

## ✅ Milestone 35 — Sharper glasses for the second mountain  *(VD 12.5 m DEM, 2026-07-06)*

**What we set out to do:** the Vaishno Devi hazard map was built on a blurry 30-metre elevation model
(a stopgap after we discovered the sharp one only covered Ramban). You fetched the matching sharp
12.5-metre tile for the Trikuta hills; we plugged it in and re-ran everything.

**Health check first:** the new tile passed — it covers 100 % of the corridor (the exact failure mode we
hit before), in the map projection our grid already uses, with sensible elevations from Katra's valley
floor to the high ridges. Each site now automatically finds *its own* sharp elevation tile.

**What sharper terrain changed:** steeper slopes emerged from the blur (typical slope up from 18° to 22°,
the steepest now 71°), so more ground fails the stability test — and crucially the **double-confirmed
core grew by about a third** (411 → 567 spots where both satellite tracks agree). The route finding
strengthened: the path above the Bhairon top now **passes directly through** double-confirmed creeping
ground for 800 metres, not merely near it. The standing everyday product still flags nothing *on* the
track, the town stays clear, and the live alarm still reads **all quiet** for late June.

**Plain-language result:** same honest young-data caveats, but the map now sees the terrain at full
sharpness — and its single most important finding (the stretch above Bhairon top) got more, not less,
convincing. That stretch is worth a real-world look.

---

## ✅ Milestone 36 — The second mountain passes its first real exam  *(VD validated on the Ardhkuwari disaster, 2026-07-07)*

**What we set out to do:** until now the Vaishno Devi product was honestly labelled "not yet tested at
this site." You gave us what was missing: the official GSI report on the **26 August 2025 Ardhkuwari
disaster** (32 lives lost near the Inderprastha Bhojnalaya on the pilgrim track) plus GSI's own table of
40 surveyed danger spots along the routes. We turned that into the site's first genuine exam.

**A chilling detail from the report itself:** GSI had *already flagged the exact slopes that failed* —
years before — as vulnerable spots Nos. 110 and 111. This is precisely the kind of place-and-warn problem
our tool exists for.

**The when-test (strongest result):** we fetched the real 2025 rain record for these hills. The disaster
day turns out to be **the wettest day of the entire season — 191 mm** — and our alarm, given only rain
data, marks **that exact day as the single most dangerous day of 2025** and would have been at full ALERT
on it. The honest asterisk: that monsoon was so relentless that the alarm would have been ON for many
days that season — so "we'd have been alarmed that day" matters less than "that day was our #1."

**The where-test:** our standing hazard map scores **clearly better than random luck** at its very first
scoring (about the same grade Ramban earned after months of tuning) — 4 in 5 of GSI's danger spots lie
within 2 km of one of our 37 flagged zones. **The humbling part:** our "double-confirmed" spots — where
both satellite tracks agree ground is creeping — are all *away* from the track and scored zero against
GSI's track-side list. Lesson learned and recorded: the track's dangers are fast rockfalls off cut
slopes, a different beast from the slow creep radar sees best. For the *track*, trust the wide validated
map; the double-confirmed core above Bhairon top is still worth its field check, but it's answering a
different question.

**Plain-language result:** the Vaishno Devi warning system is now **validated against a real disaster** —
it beats chance on where, and its worst-day-of-the-season call lands exactly on the day that killed 32
people. Its dashboards now wear the site's own scores, earned, not borrowed.

---

## ✅ Milestone 37 — The second mountain earns its own dial settings  *(VD operating-point sweep, 2026-07-07)*

**What we set out to do:** the new site's two warning tiers were still using **Ramban's** dial settings —
the assumed ground-wetness levels (m=0.50 and 0.70) that decide how wide each warning net is. Borrowed
settings were the honest stopgap; now that the site has its own graded exam (Milestone 36), we could tune
the dials against *its own* ground truth.

**What we did, plainly:** we turned the wetness dial through sixteen positions and graded the resulting
map at each one against the GSI danger-spot list (with the usual 5,000-random-points luck control). Then —
the important discipline — we did **not** pick the single best-scoring position. The very best score sat
right next to a cliff where the grade collapses; with only 41 ground-truth points, that peak could topple
when the next radar pass arrives. We picked the **middle of the stable plateau** instead.

**The new dials:** the act-now list tightens to **21 zones with a clearly better grade** (0.70 vs 0.62,
twice as good as luck, two-thirds of random ground correctly rejected); the wide watch net moves slightly
wider and now catches **38 of GSI's 41 danger spots**. Perfect 41/41 was available — for a net half again
as big flagging most of the corridor — and we declined it, on paper, with reasons.

**Built to travel:** the dial settings now live in each site's **config file** — Ramban keeps its own
tuned values, the shrine route gets its own, and any third mountain will get the same sweep instead of
hand-me-downs. Every dashboard and back-test inherited the new settings automatically and the disaster-day
catch was re-verified intact.

**Plain-language result:** the shrine-route warning system now runs on **dial settings earned from its own
disaster record** — a sharper act-now list (grade 0.70), a wider catch-almost-everything watch net (38/41)
— chosen for robustness over bragging rights, with the reasoning written down.

---

## ✅ Milestone 38 — Watching for the failures that give no warning  *(Bhavan overhang toolkit, 2026-07-08)*

**What we set out to do:** the user had drawn a worrying rock formation hanging directly above the
Vaishno Devi shrine complex. Our radar method is built for *slow-creeping* slopes — but an overhang
doesn't creep; it holds, and then one day it lets go. Our own honesty notes call this the blind spot:
the fast, brittle failures the creep map cannot see. So we built the first tools aimed at exactly
that class.

**Tool 1 — a tripwire in the radar's static.** Every 12 days the satellite compares "how similar does
this patch of ground look to last time" — a quantity called *coherence*. Undisturbed rock looks almost
identical pass after pass; a slope that has just collapsed looks completely scrambled. So instead of
measuring slow motion, we now watch for a **sudden scramble** over the drawn formation. The clever bit:
rain and growing vegetation scramble the *whole scene* a little, so the script only raises its hand when
the formation scrambles **more than the rest of the area did** — and on its very first run it correctly
ignored one rainy fortnight that had dimmed the entire scene. Current reading: quiet.

**Tool 2 — "if it falls, what does it hit?"** A century-old empirical rule says falling rock almost
always stops before a line drawn downhill at a certain angle from where it broke off. We swept that
line from every point of the formation across the fine 12.5 m terrain model and shaded three zones:
*likely reach*, *possible reach*, *extreme worst case*. The sober result: **the shrine complex below
sits inside the likely-reach zone**, the ropeway's lower station in the possible zone, and about
2.3 km of pilgrim track in the likely band. (Stated equally plainly: this is a "could a rock get
there" screen — no bouncing physics, no accounting for barriers already installed.)

**Tool 3 — asking who already knows.** Before instrumenting a face above a famous shrine, check the
records. They are eloquent: the government geologists' own survey flags rock-wedge failure spots on the
track a few hundred metres below the formation; the shrine complex itself had a **rain-triggered slope
failure in March 2016** that took 37 deep steel anchors to fix; and the shrine board has run a rockfall
programme with engineering partners **since 2012** — steel nets, catch fences, shelter sheds. Our
concern isn't paranoia; it's the same concern the authorities have been paying to manage for a decade.
First step of any field visit is now: *ask them for the maps of what's already been reinforced.*

**Plus a paper instrument:** a step-by-step field protocol for the cheapest monitoring there is —
painted marks and small plaster bridges across the cracks behind the overhang, re-photographed monthly
and after storms. If a crack opens even a couple of millimetres, the plaster snaps and the photos prove
it: an early warning the radar cannot give for this kind of failure.

**Plain-language result:** the formation above the shrine is now **watched** (radar tripwire, currently
quiet), its **consequence is mapped** (the complex is within likely reach of a fall), and the **paper
trail confirms** the slope system is a known, actively managed hazard. The blind spot isn't closed — no
tool here predicts *when* — but for the first time the pipeline has instruments pointed at it.

---

## ✅ Milestone 39 — From "a project with two sites" to "a product you point at mountains"  *(multi-AOI productization, 2026-07-12)*

**What we set out to do:** we had proven the pipeline twice — built on Ramban, replicated on Vaishno
Devi. But the *knowledge of how to do that* lived partly in documents, partly in memory, and partly in
"defaults that happened to be right." If we (or anyone else) pointed the tool at a third mountain next
year, what would they need? Which steps are automatic and which need a human to fetch a map or read a
soil study? Where would they even check what state each mountain is in? This milestone turned all of
that from folklore into machinery.

**A filing cabinet for mountains.** Every site now has exactly one settings file in a registry folder
— Ramban's card, Vaishno Devi's card, and a template for the next one. The master switch is a single
line saying "the pipeline currently points HERE." You can also aim any individual command at any site
without touching the switch. While building this we caught a quiet trap: the old "just pass a config
flag" advice only actually worked on 4 of our ~30 scripts — the rest decide their site the moment they
wake up, before reading any flags. The fix (an environment setting every script respects) is exactly
the kind of thing better discovered now, on purpose, than next year in the middle of a monsoon.

**The soil numbers can no longer sneak.** The strength-of-the-ground numbers (how much cohesion, what
friction angle) used to be built-in defaults — correct for Ramban, *checked* for Vaishno Devi, but a
third site would have inherited them silently, and wrong soil numbers make a confident wrong map. Now
each site's card carries its own soil values **with a note saying where they came from**, and a test
pins the defaults so nothing changed numerically for the two existing sites.

**A control room wall.** One command now draws a status board: one card per mountain, showing its
current alarm state (Vaishno Devi: WATCH, all zones live), how fresh its rainfall data is, every
pipeline stage as a checklist — including the *human* steps like "do the soil homework" and "build the
verified landslide list" — and, for whatever's missing, **the exact command to run next**. On its very
first run it caught something real: Ramban's live rainfall had quietly fallen 15 days behind, and the
board printed the command to fix it.

**A recipe book for the next mountain.** A step-by-step playbook now walks a newcomer from "draw a
polygon around your valley" to "live monsoon monitoring," honestly split into what the machine does
and the five things only a human can do (draw the boundary, read the soil literature, fetch the fine
terrain tile, verify the landslide history, tune the alarm dials). It ends with the scaling plan: why
adding site #3 is now mostly filling in one card, and where the next radar satellite (NISAR) will plug
in so every site benefits at once.

**Plain-language result:** the pipeline stopped being "a research project that happens to run in two
places" and became **a product with a registry, a dashboard, and a manual**. Nothing scientific
changed — the same maps, the same alarms — but the path from "new mountain" to "monitored mountain" is
now written down, checked by tests, and watched from one screen.

---

## ✅ Milestone 40 — We asked whether the soil homework matters. The mountain answered: completely.  *(soil-sensitivity sweep, 2026-07-13)*

**What we set out to do:** of all the manual chores a new mountain demands, the most tedious is the
"soil homework" — digging through geology reports to find how strong the local ground actually is
(its cohesion, its friction, how deep the loose layer goes). We suspected it might not matter much:
maybe any reasonable textbook values would give nearly the same danger map, and we could skip the
homework at future sites. That's a testable claim, so we built a test: recompute the danger map for
every plausible combination of soil values the literature allows, and score each one against the
real landslide record. Total cost: a new script and about seven seconds of computing.

**What we found:** the suspicion was wrong — decisively. Across values that are all *defensible from
published studies*, the alert map swung from **125 danger zones down to zero**. Not "slightly
different zones" — at several in-range settings the entire warning product simply vanishes, because
the maths declares every slope strong enough to hold. The single most powerful number turned out to
be the most mundane: **how thick the loose soil layer is**. Assume 2 metres instead of 3, and all 21
of our validated warning zones disappear.

**The tempting shortcut that doesn't work:** couldn't we just skip the homework and re-tune the
alarm dial (the assumed wetness) until the map scores well again? Mathematically, yes — wetness and
soil strength push the same lever. But then the dial stops meaning "how wet the ground is" and
becomes an arbitrary fudge factor, and the rainfall-driven part of the warning system — *"this much
rain makes the ground this wet, which tips these slopes"* — loses its physical honesty. A map tuned
that way might still rank slopes usefully, but the WHEN of the warning would be built on sand.

**Plain-language result:** the soil homework stays — now by *measurement*, not just principle. And
the test itself became a permanent tool: every future site runs the seven-second sweep and gets a
chart showing exactly which assumptions its warning map stands on. One more thing changed: the
wish-list item "confirm the soil depth with a field measurement" jumped from nice-to-have to **the
most valuable single number a site visit could bring back**.

---

## ✅ Milestone 41 — Putting error bars on our own report card (and daring a dumb map to beat us)  *(validation statistics, 2026-07-13)*

**What we set out to do:** every score we'd ever quoted — "our map beats chance, AUC 0.64" — was a
single number computed from a small list of known landslides. A skeptical reviewer would ask two
fair questions we couldn't answer: *"with only ~40–140 landslides on record, how sure are you that
number isn't luck?"* and *"would a much dumber map — say, just painting every steep slope red — score
the same?"* So we built the statistical machinery to answer both, without changing the science at
all: error bars (resampling our landslide list ten thousand times to see how much the score wobbles),
a formal "is this better than random?" test, and a **ladder of deliberately dumb rival maps** —
steepness alone, a simple statistical blend of steepness and wetness-of-terrain, physics without the
satellite, satellite without the physics — each scored by exactly the same rules as our product, and
each allowed to tune itself to its best possible score. We stacked the deck *against* ourselves on
purpose: beating a rival that got every advantage is the claim no one can argue with.

**What we found at Ramban:** the full system beats every rung of the ladder. Most tellingly, the
satellite measurements alone score *worse than random guessing*, and the physics alone barely
better — but fused together they beat everything. The whole really is more than its parts, and now
that's a measured fact with error bars, not a slogan.

**What we found at Vaishno Devi — the honest surprise:** our map beats its own ingredients easily,
but a dumb "paint everything steeper than 40° red" map ties it on the raw score. The catch: that
dumb map needs **155 zones** to do what ours does with **21**, and it can never say *when* danger
rises — it's red forever. Our system's real advantages there are its short, precise list, its
proven timing (it flagged the two deadly events on the exact day), and its ability to rank zones by
fragility. But on the pure "where are the landslides?" score, on this small corridor-biased record,
we cannot claim to beat simple steepness — so we don't. It's in the ledger, stated plainly.

**Plain-language result:** every headline number now comes with an honest range ("0.71,
plausibly 0.66–0.75") and a proof it beats randomness (99.99% confidence at both sites for the
alert maps). The dashboards now show these ranges automatically. And the dumb-map ladder is now the
permanent bar to clear: the next two science upgrades (smarter wetness, smarter soil physics) must
beat it — measurably — or they don't ship.

---

## ✅ Milestone 42 — We stopped pretending the whole mountain gets wet at once  *(TWI-distributed saturation, 2026-07-13)*

**What we set out to do:** our danger model had a hidden oversimplification. On a rainy day it treated
*every* slope as equally soaked — one "wetness" number for the whole mountain. But rain doesn't work
that way: water runs downhill and collects in valley hollows, while ridges shed it and stay drier. We
already measure exactly where water tends to collect (a "wetness index" computed from the shape of the
land). So we let each patch of ground have its own wetness — hollows a bit wetter, ridges a bit drier
than the mountain's average — controlled by a single new dial. Crucially, the *average* stays exactly
what the rain says, so this only moves wetness around; it doesn't secretly make everything wetter.

**What we found:** two things, one expected and one genuinely reassuring. Expected: concentrating the
"wet" onto the hollows made the danger map **sharper and smaller** — it stopped painting dry ridges as
hazardous. Reassuring: we tuned that one dial separately on two different mountains with two different
landslide records, and **both mountains independently landed on the exact same setting**. A number
that transfers between sites like that is measuring something real about how mountains wet up, not just
fitting one dataset. At Vaishno Devi it made the concrete difference we'd been chasing: last session's
scorecard showed our map merely *tying* a dumb "just flag every steep slope" map; with this upgrade our
map pulled ahead of it — same coverage, a tenth as many alert zones.

**The honest part:** we kept the same error bars and significance tests from last session pointed at
this result. The raw improvement in the score is real but small enough to sit inside the uncertainty,
so we don't oversell it — the trustworthy wins are the tighter, more precise map and finally beating
the "dumb baseline," not a dramatic jump in the number. And it sharpens *where* the danger is, not
*when*: on the very wettest days the whole slope is soaked and everything lights up regardless. We
adopted the setting for both sites, and it's one line away from being switched off if a future site
disagrees.

---

## ✅ Milestone 43 — We built the fancier physics, tested it fairly, and said no  *(van Genuchten suction, 2026-07-13)*

**What we set out to do:** two things. First, re-examine last milestone's wetness upgrade with fresh
eyes — and that audit caught two corners of the system (the season timeline and the watch-list
ranking) still quietly using the *old* uniform-wetness maths. We fixed that the durable way: all the
"how wet makes this slope fail" arithmetic now lives in exactly one file that every tool imports, so
the pieces can never drift apart again, and a 22-point check on both mountains confirmed everything
agrees to the fourth decimal. Second, the last item on our science wish-list: real soil doesn't lose
strength *linearly* as it wets — laboratory curves show the suction that glues damp soil together
collapses suddenly over a narrow wetness range. We built that curve into the model (carefully: bone
dry and fully soaked still give *exactly* the strengths we measured — the curve only reshapes the
journey between them), with a switch that leaves everything unchanged until a site turns it on.

**What we found:** we tested four published versions of the curve — spanning the plausible soil
types for our mountains — and let each one re-tune the wetness dial to its own best score, the most
generous test we could design. **None of them beat the simple straight line at both sites.** The
best came within a whisker at one mountain and exactly tied the other — differences far smaller than
our own error bars. The diagnosis is more interesting than the score: with only a *map* of past
landslides to check against, the curve's shape and the wetness dial trade off against each other
almost perfectly — the data literally cannot tell the curves apart. What *would* tell them apart is
either a laboratory measurement of our actual soil's curve, or precise *dates* of when individual
slopes gave way — both already on our field wish-list, now with one more reason.

**Plain-language result:** the fancier physics is built, verified to the last bit, and one
configuration line away from use — but it stays switched off, because the honest reading of our own
statistics says it hasn't earned its two extra assumptions yet. Declining our own upgrade on
evidence is the same discipline as reporting the slope-map tie in Milestone 41: the numbers decide,
not the effort invested. The science plan's three upgrades are now all resolved: statistics
(adopted), distributed wetness (adopted), suction curve (built, waiting for the data that can
justify it).

---

## ✅ Milestone 44 — We found out why the computer crawled, then put the data warehouse on a diet  *(storage & automation overhaul, 2026-07-15)*

**What we set out to do:** the automatic monsoon-watch job seemed to be downloading huge batches of
radar data and grinding the computer to a halt at 100% disk. Find out what it was really doing, stop
the slowdowns, and free up disk space.

**What we found:** the job was innocent — its whole download was about 4 KB of rainfall numbers (the
size of a short email), and it finished cleanly. The real culprits were three quiet
misconfigurations: the virtual machine that Docker runs in had no memory limit (it could grab half
the computer's RAM and every CPU core the moment it woke up), a leftover registry entry was starting
Docker at every login even though its own setting said "don't", and the job's missed 8 AM slot was
firing the moment the user logged in — exactly when they wanted to use the machine.

**What we changed:** capped the virtual machine (it now peaks under 2 GB instead of 8), removed the
stale autostart, and taught the job to shut Docker down properly (it turns out killing just the
visible window leaves a background service running that can quietly restart everything). Then the
big one: the 47 GB of original radar zip files were backed up to Google Drive and deleted — we
proved the pipeline only ever needed one tiny text file from inside each zip, so those text files
now live with the extracted data, and the zips became disposable. Future downloads land on a plain
folder outside the cloud-synced documents tree.

**Plain-language result:** ~56 GB of disk came back (the drive went from 85 to 150 GB free), the
2-day watch cycle now runs in under 5 minutes using a fraction of the memory, and the machine stays
responsive while it does. Every change was tested the hard way — including a rehearsal of the
MintPy preparation step with zero zips on disk (byte-for-byte identical output) — and the testing
itself caught a real bug nobody would have seen otherwise: Docker containers can't see through
Windows folder shortcuts (junctions), so the container view needed its own explicit mapping.

---

## ✅ Milestone 45 — We audited our own product like a skeptic, and it held up  *(full-product verification, 2026-07-17)*

**What we set out to do:** before trusting the system any further, put the whole product on
trial — the math, the code, and the data — as if we were an outside reviewer trying to catch it
being wrong.

**What we did:** three separate examinations. For the *math*, we re-wrote the landslide physics
formula from the textbook, completely independently of our engine, and compared the two answers at
every single map pixel — they agreed to the smallest difference a computer can represent (better
than a millionth). We also re-derived the rainfall danger thresholds from raw daily sums and got
the exact same warning days the product reports. For the *code*, every script compiles and every
test suite passes. For the *data*, every map layer sits on the right grid with physically sensible
values, both landslide inventories are intact and inside their areas, the rainfall records have no
missing days, and every number quoted in our documentation matches the actual files on disk.

**The honest wrinkles:** one radar stack (the newer Vaishno Devi one) is noisier than the others
because its data chain is still short — but our confidence system already measures exactly that
and marks its detections accordingly. And a few "failures" during the audit turned out to be the
auditor's own stale notes: the automatic watch cycle had quietly run that very morning — fully
unattended, in about four minutes — and freshened the data underneath us. That accidental proof
that the automation now works on its own was the nicest result of the day.

**Plain-language result:** zero bugs found, and the audit itself became a permanent 12-test guard
that will re-check the physics and data automatically from now on. The system doesn't just say
the right things — we've now verified, pixel by pixel, that it computes them.

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

- **Validation + the operational warning are now COMPLETE (M23–25).** The danger map is scored and
  beats chance (AUC 0.41→**0.55** at a realistic wetness, M23); the realistic-wetness map is the **default**
  product (M24); the rainfall trigger is now a **selective temporal gate** (27 alarm days, not 112, M24);
  and the alarm is **per-slope, ranked, on one operator screen** (M25). *Only remaining validation lead:* a
  *temporal* scored test with verified per-landslide **dates** — but the GSI inventory we have is undated,
  and that portal has moved, so this is parked (we already validate against 4 dated events).
- **Spring-trigger cause — "primed slope + a cloudburst" (M17–20), now operationally caught (M24).** The
  deadly **20 April 2025 cloudburst** is a Δ=0 alarm; the *road/tunnel construction* angle is still an open
  investigative lead.
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

## ✅ Milestone 46 — One button instead of five commands, and a tidy house  *(control panel + repo restructure, 2026-07-17)*

**What we set out to do:** two quality-of-life upgrades. First, make refreshing the analysis as
easy as clicking a button — until now, updating the rainfall, regenerating the alarms, and
rebuilding the dashboards meant typing several Docker commands in the right order. Second, tidy
the project folder: reading material (guides, runbooks, field briefs, old plans) had piled up in
the open next to the working files, and it was getting hard to know what to read.

**What we built:** a small **local control panel** — you double-click `control_panel.bat`, a page
opens in your browser, and three buttons do the work: *Refresh cycle* (fetch the latest rainfall
and update every site's warning state), *Refresh status board*, and *Rebuild 3-D dashboard*. You
watch the progress live, and when it finishes, a **results hub** page lists every dashboard with
"updated X minutes ago" stamps — one click opens them. Under the hood the buttons run exactly the
same commands the scheduled watcher runs, so there is one way of doing things, not two. The panel
deliberately never starts or stops Docker — that stays your job, by your own earlier decision.

**Did it work?** Yes, proven the honest way: we pressed the real buttons against the real
pipeline. The full refresh ran clean for both sites in about 3 minutes; the rebuilt 3-D dashboard
came out with exactly the same alert numbers as always (a free extra check that the whole physics
cascade still behaves); and with Docker off, the panel says plainly "start Docker Desktop
yourself" instead of failing mysteriously.

**The tidy-up:** all reading material now lives in one `docs/` folder — guides (the science
primer, the project vision), runbooks (how to onboard a new site), field briefs, reference
papers, and an archive for superseded plans (each marked with *why* it's archived). A single
`docs/INDEX.md` page answers "what should I read, in what order?" and maps every old location to
the new one. The map polygons and credential templates moved into `config/`. The working files
the rituals depend on (this file, the KPI ledger, the bug log, the session review) stayed exactly
where they were, untouched. And we re-ran every test suite afterwards — all six, all green — to
prove the move broke nothing.

**Bottom line:** day-to-day operation is now *start Docker, click a button, read the dashboard* —
and a newcomer opening the project sees a clean front door instead of thirty files.

## ✅ Milestone 47 — The dashboard learned its history  *(Past-events tab, 2026-07-18)*

**What we set out to do:** give the warning dashboard a memory. Until now it only showed the
*present* — which slopes are creeping, how wet it is today. But anyone standing in front of it
would fairly ask: "what has actually happened here before, and how bad was it?" We wanted a view
of the documented past landslides at each site, worst first, without breaking the clean look of
the page.

**What we built:** a new **Past events** tab on both sites' dashboards. It lists every documented
landslide disaster we could verify, ranked by the damage it caused — lives lost first, then
injuries, then destroyed roads and houses. Every row shows: a clickable map link that opens the
exact spot in Google Maps, what happened and what triggered it, *how solid the record is* (a
colour-coded confidence badge — hover it and it tells you why we believe it), the sources
themselves, and — the part that ties past to present — **how that historical spot stands in
today's alert system**: how far it sits from the nearest hazard zone our radar-plus-physics map
is watching right now, and how fragile that zone is.

**The honest parts, by design:** we did NOT just copy events from news articles. Every event was
checked against an official report, a peer-reviewed paper, or at least two independent news
outlets — the hard lesson from earlier sessions (one wrong date once inverted a whole
conclusion, and one AI-generated "research" document simply invented a disaster that never
happened; that fake stays excluded, and there is now an automatic test that keeps it out). Three
rows we could *not* fully verify are openly labelled "pending review" instead of being quietly
dropped or quietly trusted. And where a historical disaster site sits *outside* today's mapped
zones, the page says so plainly — adding that this means "not currently measured", never "safe".

**What the history says:** at Vaishno Devi, the worst recorded disaster is recent — the August
2025 Ardhkuwari landslide (34 lives) — and it happened 1.6 km from a zone our current map
already flags as fragile. On the Ramban highway corridor, the record is dominated by the 2022
tunnel collapse (10 workers) and the 2025 cloudburst; most of those spots lie outside our current
radar coverage — a limitation we have documented all along, now made visible on the page itself.

**Bottom line:** the dashboard now answers three questions instead of two — *where* could slopes
fail, *when* is the danger real, and *what has this mountain already done* — with every claim
carrying its receipt.

**Addendum (same day) — the tab earned its keep immediately.** While reviewing the flagged rows,
the user corrected one: the doubtful Ramban entry was not an old duplicate at all, but a real
slide that buried the highway on **7 April 2026** — and our alarm calendar shows the system was
at full **ALERT that very day** (rainfall 2.13× the danger line). A second event the user
brought in — the **8 July 2026** landslide near Himkoti that suspended the Vaishno Devi battery
cars — landed on a day our gate was at **WATCH** (armed, correctly short of a full alarm for
what turned out to be a no-casualty track blockage). Two real 2026 events, both falling exactly
on days the system had flagged — the first live in-season validation of the monsoon watch. Also
per user request: every link on the dashboard now opens in a new browser tab, so you never lose
the page you were reading.

## ✅ Milestone 48 — A second rain sensor that sees the bursts  *(sub-daily IMERG gate, 2026-07-18)*

**What we set out to do:** fix the alarm's known blind spot. Our rainfall gate ran on a *daily
average* over the whole area — and a daily average hides exactly the thing that kills people in
these mountains: a violent, local cloudburst. A day with one savage hour of rain and 23 quiet
hours averages out to "drizzle". We had proven this blind spot exists (the deadly April 2025
cloudburst read low on the daily average), and we had just watched it happen again: the 8 July
landslide at Himkoti registered only a mild "WATCH" on the daily gate.

**What we built:** a second, independent rain sensor for the dashboard. NASA's GPM satellite
measures rain every **30 minutes**, and it reaches us only about **a day** after it falls —
against nearly a week for the daily weather data. Every refresh cycle now also pulls this
half-hourly satellite rain and asks, for each day: *was there any burst — over any window from
half an hour to a day — that crossed the same proven danger line?* The dashboard gained a card
showing the newest satellite day, its burst danger level, and the season's biggest bursts.

**Did it work? Tested on this season's two real landslides — and the answer is the best kind:
the two sensors catch different killers.** The 8 July Himkoti slide, which the daily gate
under-called, lights up as a clear **ALERT** on the burst sensor — a sharp 3-hour downpour whose
signature was measurable **hours before the evening collapse**. And the 7 April highway burial
at Digdol — days of relentless soaking with no single burst — is the opposite: the burst sensor
barely stirs, but the daily gate had already raised the full alarm that morning. One sensor for
the long soak, one for the sudden burst; **together, both of this season's verified landslides
read full ALERT on the day they happened.**

**The honest part:** the burst sensor is deliberately labelled *experimental* on the dashboard.
Its alarm thresholds haven't yet earned the same validation the daily gate has (at short
timescales the danger line trips more easily, and we can't yet say how often it cries wolf);
satellite rain is an 11-km-pixel average; and the newest day is always marked provisional while
its data is still arriving. The official alarm stays the validated daily gate — the burst card
is the sharp-eyed second opinion beside it.

**Bottom line:** the dashboard now watches the rain two ways — slow and fast — and this season's
evidence says that's exactly the pair you need.

## ✅ Milestone 49 — The rain sensor got its rulebook, and the new satellite passed its audition  *(Plan Tiers 1+2, 2026-07-18)*

**What we set out to do:** two things from the strengthening plan. First, give the new burst
sensor (Milestone 48) proper rules — when exactly should it shout? — instead of borrowed ones.
Second, audition NISAR, the new NASA/ISRO L-band radar satellite, on our own mountains: does it
really see through the vegetation that blinds our current radar?

**The rain rulebook:** we replayed the whole of 2025 through the burst sensor. It correctly
flagged every deadly landslide day — including reproducing, through the production system, the
exact verdicts of last month's hand study. From six verified events we set the shout-threshold
at three times the danger line: every fatal day stays caught, and the number of alarm days per
season roughly halves. We also learned something sobering by checking the satellite rain
against the Katra rain gauge on the two worst days: **the satellite saw only a fifth of what
the gauge measured** — a wide-area average simply cannot match a rain gauge standing under a
cloudburst. That is exactly why we refuse to make the sensor less sensitive than this. And we
tested a tempting upgrade — giving every hazard zone its own rain reading — and found our areas
are simply too small for it to matter (the rain pixels are bigger than the zones), so we
declined to build it. The dashboards now show a combined two-sensor reading; the official alarm
remains the fully validated daily gate.

**The NISAR audition:** we downloaded its first winter interferogram over Ramban and compared
it, pixel by pixel, against our own radar from the same fortnight. The result is the best kind
of clear: where our current radar already works, the newcomer adds nothing — but **in exactly
the places our radar goes blind, NISAR recovered 75–87% of the lost ground** to usable quality.
And this was measured in winter, when vegetation is thinnest — the monsoon advantage should be
larger. Verdict: when NISAR's routine data stream reaches this region (our watcher now checks
automatically), it earns a permanent place in the pipeline.

**Bottom line:** the burst sensor now has evidence-based rules and an honest bias sheet; the
per-zone idea was measured and politely declined; and the next-generation satellite proved, on
our own slopes, that it can see where we currently cannot.

## ✅ Milestone 50 — Three hard questions, three honest answers  *(Plan Tiers 3+4, 2026-07-18)*

**What we set out to do:** answer the three toughest "but have you checked…?" questions still
hanging over the project. Would a machine-learning map beat our physics? Can ordinary satellite
photos see the fast rockfalls our radar can't? And is the shortcut we use for "where would
debris flow?" actually good enough?

**Question 1 — ML vs physics.** We built a statistical landslide-susceptibility model from
terrain data and scored it against our physics map on the same 112 field-verified landslides.
At first glance the statistical model wins. Then we looked at *what it learned*: almost
entirely "low elevation = landslide" — which is really "landslides get RECORDED along the
valley highway". Remove elevation and its advantage vanishes completely. The lesson is worth
the whole exercise: **a model trained on where people report landslides learns where people
walk, not where mountains fail** — and our physics map, which cannot cheat that way, is the
more honest instrument.

**Question 2 — can photos see the rockfall?** We compared satellite images from before and
after the Ardhkuwari disaster. Everything around the site turned greener after the monsoon —
except the disaster site itself, which conspicuously failed to green (in the worst 6% of the
whole area). A real signature, but not scream-off-the-page strong: a narrow rocky chute is at
the limit of what 20-metre pixels resolve. Verdict, honestly graded: good enough for
*screening* after an event, not yet a *detector* — sharper imagery is the named upgrade.

**Question 3 — the debris-flow shortcut.** We computed real water routing over the terrain —
which slopes actually drain into big channels — and compared it with the quick proxy the
system has used. They disagree on **half the hazard zones** (on the Ramban highway, seven of
eight). That settles it: the proxy gets replaced with real routing in a properly re-scored
run right after the merge.

**Also:** the growing table of "which events did each alarm arm catch, and how fast" is now a
permanent, tested project artifact — three fatal events, all caught on the day by at least one
arm. Two items wait on the user: the GACOS atmospheric-correction request (form values are
printed and ready) and the soil lab tests.

**Bottom line:** the ML challenger turned out to be reading the road; the camera can screen but
not yet detect; and the plumbing shortcut is now scheduled for honest replacement. Every answer
made the product more trustworthy — including the ones that found our own shortcuts wanting.

## ✅ Milestone 51 — We finally asked our fast alarm: how often do you cry wolf?  *(burst-arm false-alarm measurement, 2026-07-25)*

**What we set out to do:** settle the one honest caveat that has followed our new fast rain
sensor since the day it shipped (Milestone 48). We could show it catches things the slow sensor
misses — but we had never measured how often it goes off when *nothing* happens. Until you know
that, a sensitive alarm is just an alarm nobody will keep listening to. This was the last item
blocking it from being called something better than "experimental", and it needed no new data
and nothing from the user — only a careful look at the two seasons of rain records we already had.

**The trick that made the question answerable: count interruptions, not days.** Our earlier
attempt counted *flagged days*, which is misleading, because mountain rain arrives in spells. An
alarm that flags eleven days might be interrupting you eleven separate times — or three times,
for a few days each. So we grouped consecutive flagged days into **episodes**: one episode is one
time the system asks a human to make a decision. Then we asked of each episode: did a real,
verified landslide happen in or near it? And — the part that makes the answer trustworthy — we
ran the *exact same count* on the old, validated slow alarm, so the new sensor is measured
against the one we already trust rather than against an invented standard.

**What we found: the two alarms have opposite personalities.** The fast sensor is *twitchy but
brief* — it raises many short alarms, typically a couple of days each. The slow one is *calm but
endless* — far fewer alarms, except one of them runs for **92 days without a break**, which is
its own kind of useless. Add it up and the fast sensor asks for attention somewhat more often,
yet costs **less than half as many total alarm days** as the alarm we already trust. Saying
"watch these two days" is cheaper to live with than saying "watch this quarter", even if you say
it more often. Numbers: `RESULTS_AND_KPIS.md` §63.

**And an uncomfortable discovery, recorded rather than buried.** We folded in the fatal 22 July
boulder strike on the Ramban highway. It turns out the fast sensor read only "watch" — not full
alert — on the day two people died. It *had* raised a full alert four days earlier and never
went quiet in between, so it was awake the whole time. But this is the first death our fast
sensor didn't call at the top level on the day, and it means the threshold we picked in July may
sit slightly too high. We measured exactly what it would cost to lower it (about 50% more alarm
days — and even then the sensor would still be quieter than the slow one) and left the decision
to the user. We changed nothing on the live dashboard.

**The honest part:** our landslide records only contain failures serious enough to make the news.
So an alarm we can't tie to a recorded landslide isn't proven to be *wrong* — the mountain may
well have moved somewhere nobody was watching. We therefore report a range rather than a number,
and only ever compare the two alarms against each other, never score either in isolation.

**Bottom line:** the fast rain sensor now has a measured price tag instead of a caveat — it does
not cry wolf more than the alarm we already rely on — and the same exercise handed us a real
question about where its threshold should sit.

## ✅ Milestone 52 — We lowered the fast alarm's trigger, and checked our reasoning twice  *(threshold 3.0 → 2.4, 2026-07-25)*

**What we set out to do:** act on the question Milestone 51 raised. Two people died in the
22 July boulder strike and our fast sensor called it only "watch", not "alert", on the day.
The user decided to lower the trigger. Our job was to do it properly and — just as important —
to write down honestly whether it was the *right* thing to do.

**What changed, and what didn't.** Nothing about the rain measurement moved: every day's
rainfall numbers are **identical** before and after. We only moved the line we draw through
them. Across two seasons at both sites, exactly **20 days** changed grade — every single one
from "watch" up to "alert", and no day moved the other way, which is the only thing lowering a
line is allowed to do. Alert days went from 43 to 63 out of 654.

**What it bought:** **all four fatal landslides on record are now flagged at the top level on
the day they happened**, up from three of four. The 22 July strike is now an "alert".

**Was it actually the right call? Our honest answer: yes — for a better reason than the obvious
one.** The tempting justification is "we set it just below the event we missed", which is
fitting the rule to the last thing that went wrong — a bad habit. But when we looked properly,
*any* trigger between 1.1 and 2.44 catches exactly the same set of past events. So the real
choice was: within that whole band, which value cries wolf least? That's the top of the band —
2.4. It's the cheapest setting that buys the extra catch, which is a principled choice rather
than a reactive one. It also moves in the direction our earlier measurements already pointed:
satellite rain *under*-reads the worst storms by a factor of five, so if anything our numbers
are too low on the days that matter.

**And the fragility we're not hiding:** 2.4 sits barely 2% below the event that justified it. If
NASA ever reprocesses that day's data slightly downward, the catch quietly vanishes. So we wrote
an automatic check that fails loudly if that ever happens, with instructions to re-derive the
number rather than paper over the test.

**A near-miss worth telling.** While updating the dashboards, we regenerated the 2025 ones too —
and discovered they came back *different*, because that tool rebuilds a past season using
**today's** hazard map and landslide list rather than the ones that existed at the time. It
would have silently rewritten published historical figures. We only caught it because we'd
backed everything up first and compared file-by-file; the tool itself reported complete success.
We put 2025 back exactly as it was and wrote the trap into the error log.

**Bottom line:** the trigger moved for a reason we can defend, the change is confined to the
experimental fast sensor (the official alarm is untouched, byte for byte), and the one weak
point in the reasoning now has an automatic tripwire on it.

## ✅ Milestone 53 — The new satellite finally started broadcasting, and we caught our own tool inventing a result  *(NISAR forward stream, 2026-07-25)*

**What we set out to do:** the plan had a date on it. Back in July we checked whether NISAR —
the new NASA-ISRO radar satellite, and the single biggest upgrade available to this project —
had started delivering routine data over our valleys. It hadn't, so we wrote "recheck monthly"
and predicted the window would open around July 2026. Today the watcher said it had: **the
stream is live, with data from 19 July — making NISAR the freshest radar over Ramban by about
ten weeks**, because the old European satellite that fed us stopped operating in June.

**Why we cared so much.** Our biggest known weakness is that ordinary radar loses its grip on
green, vegetated slopes — which is why our movement map covers only a fraction of each valley.
NISAR uses a longer wavelength that sees through leaves. We measured that last winter: it
recovered **75–87%** of the ground the old radar loses (Milestone 49). But we said so honestly
at the time: *winter is the easy season*. Bare branches. The number that really matters is the
monsoon one, when the canopy is thickest. Now, at last, we could measure it.

**What happened instead — and this is the story.** The monsoon data came back looking dreadful.
Our tool dutifully printed a tidy result: the new radar recovering **0%** of the lost ground —
the exact opposite of the winter finding. It would have been very easy to write that down.

It was wrong. The new files simply have **no data at all** over our two valleys — a blank hole
left by the processing, not a measurement. Three things gave it away. First, the *old* radar
looking at the same slopes on the same days was perfectly healthy — and it's the one that's
supposed to struggle first, so the ground plainly hadn't gone quiet. Second, the file
contradicts itself: one layer says "no signal here", another says "valid measurement here", on
the very same pixels. Third, the values weren't *low* — they were **absent**: every single one
of the 64,496 measurements over Ramban was blank.

**The uncomfortable part we're keeping in writing:** NASA's own quality report marks these files
**PASS**, because its alarm only goes off if a file is more than 99% empty — and these are only
about half empty. A clean bill of health from the supplier told us nothing about whether *our
particular valleys* had data. We downloaded a second file to be sure it wasn't a one-off; the
hole was in exactly the same place.

**What we built as a result.** The tool now checks whether there is actually data over a valley
*before* it computes anything, and if there isn't it prints "**ABORTED — no verdict**" with the
evidence instead of a number. A blank hole can never again come out the other end dressed as a
finding. Five automatic tests hold that behaviour in place.

**Bottom line:** the big satellite upgrade is real and now flowing, the winter result still
stands untouched, the monsoon confirmation waits on NASA reprocessing these early files — and
our tool learned the difference between "nothing is happening" and "we cannot see". That last
one is the actual milestone.

## ✅ Milestone 54 — We security-tested our own dashboards and found a real hole  *(stored XSS found and fixed, 2026-07-25)*

**What we set out to do:** check the whole codebase for security weaknesses. Most of it came
back clean — no unsafe command execution, no leaked passwords or keys, the file-download paths
properly fenced, the container running without admin rights, every library up to date. But one
finding was serious.

**The hole.** Our dashboards show a table of past landslides at each site — name, damage,
and numbered links to the news sources. We were pasting those straight into the web page
without neutralising them. If any of that text happened to contain web *code* rather than plain
words, the browser would run it instead of displaying it.

**Why that actually mattered here, rather than being theoretical.** Two things line up badly.
First, we ourselves wrote the rule that this record is **not** trustworthy input — its rows come
from news articles and from AI-generated research summaries, and we've already caught those
inventing events that never happened. Second, the one-click control panel serves these
dashboards from the same address it uses for its own controls. So code smuggled into a
landslide description would run *with the control panel's own privileges* — able to read any
file in our data folder and to start jobs. A sentence copied from a news site could have become
a way to read the whole project.

**We proved it before fixing it.** Four test payloads hidden in an event's name, its damage
description and a source link all came through intact and live. Then we fixed it — every piece
of outside text is now neutralised before it reaches the page, and source links are only
honoured if they're ordinary web addresses (anything exotic is shown as plain text instead of a
clickable link, so no source is ever quietly dropped).

**The part we're proudest of is how we checked the fix.** Our first check searched the page for
suspicious words and reported three payloads as "still dangerous" — they weren't. Neutralised
text still *contains* those words; it just can't do anything. Searching for words can't tell the
difference between disarmed and armed. So we rebuilt the check to read the page the way a
browser does and ask what would actually run. Then we added the important bit: we deliberately
switched the fix off and confirmed the test **fails**. A safety check that can never fail tells
you nothing.

**Bottom line:** we went looking for weaknesses in our own work, found a genuine one, proved it
was real, fixed it, and proved the fix — including proving that our proof works. All four live
dashboards now come back clean, and the official alarm figures are untouched, byte for byte.

---

## ✅ Milestone 55 — We taught the system to look at the water, not just the slope  *(flash-flood arm F0+F1 built, 2026-07-28)*

**What we set out to do.** Until now the tool answered one question: *is this slope creeping, and
is it raining hard enough to push it over?* But a slope can also fail because a flash flood in
the stream below scours away its foot — the hillside doesn't slide so much as lose the ground it
was standing on. We wanted to add that second story, without disturbing anything already working.

**The honest re-scoping first.** The natural request is "tell me how much flooding to expect".
We can't — not truthfully. Predicting water depth needs river gauges and a survey of the channel
bed, and we have neither. So we built what the data *can* support: where water concentrates,
which of our slopes sit next to those channels, and how hard it is raining on the basin
upstream of each one. Levels and rankings, never metres of water. Saying that plainly was the
first deliverable.

**The thing we were most worried about turned out to be free.** A flood at a point is driven by
rain falling far upstream, often much higher in the mountains — so surely we'd need a much
bigger, more expensive area of study? No. The elevation maps that already ship with every radar
product cover roughly 290 × 230 km, while our study area is a small box inside that. We measured
it: **all 22 upstream basins fit comfortably inside the maps we already had, with none running
off the edge.** The expensive radar area was never touched.

**We proved we broke nothing — we didn't just say it.** Before writing a single line of flood
code, we took a fingerprint of **116 existing result files** — every hazard map, every alarm
report, every validation score. After the new code ran, all 116 fingerprints matched exactly.
We also proved the new panel on the dashboard is a pure addition: delete it from the page and
what's left is the old page, character for character.

**Two safety catches, each deliberately tested by switching it off.** One refuses to grade a
basin that runs off the edge of the map, because we'd be measuring only part of it. The other
refuses to grade a basin whose rainfall record is missing — because "we have no data" and "it
didn't rain" are completely different answers, and quietly confusing them is exactly how a
system reports "all clear" when it actually knows nothing. We showed that without that catch,
the code really does return a confident all-clear on empty data.

**What we found, including the disappointing bit.** Only **3 of our 22 slopes** sit close enough
to a significant channel to be flood-exposed at all — so this arm speaks to a minority of sites,
and we've said so rather than dressing it up. We also found that every basin responds in about
4–7 minutes, so the clever "match the rainfall window to how fast this basin reacts" machinery
currently gives every basin the same answer. It works; it just isn't earning its keep yet.

**Where it stands.** The geometry is measured and real for both sites. The rainfall-grading half
is written and fully tested, but has **not** been run on live rainfall yet, so no flood level is
published anywhere — and nothing calls it automatically. Our test suite grew from **114 checks
to 151**, all passing.

---

## ✅ Milestone 56 — We switched the flood arm on, and it immediately taught us two things  *(first live run, 2026-07-28)*

**What we set out to do.** Milestone 55 built the flood machinery but had never fed it real
rainfall. This was the moment of truth: point it at four months of actual satellite rain over
both sites and see what came back.

**It worked — and then it didn't, in an interesting way.** Three of Ramban's eight basins came
back with "no rainfall data". Our safety catch had done its job and refused to guess. But
something looked wrong: two *other* basins of exactly the same size had worked fine. If the
satellite genuinely had no data over that patch of mountain, size wouldn't be the deciding
factor — and identical sizes wouldn't give opposite answers.

**The cause was us, not the satellite.** The rain data comes in roughly 11 km squares. Our
basins are about half a kilometre across — far smaller than one square. When you ask the data
service for an average over an area smaller than its own grid, it only answers if the tiny area
happens to contain the exact centre point of a square. Whether it does is pure luck of position.
Three of our basins were unlucky. We proved it by asking the same question three different ways
and watching the answer flip from "nothing" to a real number. The fix tells the service to look
more finely inside small areas. Importantly, this invents nothing: the underlying measurement is
still an 11 km average, and every page we produce says so. We confirmed the fix was a *rescue*
and not a distortion — the five basins that already worked returned exactly the same numbers
afterwards, to the decimal.

**The second lesson was almost worse, because nothing was broken.** Our first summary announced
"8 of 8 basins on FLOOD-ALERT". Every number in it was correct. But it was reporting the *worst
half-hour of the entire monsoon* as though it were today's situation. In reality about 84% of
days were quiet, and that very day was completely dry. On a warning page, that's not an untidy
label — it's telling someone there's an emergency when there isn't. We split the two apart: the
page now leads with **today**, and shows the season's worst separately and clearly labelled as
history.

**What the real numbers say.** Across the monsoon, a typical basin had **4 alert-grade days, 15
watch-grade days, and 99 quiet days** out of 118. On the day we ran it, every basin at both sites
was quiet. The worst moment of the season was 1 July at Ramban and 18 July at Vaishno Devi.

**We also connected it to the daily routine.** Previously you had to run the flood check by hand.
Now it refreshes automatically whenever the alarm updates — because a flood warning that isn't
current isn't a warning. If the rain service is unavailable, it's skipped and everything else
carries on exactly as before.

**Bottom line:** our checks grew from **114 to 154**, all passing, and the 116 fingerprinted
result files from the original system are still untouched, byte for byte. The most valuable
output of the day wasn't a number — it was two mistakes that only appeared when we stopped
testing and started *using* the thing.

---

## ✅ Milestone 57 — We checked our own homework against the plan, and found we had skipped the exam  *(audit sweep, 2026-07-28)*

**What we set out to do.** Before calling the flood feature finished, re-read the plan we wrote
at the start and compare it — line by line — against what actually got built. Not against our own
progress notes, which had twice said "done", but against the original document.

**What we found was the thing we had most needed to catch.** The plan contained one sentence we
had written ourselves: the flood arm must be replayed against the real disasters we have records
for, and *that result decides whether the card is allowed on the dashboard at all*. We had never
run it. The card was already on the dashboard, wired into the daily routine, with 154 passing
tests behind it. Every test we wrote passed. We simply hadn't written the one the plan demanded.

**So we ran it, and it failed.** On the 22 July 2026 Gangroo–Ramsu disaster — two deaths — our new
flood arm said "watch", while the older rainfall system we already trust said "alert". A brand new
safety feature was *quietly downgrading* a day people died. That is worse than having no feature.

**The cause was a single misread line.** The plan said to test each basin across rainfall windows
"from half an hour up to six hours", starting from how fast that basin reacts. We built it to test
*one* window — the shortest. Our basins react in about five minutes, so every basin was only ever
judged on half-hour bursts. The rain that killed people on 22 July fell over six hours. We had
built an instrument that was, by construction, unable to see the event it most needed to see.

**Fixed, it now beats the system it sits beside.** Testing the full range of windows, both fatal
events come out clearly:

| disaster | old rainfall system | new flood arm |
|---|---|---|
| 20 Apr 2025 Ramban cloudburst (3 deaths) | alert | **alert, 1.6× stronger** |
| 22 Jul 2026 Gangroo–Ramsu (2 deaths) | alert | **alert, 1.7× stronger** |

That is the result the whole idea rested on: looking at rain over the *basin above* a slope really
does see these disasters more sharply than averaging rain over the whole area.

**We also admitted a check that didn't work.** We tried to verify our river-network maths against
a published global one. First attempt compared the wrong points and suggested we were wrong by up
to 300×. Fixed that, and a second problem appeared: our map and theirs are drawn at slightly
different resolutions, so at these small stream sizes they simply don't line up — and near the big
Chenab river the comparison jumps onto the wrong river entirely. Only one of eight comparisons
survived. **So we recorded the check as "inconclusive" rather than publishing a confident number
based on a single point.** Not every check works, and saying so is part of the job.

**Bottom line:** the most valuable hour of this project was spent not writing code, but re-reading
our own plan and discovering the test we had agreed to run and then forgotten. Checks now stand at
**155**, all passing, and the original system's 116 result files remain untouched.

---

## ✅ Milestone 58 — The flood arm meets the disaster record, and we made our mistakes unrepeatable  *(2026-07-29)*

**What we set out to do.** Finish the flood feature properly: cover all four seasons of data the
rest of the project uses, put its verdicts next to the two rainfall systems we already trust in
the project's scorecard, and — most importantly — make sure the four mistakes we'd made building
it cannot happen again to anyone.

**The missing quarter, and what it found.** We had never run the flood arm over Vaishno Devi's
2025 season. Doing so, its worst reading of the entire season lands on **26 August 2025** — the
Ardhkuwari disaster, 34 deaths, the deadliest event in our records — and it is the strongest
flood signal anywhere in the whole dataset, with **every one of the 14 basins on alert that day**.

**The scorecard now has three columns, and it separates the serious from the ordinary.**

| what happened | deaths | flood arm | basins on alert |
|---|---|---|---|
| Ardhkuwari, 26 Aug 2025 | 34 | ALERT | **14 of 14** |
| Banganga, 21 Jul 2025 | 1 | ALERT | 12 of 14 |
| Ramban cloudburst, 20 Apr 2025 | 3 | ALERT | 6 of 8 |
| Gangroo–Ramsu, 22 Jul 2026 | 2 | ALERT | 4 of 8 |
| two non-fatal slips | 0 | watch only | **0 of 8** |

Every fatal event alerts; neither non-fatal event does. **We are being deliberately careful about
how much that proves**: it's seven events, and they're the same seven the older system was tuned
on. It describes the arm; it doesn't independently validate it. We've written that limitation
next to the table rather than letting the table speak for itself.

**Making the mistakes unrepeatable — the real work of the day.** We had made four errors: we
skipped our own plan's pass/fail exam; we misread one sentence and built an instrument blind to
the rain that kills; we blamed the data source for a bug in our own query; and we compared our
map to a reference map at the wrong place and "found" a 300× disagreement that never existed.

Rather than just fixing them, we made each one structurally impossible to repeat:
- the exam we skipped is now an **automatic test** that runs with every check, and it has its own
  self-test that deliberately rebuilds the broken version and demands it be rejected;
- the four lessons are written into the project's standing instructions, so the next session
  starts by re-reading the plan against the actual work — not against its own progress notes;
- the plan document itself now opens with a plain statement of what was actually built and where
  it differs from what was written, so it can never quietly mislead whoever reads it next.

**One thing we were careful about.** Adding columns to the scorecard meant changing a file our
own safety net protects. We backed it up, proved the change added three columns and altered
**zero existing values**, confirmed nothing else had moved, and only then updated the safety net.
Changing a protected file should be a decision, never a side effect.

**Bottom line:** checks now stand at **157**, all passing. The flood arm covers all four seasons,
sits in the project scorecard, and — for the first time — cannot silently break the promise it
was built to keep.

---

## ⚠️ Correction to Milestone 58, and a verdict two years of work waited on  *(claims audit, 2026-07-29)*

**We got something wrong in Milestone 58, and the user's instinct is what caught it.** Asked to
re-check the session for silent errors, we re-verified every claim against the actual data files
— and found the summary above says "every fatal event alerts; neither non-fatal event does."
That second half is **false**. There are *three* non-fatal events in our records, not two, and
one of them — the Himkoti landslide of July 2026 — does trigger a flood alert. The table in
M58 silently omitted it. So the honest statement is weaker: all four fatal events alert, and
the only two events that stay below alert are the two weakest ones by *every* measure we have.
The flood arm follows our rainfall-burst system closely; it does not magically tell deadly
events from harmless ones. We also overclaimed that the flood arm's number is now "the same
statistic" as the calibrated one — it's the same *kind* of number, but computed over a narrower
set of time windows, and we've corrected that too.

**How could this happen with 169 passing checks?** Because every check tests the *data*, and
the data was right. The wrong part was the English sentences we wrote about the data — and no
test re-reads prose. Both errors came from summarising from memory instead of counting from the
file. The project's standing rules now require every number in a written conclusion to be
re-derived by a command at the moment of writing — and forbid comparing two metrics as "the
same" without putting their definitions side by side.

**And one genuinely good piece of news from the same night.** While we were auditing, the
project's scheduled overnight run fired on its own — and our safety net immediately flagged
that four protected files had changed. Investigating *before* reacting showed it was exactly
the legitimate nightly refresh, running the new flood check unattended for the first time,
correctly and in the right order. Better still: the fresh weather data finally covered 22 July
2026 — the fatal boulder-strike day whose official verdict had been "pending" for a week. The
verified daily system reads it as a clear **ALERT**. That closes the last open question:
**every deadly event in our records is now flagged, on the day, by both trusted systems.**

---

## ✅ Milestone 59 — We answered three practical questions: a scary graph, an ageing map, and a cluttered disk  *(2026-08-01)*

**A scary-looking spike turned out to be the system working.** You noticed the rainfall-danger
graph on the Vaishno Devi dashboard shooting up in late July and asked: is that a bug? We
checked it the careful way — recomputed the number straight from the raw weather data (it
matched to four decimals), and then cross-checked a *completely separate* rain source, the GPM
satellite, which showed the same burst. It's real: about **147 mm of rain in a single day on 21
July 2026** — the same storm that caused the fatal boulder strike a day later. The graph even
stays high for a week afterward, which is correct, not stuck: it's the "ground is still soaked"
memory doing its job. We turned this one-off check into a permanent automatic test, so next time
a number looks surprising, the computer confirms it against the raw data instead of us having to
investigate by hand.

**The ageing hazard map: we priced the refresh, and it's your call.** The dashboard honestly
flags that the Vaishno Devi hazard map is built from radar that's now ~37 days old, and that
newer radar has arrived. We checked exactly what a refresh would take (without spending
anything): **5 new radar image-pairs** need processing, costing about **50 of our 8,000
processing credits** — trivially cheap. The catch isn't the credits; it's that turning those
into a new map is a heavy, multi-hour, multi-session computation that needs you at the wheel
(it involves stitching two different satellites together, a judgement call). So we've laid out
the exact plan and cost, and left the "go" button for you.

**A tidy-up tool that refuses to be dangerous.** The project's data folder has grown to ~52 GB,
mixing three very different things: irreplaceable downloads that cost credits to obtain,
validated results that must never be touched, and cheap throwaway caches. Deleting the wrong one
is a real risk. So we built a **read-only map** of every file that sorts them into four buckets —
*never touch* (16 MB of validated/committed results), *upload before deleting* (47 GB of
raw downloads), *delete freely* (4.8 GB of rebuildable caches — an easy win), and *ask a human*
(just 3 ground-truth files it wisely refuses to guess about). By design the tool **cannot delete
anything** — it only tells you what's safe; you do the deleting. It even double-checks that all
116 protected results are still present and accounted for.

**Bottom line:** all three questions answered, one new safety tool, and our automatic checks grew
to **181**, all passing.
