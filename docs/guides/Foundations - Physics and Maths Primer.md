# 📚 Foundations — The Physics & Maths Behind the Project

**A beginner's primer.** This document builds the conceptual base you need to
**confidently discuss this project with anyone** — from a curious friend to a
remote-sensing expert. It assumes you remember little from school physics/maths
and rebuilds each idea from scratch, with analogies, the (gentle) formula, and
**where it shows up in our actual project**.

**Companion to [milestone.md](../milestone.md):** that file tells the *story* of
what we did; this file explains the *science* of why it works. Wherever you see
🔗 **In our project**, it ties a concept back to a milestone.

> **How to read this:** You do not need to memorise formulas. Aim to understand
> each idea well enough to explain it in plain words and answer a follow-up
> question. The "Interview Prep" section (Part D) is your quick-revision cheat
> sheet before any public discussion.

---

## Table of Contents
- [The 30-Second Pitch](#the-30-second-pitch)
- [Part A — The Physics](#part-a--the-physics)
- [Part B — The Maths](#part-b--the-maths)
- [Part C — The Geoscience (just enough)](#part-c--the-geoscience-just-enough)
- [Part D — Interview Prep: Likely Questions & Confident Answers](#part-d--interview-prep-likely-questions--confident-answers)
- [Part E — Honest Limitations](#part-e--honest-limitations)
- [Glossary](#glossary)

---

## The 30-Second Pitch

> "Radar satellites orbit Earth and bounce microwaves off the ground. By very
> precisely comparing the *timing* (phase) of the wave between two passes over
> the same spot, we can measure if the ground moved — down to a few millimetres.
> We use this to watch Himalayan hillsides for slow creep that can precede a
> landslide — above the NH-44 highway in Ramban, and along the Vaishno Devi
> pilgrimage route — fused with real rainfall into a live, weather-gated warning,
> validated against documented landslides at both sites."

Everything below explains the words in that paragraph.

---

# Part A — The Physics

## A1. Waves 101 (the absolute basics)

A wave is a repeating wiggle. Three words describe it:

- **Wavelength (λ):** the distance between two wave crests. (Our radar: about
  **5.6 cm** — "C-band".)
- **Frequency:** how many crests pass per second. (Our radar: ~5.4 billion per
  second = 5.4 GHz.)
- **Phase:** *where in its cycle* the wave is right now — like the position of a
  clock's second hand, measured in degrees (0–360°) or radians (0–2π).

**Analogy:** Imagine a spinning wheel with a painted dot. Wavelength is how far
the wheel rolls in one full turn. Phase is the current angle of the painted dot.

🔗 **In our project:** the radar wavelength (5.6 cm) is the "ruler" we measure
the ground with — and phase is what lets us measure *fractions* of that ruler,
giving millimetre precision.

---

## A2. Radar, and why we use it

**Radar = RAdio Detection And Ranging.** The satellite *sends* its own microwave
pulse and listens for the echo. Two big advantages over a normal camera:

1. **It works day or night** (it brings its own "light").
2. **It sees through clouds and rain** (microwaves pass through them).

For a monsoon-soaked, cloud-covered region like the Himalayas, this is decisive —
an optical satellite would just see clouds for months. Radar is an **active**
sensor (makes its own signal); a camera is **passive** (relies on sunlight).

🔗 **In our project:** we use **Sentinel-1**, a European radar satellite that
revisits Ramban roughly every **12 days**.

---

## A3. SAR — what "Synthetic Aperture" means

A sharp radar image normally needs a giant antenna. A satellite can't carry a
kilometre-long antenna — so it *fakes* one. As it flies, it records echoes from
many positions along its path and combines them by computer, as if they came
from one enormous antenna. That trick is the **"synthetic aperture"** in **SAR
(Synthetic Aperture Radar)**.

**Analogy:** Instead of one huge eye, take many small snapshots while walking and
stitch them into one ultra-sharp picture.

🔗 **In our project:** every Sentinel-1 image is a SAR image. We specifically use
the **SLC** ("Single Look Complex") form, which keeps the all-important *phase*
information (see next).

---

## A4. Phase — the secret to millimetre measurement

Here's the heart of everything. When the radar wave travels to the ground and
back, the **phase** of the returning wave depends on the exact distance
travelled. If the ground moves even slightly toward or away from the satellite
between two passes, the wave travels a slightly different distance, and its phase
shifts.

Because we can measure phase to a tiny fraction of a cycle, and the wavelength is
only ~5.6 cm, we can detect distance changes of **millimetres**.

**The key formula (gentle version):**

> displacement = − (λ / 4π) × (phase change)

- λ = 5.6 cm is the wavelength.
- The "4π" (not 2π) is there because the wave makes a **round trip** — to the
  ground *and back* — so the path change is twice the ground movement.
- **One full phase cycle (2π, "one fringe") = half a wavelength of movement ≈
  2.77 cm.**

**Analogy:** A wheel of known circumference rolls along the ground. By watching
the exact final angle of the painted dot, you can tell how far it rolled — to a
fraction of one turn. Phase is that angle; wavelength is the circumference.

🔗 **In our project:** in **Milestone 1** we converted the radar's phase into
ground displacement in metres using exactly this formula. The "− sign" sets our
convention: **negative = ground moving away from the satellite (e.g. sinking or
sliding downslope).**

---

## A5. Interferometry — comparing two passes (the "interferogram")

**InSAR = Interferometric SAR.** Take two SAR images of the same place from two
different dates and subtract their phases. What's left — the *phase difference* —
is the **interferogram**, and it reveals how the ground moved between the two
dates.

Classic interferograms look like psychedelic rainbow contour maps. Each complete
colour cycle ("fringe") = 2.77 cm of movement along the radar's line of sight.

**Analogy:** Two photos of a crowd taken a minute apart. Overlay them and look at
what *changed* — that difference is the interferogram. Everything static cancels;
only motion stands out.

🔗 **In our project:** we ordered **183 interferograms** (pairs of dates) from
ASF's HyP3 service. Each one is a "how much did the ground move between date A and
date B" map.

---

## A6. Line-of-Sight (LOS) — why we don't measure pure up/down

The satellite doesn't look straight down; it looks **sideways at an angle**
(~30–45° from vertical for Sentinel-1). So it only measures the part of the
ground's motion that happens to point **toward or away from the satellite** —
the **Line-of-Sight (LOS)** component. A purely sideways slide perpendicular to
the look direction is partly invisible to it.

**Analogy:** Watching someone's shadow from an angle. You see a *mix* of their
side-to-side and up-down motion, not the pure vertical.

To untangle true vertical vs horizontal motion, you combine views from different
geometries — which is why **ascending** and **descending** passes matter (A9).

🔗 **In our project:** our velocity map is a **LOS velocity** (movement along the
radar's slanted view). Full 3-D decomposition (separating vertical from
east-west) is a later step needing both ascending and descending data.

---

## A7. Coherence — when to trust a pixel

For the phase comparison to mean anything, the ground must look *electromagnetically
similar* between the two passes. **Coherence (γ)** is a number from **0 to 1**
measuring that similarity:

- **Near 1:** the surface barely changed (bare rock, concrete, buildings) → the
  phase is trustworthy.
- **Near 0:** the surface scrambled between passes (forest leaves moving, water,
  snow) → the phase is random noise, a lie.

**Analogy:** Two photos of a brick wall match perfectly (high coherence). Two
photos of a windblown tree look totally different (low coherence) — you can't
measure anything reliable from them.

🔗 **In our project:** in **Milestone 1** we threw away every pixel with
coherence below **0.4** — "punching holes" in the data on purpose so vegetation
noise can't masquerade as landslides.

---

## A8. The atmosphere problem (the great impersonator)

Radar waves slow down slightly when passing through **wet air** (water vapour).
If one pass had more humidity than the other, the wave is delayed — and that
delay looks *exactly like the ground moved*, even though it didn't. This is the
**Atmospheric Phase Screen (APS)** problem.

Two crucial clues let us separate atmosphere from real motion:

1. **Atmosphere correlates with terrain height** — valleys hold more wet air than
   ridges, so fake "motion" often mirrors the topography.
2. **Atmosphere is random in time but smooth in space** (a cloud covers a wide
   area today, gone tomorrow). **Ground motion is the opposite** — smooth in time
   (a creeping slope keeps creeping) but sharp in space (the slope moves; the
   road 50 m away doesn't).

🔗 **In our project:** we attacked this twice. In **Milestone 1** we statistically
flagged interferograms whose "motion" correlated too strongly with elevation
(the height clue). In **Milestone 2** we removed broad, smooth spatial patterns
(the space-vs-time clue) and subtracted a "tilt" from each image (the deramping
fix).

---

## A9. Orbits, look directions, and baselines

- **Ascending pass:** satellite flying south→north (looking roughly east).
- **Descending pass:** flying north→south (looking roughly west).
  Combining both lets you separate vertical from horizontal motion.
- **Perpendicular baseline:** the sideways distance between the satellite's two
  orbital positions for a pair. If it's too large, the two views are too
  geometrically different and the phase decorrelates (geometric noise). Smaller
  is better.

🔗 **In our project:** we **strictly never mix** ascending and descending images
in one interferogram — their geometries are incompatible and would corrupt the
math. We sorted all data into 5 "stacks" by direction + orbit track + frame.

---

# Part B — The Maths

## B1. Pixels, rasters, and grids

A satellite image is a **raster**: a grid of **pixels**, each holding a number
(here, a phase or a displacement). Our pixels are **~80 m × 80 m** on the ground.
Each raster also carries **georeferencing** — which real-world coordinates each
pixel sits at — so it can be laid over a map.

🔗 **In our project:** every `.tif` file we produce is a raster. A "velocity map"
is a raster where each pixel's number is a speed in mm/year.

---

## B2. Phase wrapping & unwrapping (the 2π puzzle)

Phase is measured **modulo one cycle** — the instrument can tell you the wave is
at 30° but *not* how many full turns it already made. This is **wrapped phase**.

**Analogy:** A 12-hour clock shows "3 o'clock" but not whether 3 days passed.
Recovering the full elapsed time is **phase unwrapping** — counting the hidden
whole cycles. It's a hard, error-prone step: a mistake adds a whole fringe
(2.77 cm) of fake jump.

🔗 **In our project:** HyP3 does the unwrapping for us, but unwrapping *errors*
are a known troublemaker. In **Milestone 2** our quality filter (temporal
coherence) was designed partly to catch pixels whose unwrapping looks
inconsistent.

---

## B3. Turning many pairs into a timeline: linear systems & least squares

We have many interferograms, each saying "between date A and date B the ground
moved by X." We want the opposite: the ground's position at **every** date,
relative to the start. That's a system of equations.

Write it as a matrix equation:

> **A · d = m**

- **m** = all our measured pair-movements (what we observed).
- **d** = the unknown ground positions at each date (what we want).
- **A** = the **design matrix** — bookkeeping that says which two dates each
  measurement connects.

We usually have *more* measurements than unknowns (good — it's redundant), so no
exact answer fits all of them due to noise. **Least squares** finds the **d** that
comes *closest* to satisfying all equations — the best compromise.

**Analogy:** You have many noisy "A is 3 cm higher than B" statements. Least
squares finds the single set of heights that disagrees with all the statements as
little as possible. It's the multi-dimensional cousin of drawing a best-fit line
through scattered dots.

🔗 **In our project:** this *is* the SBAS inversion in **Milestone 2** — the core
engine that turns 31 image-pairs into one continuous displacement timeline per
pixel. ("SBAS" = Small BAseline Subset.)

---

## B4. The design matrix, "rank", and connectivity

For least squares to have a unique answer, the measurements must **chain together
across all dates** with no gaps. In maths terms the design matrix must be **full
rank**.

**Analogy:** A relay race. If every runner hands the baton to the next, the chain
is complete and you can time the whole race. If one handoff is missing, the race
splits into two disconnected groups and you **can't** compare a runner in group 1
to one in group 2 — the timeline is broken into "islands."

🔗 **In our project:** before inverting, in **Milestone 1's** final step we drew a
**network graph** and checked the chain was unbroken. When quarantining bad
images split it into islands, we "rescued" a few borderline images just to keep
the chain connected. Full rank = solvable; broken chain = the math fails silently.

---

## B5. From timeline to speed: linear regression (the slope)

Once each pixel has a displacement *timeline* (position at each date), the
**mean velocity** is just **how fast it trended over time** — the **slope** of a
straight line fitted through those points.

**Analogy:** Plot your weight each week for a year and draw the best straight
line through the dots. Its steepness (kg per month) is your trend. Our velocity
is the same idea: millimetres per year.

🔗 **In our project:** the deliverable `..._mean_velocity_los.tif` is exactly this
slope, computed for every pixel. Negative slope = sinking/sliding away from the
satellite.

---

## B6. Correlation and R² (the atmosphere detector)

**Correlation** measures how strongly two things move together, from −1 to +1.
**R²** (correlation squared, 0 to 1) says *what fraction of one variable is
explained by the other.*

- R² near 0: no relationship.
- R² near 1: tightly linked.

🔗 **In our project:** in **Milestone 1** we computed R² between each
interferogram's apparent "movement" and the terrain **elevation**. A high R²
(say > 0.5) means the "movement" is really just atmosphere hugging the
topography — so we quarantined that image. This is the maths behind the "height
clue" from A8.

---

## B7. Filtering: high-pass / low-pass, space vs time

A **filter** keeps some patterns and removes others:

- **Low-pass:** keeps broad, smooth, slowly-varying stuff; removes sharp detail.
- **High-pass:** the opposite — keeps sharp, local detail; removes broad trends.

**Analogy:** A music equalizer. "Bass" = broad/smooth (low-pass keeps it);
"treble" = sharp/detailed (high-pass keeps it).

Recall from A8: **atmosphere is broad and smooth** (bass), **landslides are sharp
and local** (treble). So to remove atmosphere we apply a **spatial high-pass** —
discard the broad smooth pattern, keep the local anomalies.

🔗 **In our project:** in **Milestone 2** we used a spatial high-pass to strip the
broad atmospheric "haze" from the velocity map, leaving the localized signals a
landslide would create.

---

## B8. Map coordinates & projections (light touch)

Earth is round; maps are flat. A **projection** is a recipe for flattening it.
You'll hear:

- **Latitude/Longitude (WGS84):** angles on the globe (degrees).
- **UTM:** a flat grid in **metres**, great for measuring distances and slopes.

🔗 **In our project:** our data is in **UTM (metres)** — convenient because slope
calculations for Phase 3 need real-world distances, not degrees.

---

# Part C — The Geoscience (just enough)

## C1. Why Ramban, and what triggers landslides

The **NH-44** is a strategic highway through steep, geologically young, fractured
Himalayan slopes. Two triggers dominate:

- **Monsoon rainfall** — water seeps into soil, adds weight, and lubricates
  potential slip surfaces.
- **Western Disturbances** — winter storm systems delivering intense
  precipitation.

Slopes often **creep slowly for weeks** before a sudden failure. Catching that
creep is the whole point of measuring millimetre motion.

## C2. Slope angle — the single biggest driver

The **slope angle (β)** is how steep the ground is, computed from the DEM by
looking at how fast elevation changes from one pixel to the next. Steeper ground
has more of gravity pulling material *down the slope* rather than *into* it, so
slope is the dominant control on landslide risk.

**Analogy:** a ball on a gentle ramp stays put; on a steep ramp it rolls. The
steeper the ramp, the less it takes to start moving.

🔗 **In our project:** in **Milestone 3** we computed slope from the DEM
(median ~28° over Ramban — genuinely steep). *Caveat:* our DEM is coarse (80 m
pixels), which **smooths out and under-estimates** real steepness — a known MVP
limitation we'll fix with a finer (12.5 m) DEM later.

## C3. Topographic Wetness Index (TWI) — where water collects

Water weakens slopes, and water flows downhill and pools in valleys and hollows.
**TWI** estimates how wet each spot tends to be, by combining two things: **how
much uphill land drains into it** (more drainage = wetter) and **how steep it is**
(flatter = water lingers).

> TWI = ln( upslope drainage area ÷ tan(slope) )

High TWI = valley bottoms and hollows (wet, weaker). Low TWI = ridges (dry).

**Analogy:** after rain, puddles form in the dips where lots of ground drains
into a flat spot — never on a steep ridge. TWI is a map of "where the puddles
form."

🔗 **In our project:** **Milestone 3** computes TWI from the DEM (using a simple
"D8" rule that routes each cell's water to its steepest downhill neighbour). For
now it's an information layer; later it can spatially set *how saturated* each
pixel is in the stability calculation.

## C4. The Infinite Slope model & Factor of Safety (FS)

Engineers judge a slope by its **Factor of Safety (FS)** — a tug-of-war ratio:

> FS = (forces resisting sliding) ÷ (forces driving sliding)

- **FS > 1:** resistance wins → stable.
- **FS < 1:** gravity + water win → failure.

The **Infinite Slope model** is the simplest way to compute FS for a shallow
landslide (a thin layer of soil sliding on bedrock). Its formula:

> FS = [ c' + (γ − m·γ_w)·z·cos²β·tanφ' ] ÷ [ γ·z·sinβ·cosβ ]

In plain words, each symbol is a real, intuitive thing:
- **c' (cohesion):** how "sticky" the soil is (roots, clay) — resists sliding.
- **φ' (friction angle):** how much the grains grip each other — resists sliding.
- **β (slope):** steepness — drives sliding (bigger β, bigger driving force).
- **z (depth):** how thick the sliding layer is.
- **γ, γ_w:** the weight of the soil and of water.
- **m (saturation):** how waterlogged it is, 0 (dry) to 1 (fully soaked).

The key insight: as **m** rises (rain soaks in), the water *buoys* the soil,
cutting the friction that holds it — so **FS drops**. That's monsoon turning a
stable slope unstable, captured in one term.

**Analogy:** a dry sandcastle holds; pour water in and it slumps. Same sand,
same slope — water removed the grip.

**The sandcastle has a second half — matric suction (Milestone 26).** A *damp* sandcastle holds far
better than a *dry* one: a little moisture creates surface-tension "bridges" between grains — an **apparent
cohesion** — that you lose both when it dries out *and* when it floods. So a slope's stickiness c isn't one
number: it's **high when damp (c' + suction)** and **low when saturated (c' alone, suction gone)**. We split
it — FS_dry uses the high (GSI-measured dry) cohesion, FS_sat uses the low one — and because c slides
linearly from the dry to the wet value as m rises, **FS stays a straight line in m**, so the whole
`FS_real = (1−m)·FS_dry + m·FS_sat` machinery is untouched.

🔗 **In our project:** **Milestone 3** computes FS for **dry (m=0)** and **monsoon-soaked (m=1)**; the
friction angle φ'=36° is the **GSI site-measured** value (Milestone 22). **Milestone 26** added the
matric-suction split (c_dry≈18.5, c_wet=5 kPa): dry slopes are now correctly much stronger (almost none
unstable when dry), the soaked worst case is unchanged, and — because suction protects the in-between days
— the realistic operating wetness rose (~40%→~55% soaked) and the validated score *improved* to its best
(AUC 0.61). Remaining assumption: the suction-vs-wetness curve is taken as linear (a nonlinear retention
curve is the next refinement); depth z and the exact cohesion units await lab confirmation.

## C5. Fusing physics with measurement — the hazard map

FS is *theory* ("this slope **should** be unstable"). Our InSAR velocity is
*observation* ("this slope **is** actually moving"). The strongest warning is
when **both agree**.

🔗 **In our project:** **Milestone 3** combines them into a 3-level hazard map:
- **HIGH** = theoretically unstable (FS < 1) **AND** measurably creeping
  (velocity beyond −15 mm/yr).
- **WATCH** = one condition but not both.
- **LOW** = neither.

This "physics AND observation" rule is exactly the logic the automated warning
system (Phase 4) runs on.

---

# Part C-bis — The Agentic Warning System (Phase 4)

## C6. What "agentic" means here

An **agent**, in software, is a component with one clear job that takes inputs,
reasons, and produces outputs — and several agents can be chained so each
hands off to the next. Our system has **three**, each a specialist:

- **Agent 1 — InSAR Auditor:** reads the movement map, reports *where the ground
  is creeping*.
- **Agent 2 — Meteorological Trigger:** reads the weather (rainfall), reports
  *how waterlogged and therefore weak the slopes are*.
- **Agent 3 — Cascading Reasoner:** combines the two and decides *where to raise
  an alarm*, then explains itself.

**Analogy:** a newsroom. One reporter covers the ground sensors, another covers
the weather, and an editor combines both into the story that goes out. Each does
one job well; the editor reasons over their inputs.

**Important honesty point:** our agents are currently **deterministic rules** (a
fixed "if-this-then-that" Python pipeline), *not* a learning AI or a large
language model. That's a deliberate MVP choice — it's reproducible, needs no
internet or API keys, and is easy to audit. A real "thinking" LLM agent is a
future upgrade.

🔗 **In our project:** **Milestone 4** built exactly this three-agent pipeline as
`agentic_orchestrator.py`.

## C7. Cascading reasoning & the alert rule

"Cascading" means one finding triggers the next check, like dominoes. The core
rule is the project's headline logic:

> **Raise an alert where the slope is theoretically unstable (FS < 1) AND we
> have measured it actually creeping (velocity < −15 mm/yr).**

Single flagged pixels are ignored as noise; only **clusters** (groups of
neighbouring danger pixels) become alert *zones*, each pinned to a real
latitude/longitude with a plain-English reason.

**Analogy:** a smoke alarm that only sounds when it detects **both** smoke *and*
heat — far fewer false alarms than either sensor alone.

🔗 **In our project:** the rainfall scenario visibly drives the cascade — **dry**
day → 29 alert zones; **monsoon** → 222. That jump is the system reacting to its
trigger.

## C8. Downstream risk & LLOF (Landslide-Lake Outburst Flood)

A landslide is dangerous not only where it sits but **downhill** of it. If debris
slides into a river and dams it, water builds up behind the natural dam until it
suddenly bursts — a **Landslide-Lake Outburst Flood (LLOF)** that can devastate
communities far downstream.

**Analogy:** blocking a stream with a pile of dirt — the pond grows quietly, then
the dirt gives way and a wall of water rushes down.

🔗 **In our project:** Agent 3 flags an alert zone for *potential downstream
risk* if it's a large, steep, failing slope near a valley channel. **Caveat:**
this is currently a rough rule-of-thumb using our "wetness index" as a stand-in
for rivers — a proper version needs real river/flow-routing data.

---

# Part C-ter — Scaling & Hardening (Milestones 6–8)

## CT1. Connectivity rescue & the "load-bearing bridge"

The SBAS maths (B3–B4) needs the acquisition dates to form **one connected
network**. If the clean (KEEP) links leave the dates split into separate "islands,"
the system is rank-deficient and the inversion is silently wrong. To join two islands
you must promote ("rescue") a borderline (CONCERN) interferogram to act as a **bridge**.

**The key insight:** a bridge is an **unredundant single point of failure**. Inside a
dense island, a noisy link is averaged out by its neighbours (B3's redundancy); a
bridge is the *only* path between two islands, so its noise flows **undamped** into
every measurement that crosses it. A rescue must therefore clear a *stricter* quality
bar than an ordinary link — not a looser one.

**Everyday analogy:** one rickety plank bridging two solid islands. On the island you
can step around a weak board; on the single bridge, one bad board dumps you in the
river — so you inspect that plank far more carefully.

**How we do it (the gate):** a candidate bridge is allowed only if it's clean enough —
atmospheric R² ≤ 0.45 (A8/B6) **and** coherence ≥ 0.6 (A7). If a gap's only candidates
fail, we **refuse to bridge it** and handle that stretch differently (SVD /
period-split) rather than injecting noise. Among clean-enough candidates we pick the
one with the **most coverage**, because the bridge also caps how much *ground* the
whole network can solve.

🔗 **In our project: Milestone 7.** `sbas_network_graph.py` auto-selects rescues and
emits a "rejected bridges + reasons" audit; `apply_connectivity_rescues.py` applies
them. Real catch: ranking by *cleanest alone* once picked a longer-baseline bridge
that halved usable pixels — so we switched to **coverage-first** among gate-passers.

## CT2. Many looks, one map (why you can't just average)

Each satellite track views the slope from a different angle, so each measures a
different **projection** of the true 3-D motion onto its own line-of-sight (A6). Two
tracks reporting different LOS speeds for the same slope aren't contradicting each
other — they see the same motion from different directions. So you must **not** blur
their velocities into one number.

**Everyday analogy:** two people photograph the same walker from different corners.
You can't average "how fast they cross *my* photo" — the angles differ. But if *both*
photos show danger, you're doubly sure.

**What we do — union at the decision level:** compute danger *per track*, then combine
by logical **OR** — a slope is flagged if **any** track sees it unstable + creeping;
spots flagged by **two or more** tracks are the most trustworthy. (The "proper"
alternative — combining ascending + descending LOS into true vertical + east-west
motion — is a later step needing the descending tracks.)

🔗 **In our project: Milestone 7.** `run_multistack.py` builds the area-wide hazard as
a union across 3 ascending tracks; 26 monsoon zones are confirmed by ≥2 looks.

## CT3. MintPy & the ERA5 atmosphere filter

Our home-built engine leaves a ~30 mm/yr "fuzziness" floor, dominated by the
atmosphere (A8). **MintPy** is the peer-reviewed, field-standard SBAS package; its big
advantage is a *physical* atmosphere correction: it downloads **ERA5** (a global
weather reanalysis — temperature/pressure/humidity on a grid for any past hour),
computes the extra signal delay the air added on each radar pass, and **subtracts it**
— instead of our statistical "discard suspicious images" approach.

**Everyday analogy:** our method spots and throws away photos shot through heat-haze;
MintPy instead *models* the haze from that day's weather record and removes it, keeping
the photo.

🔗 **In our project: Milestones 8–9.** We built MintPy its own container, verified the
ERA5 download credentials, and ran MintPy on frame106 with the correction first OFF
(Milestone 8) then **ON** (Milestone 9). Switching ERA5 on **nearly doubled** the
agreement with our independent custom engine (Pearson r **+0.28 → +0.55** on the same
pixels) and **cut MintPy's velocity scatter from ~39 to ~21 mm/yr** — direct evidence
that the atmosphere, not real ground motion, dominated the earlier disagreement. Two
independent SBAS implementations now corroborate each other at r≈0.55–0.59.

**Two flavours of atmosphere (Milestone 21 — the method comparison).** The air delay has
two parts: a **stratified** part that tracks *elevation* (thicker air column lower down —
think haze that's denser in the valley), and a **turbulent** part (random weather swirls).
There are two ways to remove it: a **weather-model** correction (ERA5) that models the *real
3-D air* that day, or a cheap **empirical "height-correlation"** correction (Doin 2009 — the
same idea as the TRAIN toolbox's *power-law* method) that just fits delay-vs-elevation from
the radar data, no weather needed. We compared all three (none / ERA5 / height-correlation)
on the *same* pixels: **ERA5 cut the scatter 31 %** (30.5 → 21 mm/yr); the empirical method
*improved agreement* between the two engines but **barely moved the scatter** — because it
only removes the *stratified* part, leaving the *turbulent* haze that actually dominates our
floor. Lesson: here you **need the weather model**; the cheap topo-only trick isn't enough.
(This is the kind of "we compared correction methods" check reviewers look for — Bekaert et
al. 2015.)

---

## CT4. Disconnected networks, SVD, and the courage to discard a stack

Recall B4: turning interferograms into a timeline needs the acquisition dates to form one
connected chain. Sometimes too many pairs are thrown out (vegetation, weather) and the chain
breaks into **islands** of dates separated by gaps the maths can't cross. Two things then go
wrong — and both sank our descending tracks (Milestone 10):

**1. Rank-deficiency (the gap problem).** If the dates split into islands, you cannot know
the *relative* motion between islands — no interferogram bridges them. MintPy still returns
an answer using the **SVD** (singular value decomposition), a linear-algebra tool that gives
the **minimum-norm** solution: the smallest, simplest motion consistent with the data. That's
a reasonable *guess* across the gap, but it's a regularization assumption, not a measurement —
so the velocity "can be biased" (MintPy says exactly that).

**2. Short-baseline noise amplification.** Velocity is a *slope* = displacement ÷ time. Shrink
the time window — e.g. analyse one short island on its own (a **period-split**) — and the same
measurement noise is divided by a smaller time, so the velocity *error grows*. A ~3-month
window is roughly twice as noisy as a ~6-month one, from the arithmetic alone.

**Everyday analogy:** estimating a car's speed from two photos. Over an hour, a 1-metre
position error barely dents the speed; over five seconds, that same error makes the speed look
wildly wrong. Short baseline → noisy speed.

**Quality coherence ≠ trustworthy velocity.** A pixel can have high *temporal coherence* (its
timeline fits the interferograms well *within* each island) yet a meaningless velocity (the
slope across SVD-bridged or short windows). Good fit ≠ good slope — a subtle trap.

🔗 **In our project: Milestone 10.** Both descending stacks were dumped. One had no coherent
anchor anywhere (~1% usable). The other gave physically-impossible velocities — std **57 mm/yr**
on the full (SVD-bridged) network, *worse* at **137 mm/yr** when period-split — versus
**21–30 mm/yr** for the ascending stacks. A real signal can't be 2–5× noisier just from the
opposite look direction, so it's noise; we refused to fold it into a good result. Discarding
bad data is a feature, not a failure.

---

# Part C-quater — From a Hazard Map to a Forecast (Milestone 11)

## CF1. Inverse-velocity time-to-failure (Fukuzono/Voight)

So far the hazard map says *where* a slope is dangerous. The inverse-velocity method takes the
next step — estimating *when* it might fail — from the per-pixel movement timeline we already
produce (B5), with no new data.

**The idea.** A slope heading for collapse enters "tertiary creep": it speeds up in a
characteristic way. Fukuzono (1985) noticed that the **inverse** of velocity, 1/v, plotted against
time falls in a roughly **straight line that reaches zero at the moment of failure**. So you fit a
line to the recent 1/v points and read off where it crosses zero — the projected failure time t_f.

**Gentle formula.** If velocity grows like v ∝ 1/(t_f − t), then 1/v ∝ (t_f − t) — a straight line
hitting zero at t = t_f. Fit 1/v = a + b·t; the crossing is **t_f = −a/b**, and the lead time is
t_f − today.

**Everyday analogy.** A kettle's whistle rising in pitch — extrapolate the trend and you can guess
when it'll peak. Inverse velocity does this for a slope. But it only works once the slope is
*genuinely accelerating*: a slope creeping at a *steady* pace has a flat 1/v line that never
reaches zero, so it (correctly) predicts no failure.

**The catch (and the discipline).** 1/v blows up when v is near zero, so the method is very
noise-sensitive — left ungated it will happily fit a "failure" to random wobble. The safeguard is
*gates*: only trust a prediction when the slope is **consistently** moving the failure direction
and the 1/v line is **significantly** decreasing. We learned this the hard way (Part E / error log).

🔗 **In our project: Milestone 11.** We screen every alert zone this way. Honestly, with only
~3.5 months of data at our ~30 mm/yr noise floor, **no zone shows significant acceleration** — all
are steady creep. The machinery is built and noise-hardened, and will project a failure date
automatically once the data shows acceleration (a longer series, or a real event onset).

## CF2. Rainfall intensity–duration (ID) thresholds — the trigger

CF1 reads the slope's *motion*; CF2 reads the thing that sets it off — *rainfall*. The
field-standard landslide TRIGGER is an intensity–duration threshold. The insight: a burst matters
more than the total — 100 mm in 6 hours is far more dangerous than 100 mm over a week, because the
ground can't drain fast enough.

**The idea.** Plot mean rainfall intensity I (mm/h) against duration D (h). Decades of landslide
records define a line I = a·D^(−b) — high for short bursts, lower for long soaks — above which
slopes have historically failed. We use the classic global Caine (1980) curve, I = 14.82·D^(−0.39),
as a conservative baseline.

**Gentle formula.** For a window of duration D, the cumulative rain that just reaches the threshold
is C = I·D = 14.82·D^0.61 (D in hours). Exceed C over any duration and the trigger fires.

**Everyday analogy.** A sink with a slow drain: a gentle trickle is fine, but open the tap and it
overflows. Soil has a drainage rate; rain above that rate, for long enough, saturates and fails it.

🔗 **In our project: Milestones 12–13.** We pulled real ERA5-Land daily rainfall for Ramban across
May–Oct 2025 (1,233 mm) and screened it against Caine — exactly one day crossed the line, **26 Aug
2025, ~134 mm/day**, the season's true trigger (vs the made-up "120 mm/72h monsoon"). We then
**coupled** it into the Factor of Safety: the infinite-slope FS is *exactly linear in saturation m*
(C4), so for any day's measured wetness we blend the two end-member maps,
**FS_real = (1−m)·FS_dry + m·FS_saturated**, with no recompute. Walking that across the season gives
a **time-resolved hazard** — alert zones rise through the monsoon, peak at 222 on 26 Aug, then decay
as the soil dries. So now: *where* (C5) + *is it moving* (CF1) + *did the trigger fire & how wet is
it now* (CF2) → one warning that **tracks real weather over time**.

---

## CF3. Snowmelt & freeze-thaw — the other water (and what a negative result teaches)

Rain isn't the only water that loads a Himalayan slope. In spring, **melting snow** soaks the ground,
and repeated **freeze–thaw** (water freezes in cracks, expands, prises rock apart, then thaws and
lubricates) mechanically weakens it. The back-test (Milestone 14) caught our rain-only trigger missing
the **April–May 2025** failures — exactly the snowmelt/freeze-thaw season — so we added both.

**The idea.** Treat the water reaching the slope as **water = rain + snowmelt**, and screen *that*
against the rainfall trigger curve (CF2); separately flag days whose temperature swings across 0 °C
(Tmin < 0 < Tmax) as freeze–thaw.

**Everyday analogy.** A fridge defrosting: the puddle isn't from new spills, it's yesterday's ice
turning to water. Snowmelt is the mountain's slow defrost feeding the slope days after the snow fell.

**Gentle formula.** water_d = rain_d + snowmelt_d; freeze_thaw_d = (Tmin_d < 0 °C) AND (Tmax_d > 0 °C).

🔗 **In our project: Milestone 16 — and an honest negative result.** Real ERA5-Land gave **59 mm of
snowmelt** for the season (vs 1,350 mm rain), mostly early April. That's far below the heavy-burst
trigger line, so it added **no new trigger day**, and the freeze-thaw flag was **0** because the
*area-average* temperature never crossed freezing (the warm valley floor hides the cold high slopes —
proper freeze-thaw needs temperature *by elevation*). The lesson is the value: this **rules snowmelt
out** as the reason we missed April–May and points at the true culprit — the global rainfall record
**under-counts intense mountain cloudbursts** (it logged ~9 mm on a documented mudslide day). So the
next fix is pinpointed: a **rain-gauge product (CHIRPS/GPM) + a regional trigger curve**. (Ruling a
cause *out* is real progress.)

🔗 **Update — Milestone 19: freeze-thaw, resolved by elevation.** The "0 freeze-thaw days" above was an
artifact of the *area-average*. Temperature falls ~**6.5 °C per km** of height (the **lapse rate**), so we
estimated the temperature at each elevation band from the DEM and counted again: freeze-thaw **switches on
around ~2,500 m** and strengthens upward, while the road/failure sites in the **warm valley (~1,540 m) still
see zero**. So freeze-thaw works the **higher source slopes above the road**, not the road itself. And the
ground was **moderately wet** on both 2025 event days (≈33 % / 20 % of the season's peak wetness) from
snowmelt + earlier rain — even with no rain that day. Net picture: the spring slopes were **slowly primed**
(damp + freeze-thaw aloft) — a *mechanistic* story, honestly tagged as first-order (constant lapse rate,
reference height = DEM mean), that explains *vulnerability*. (Subsequent date correction, CF5/Milestone 20:
the major 20 Apr event then *was* tipped over by a cloudburst — so the full picture is **primed slope +
acute trigger**, not priming alone.)

## CF4. Slope-parallel velocity (V_slope) — reading the motion downhill

Our radar measures only the motion *along its line of sight* (A6) — a slanted direction. A landslide
moves *downhill*. So the radar under-reads creep, and on some slopes is nearly blind to it. With one
look direction we can't fully separate up/down from sideways (that needs ascending + descending, CT2,
still deferred), but we **can** project the LOS speed onto the steepest-descent direction, assuming
the motion is downslope.

**The idea.** Build two unit vectors at each pixel: the LOS direction **l** (from the radar geometry,
HyP3's `lv_theta`/`lv_phi`) and the downslope direction **d** (from the DEM's slope + aspect). Their
dot product **C = d·l** is the **sensitivity**: how much of a downhill motion the radar actually sees.

**Gentle formula.** V_slope = V_LOS / (d·l). Because |d·l| ≤ 1, this *amplifies* the measured speed
(recovering the part the radar missed). Where |d·l| is tiny (downhill ⟂ LOS), the slope is a **blind
spot** and we mask it.

**Everyday analogy.** Watching a car drive away at an angle through a narrow doorway: you only see part
of its speed. If you know the road's direction, you can work out its true speed — unless it crosses
your view exactly sideways, when you can't judge it at all.

🔗 **In our project: Milestone 15.** Across the 3 ascending tracks, **24–42 %** of measured ground turns
out to be a single-look **blind spot** (downhill nearly perpendicular to the LOS) — we now map exactly
where we're flying blind. For the rest, projecting to downslope **magnifies creep ×1.4–1.6**, sharpening
both the creep map and the failure-timing method (CF1). It's the cheap, single-track stand-in for the
full vertical+east-west decomposition awaiting better descending data.

---

## CF5. Regional vs global trigger lines, and gauge vs reanalysis rain

The rainfall trigger (CF2) has **two** dials, and getting either wrong mistimes the warning.

**Dial 1 — the threshold line.** The intensity–duration curve I = a·D^(−b) is *fitted to a region's own
history*. The classic **Caine (1980)** curve is a **global** average — deliberately conservative — so for
a specific, very wet, very steep place it sits far too high. For the NW Himalaya the published curve is
I = 2.9993·D^(−0.4152): about **19 mm of rain in a day** trips it, versus Caine's **~100 mm/day**. A
locally-confirmed line (a separate NH-44 study finds slides at ~14 mm/day) is **~5× more sensitive**.

**Dial 2 — the rain measurement itself.** A *reanalysis* like ERA5-Land is a physics model on a coarse
grid; it **smooths away** the intense, localized cloudbursts that mountains squeeze out of the air
(*orographic* rain). A **gauge-blended** product like **CHIRPS** mixes satellite estimates with real
ground rain-gauge readings, so it recovers more of those bursts.

**Everyday analogy.** Dial 1 is the *speed limit* — a national default vs the one actually posted for
this hairpin bend. Dial 2 is your *speedometer's accuracy* — a rough estimate vs a calibrated reading. To
catch real speeding you need both the right limit **and** a trustworthy gauge.

**The catch (a real lesson).** Lowering the line catches more real events — but lower it too far and it
flags *everything*. Our regional line caught both missed spring events (0/2 → 2/2) but then fired on
**112 of 214 days**: **sensitive, not selective**. The fix is a "how rare is this rain?" filter
(percentile / return-period) and an *antecedent* (how-wet-already) criterion on top of the line.

🔗 **In our project: Milestone 17.** We made the threshold a documented, citeable switch (`caine1980`
vs `nwhimalaya`) and built the CHIRPS gauge-rain pipe (Google Earth Engine) ready to run. The regional
line alone flipped the spring back-test to 2/2 on unchanged data — confirming the missed events were
substantially a *too-cautious-line* problem — while honestly exposing the over-triggering still to fix.
We then built the selectivity filter (`rainfall_specificity.py`) and it gave a *decisive* answer: scoring
each day by how far above the line it sits (E = rain ÷ threshold), the 26 Aug cloudburst is E≈7, but
27 Apr is only E≈1.4 and **8 May is E≈0.67 — *below* the line**. So on the reanalysis rain, *no* strictness
setting is both quiet and catches both events — pointing the finger at Dial 2, the rain *measurement*.

**So we tested Dial 2 — and got an instructive negative.** We finished the Earth Engine sign-in and pulled
**CHIRPS** (gauge-blended) for the AOI. It turned out **drier** than ERA5-Land here (998 vs 1,350 mm), and
on the event days it recorded *less* rain, not more (27 Apr **0.0 mm**, 8 May **4.2 mm**; event E even
lower, 0.70 / 0.57). So **two independent ~5–9 km products agree there was little grid-scale acute rain on
the documented spring dates** — the gauge hypothesis is *refuted*, not confirmed. The lesson for Dial 2:
swapping one ~5 km product for another doesn't help if the triggering rain is *sub-grid* (a local cell
smaller than the pixel) or if the spring failures simply weren't acute-rainfall-driven (snowmelt-soaked
ground, construction, fuzzy dates). The honest redirection: finer/faster rain (GPM IMERG, 0.1°/30-min) or a
chronic-saturation framing — not another daily gauge product. (Milestone 17.)

**So we tested the sub-daily angle too — and then a date check overturned the answer (the honest part).**
GPM IMERG measures rain every 30 minutes, so it sees short convective bursts a *daily* total averages away.
On the dates our inventory listed (27 Apr dry, 8 May only grazing the line), IMERG showed no cloudburst — so
we *first* concluded rainfall was ruled out. **But sourcing a better inventory revealed the real major event
was the 20 April 2025 cloudburst** (3 deaths, NH-44 destroyed at 5 sites, ~100 mm/1 hr) — a date our
news-derived list had *wrong*. Re-screened, **20 Apr is a clear crossing (E=2.25)** and the regional curve
flags it at Δ=0 — so the deadly spring event **WAS rainfall-triggered, and the model catches it.** What
survives from the "negative" is only the *measurement* lesson: the daily **AOI-mean** products dilute a
localized cell, so you need **sub-daily / point** rain (IMERG) to see it. The refined picture: **primed
slopes + a cloudburst trigger**, model captures both. The deeper lesson: triangulating across datasets is
good, but **a single wrong inventory date can invert your conclusion** — verify the ground truth.
(Milestones 18–20.)

---

## CF6. Grading a hazard map honestly — the null control, ROC & AUC, and the wetness dial

Saying "71 % of real slides are within 2 km of a flagged zone" *sounds* good — but it's almost meaningless
on its own. If you painted the **whole** map red, you'd score 100 %. The question is not "are slides near our
zones?" but **"are slides *closer* to our zones than random ground is?"** Answering it needs three ideas.

**1 — The null control (a fair yardstick).** Scatter a few thousand **random points** inside the study
area. These stand in for "pure luck." Now you have two groups: the **real** slides (positives) and the
**random** points (negatives). For each point, measure the distance to the nearest flagged zone.

**2 — TPR, FPR, and the ROC curve.** Pick a distance threshold (say 500 m) and call a point "detected" if a
zone is within it.
- **TPR** (true-positive rate / *recall*) = fraction of **real** slides detected.
- **FPR** (false-positive rate) = fraction of **random** points detected — your "false-alarm" rate set by
  how much area you flag.
Sweep the threshold from tiny to huge and plot TPR (up) vs FPR (right): that's the **ROC curve**. The
diagonal TPR = FPR is **pure chance** (no skill). Bowing *above* the diagonal = skill; *below* = worse than
guessing.

**3 — AUC (one number).** The **Area Under the ROC Curve** squeezes the whole curve into a single grade:
**0.5 = a coin-toss**, 1.0 = perfect, **below 0.5 = worse than random**. A cousin metric is **lift** =
TPR ÷ FPR at a given distance ("how many times better than luck"); lift = 1 is chance.

**Everyday analogy.** A metal detector that beeps *everywhere* finds every coin (TPR = 1) but is useless
(FPR = 1 too). AUC asks whether it beeps on coins *more than* on bare sand — across all sensitivity settings.

🔗 **In our project: Milestone 23.** Graded this way, the worst-case map scored **AUC 0.41 — below a
coin-toss** (it pinpoints well at 100 m, lift 1.6×, but flags so much ground that the skill drowns by 2 km).
Two honest consequences: (a) the earlier "71 % within 2 km" (CF/M22) was *indicative, not a grade*; (b) it
told us *why* — we'd drawn the map assuming the ground was **fully soaked everywhere** (worst case).

**The wetness dial (and why the rain-line can't fix a map).** Our Factor of Safety is **exactly linear** in
the soil saturation *m* (CF/C4): FS_real = (1−m)·FS_dry + m·FS_sat. So lowering *m* just **raises the failure
bar uniformly** — only the steepest, most-marginal slopes stay flagged. Crucially, the real rainfall record
says the ground only reaches m = 1 on **11 of 214 days** (median ≈ 0.26). Redrawing the map at a *realistic*
wetness (m ≈ 0.25–0.40) lifted the grade to **AUC 0.55 (beats chance)** and close-range lift to **5.6× at
100 m** — at the cost of catching fewer slides overall (the **recall ⇄ precision trade**). The subtle point:
the regional **rain-trigger line decides *when* to raise an alarm (a *temporal* gate) — it cannot move a
*spatial* score.** The map improved purely from the **saturation *level*** we drew it at. Keeping "when"
(rain line) separate from "where/how-much" (wetness level) is what makes the result honest rather than
over-sold.

---

## CF7. The operational alarm — gating *where* by *when* (and making the trigger selective)

A danger **map** (CF6: *where* — the slopes that beat chance) is only half a warning. The other half is a
**calendar** (*when* — is today actually dangerous?). CF7 joins them.

**The problem with the raw rain line.** The regional I–D curve (CF2/CF5) is a **lower bound**: below it,
slides are rare. But "above the line" fires on **112 of 214 days** — half the season. An alarm that rings
every other day is useless.

**The fix — grade by *how far* above the line.** Don't ask "is it above the line?" (yes/no); ask "**how far
above?**" via the exceedance ratio **E(t) = (today's rain) ÷ (threshold rain)**. E = 1 is exactly on the
line; a real cloudburst sits far above (20 Apr 2025: E ≈ 2.9; the 26 Aug monsoon peak: E ≈ 7). So define
three states:
- **DORMANT** (E < 1): below the line — the map is not armed.
- **WATCH** (1 ≤ E < 2): line crossed — the validated footprint is *armed*, keep watch.
- **ALERT** (E ≥ 2): well above — *raise the alarm* on the footprint.

**Everyday analogy.** A smoke detector that beeps at the faintest whiff of toast is ignored; one that stays
quiet until there's *real* smoke gets trusted. E is the "how much smoke" dial.

**Crucial honesty — the footprint stays fixed.** On a wet day we do **not** redraw the map bigger (that is
exactly what over-flagged in CF6). The *where* is always the validated operational map; only the *when*
state changes. The regional line decides timing; the map decides place.

🔗 **In our project: Milestone 24.** The ALERT gate (E ≥ 2) fires on just **27 days (13% of the season)** —
**4× less** than the raw 112 — yet still lights up on exactly the right windows: the **20 April cloudburst
is a Δ=0 ALERT** and the August monsoon peak is covered. All **4** documented disasters fall in an armed
(WATCH+) window; **3 of 4** reach full ALERT. The two that only reach WATCH (27 Apr, 8 May) had rain too
*localized* for our coarse weather grid to register a high E — the same gauge/sub-daily limitation CF5
names, kept on the record. One AOI-average rain value gives one E per day, so the *timing* gate is
area-wide; but the alarm is now differentiated **per slope** by each zone's own breaking point (CF8) —
so on an alarm day you still get a worst-first list of *which* slopes are in play, not just "the area."

**A companion reality check (Milestone 24).** We also ran our cleanest, "atmosphere-physically-removed"
radar velocity (the MintPy ERA5 product, CT3) through the same danger map on one track. It agrees with our
everyday high-pass method on the broad field (correlation ≈ 0.55) but flags only **half** as many creeping
pixels, and they **barely overlap** (of the premium method's creep pixels, only ~18% are also flagged by
the everyday one). The lesson, written into our limitations: *which exact pixels "creep" on a **single**
track is not robust to the processing choice — trust the spots multiple tracks agree on.*

---

## CF8. Critical saturation m* — giving every slope its own breaking point (per-zone gating)

CF7's alarm is *area-wide*: one rainfall number per day flips the whole footprint together. But the slopes
aren't identical — some are perched right at the edge, others have more margin. The honest way to tell them
apart is **not** per-zone rainfall (rain is nearly uniform at the weather grid's ~10 km over our ~22 km
area), but each slope's own **breaking point**.

**The idea (and why it's just algebra).** The Factor of Safety is a **straight line** in soil saturation
m (C4): FS(m) = FS_dry + m·(FS_sat − FS_dry). Failure is FS = 1. Solve that line for m and you get the
**critical saturation**:
$$ m^* = \frac{1 - FS_{dry}}{FS_{sat} - FS_{dry}} $$
— the wetness at which *this specific slope* tips into failure. Low m* = fails when barely damp (most
dangerous); m* near our operating 0.40 = only fails when very wet.

**Everyday analogy.** Every slope is a glass filled to a different level. m* is how much more water each can
take before it overflows. Today's rain raises everyone's water by the same amount — but the glasses already
near the brim spill first. So you watch those.

**How it gates per zone.** Two levels: the regional rain gate (CF7) decides *whether* any alarm fires
today; then the **active slopes** are exactly those whose m* the day's saturation has reached (m* ≤ m
today). The active set is always a subset of the validated footprint — it never adds new ground, so it
can't drift back into the over-flagging of CF6.

🔗 **In our project: Milestone 25.** Across the 95 operational zones, m* ranges 0.00 → 0.40: **44 fail when
barely wet**, 33 on a wet day, 18 only when very wet. The active list **breathes from ~53 on the drier
alarm days to all 95 on the wettest**, always ranked worst-first, and feeds the dashboard's "which slopes,
today" panel. On the 20 April cloudburst, the spring snowmelt had already raised the ground to m ≈ 0.66, so
**all 95 were active** — correctly. This turns "the area is dangerous today" into "**these specific slopes,
in this order**," from physics and data we already had — no new satellite passes.

**Gate vs rank — when NOT to gate (Milestone 30).** This gating *narrows* a list down, which is right for the
short, trusted ALERT map (CF9). But the wide WATCH map (CF9) exists to *not miss anything* — narrowing it
would shrink the very breadth that is its purpose (like casting a wide net then throwing fish back), and would
use the gate outside the validated footprint where its "can't balloon" safety no longer holds. So for a
high-recall list you **rank, don't gate**: keep every zone and sort it worst-first by a triage priority
**(1 − m\*) × P** = fragility (this section) × detection confidence (CF10). A zone tops the list only if it is
*both* fragile *and* convincingly moving — and nothing is dropped, so the safety net is preserved.

---

## CF9. Two warning tiers — precision vs recall (the short ALERT list and the wide WATCH list)

Every detector faces one unavoidable trade. Cast a **narrow** net and almost everything you flag is real
(**high precision**) — but you **miss** the quiet cases (**low recall**). Cast a **wide** net and you catch
nearly everything (**high recall**) — but most of what you flag is noise (**low precision**). You cannot
maximise both at once; you *choose* where to sit on the curve.

**The two measures (from CF6).**
- **Precision** = of the slopes we flagged, how many were really near a slide. *"When we point, are we right?"*
- **Recall (TPR)** = of the real slides, how many we flagged. *"Of the ones that failed, how many did we catch?"*

**Everyday analogy.** A smoke alarm tuned to scream only at a real blaze (precise) may stay silent on a slow
smoulder; one tuned to chirp at burnt toast (high recall) catches every fire but cries wolf. Sensible
buildings use **both** — a quiet detector that means "act now," and a sensitive one that means "go check."

**How we get two tiers from one model.** The only dial we turn is the assumed **wetness** m (CF6/C4).
- **ALERT** = a *moderately* wet day (m = 0.50): the Factor-of-Safety line tips only the slopes already on the
  edge → a **short, precise** list (12 slopes, grade 0.64).
- **WATCH** = a *sustained-soaked* day (m = 0.70): the same line now tips more marginal slopes → a **wide,
  high-recall** list (132 slopes). As a whole it's near coin-toss, but its **two-pass-confirmed** core still
  beats chance — a trustworthy ring inside the wide net.

🔗 **In our project: Milestone 28.** Raising the wetness dial from 0.50 to 0.70 widens the footprint 12 → 132
slopes and lifts recall ~**0.25 → 0.63** (≈2.5× more real slides caught), at the cost of discrimination (grade
0.64 → 0.50). Going to the fully-soaked worst case (m = 1.0, 393 slopes) barely raises recall (0.63 → 0.70)
for triple the noise — so WATCH stops at 0.70. The two tiers compose with CF7's *when*: monitor the wide WATCH
map; act on the precise ALERT core when the rainfall gate escalates.

---

## CF10. Detection confidence — turning the noise floor into a probability (and why "confident" ≠ "right place")

Every measurement has noise. Our velocity has a ~15–25 mm/yr atmospheric **noise floor** (§2), and the creep
test is a hard line at −15 mm/yr. A slope at −18 barely clears the line; one at −45 clears it by miles.
Treating both as equally "creeping" hides that difference — so we put a probability on it.

**The idea (it's just a z-score).** If the true speed is the measured speed ± noise σ, the chance the slope
is *really* past the −15 line is
$$ p = \Phi\!\left(\frac{-15 - v}{\sigma}\right) $$
where Φ is the bell-curve CDF. Far past the line → p near 1; barely past → p near 0.5.

**Two witnesses beat one.** If two independent satellite passes each give p, the chance *both* are fooled by
noise is (1−p)², so the combined confidence is **P = 1 − Π(1 − p)**. Two "0.7" looks → 0.91. This is the
formal version of "trust the slopes that more than one geometry confirms" (CF6 / the ≥2-look core).

**Everyday analogy.** One smoke detector beeping might be a fly; two detectors in different rooms beeping is
almost certainly real. Independent confirmations multiply your certainty.

**The honest catch — confident ≠ correct location.** We checked whether keeping only high-confidence slopes
better matches the *known* landslide map. It doesn't. "Confident the slope is *moving*" and "this is a *known
landslide* spot" are different axes — a slope can be unmistakably creeping yet not on a mapped slide. So the
confidence is for **triage** (ignore likely-noise), riding *alongside* the location-accuracy grade (CF6) and
the rainfall-timing alarm (CF7) — never replacing them.

🔗 **In our project: Milestone 29.** Per-track noise floors 14–24 mm/yr; every alert now carries a detection
confidence (operational median 0.77, monitoring-tier median 0.85), with multi-look corroboration lifting some
to ~1.0. Filtering by it doesn't change the inventory grade (AUC 0.50 → 0.51 → 0.48) — confirming it is a
distinct, complementary trust axis, not a spatial ranker.

## CF11. Error bars, permutation tests, and the dumb-baseline ladder — grading the grade itself

CF6 taught us to grade the map honestly (null control, ROC/AUC). But an AUC from ~40–140 known
landslides is itself a *measurement* — it has noise. Two tools put honesty on the honesty:

**Bootstrap confidence interval — "how much would the score wobble?"** Re-draw the landslide list
from itself, with replacement, 10,000 times; recompute the AUC each time; the middle 95% of those
scores is the interval. Quote **"AUC 0.71 [0.66–0.75]"**, never a naked third decimal. *Analogy:*
instead of weighing yourself once, you weigh yourself 10,000 mornings and report the range — a
one-off 0.707 vs 0.696 difference stops looking meaningful the moment you see the spread.

**Permutation test — "could random luck do this?"** Pool the real landslides with the 5,000 random
control points, shuffle which labels are "real" 10,000 times, and ask how often shuffled labels
score as well as ours. If (almost) never, the map genuinely knows something: **p = 0.0001** — the
smallest value 10,000 shuffles can resolve — at both sites' alert maps.

**The ablation ladder — "would a dumber map do the same?"** A score means little without a rival. So
we score, *by the identical rules*, a ladder of deliberately dumb maps: steepness alone; a textbook
statistical blend of steepness + terrain-wetness; our physics without the satellite; our satellite
without the physics. Each rung even gets to cheat — it tunes its threshold to its own best score.
The claim worth making is **incremental skill**: what the fusion adds *over each rung*.

**What the ladder said.** At Ramban: the fusion beats every rung; satellite-alone is *below* chance
and physics-alone barely above — the value is provably in the combination. At Vaishno Devi: the
fusion beats its own ingredients, but a bare "steeper than 40°" map **ties it** on raw AUC (needing
155 zones and lower precision to match our 21) — so there we claim footprint economy, timing (the
two Δ=0 disaster catches), and per-zone ranking, *not* raw spatial superiority. Reporting the tie
is the credential.

🔗 **In our project: §44 / Milestone 41.** `validation_stats.py`; dashboards now read the interval
and p-value live; the ladder is the permanent bar the next science upgrades must clear.

## CF12. Where the ground gets wet first — TWI-distributed saturation

Until now the "wetness dial" (CF6) turned the *whole* mountain equally wet on a given day: one
saturation number `m` for every slope. But water doesn't wet a hillside uniformly — it runs downhill
and pools where the land converges. We already measure exactly that tendency: the **Topographic
Wetness Index** (TWI, CF/Part C), high in valley hollows, low on dry ridges. So we let each pixel
have its own saturation:

  m_i = clip( m + κ·(TWI_i − TWI_mean), 0, 1 )

The average is still `m` (TWI is measured from its own mean), so the day's *overall* wetness — set by
the rainfall — is unchanged; **κ just redistributes it**, giving convergent hollows a head start and
ridges a lag. One new knob, κ ("how strongly TWI tilts the wetness"), tuned per site against the
landslide record exactly like every other dial. κ=0 is the old uniform behaviour.

**Everyday analogy.** Same rain falls on a car park, but the puddles form in the dips, not on the
crown. Painting the whole lot "equally wet" misses where you'd actually slip.

**Why it helped.** Both mountains, on separate landslide records, independently preferred the *same*
gentle tilt (κ=0.06) — and it concentrated the alert on the wet, failure-prone hollows: the danger
map got sharper and smaller. At Vaishno Devi this was the difference that finally pushed the model
*past* the "dumb steep-slope map" it had merely tied in CF11 — same skill, a tenth the zones.

**The honest caveat.** It sharpens *where*, not *when*: on the wettest days the whole slope is soaked
(`m`≈0.9) and everything lights up regardless of κ; the tilt matters most on moderate days. And the
raw skill gain sits inside the error bars (CF11) — the trustworthy wins are the tighter footprint and
beating the baseline, not a proven jump in the score.

🔗 **In our project: §45 / Milestone 42.** `kappa` config key; TWI-distributed m_i in the engine;
swept via `rainfall_selectivity_backtest.py --kappas`; adopted at 0.06 for both sites.

## CF13. The suction curve we built and didn't use — nonlinearity, identifiability, and saying no

Damp soil is glued together by **matric suction** — the same capillary pull that makes a sandcastle
stand. Our model had treated that glue as fading *linearly* from dry to soaked. Laboratory
**soil-water retention curves** (van Genuchten's equation) say otherwise: the glue holds, holds…
then collapses over a narrow wetness band. We built that curve in:

  ψ(m) = (1/α)·(m^(−1/(1−1/n)) − 1)^(1/n)  → extra cohesion = min(c_dry − c_wet, ψ·m·tanφ′)

Two safeguards made it honest. The **cap** (`min`) means suction can never claim more strength than
the *measured* dry end-member; and ψ(1)=0 means fully-soaked strength is exactly the measured wet
value. So the curve only reshapes the *journey* between two anchored facts — and because only
cohesion changes, the whole thing rides on the existing maps as a correction term (no reprocessing).

**Everyday analogy.** Wet sand is sticky across a wide range of dampness, then suddenly turns to
soup. A straight line between "dry beach" and "soup" misses the cliff-edge. The question is *where*
the cliff sits — that's what α and n encode, and they differ by soil type.

**What the test said — and the concept that matters: identifiability.** We tried four published
(α, n) pairs spanning our soil's plausible textures, each allowed to re-tune the wetness dial to its
own best score. None beat the straight line at both mountains. Why? Scored against a *map* of past
landslides, curve shape and dial setting are nearly interchangeable — moving one mimics the other, so
the data **cannot identify** the curve's parameters. A parameter the data can't pin down is a
liability, not physics. What would pin it down: a lab curve for *our* soil, or the *dates* individual
slopes failed (the curve's real signature is timing, not placement).

**The discipline.** The mechanism ships, verified bit-for-bit at the end-members and guarded by its
own test file — switched off. Adopting it would have added two borrowed parameters for a gain our own
error bars (CF11) call noise. Saying "not yet" to your own upgrade is the same muscle as publishing
the slope-map tie.

🔗 **In our project: §46 / Milestone 43.** `fs_real.py` (all wetness→FS physics in one module — an
audit found two tools still on the old maths, CF12's layer now cannot drift), config `suction:`
block (absent = linear), `tests/test_fs_real.py`.

---

## CF14. Two rain sensors, one danger line — the sub-daily burst gate (IMERG)

CF2 gave us the danger line: rain of intensity *I* sustained for duration *D* has historically
triggered landslides when *I* ≥ a·D^(−b). CF5 taught that *which rain data* you feed that line
matters. This section is the operational conclusion of both: the same curve, fed by a **second,
much faster rain sensor** (Milestone 48).

**The blind spot.** Our daily gate feeds the curve a *daily, area-averaged* rainfall value. But
average a day with one savage hour of rain and 23 dry hours and you get "drizzle" — the
mountain-killer cloudburst literally averages away. We proved this on the deadly 20 Apr 2025
cloudburst (clear crossing on half-hourly data, invisible on the daily mean) and watched it
again on 8 Jul 2026 (Himkoti: daily gate said only WATCH).

**The fix.** NASA's GPM IMERG product estimates rain every **30 minutes** on a ~11 km grid,
arriving ~**1 day** after it falls (the daily reanalysis takes ~6). Each day we slide windows of
every length from half an hour to a day through the half-hourly series and ask: did *any*
window's mean intensity cross the same danger line?

> E_sub(day) = max over D ∈ {0.5…24 h} of  [ (rain in the D-hour window ending that day) / D ] ÷ (a·D^(−b))

The windows deliberately **cross midnight** — a burst at 23:30 belongs to the day it ends in,
not to neither. **Everyday analogy:** the daily gate reads the rain gauge once every evening;
the burst gate is a security camera that never blinks — it catches the smash-and-grab that
happened between readings.

**What this season proved (the best possible answer): the two sensors catch different
killers.** The 8 Jul Himkoti slide — under-called by the daily gate — is a clear **ALERT** on
the burst gate (a 3-hour downpour, measurable *hours before* the evening collapse). The 7 Apr
Digdol highway burial — days of soaking, no single burst — is the mirror image: the burst gate
barely stirs, the daily gate had already raised full ALERT. Long soak → daily arm; sudden burst
→ sub-daily arm; combined, **both of 2026's verified events read ALERT on the day**.

**Why it shipped "experimental".** At short durations the same curve trips far more easily, and
this arm's false-alarm rate was *unmeasured* — it had no back-tested operating points the way
the daily gate has (CF7). So it ships as a labelled **second opinion** beside the validated
alarm, not as the alarm. Also honest: an 11-km pixel still averages over a slope; no snowmelt;
the newest day is provisional while its data arrives. **That false-alarm gap is now closed —
see CF16.**

🔗 **In our project: Milestones 48–49 / §55 & §58.** `imerg_gate.py` (incremental cached
half-hourly fetch + daily E), the "sub-daily burst check" card, and a non-fatal hook in
`live_alarm.py`. The arm was then CALIBRATED on six verified events (§58): burst ALERT at
**E ≥ 3** — later lowered to **E ≥ 2.4** (§64, see CF16) — with a measured caveat that
drives the choice — IMERG read only **0.16–0.22×** the Katra gauge on the two worst 24-h
anchors (an 11-km pixel average vs a point gauge under a cloudburst), so E is biased LOW in
the events that matter and the threshold must never be pushed high. Per-zone rain was probed
and declined: our zones sit inside ~3 IMERG pixels, so zone-level E barely departs from the
AOI mean (≤1.29× on decision days). A display-only "two-arm read" line now sits on the banner;
the validated daily alarm is untouched.

---

## CF15. When the clever model is just reading the road — reporting bias in inventories

CF6 taught us to grade maps against a landslide inventory. This section is the trap hidden in
that idea (Milestone 50): **an inventory records where landslides were *noticed*, not where
they *happened***. Ours hugs the NH-44 highway — because that is where the GSI surveys, where
traffic stops, where reporters stand.

We built a statistical susceptibility model (logistic regression on terrain: elevation, slope,
wetness, curvature) and scored it against the physics map on the same 112 verified points. The
statistical model "won" — until we read its weights: nearly all of its skill was one feature,
**low elevation**, which in this valley simply means *near the highway*. Removing that single
feature erased its entire advantage. **Everyday analogy:** train a model to find lost keys
from past discoveries and it will learn "keys are found under streetlights" — because that is
where people look, not where keys fall.

> A model trained on a biased inventory learns the bias, fluently, and calls it skill.

The physics map cannot learn where people look — it only knows slopes, water and strength.
That *independence* is precisely its value, and why the ensemble of the two gained nothing:
the statistical half brought mostly bias to the table. The general rule: before celebrating
any data-driven hazard model, ask *what its features are proxies for* — and test by deleting
the suspicious one.

🔗 **In our project: Milestone 50 / §60.** `susceptibility_crosscheck.py` — LR CV AUC 0.731 →
0.560 without elevation, vs physics 0.575 on the same raw-pixel protocol (deliberately not
comparable to the §16/§44 zone-buffer scores). The corridor bias itself is an old friend:
CV3/CV4 already carried it as the inventory's documented caveat; this experiment measured it.

---

## CF16. How often does an alarm cry wolf? — episodes, bounds, and judging in one currency

CF7 made the daily gate *selective*; CF14 added a faster second arm but shipped it with a hole:
nobody had measured how often it fires when nothing happens. This section is how you measure
that honestly when your ground truth is radically incomplete (Milestone 51).

**Trap 1 — counting days flatters the wrong alarm.** Mountain rain arrives in *spells*. An arm
that flags 11 days might have interrupted you 11 times or 3 times. The operational unit is not
the day but the **episode**: a run of consecutive flagged days (merging spells separated by a
single quiet day) — *one episode = one time the system asks a human to decide*.

> unexplained-episode rate = (episodes with no verified event in or near them) ÷ (days of record) × 100

**Everyday analogy:** a smoke detector that chirps once a month for a week is not "30 alarms" —
it's one alarm you learn to ignore. Counting chirps hides that; counting episodes reveals it.

**Trap 2 — "unexplained" is not "false".** Our inventory records only failures serious enough
to be reported. A flag with no matching record may be perfectly correct rain over a slope
nobody watched. There is no fix, only honesty: report a **bound**. Attribute episodes to events
with a *strict* window (±1 d) and a *generous* one (±10 d); the strict count is the **upper
bound** on false alarms, the generous count the **lower bound**, and the truth sits between.

**Trap 3 — windows must respect the edge of the record.** A ±10-day window applied near the end
of a series can "catch" an event the arm never had data for (our daily arm's season stops ~5
days back, waiting on ERA5-Land). That is *pending*, not a catch and not a miss — see the error
log. Clip the metric to the record's span or it invents skill exactly where the data runs out.

**Trap 4 — never score a new instrument in absolute terms.** The bias above afflicts *both*
arms identically. So the only defensible claim is a **comparison**: run the identical
measurement on the arm you already trust, and report the new one relative to it.

**The shape of the answer we got.** The two arms turned out to have opposite temperaments —
**acute vs chronic**. The burst arm raises many short episodes; the daily arm raises few, but
one of them runs unbroken for 92 days (42.6% of a season at WATCH — alarm fatigue by another
name). The burst arm therefore interrupts more often while costing **less than half the total
alarm days**. "Watch these two days" is cheaper to live with than "watch this quarter". A
single ratio would have hidden all of that, which is why the ledger reports days, episodes,
mean/longest episode length, and the bound side by side.

**The bonus finding — a new event can move a fixed point.** Adding the 7th verified event (the
fatal 22 Jul 2026 boulder strike) dropped the *same-day fatal floor* from E=3.07 to **2.44**:
the then-shipped ALERT threshold of 3 no longer reached every fatal event on the day it happens
(it had alerted 4 days earlier and never gone quiet). The disciplined response is not to quietly
re-tune the live gate but to **price the change** first — and then let whoever owns the
consequences decide. That decision was taken (§64): **k lowered 3.0 → 2.4**.

**How to justify a threshold move without overfitting it (the §64 argument).** The tempting
justification — "set it just below the event we missed" — is fitting the rule to the newest
failure, and it ratchets with no floor: the next fatal event reads 1.8 and the same logic demands
1.8. The defensible version asks a different question. Sort the event exceedances (0.99, 1.09,
**2.44**, 3.07, 3.90, 4.19, 9.21). *Any* k in the open band **(1.09, 2.44]** catches the identical
set of events — recall is a **step function**, flat across the whole band. So the only real
choice is *within* the band, where the criterion is selectivity: higher k, fewer false alarms.
2.4 is the top of the band, hence the **cheapest threshold that achieves the recall step** (63
alarm days vs 81 at k=2.0). Two supports: it moves in the direction the gauge-bias measurement
already pointed (IMERG under-reads extremes ~4.5–6×, so E is biased low where it matters), and
the arm still flags fewer days than the validated daily arm.

> **Rule of thumb:** before defending a threshold, plot recall against it. If recall is flat over
> a range, your evidence does not pick a point in that range — only a *cost* criterion can. If
> recall is *not* flat and you land exactly beside your newest data point, you are overfitting.

**The fragility that comes with it.** k=2.4 sits **1.6%** below the fatal floor of 2.44. A data
re-fetch or product reprocessing that nudges that E down silently un-catches the very event that
justified the move. The fix is not a comment but a **tripwire**: a test asserting
`min(fatal burst_E) ≥ BURST_ALERT_K` that fails loudly and says *re-derive k, do not edit this
test*. Any operating point chosen with a thin margin needs one.

**A trap found while regenerating (worth its own line).** Re-running a *past* season's alarm
report is not reproduction — the tool took the season from its arguments but the hazard footprint
and event inventory from **today's** disk, so it recomputed 2025 against the present and
overwrote published historical numbers, while reporting complete success. Only a byte-comparison
against a pre-change backup caught it. **"Idempotent" means same inputs → same outputs, and it
fails silently the moment one of the inputs is "the current state of the repo."**

🔗 **In our project: Milestone 51 / §63.** `imerg_calibration.py` gained the episode
measurement (`episodes`, `false_alarm_profile`), run over four AOI-seasons for both arms, and
now *generates* the temporal-skill table it used to have typed by hand (which is how the 22 Jul
event went missing from it). `imerg_gate.py`'s `BURST_ALERT_K` is deliberately **unchanged**
pending the user's call.

---

# Part C-quinquies — A Second Mountain: Transfer, Route Risk & a Real Disaster (Milestones 31–36)

## CV1. What travels with the tool — and what must be earned again

When you point a working system at a **new place** (the Vaishno Devi pilgrimage route, ~40 km from Ramban),
you discover which parts of it were *science* and which were *local knowledge in disguise*.

**What travels free:** the physics (radar, phase, FS — Parts A–C), the pipeline (order → audit → invert →
hazard → alert), and the *methods* of honesty (null controls, tiers, gates). **What must be earned again at
each site:** the **soil numbers** (φ and cohesion were measured on Ramban-area slopes; the new mountain is
limestone/dolomite + loose scree — different material, borrowed values), the **elevation tile** (the sharp
12.5 m DEM is a per-site download), the **operating points** (m = 0.50/0.70 were *tuned* on Ramban's
inventory), and above all the **validation** — a score earned on one mountain is not a credential for
another.

**Everyday analogy.** A good recipe travels; your oven's quirks don't. A chef moving kitchens keeps the
recipe but re-learns the oven — and doesn't hang the old kitchen's Michelin star on the new wall.

**Two engineering lessons worth telling.**
- *A second site is a free integration test.* Pointing the pipeline at Katra immediately exposed three
  hidden "only-works-for-Ramban" assumptions (a quality bar a short radar series can never reach; a DEM
  tile that covers only Ramban; a function whose caller was never updated). Each was invisible while only
  one site existed — and each fix made the tool genuinely site-agnostic.
- *Two sites must not share drawers.* The same satellite frames cover both mountains, so outputs would have
  silently overwritten each other. Every per-site file now lives in its own named folder/filename (the
  "slug"), and — the honesty guard — a site's dashboard **cannot display another site's accuracy scores**:
  if it hasn't been tested locally, it says so, in plain words.

**A lucky physics bonus:** because radar frames are ~250 km long, the archive we'd already bought for
Ramban also photographs the new mountain — history for free.

🔗 **In our project: Milestones 31, 32, 34, 35.** Phase 1→4 replicated in days, not months; three latent
assumptions fixed; per-site folders + "not yet back-tested at this site" cards; the site's own 12.5 m DEM
sharpened slopes (median 18°→22°) and grew the two-track-confirmed core by ~38 %.

---

## CV2. Route exposure — turning a hazard map into "which part of the path?"

A hazard map answers "*where is the ground suspect?*" A pilgrim, engineer or administrator asks a sharper
question: "*which stretch of MY path is near that ground?*" The bridge between the two is embarrassingly
simple mathematics: **distance**.

**The gentle method.** Walk along the route in small steps (we use 40 m). At each step, measure the
straight-line distance to the nearest flagged pixel or alert zone. (Computers do this instantly with a
*distance transform*: for every cell in a grid, precompute how far it is to the nearest "on" cell.) Then
classify each step by the *strongest* thing it is near, and merge consecutive steps of the same class into
**segments** — a ranked to-do list instead of a coloured cloud.

**The honest yardstick matters more than the method.** How near is "near"? We didn't invent a number — we
reused the one the *scoring* earned (CF6): our maps demonstrably discriminate at **≤250 m**, so that is the
exposure buffer; within one pixel (80 m) counts as a direct hit. Claiming more precision than your
validation supports is how honest tools become dishonest slides.

**Everyday analogy.** A weather map shows storms; a pilot's briefing says "your route clips the storm cell
for 30 miles after waypoint X." Same data — different, more actionable question.

🔗 **In our project: Milestone 33 (+ the §31 addendum).** The route (real OpenStreetMap geometry: the old
track, both modern variants, the ropeway) against the union map: **one 800 m stretch above the Bhairon top
passes directly through two-track-confirmed creeping ground** (the "go look here first" finding); the
modern route variants ride through the wide monitoring net; the town and trek start are clear. And the
sobering read the overlay forced us to print: the 26 Aug 2025 disaster site itself sits **598 m** from our
nearest zone — *beats-chance at 2 km* is not *pinpoints-the-site at 250 m* (see CV4).

---

## CV3. Failure classes — the slow creep radar sees, and the fast rockfall it doesn't

Not all landslides are the same physical animal, and no single instrument sees them all.

**What SBAS InSAR is built for:** **slow, persistent creep** — a hillside moving millimetres-to-centimetres
per year, coherently, over many 12-day revisits. That is exactly the precursor motion of large, deep-seated
slides.

**What the pilgrim track mostly suffers:** **fast, brittle, small failures** — rockfall off a cut slope, a
debris chute in loose scree, a boulder shaken free by a cloudburst. These give *no slow warning creep* at
80 m scale; between two satellite passes the ground goes from "fine" to "fallen" (and the radar often just
sees the pixel *decorrelate* — turn to static — rather than move).

**Why this matters for reading our maps.** At the new site, our most *measurement-certain* product — the
two-track-confirmed creep core — scored **zero** against the GSI list of track-side danger spots, while the
broader physics-weighted map beat chance. That is not a contradiction: the core detects a **different
failure class** (deep massif creep, up-slope, away from the path) than the cut-slope rockfall the GSI
surveyors catalogued at track level. Two questions, two answers: *"which slopes are measurably creeping?"*
(core) and *"which cut-slopes menace the path?"* (physics map + GSI's own survey).

**Everyday analogy.** A cardiologist's ECG is superb at slow heart-rhythm disease and useless for a broken
arm. Scoring the ECG on an X-ray's caseload gives zero — that indicts the *pairing*, not the instrument.

**The honest to-do this opens:** catching fast failures wants different signals — *coherence-drop* change
detection (the radar pixel suddenly turning to static IS the event), optical before/after imagery, or a
cut-slope geometry layer in the reasoner. Recorded as the main gap to close.

🔗 **In our project: Milestone 36 (revision).** Trust guidance rewritten: for *track* hazard, lead with the
validated physics map (AUC 0.62); the creep core (incl. CV2's 800 m segment) remains the best-corroborated
*creep* — it is answering a different question than the corridor inventory asks.

---

## CV4. Validating on one real disaster — what a single event can and cannot prove

On 26 August 2025 a landslide at Ardhkuwari on the pilgrim route killed 32 people. The official GSI report
gave us what no amount of processing can synthesise: a **verified date, place, and 40 surveyed danger
points**. How much can one event validate?

**The when-test, done honestly.** Feed the model only 2025's weather and ask what it would have said.
Result: the disaster day was the season's **maximum rain day (191 mm)**, the model's exceedance E peaked
**that exact day**, and the gate stood at full ALERT (Δ = 0). But here is the discipline: that monsoon was
so relentless the gate was at ALERT on **59 days** — so "we were alarmed that day" is *necessary* evidence
(silence would have falsified us) yet weak *sufficient* evidence. The strong fact is the **peak**: of ~200
days, the model's single loudest day was the day that killed. One event can *corroborate*; only many events
can *calibrate*.

**The where-test, both truths.** Against GSI's 40 points + the disaster (with a 5,000-point luck control):
the standing map scores **AUC 0.62, recall 0.81 within 2 km, 1.67× better than luck** — genuinely beats
chance at its very first exam, with borrowed soil numbers and seven weeks of radar. AND: at the honest
250 m yardstick the disaster site itself is **598 m outside** our nearest zone. Both sentences are true.
The first says the method has real skill; the second names the calibration target and the failure-class
gap (CV3). A tool that can say both is worth trusting; one that only says the first is marketing.

**One more bias to confess:** the GSI points hug the track (that's where surveyors walk), and most are
*assessed-vulnerable* spots rather than occurred slides — so the ground truth itself is corridor-biased,
exactly like Ramban's highway inventory. The score is real, but it grades "near the corridor's danger," not
"everywhere on the mountain."

**Everyday analogy.** A weather service that named the season's one deadly storm-day as its top-ranked risk
day has shown real skill — but if its flood map drew the water 600 m from the street that drowned, you'd
praise the forecast, fix the map, and never conflate the two.

🔗 **In our project: Milestone 36.** First site validated against a real disaster; dashboards now wear the
site's **own earned** scores (AUC 0.62 / recall 0.85); GSI's note also records that the exact failed slopes
had been flagged by GSI years earlier — the institutional gap our tool exists to help close.

---

## CV5. Instruments for the fast failures — the coherence tripwire and the energy line

CV3 named the gap: brittle failures give no creep to measure. This section is the first pair of
instruments pointed at that gap (Milestone 38).

**Coherence as a tripwire.** Every interferogram comes with a *coherence* map — per pixel, "how similar
did this patch of ground look on the two dates?" (0 = pure static, 1 = identical). We normally use it
only as a quality filter. But read over time it is a *change detector*: bare rock holds high coherence
pass after pass, and a slope that has just collapsed turns to static — **the pixel decorrelating IS the
event**. The catch: rain-wet ground and flushing vegetation also lower coherence, across the *whole
scene*. So the watch flags only a **localized** drop:

> flag if (polygon's drop vs its own history ≥ 0.12) **and** (its drop *relative to the AOI mean* ≥ 0.12)

Two satellite tracks give an independent second witness — a drop on both is much harder for noise to
fake. **Everyday analogy:** a shopkeeper's window rattles in every storm (scene-wide) — you only run
outside when *your* window rattles on a calm day, or louder than the whole street's.

**The energy line (Fahrböschung / shadow angle).** For "if it falls, what does it hit?" there is a
century-old empirical rule (Heim 1932; Evans & Hungr 1993): a falling rock almost always comes to rest
before the line drawn from its detachment point at a characteristic angle to the horizontal —

> reachable if  (height drop / horizontal distance) ≥ tan(reach angle)

Most fragmental rockfall stops inside the **32°** line; median events reach ~27.5°; the empirical
extreme is ~**22°**. Sweep that line from every cell of the source polygon over a fine DEM and you get
three nested "runout cones" — no physics simulation, just a well-tested envelope. **Everyday analogy:**
you don't need ballistics to know where dropped marbles end up on a staircase — the bottom landing, and
generations of janitors can tell you how far they roll.

**What these tools do and don't claim.** The tripwire detects *after or during* failure (early only if
the face fails piecewise); it never predicts. The cone says *could reach*, not *will* — it ignores
bounce, barriers and intervening ridges. Their value is honest coverage: watch + consequence for the
failure class the creep map is blind to.

🔗 **In our project: Milestone 38 / §34.** `coherence_watch.py` (first run over the Bhavan overhang:
quiet — and it correctly ignored a rainy fortnight that dimmed the whole scene) and
`rockfall_runout.py` (the shrine complex sits inside the 32° likely-reach cone; ~2.3 km of track in the
likely band). The records cross-check found the slope system already under managed treatment
(2016 Bhawan failure, SMVDSB/THDCIL programme since 2012) — corroboration, and a reminder to ask for
the as-builts before instrumenting.

---

# Part D — Interview Prep: Likely Questions & Confident Answers

Short, honest answers you can give without hand-waving.

**Q: How can a satellite hundreds of km up measure millimetres?**
A: It doesn't measure distance directly — it measures the *phase* (timing) of its
radar wave, which shifts by a measurable fraction of a cycle when the ground moves
a fraction of the 5.6 cm wavelength. Phase precision buys millimetre sensitivity.

**Q: Why radar instead of ordinary satellite photos?**
A: Radar makes its own signal, so it works at night and *sees through clouds* —
essential in the cloudy, monsoon-heavy Himalayas where optical images would be
blank for months.

**Q: What's an interferogram?**
A: The phase difference between two radar passes of the same place — a map of how
the ground moved between two dates.

**Q: What's your biggest source of error, and how do you handle it?**
A: The atmosphere — water vapour delays the radar and mimics ground motion. We
handle it three ways: discard low-coherence (noisy) pixels, flag images whose
"motion" correlates with terrain height, and high-pass filter out broad smooth
patterns (atmosphere is broad; landslides are local).

**Q: Why throw away so much data (coherence masking)?**
A: A pixel covered in moving vegetation gives random phase — noise that would look
like a huge fake landslide. We'd rather have fewer, trustworthy pixels than many
lying ones.

**Q: How do you know your code actually computes the physics you claim?**
A: We audited it like an outside reviewer (2026-07-17): re-wrote the Factor-of-Safety
formula independently from the textbook and compared it against our published hazard
rasters at *every pixel* — agreement to the smallest float difference — and re-derived
the rainfall thresholds from raw daily sums, reproducing the product's warning days
exactly. That audit is now a permanent 12-test suite that re-runs the comparison, so
the claim "the maps implement the stated equations" is continuously machine-checked,
not taken on faith (RESULTS_AND_KPIS.md §49).

**Q: What does "LOS velocity" mean — is that up/down motion?**
A: It's motion along the radar's *slanted* line of sight, a mix of vertical and
horizontal. Separating pure vertical needs combining ascending and descending
passes — a later step.

**Q: What is SBAS / why a "network" of pairs?**
A: Small BAseline Subset. We don't just compare first-to-last; we build a
connected web of short-time-gap pairs and solve them together with least squares.
Redundancy averages down noise and the short gaps keep coherence high.

**Q: You mentioned the data must be "connected" — why?**
A: To build one continuous timeline, every date must chain to the others through
the pairs. If quarantining bad images breaks the chain into islands, the math
can't relate one island's motion to another's — like a relay race with a dropped
baton.

**Q: How accurate is the final number?**
A: Our current background noise floor on the test stack is roughly ±30 mm/year —
good for catching dramatic movers, and we have a clear path (fuller atmospheric
correction, combining more satellite tracks) to tighten it for subtler signals.

**Q: Is this predicting landslides?**
A: Not yet — Phases 1–2 measure *movement* and Phase 3 turns it into a rough
*hazard map*. A validated *forecast* (with rainfall, Phase 4) is the goal, not
yet the reality. Movement + slope physics is an ingredient of prediction, not the
prediction itself.

**Q: So is the finished product an early-warning system?**
A: No, and I claim less on purpose. It's a **decision-support prioritization
prototype**: it ranks WHERE slopes deserve inspection (scored above chance
against verified landslide inventories at two sites) and WHEN regional rainfall
warrants heightened vigilance (both in-window fatal events caught on the day).
It does not predict individual landslides, and no evacuation or closure decision
should rest on it — that authority and that burden of proof belong to agencies
like GSI and the district administration. The smaller claim is the one every
number in the repo actually supports, and it's the difference between a
defensible research product and an overclaimed one.

**Q: How do you decide a slope is dangerous?**
A: Two independent checks must agree. First, physics: the Infinite-Slope Factor
of Safety, from the slope's steepness and soil strength, must say it's unstable
(FS < 1). Second, observation: our InSAR must show it's actually creeping. A spot
that's both theoretically unstable *and* measurably moving is the highest concern.

**Q: Why does almost the whole map go unstable in the monsoon scenario?**
A: When soil saturates, water buoyancy cuts the friction holding it, so the
Factor of Safety drops below 1 across most steep slopes. That's physically the
point — monsoon water is the trigger. But the *absolute* fraction depends on our
assumed soil strength and a coarse terrain model, so we read it qualitatively
(monsoon = widespread elevated risk) and trust the *combined* hazard pixels
(physics AND measured motion) far more than FS alone.

**Q: Have you validated this against real landslides?**
A: We ran the first back-test against documented Ramban failures. Spatially it's promising — 8 of 9
known NH-44 black-spots (Panthyal, Khooni Nallah, Digdol…) fall within ~2 km of a flagged zone. But
the back-test caught a real problem: our rainfall trigger picked late August, while the documented
2025 failures were April–May. It exposed that our window starts too late (1 May) and that the
reanalysis rainfall we used under-counts mountain cloudbursts — so the fix is an April start + a
gauge product. A validation that finds its own gaps is doing its job; the rigorous *scored* test
awaits the official GSI Bhukosh inventory (~302 mapped Ramban slides).

**Q: You found your trigger missed the real spring landslides — did you fix it?**
A: Partly, and the *way* it failed is the interesting part. Two suspects: the *threshold
line* and the *rain measurement*. Fixing the line — swapping the conservative **global**
Caine curve (≈100 mm/day) for the **published NW-Himalaya** one (≈19 mm/day; a separate
NH-44 study confirms ~14 mm/day triggers slides here) — flipped the spring back-test 0/2 →
2/2 on the same rainfall. But that line fires on 112 of 214 days (sensitive, not selective),
so "2/2" is partly automatic. Then I tested the measurement: I pulled the **gauge product
CHIRPS** — and it came back *drier* than our reanalysis on the exact event days (0 mm on
27 Apr, 4 mm on 8 May). So **two independent ~5 km products agree there was barely any
heavy rain at grid scale when those slopes failed** — which means the spring events probably
weren't a "missed rainstorm" at all, but a sub-grid local cell, snowmelt-soaked ground, or
construction. I'd rather report that clean negative than pretend a gauge swap fixed it; it
redirects me to finer/faster rain (30-min IMERG) or a saturation model.

**Q: Aren't your soil strength numbers just guesses?**
A: Less so now. The friction angle is **36°** — the value **GSI actually measured**
on these slopes (their NH-244 Ramban/Doda field study reported 36.4–39.1°), so the
biggest soil parameter is grounded in real data, not a textbook. Cohesion is still a
conservative (wet-reduced) assumption pending lab values, so FS stays a *relative*
screening tool — and we still lean on the measured-motion half of the hazard rule.

**Q: You call it "agentic" — is there a real AI deciding things?**
A: Not yet. The "agents" are three deterministic, rule-based modules (sensors +
weather + a combiner) chained together. We chose that on purpose for the MVP:
it's reproducible, offline, and auditable. Swapping in a real reasoning AI is a
planned upgrade, but the *decision logic* is what matters and that's already here.

**Q: How does the system actually raise an alert?**
A: One rule: a spot must be **both** theoretically unstable (Factor of Safety < 1
under the rainfall scenario) **and** measurably creeping (InSAR velocity beyond
−15 mm/yr). We then group neighbouring flagged pixels into zones, drop isolated
specks as noise, and write each zone a plain-English reason. It's like a smoke
alarm needing both smoke and heat.

**Q: Does the rainfall part use real weather?**
A: In this demo it's *what-if* scenarios — dry, monsoon, extreme — that set how
saturated the slopes are. That already shows the system reacting (dry → few
alerts, monsoon → many). Wiring in live rainfall forecasts is the next step.

**Q: What do you do when a data source doesn't meet your quality bar?**
A: Discard it — explicitly and on the record. Both our descending satellite tracks failed:
one had no coherent reference pixel anywhere (~1% usable), the other produced
physically-impossible velocities (2–5× noisier than the ascending tracks) that a textbook
period-split only worsened. We dumped both rather than dilute a good result, and documented
exactly why. Knowing when to throw data away is part of the method, not an exception to it.

**Q: How do you know *when* rain is dangerous, not just that it's the monsoon?**
A: Intensity–duration thresholds — the field standard. It's not the total that matters but the
rate: a known curve (we use Caine 1980) says how much rain over how short a time has historically
triggered failures. We screened the real 2025 rainfall for Ramban and it flagged one specific day,
**26 August (~134 mm)**, as the season's trigger — far more actionable than "the monsoon is wet."
Caveat: our modelled rainfall under-counts mountain cloudbursts, so a gauge product would likely
flag *more* trigger days.

**Q: Can your system predict *when* a slope will fail, not just where?**
A: The machinery is in place — the inverse-velocity (Fukuzono) method: as a slope accelerates,
1/velocity falls linearly to zero at the failure time, using the time series we already produce
(CF1). Honestly, none of our zones are accelerating right now — they're creeping *steadily* over a
short, noisy window — so it correctly returns "no imminent failure," not a fabricated date. It will
project dates as the record lengthens or a real acceleration begins. And we gate it hard: inverse
velocity will otherwise fit "failures" to noise — we caught exactly that in our own first run and
fixed it (Part E).

**Q: You only have one look direction — how do you get *downhill* motion, and where are you blind?**
A: We project the line-of-sight speed onto the steepest-descent direction from the DEM (V_slope = V_LOS
÷ d·l, CF4). The dot product d·l is the sensitivity: it tells us that **24–42 %** of our measured ground
has its downhill direction nearly perpendicular to the radar, so it's a single-look **blind spot** — we
map exactly where. For the rest, projecting recovers the part the radar missed (×1.4–1.6). It's honest
about the one-track limit and is the cheap stand-in for the full ascending+descending decomposition.

**Q: You added snowmelt to fix the spring miss — did it work?**
A: It became the project's best lesson in scientific honesty. Snowmelt (~59 mm) was too small to trigger,
which pointed at the rainfall *record*, so I tested a regional trigger curve, then gauge rain (**CHIRPS**),
then half-hourly **GPM IMERG**. On the dates my inventory listed (27 Apr / 8 May) all three showed little
rain, so I *first* concluded rainfall was ruled out and the slopes were merely "primed." **Then, sourcing a
better landslide inventory, I found my dates were wrong** — the real deadly event was the **20 April 2025
cloudburst** (3 deaths, NH-44 destroyed, ~100 mm/1 hr). Re-checked, **20 Apr is a clear rainfall trigger**
(IMERG E=2.25; the regional curve flags it at Δ=0) — so the major spring failure **was** rainfall-driven and
the model catches it. The refined, honest answer: **primed slopes + a cloudburst trigger**, model captures
both; the smaller 8 May event stays marginal; and the daily *AOI-mean* products under-read the localized
cell (so you need sub-daily/point rain). The meta-lesson I'd lead with in an interview: I let the evidence
**reverse my own published conclusion** — and a single wrong inventory date was what had flipped it, which is
exactly why verified ground truth (GSI Bhukosh) is the next step.

**Q: Your map sits near 71 % of real slides — how good is that, really?**
A: On its own, almost meaningless — if I flagged the whole map I'd "catch" 100 %. So I graded it **fairly**:
I scattered 5,000 random points as a luck control and asked whether real slides are *closer* to flagged
zones than random ground is, across all distances — that's a ROC curve, summarised by **AUC** (0.5 = a
coin-toss). The worst-case map scored **0.41 — below chance**: it pinpoints well at 100 m (1.6× better than
luck) but flags so much ground that the skill drowns by 2 km. That diagnosis led to the fix: I'd drawn the
map assuming the soil was **fully soaked everywhere**, but the rainfall record only reaches that on 11 of
214 days. Redrawn at a **realistic wetness**, the grade rose to **0.55 — beats chance — and 5.6× better than
luck at 100 m**, trading some recall for precision. The honesty point I'd stress: the rain-trigger *line*
decides *when* to alarm and can't move a *spatial* score — the map improved purely from the wetness *level*.

**Q: You moved the tool to a second site — what actually transferred?**
A: The physics, the pipeline, and the honesty methods transferred; the *numbers* didn't. Soil strength,
the fine DEM tile, the operating points and — crucially — the validation score all have to be earned per
site. We enforce that in software: a new site's dashboard literally cannot display another site's accuracy
scores; until it's back-tested locally it says "not yet back-tested at this site." Bonus lesson: the second
site was a free integration test — it exposed three hidden single-site assumptions in one afternoon.

**Q: You validated the new site on one disaster — is one event enough?**
A: Enough to *corroborate*, not to *calibrate*. The strong fact isn't "we were at ALERT that day" — that
monsoon had 59 ALERT days — it's that the model's **peak** danger day of ~200 was exactly the day that
killed 32 people, and spatially the map beat a 5,000-point luck control (AUC 0.62) at its first exam.
I'd also volunteer the counter-fact unprompted: the disaster site sits 598 m from our nearest zone, outside
our honest 250 m yardstick. Real skill at 2 km, not yet pinpoint precision — both statements are true.

**Q: Your most-confirmed pixels scored ZERO against the official danger list — doesn't that sink the method?**
A: It's a failure-class mismatch, not a method failure. SBAS radar measures *slow creep* — precursor motion
of deep slides; the track-side list is *fast cut-slope rockfall*, which gives no slow warning at 80 m scale.
Scoring a creep detector on a rockfall caseload is scoring an ECG on broken arms. The right response — which
we took — is to re-scope the claim (the physics map, which does score, leads for track hazard) and add
rockfall-appropriate signals (coherence-drop change detection, optical) to the roadmap.

**Q: You admitted radar can't see fast rockfall — so what do you actually do about a cliff you're worried about?**
A: Three things, none of them creep measurement. First, a **coherence tripwire** (CV5): the radar's own
per-pixel similarity score turns to static when a face fails, so we watch each drawn polygon's coherence
against its own history — and against the AOI mean, so a rainy fortnight that dims the whole scene doesn't
false-alarm. Second, an **energy-line runout screen**: a century-old empirical angle rule that converts
"unstable face" into "the shrine complex below is within likely reach" — the number an authority acts on.
Third, the **paper trail**: the records showed this face system already had a treated 2016 failure and a
decade-old mitigation programme — so step zero is asking for the as-builts, not installing instruments.
I'd stress the honesty: the tripwire detects, it does not predict; the cone says *could reach*, not *will*.

**Q: What would you do differently with more resources?**
A: Three things, in order: a denser landslide inventory with verified dates (validation is the bottleneck,
not processing); sub-daily point rainfall so the alarm varies per zone instead of per region (an extreme
season saturates an AOI-wide gate); and lab-confirmed soil parameters — the second site's values are now
corroborated by published site studies (§37), but nothing has been measured on-site for this project.

**Q: Your soil parameters come from literature, not measurement — how do you know they don't drive the result?**
A: Because we measured exactly that (§42) — and re-measured it after upgrading the wetness physics
(§47), where the verdict held and sharpened. We swept every soil parameter across its
literature-plausible range and re-scored the operational alert map at each setting: the footprint
swung from ~120 zones to zero, and in-range values of soil depth alone can erase the product. So the
honest answer is: they DO drive the result — which is why the per-site soil pass is a required,
documented step with provenance recorded in each site's config, why we ran this sensitivity sweep
at all, and why a field-measured soil depth is our top-priority ground-truth item. The wrong answer
would have been to hide the sensitivity; instead it's a chart in the repo. And no, re-tuning the
saturation dial can't substitute — soil strength and wetness are degenerate spatially, but the
rainfall-to-wetness physics that times the warning only stays meaningful if the soils are right.

**Q: Your AUC is 0.71 on 46 landslides — how do I know that isn't luck, or something a slope map gets for free?**
A: Because we tested both, formally (§44/CF11). Luck: a permutation test — shuffle which points are
"real landslides" 10,000 times — says chance matches our score about one time in ten thousand
(p=0.0001, both sites). And every number now carries a bootstrap interval, so I'd say "0.71,
plausibly 0.66–0.75", never the bare third decimal. The slope-map question is sharper, and the
answer differs by site — which is exactly what makes it credible. At Ramban the fusion beats
every dumb baseline we could build, *including* letting each one tune itself to its best score;
satellite-alone and physics-alone are each ≈chance there, so the skill is provably in the
combination. At Vaishno Devi a bare "steeper than 40°" map *tied* our raw AUC in the first pass —
and I'd volunteer that unprompted. What I'd add now is what we did about it: the TWI-saturation
upgrade (next question) lifted VD to 0.757, a point-estimate lead over that slope map, with a tenth
the zones — while the other earned advantages (7× fewer zones at higher precision, the two fatal
events caught at Δ=0 that no static map times, per-zone fragility ranking) stand regardless.

**Q: You said one upgrade broke that tie — what was it, and are you sure it isn't just curve-fitting?**
A: We stopped pretending the whole mountain gets equally wet. Water pools in hollows and drains off
ridges, and we already measure that tendency (the wetness index, TWI). So each pixel's saturation
became m + κ·(TWI − mean) instead of a flat m — one new knob κ, tuned against the landslide record
like every other dial (§45/CF12). Two things guard against curve-fitting. First, κ *redistributes*
wetness but keeps the day's average fixed at the rainfall value, so it can't quietly crank the whole
map wetter — it's a physically-constrained tilt, not a free parameter. Second, and this is the real
check: **both mountains, on completely separate landslide records, independently picked the same
κ=0.06.** A curve-fit to one inventory wouldn't transfer; a real physical effect does. It sharpened
the danger map at both sites and pushed VD past the slope-only baseline. I stay honest that the raw
score gain is inside the error bars — the solid wins are the tighter footprint and clearing the
baseline, not a proven jump in the number.

**Q: You spent a session building nonlinear suction physics and then didn't use it — wasn't that wasted?**
A: It's the most informative negative result in the project (§46/CF13). The build cost was small —
the curve rides on the existing maps as a cohesion correction, anchored bit-exactly to the measured
dry and wet strengths — and the test was maximally generous: four published parameter pairs, each
allowed to re-tune the wetness dial to its own best score, on two mountains. None beat the simple
linear model at both. The finding is *why*: against a spatial landslide map, curve shape and dial
setting trade off almost perfectly — the parameters aren't identifiable from our data. That told us
something we didn't know: the next unit of validation value is a lab retention curve or dated
per-zone failures, not more model complexity. And the mechanism isn't waste — it's one config line
away the day that data exists. A pipeline that only ever adopts its own upgrades isn't testing them.

**Q: Could this scale to ten sites? What's automated and what isn't?**
A: The plumbing scales; the science must be earned per site — and we've made that split explicit
(M39). Everything site-specific lives in one registry config per AOI; outputs are name-spaced so
sites can't collide; the radar library is shared across sites on the same satellite frames; and a
status dashboard shows every site's stage checklist, current alarm state, and next command. What
stays human per site — deliberately — is drawing the boundary, the soil literature/field pass, a
*verified* landslide inventory, and tuning the alarm operating points against it. Ten sites is ten
config cards plus ten rounds of that homework; the pipeline itself doesn't change. When NISAR data
matures, its adapter plugs in at one shared seam, so every registered site inherits it at once.

---

**Q: Why do you run two rainfall gates — isn't one danger curve enough?**
A: One curve, two *sensors*, because rainfall kills two ways. A multi-day soak shows up in a
daily average; a one-hour cloudburst averages away in it. Our daily reanalysis gate (validated,
the official alarm) catches the soak; the half-hourly satellite gate (IMERG, experimental)
catches the burst — and it runs ~5 days fresher. This season's two verified events split
exactly along that line: the 7 Apr highway burial was a soak (daily arm ALERT, burst arm
quiet), the 8 Jul Himkoti slide was a burst (burst arm ALERT hours ahead, daily arm only
WATCH). Combined, both read ALERT on the day. The burst arm stays labelled experimental until
it earns back-tested thresholds of its own — at short durations the curve trips easily. **Its
false-alarm cost is now measured (CF16/§63):** at its shipped threshold the burst arm costs
**less than half the alarm days** of the validated daily arm while interrupting somewhat more
often — acute vs chronic. A priced second opinion now, not an unquantified one.

**Q: How can you claim a false-alarm rate when your landslide inventory is obviously incomplete?**
A: I can't — and I don't. An episode I can't tie to a recorded landslide isn't proven wrong;
the mountain may have moved where nobody was watching. So I report a **bound** rather than a
number: attribute alarm episodes to events with a strict window and a generous one, and the
true rate lies between the two counts. And because that incompleteness biases *both* arms
identically, the only claim I'll defend is a **comparison** — the new arm against the arm we
already validated, on the identical yardstick. Two further disciplines keep it honest: count
**episodes**, not days (rain arrives in spells, so days flatter a chronic alarm), and clip
every window to the end of the record, or you manufacture a "catch" for an event your data
never reached (CF16).

**Q: A fatal event happened and your fast gate only said WATCH. Doesn't that sink it?**
A: It's the most useful thing that has happened to it. The 22 Jul 2026 boulder strike (2
deaths) read E=2.44 — below the then-current ALERT line of 3 — on the day. The arm wasn't
asleep: it had raised ALERT four days earlier and held WATCH continuously through the strike.
But it did mean the same-day fatal floor was 2.44, not 3.07, so a threshold picked from six
events sat slightly too high. The disciplined response isn't to quietly re-tune a live gate to
fit the newest data point — it's to *price* the change first, then let whoever owns the
consequences decide. We did both: the cost is +47% alarm days, and the threshold was lowered
to 2.4 (§64). Crucially the justification is **not** "2.44 minus epsilon" — recall is flat
across the whole band (1.09, 2.44], so every threshold in it catches the same events, and 2.4
is simply the **cheapest** member of that band. When recall is flat over a range, your evidence
can't pick a point in it; only a cost criterion can. That's the difference between choosing a
threshold and overfitting one.

**Q: Wouldn't a machine-learning susceptibility model outperform your physics map?**
A: We tested exactly that (CF15/§60). A terrain logistic regression beat the raw physics score
on our inventory — but almost all its skill came from one feature, low elevation, which in
this valley is a proxy for "near the highway where landslides get recorded". Delete that
feature and the advantage vanishes. On a corridor-biased inventory, an ML map launders
reporting bias into apparent skill; the physics map can't do that, which is its point. The
right use of ML here is as a bias detector and a challenger — not as the product.

# Part E — Honest Limitations

Being able to state weaknesses is what makes you credible.

- **The sub-daily burst gate (CF14 / §55, calibrated §58, false-alarm-priced §63) is still
  provisional:** its ALERT threshold is evidence-based — now seven verified events — and its
  alarm cost is no longer a caveat but a measurement (CF16): fewer than half the alarm days of
  the validated daily arm, at a somewhat higher interruption rate. But **n=7 is a calibration
  set, not a validation**, and the "false alarms" are only a *bounded* quantity, because our
  inventory records solely reported failures. Two measured biases bound it further: IMERG reads
  only **0.16–0.22×** of the Katra gauge on extreme days (pixel-vs-point in orographic terrain,
  so E is biased LOW when it matters most), and it carries no snowmelt. Per-zone rain was
  probed and declined at these AOI scales (~3 pixels per AOI). **Threshold moved (§64):** the
  22 Jul 2026 fatal strike read only WATCH at k=3, so k was lowered to **2.4** — all 4 fatal
  events now ALERT at Δ=0, at the cost of ~+47% alarm days and an unexplained-episode rate
  **2.4× the validated arm's**. Its margin is thin (2.40 vs a 2.44 fatal floor), guarded by a
  test. It remains a second opinion beside the validated daily alarm, not the alarm.

- **LOS only (for now):** we measure slanted (line-of-sight) motion, not pure
  vertical/horizontal. Combining ascending + descending would fix this — but both our
  descending tracks were evaluated and **rejected as too noisy** (Milestone 10 / CT4), so
  the vertical/east-west decomposition waits on better descending data. We now *quantify* this
  limit with the slope-parallel projection (V_slope, CF4 / Milestone 15): **24–42 %** of measured
  ground is a single-look blind spot (downhill ~perpendicular to the LOS).
- **80 m pixels:** each pixel averages an 80 m patch — fine for hillside-scale
  creep, too coarse for a single boulder.
- **Residual atmosphere + single-look creep is not pixel-robust (Milestone 24 / §18):** our *custom*
  engine's plane-deramp + high-pass removes the worst, not all, atmospheric noise (~30 mm/yr floor); the
  MintPy ERA5 correction (CT3) cut scatter to ~21 mm/yr on frame106. We **rolled that ERA5 velocity through
  the hazard** on frame106: it agrees on the broad field (r≈0.55) but flags **~half** the creeping pixels,
  and only ~18 % overlap with the high-pass method's. So *which exact pixels creep on a single track is
  sensitive to the velocity processing* — trust where **multiple looks agree** (the ≥2-look core, M23). The
  ERA5 product is the more physical basis but is so far **validated on only one of three tracks (§22):**
  re-running it on the other two ASC stacks gave unusable velocities — one had a coherent-but-wrong −56 mm/yr
  scene-wide bias (std 57, 25 % of pixels beyond ±100 mm/yr), the other was too low-coherence — so the
  atmosphere fix does **not** generalize for free; each track needs its own stable reference + cross-check
  before it can be trusted. The mosaic still runs on the custom velocities. **We now quantify this floor
  per zone (Milestone 29 / §24 / CF10):** each alert carries a detection confidence p = Φ((−15 − v)/σ_v) that
  its creep truly exceeds the per-track noise (σ_v 14–24 mm/yr), with multi-look corroboration combining to
  P = 1 − Π(1 − p) — so marginal creep is explicitly down-weighted. Honest caveat: this *measurement*
  confidence is **orthogonal** to inventory-proximity (filtering by it doesn't move the spatial AUC), so it is
  a triage axis (ignore likely-noise), not a spatial ranker.
- **Vegetation gaps:** dense forest decorrelates, so coverage is patchy — we get
  reliable measurements mainly on rock, soil, and infrastructure.
- **Look coverage:** Ramban runs on three ascending tracks (union + a ≥2-look core); both descending
  tracks were rejected on quality (CT4), so cross-geometry (vertical/east-west) decomposition still waits
  on better descending data. The second site currently rests on **two short ascending spring chains**
  (4 pairs each — zero inversion redundancy), so its velocity noise floor is several times Ramban's until
  the monsoon acquisitions lengthen the series (every 12 days helps).
- **Rainfall trigger — threshold fixed; the spring *source* mystery is now narrowed (CF5):** on the
  threshold dial we **switched the conservative global Caine curve for the published NW-Himalaya regional
  curve** — which flipped the spring back-test 0/2 → 2/2 — but it fires on **112/214 days** (sensitive, not
  selective), so a return-period/antecedent filter is still needed. On the measurement dial we **ran the
  gauge product CHIRPS (Milestone 17) and it was *drier* than ERA5-Land** on the (then-assumed) event dates.
  **Date correction (Milestone 20):** the real major event was the **20 Apr 2025 cloudburst**, which the
  regional curve + sub-daily IMERG *do* flag (E=2.25) — so the spring trigger is **not** ruled out; the daily
  *AOI-mean* products just dilute the localized cloudburst cell (sub-daily/point rain resolves it). **The
  over-firing is now RESOLVED by the E-graded temporal gate (Milestone 24 / CF7):** grading days by how far
  above the line they sit cuts the alarm from 112 to **27 ALERT days (13% of season, 4× fewer)** while still
  catching the 20 Apr cloudburst at Δ=0. Remaining: only sub-daily/point rain (not AOI-mean) can raise the
  E of the *localized* 27 Apr / 8 May cells (they reach WATCH, not ALERT). The real wetness IS coupled into
  the FS (Milestone 13).
- **Spatial validation is now *scored* and beats chance — but it's small-area and recall-limited (Milestone
  23 / CF6):** graded against a 5,000-point random-luck control with a ROC/AUC, the worst-case (fully-soaked)
  map scored **AUC 0.41 — below chance** (it over-flags). Redrawn at a *realistic* wetness (m≈0.25–0.40) it
  scores **AUC 0.55 (beats chance)** and **5.6× better than luck at 100 m** — the first provably-better-than-
  random result. Caveats: (a) it's one small AOI (~22×22 km), so 2 km buffers approach saturation; the honest
  detection buffer is **≤250 m**; (b) the high-grade ALERT map comes with **lower recall** (12 zones, recall
~0.25) — now complemented by a wider **WATCH tier** (m=0.70, 132 zones, recall ~0.63) whose two-pass-confirmed
core still beats chance (Milestone 28 / CF9); (c) it's
  still **spatial only** — a *temporal* scored test wants the **GSI Bhukosh** inventory with **verified
  dates** (a one-week date error once flipped the spring conclusion, M20). The temporal back-test (4/4 on the
  corrected inventory) remains *partly automatic* because the regional curve fires 112/214 days.
- **Forecasting needs a longer record:** the inverse-velocity time-to-failure screen
  (CF1) is built and noise-hardened, but ~3.5 months at our noise floor shows only
  *steady* creep — no zone is yet accelerating, so no failure dates are projected.
  "Steady" ≠ "safe"; the screen is deliberately conservative and will return dates once
  the series lengthens or a real acceleration begins.
- **Soil strength — now largely site-grounded (Milestones 22, 26):** the friction angle is
  **φ=36°** (GSI-measured on these slopes, 36.4–39.1°, vs the old textbook 32°), and cohesion is now a
  **dry/wet matric-suction split** (c_dry≈18.5 / c_wet=5 kPa, M26 / C4) instead of one flat assumed value —
  so the dry-state strength is the GSI-measured number and the saturated state correctly loses the suction
  "glue." *Update (§46/CF13):* the nonlinear van-Genuchten refinement was **built, tested against four
  published parameter sets, and deliberately NOT adopted** — its parameters are not identifiable from a
  spatial inventory (curve shape trades off against the wetness dial), so the linear curve stands *on
  evidence*, with the mechanism one config line away when a lab retention curve or dated failures exist.
  *Remaining:* the failure depth z is still assumed, and the GSI dry-cohesion **unit** ("18.5 kg/cm²" —
  physically read as ~18.5 kPa) wants lab confirmation. FS is still a *relative* screening layer, but the
  two biggest soil assumptions (friction, then cohesion) are now grounded in measurement.
- **Slope sharpness — now upgraded (Milestone 27 / §21):** the hazard grid is 80 m (set by the
  InSAR velocity), but slope is now computed on the **12.5 m ALOS DEM** at native resolution and
  *averaged* onto each 80 m cell (mean-of-slopes > slope-of-mean), fixing the old under-estimate
  (slope median 28→31°, max 56→66°). FS is correspondingly sharper. The *velocity* is still 80 m, so
  the DEM sharpens the terrain/FS, not the InSAR resolution.
- **Noisy hazard pixels:** the first hazard map flags too much — trustworthy
  mainly where HIGH pixels cluster, not as isolated single-pixel specks (a
  cluster-size filter and lower velocity noise will clean this up).
- **Second site (Vaishno Devi) — validated, with named gaps (Milestones 31–36 / §31, CV1–CV4):** the route
  product **beats chance at its first real exam** (26 Aug 2025 Ardhkuwari disaster + 40 GSI survey points:
  AUC 0.62, recall 0.81@2 km; the model's peak-danger day of 2025 WAS the disaster day) — but carry these
  four caveats when discussing it: (a) **soil φ/c are literature-corroborated but not lab-confirmed** —
  site studies (Kumar & Anbalagan 2013 + GSI overburden data, §37) bracket every value we use (φ 32–43°
  vs our 36°; c within the published dry/wet ranges), so the old "borrowed from Ramban" caveat is retired,
  though nothing has been measured on-site *for us*; (b) the ground truth is **corridor-biased**
  (GSI surveyors walk the track) and mostly *assessed-vulnerable* spots, not occurred slides; (c) the
  **failure-class gap** (CV3): track-side rockfall gives no slow creep — our creep core scored 0 against the
  corridor list, and the disaster site sits **598 m** from the nearest zone (the standing calibration
  target); (d) in an **extreme monsoon the AOI-wide gate saturates** (59 ALERT days in 2025) — per-zone
  sub-daily rain is the fix. *(Update M37: operating points are now site-earned — ALERT m=0.40 / WATCH
  m=0.75 from the local sweep, §32 — so the "Ramban-tuned dials" caveat is retired; the other four stand.)*
- **Validation statistics — the scores now carry error bars, and one honest tie (§44 / CF11 / M41):**
  every headline AUC now ships with a bootstrap 95% interval (n=46 gives ±0.05; n=138 gives ±0.04 —
  quote the range, never a bare third decimal) and a permutation p-value (both ALERT maps beat
  chance at p=0.0001; both WATCH tiers are honestly ≈chance as spatial rankers — they are recall
  nets). The ablation ladder is the fixed bar each science upgrade must clear. In §44 a tuned
  slope≥40° map *tied* our raw spatial AUC at **Vaishno Devi** (needing 155 zones vs our 21); the
  **§45 TWI-saturation upgrade (kappa=0.06) cleared it** — VD operational rose 0.707→0.757, a
  point-estimate lead over both the slope and logistic baselines, with 14 zones. Honest still: that
  gain sits inside the error bars (κ=0 and κ=0.06 CIs overlap at n≤138), so the durable wins are
  footprint economy and *beating the baseline*, plus the Δ=0 temporal catches and per-zone ranking —
  not a proven AUC step-change. At Ramban the fusion already beat every rung (both single ingredients
  ≈chance alone); kappa widened the margin. The next upgrade (van-Genuchten suction) faces the same
  ladder + CIs.
- **Fast-failure instruments are new and unproven-in-anger (Milestone 38 / CV5 / §34):** the coherence
  tripwire has never yet seen a real failure (its first timelines are 4 epochs — the minimum it can even
  flag on is 3); a storm exactly coincident with a collapse could mask the local drop; and steep-face
  layover pixels carry little signal either way. The runout cone is a *reach envelope* — no bounce,
  barrier or ridge-blocking physics, and OSM has almost no buildings mapped at the shrine complex, so
  its buildings count undercounts (the POI/route read is the trustworthy part). Neither tool predicts
  timing. Treat both as watch + consequence coverage for the CV3 class, not as forecasts.

---

# Glossary

| Term | Plain meaning |
|---|---|
| **SAR** | Synthetic Aperture Radar — a satellite radar imaging method. |
| **InSAR** | Comparing two SAR images to detect ground movement. |
| **Phase** | Where a wave is in its cycle; the key to mm precision. |
| **Wavelength (λ)** | Crest-to-crest distance; ours ≈ 5.6 cm (C-band). |
| **Interferogram** | A map of phase difference (= movement) between two dates. |
| **Fringe** | One full phase cycle = 2.77 cm of line-of-sight movement. |
| **Coherence (γ)** | 0–1 trust score for a pixel; low = noisy/vegetated. |
| **LOS** | Line-of-Sight: motion along the radar's slanted view. |
| **APS** | Atmospheric Phase Screen — fake "motion" from humidity. |
| **Phase unwrapping** | Recovering hidden whole wave-cycles (the 2π puzzle). |
| **SBAS** | Small Baseline Subset — the network-of-pairs time-series method. |
| **Design matrix (A)** | Bookkeeping of which dates each measurement links. |
| **Least squares** | Best-compromise solution to noisy, redundant equations. |
| **Rank / connectivity** | Whether the date-chain is unbroken (solvable). |
| **Velocity (LOS)** | Slope of the displacement timeline, in mm/year. |
| **R²** | 0–1: how much one variable explains another (our atmosphere test). |
| **High-pass filter** | Keeps sharp local detail, removes broad smooth trends. |
| **DEM** | Digital Elevation Model — a terrain-height raster. |
| **Slope angle (β)** | How steep the ground is; the biggest landslide driver. |
| **TWI** | Topographic Wetness Index — a map of where water tends to collect. |
| **Infinite Slope model** | Simplest equation for shallow-landslide Factor of Safety. |
| **Factor of Safety (FS)** | Resisting ÷ driving forces; < 1 means slope failure. |
| **Saturation (m)** | How waterlogged the soil is, 0 (dry) to 1 (soaked); high m lowers FS. |
| **Hazard fusion** | Combining FS (physics) with InSAR creep (observation) into a risk class. |
| **Agent (software)** | A module with one job that reasons over inputs and hands off to the next. |
| **Cascading reasoner** | Combines multiple agents' findings into a single alert decision. |
| **LLOF** | Landslide-Lake Outburst Flood — a landslide dams a river, then it bursts. |
| **Ascending/Descending** | Satellite flying S→N (looks E) vs N→S (looks W). |
| **Perpendicular baseline** | Sideways gap between two orbit positions; small is better. |
| **Raster / pixel** | A gridded image; each cell holds one number. |
| **Coherence-drop watch** | Flagging a polygon whose coherence suddenly falls more than the scene's — a fast-failure tell. |
| **Energy line (Fahrböschung)** | Empirical angle from a detachment point below which falling rock rarely travels; sweeping it gives a runout cone. |

---

*This primer grows with the project. Phases 1–4 (data, velocity, slope physics,
the agentic warning system, and the interactive 3-D explorer) are all covered
above — the 3-D view in Phase 4 Part B is a visualisation of the same science, so
it adds no new concept. Remaining additions will come with the move to live
weather data, a real reasoning AI, and the production-hardening upgrades (e.g.
MintPy, full atmospheric correction) — added in the same beginner-friendly style.*
