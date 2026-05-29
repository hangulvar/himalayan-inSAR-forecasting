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

## C2. Slope stability & "Factor of Safety" (preview of Phase 3)

Engineers judge a slope by its **Factor of Safety (FS)** — a ratio:

> FS = (forces resisting sliding) / (forces driving sliding)

- **FS > 1:** resisting wins → stable.
- **FS < 1:** driving wins → failure.

Rain *raises* the driving forces (weight, water pressure) and *lowers* the
resisting ones. Our InSAR velocity adds a live ingredient: a slope already
**measurably creeping** is far more dangerous than the static numbers suggest.

🔗 **In our project:** Phase 3 will compute FS across the AOI, using the DEM
(slope steepness) plus our InSAR velocity as a stress signal. This is the bridge
from "the ground is moving" to "this slope is dangerous."

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
A: Not yet — Phase 1–2 measure *movement*. Phases 3–4 combine that movement with
slope physics and rainfall to estimate *hazard*. Movement is an ingredient of
prediction, not the prediction itself.

---

# Part E — Honest Limitations

Being able to state weaknesses is what makes you credible.

- **LOS only (for now):** we measure slanted motion, not pure vertical/horizontal,
  until ascending + descending are combined.
- **80 m pixels:** each pixel averages an 80 m patch — fine for hillside-scale
  creep, too coarse for a single boulder.
- **Residual atmosphere:** our simple plane-deramp + high-pass removes the worst,
  not all, of the atmospheric noise (~30 mm/yr floor).
- **Vegetation gaps:** dense forest decorrelates, so coverage is patchy — we get
  reliable measurements mainly on rock, soil, and infrastructure.
- **Single stack so far:** the test result is one satellite track; full corridor
  coverage and cross-checking is still ahead.
- **Measurement ≠ prediction:** we currently quantify motion; turning that into a
  validated hazard forecast is the upcoming work.

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
| **Factor of Safety** | Resisting ÷ driving forces; < 1 means slope failure. |
| **Ascending/Descending** | Satellite flying S→N (looks E) vs N→S (looks W). |
| **Perpendicular baseline** | Sideways gap between two orbit positions; small is better. |
| **Raster / pixel** | A gridded image; each cell holds one number. |

---

*This primer grows with the project. As we complete Phase 3 (slope physics) and
Phase 4 (the warning system), new concepts (e.g. Topographic Wetness Index,
agentic orchestration) will be added here in the same beginner-friendly style.*
