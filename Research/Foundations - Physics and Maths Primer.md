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
> We use this to watch hillsides above the NH-44 highway in Ramban for slow
> creep that can precede a landslide, especially during monsoon."

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

🔗 **In our project:** **Milestone 3** computes FS for two cases — **dry (m=0)**
and **monsoon-soaked (m=1)**. Result: dry, ~13% of slopes are unstable; soaked,
~73% are. That flip *is* the seasonal hazard story. The soil numbers (c', φ', z)
are textbook assumptions for Himalayan soil, not site measurements — an honest
limitation.

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

**Q: Aren't your soil strength numbers just guesses?**
A: Yes — they're literature values for Himalayan soil, not site measurements.
That's why the FS map is a *relative* screening tool, not an absolute prediction,
and why we lean on the measured-motion half of the hazard rule.

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

---

# Part E — Honest Limitations

Being able to state weaknesses is what makes you credible.

- **LOS only (for now):** we measure slanted (line-of-sight) motion, not pure
  vertical/horizontal. Combining ascending + descending would fix this — but both our
  descending tracks were evaluated and **rejected as too noisy** (Milestone 10 / CT4), so
  the vertical/east-west decomposition waits on better descending data.
- **80 m pixels:** each pixel averages an 80 m patch — fine for hillside-scale
  creep, too coarse for a single boulder.
- **Residual atmosphere:** our *custom* engine's simple plane-deramp + high-pass
  removes the worst, not all, of the atmospheric noise (~30 mm/yr floor). The MintPy
  path now adds a *physical* ERA5 correction (CT3) that cut its velocity scatter to
  ~21 mm/yr on frame106 — but that gain is so far proven on one stack, not yet rolled
  through the hazard/alert products (those still run on the custom velocities).
- **Vegetation gaps:** dense forest decorrelates, so coverage is patchy — we get
  reliable measurements mainly on rock, soil, and infrastructure.
- **Single stack so far:** the test result is one satellite track; full corridor
  coverage and cross-checking is still ahead.
- **Rainfall is modelled + a global threshold:** the live rainfall (CF2) is ERA5-Land
  (reanalysis, ~9 km), which *under*-estimates intense orographic bursts; a gauge product
  (CHIRPS/GPM) is the planned cross-check and would likely flag MORE triggers, not fewer.
  The ID curve is a conservative *global* one (Caine 1980); a regional Himalayan curve is the
  refinement. The real wetness IS now coupled into the FS (Milestone 13), but the back-test exposed
  the cost of the modelled rainfall: it **missed the documented 8 May 2025 failure** (ERA5-Land's
  rainfall that day fell below the threshold).
- **Validation is first-pass (Milestone 14):** the back-test shows the map flags the right corridor
  (8/9 documented NH-44 hotspots within ~2 km) but that the rainfall-trigger *timing* is **not yet
  validated** — it picked 26 Aug, whereas the documented 2025 failures were Apr–May (our window
  starts 1 May, and ERA5-Land under-counts the bursts). Inventory coords are approximate; a *scored*
  precision/recall test needs the GSI Bhukosh inventory (~302 mapped Ramban slides).
- **Forecasting needs a longer record:** the inverse-velocity time-to-failure screen
  (CF1) is built and noise-hardened, but ~3.5 months at our noise floor shows only
  *steady* creep — no zone is yet accelerating, so no failure dates are projected.
  "Steady" ≠ "safe"; the screen is deliberately conservative and will return dates once
  the series lengthens or a real acceleration begins.
- **Assumed soil strength:** the Factor-of-Safety uses textbook cohesion/friction
  values for Himalayan soil, not site measurements — so FS is a *relative*
  screening layer, not an absolute prediction.
- **Coarse slope:** the 80 m DEM under-estimates true steepness, biasing FS
  toward "stable"; a 12.5 m DEM is the planned fix.
- **Noisy hazard pixels:** the first hazard map flags too much — trustworthy
  mainly where HIGH pixels cluster, not as isolated single-pixel specks (a
  cluster-size filter and lower velocity noise will clean this up).

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

---

*This primer grows with the project. Phases 1–4 (data, velocity, slope physics,
the agentic warning system, and the interactive 3-D explorer) are all covered
above — the 3-D view in Phase 4 Part B is a visualisation of the same science, so
it adds no new concept. Remaining additions will come with the move to live
weather data, a real reasoning AI, and the production-hardening upgrades (e.g.
MintPy, full atmospheric correction) — added in the same beginner-friendly style.*
