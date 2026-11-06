# Soil Pass & Inventory: A Plain Guide

*Written 2026-11-06 for the person doing the searching. The goal: by the end you'll know what these
two jobs are, why the project can't skip them, and what you're hunting for when you open a report.
Every number here came out of this project's own code or from a document I opened and read. The
few things I couldn't open are marked.*

---

## 1. The whole idea in one minute

The project makes a map of slopes that might fail. Two jobs stand behind that map, and only a
person can do them:

| | **Soil pass** | **Inventory** |
|---|---|---|
| **Everyday version** | The **ingredients** for the recipe | The **answer sheet** for marking the exam |
| **Question it answers** | "What is this mountainside made of, and how strong is it?" | "Where and when did slopes *actually* fail here?" |
| **What it produces** | Five numbers about the ground | A list of real landslides, with place, date and source |
| **Without it** | The map is calculated using another mountain's soil | The map can never be scored, so nobody knows if it's any good |

The radar, the rain data and the terrain are all automatic. No satellite can measure how strong
soil is, or tell us that a slide buried a road on a particular Tuesday. That knowledge sits in
reports, papers and newspapers, which is why this part falls to you.

---

## 2. Why a slope stands up at all

Put a book on a table and slowly tilt the table. The book stays put for a while, because grip
holds it. At some angle gravity wins and it slides.

A hillside is the same thing: **a blanket of loose soil lying on solid rock.** Landslides of the
kind we model are that blanket sliding off.

```
                      soil blanket
                    (the thing that slides)
                 ___________________
             ___/ . . . . . . . . . /___
         ___/ . . . . . . . . . . /     \___     z = how thick the
     ___/ . . . . . . . . . . . /           \    sliding layer is
    /  . . . . . . . . . . . . /  ===========
   /=========================/   solid rock
  /   ^ slip surface: where the blanket lets go
 /  slope angle
```

The model does one simple sum for every patch of ground:

> **Factor of Safety = what's holding the soil on ÷ what's pulling it down**

- **Above 1:** the holding wins, so it stays.
- **Below 1:** the pulling wins, so it can go.

This is what your real model gives for one soil, at different steepness and wetness. (These are the
Ramban values run through the project's actual `factor_of_safety` function.)

| Slope | Dry | Half soaked | Fully soaked |
|---|---|---|---|
| 20° | 3.01 | 2.12 | 1.24 |
| 25° | 2.41 | 1.69 | **0.98** |
| 30° | 2.01 | 1.41 | **0.81** |
| 35° | 1.73 | 1.21 | **0.69** |
| 40° | 1.52 | 1.06 | **0.60** |
| 45° | 1.38 | **0.95** | **0.53** |

Look along any row: **the same slope goes from safe to failing just by getting wet.** That's the
whole monsoon problem in one table. Rain doesn't push slopes over. It takes away what was holding
them, in two ways:

1. **Water between the grains pushes them apart**, so they press against each other less and grip
   less. Think of a heavy box that slides easily once it's floating on a film of water.
2. **The "sandcastle glue" disappears.** Damp sand holds a shape because tiny films of water pull
   the grains together. Pour on a bucket of water and the castle slumps. Soil does the same.

---

## 3. The five numbers, one at a time

These are the only things the soil pass needs to find.

### φ (phi), the friction angle: "how steep will a pile of this stand?"
Pour dry sand into a pile. It settles at a natural angle, and that angle is close to φ. Rough,
angular grains lock together and stand steep. Round or slippery grains spread out flat.
- **Unit:** degrees. **Our values:** 36°.
- **Normal range for hillside soil:** roughly 25–40°.

### c (cohesion), the glue
The stickiness that holds soil together even when nothing presses on it: clay, plant roots, and
the sandcastle effect. The project uses **two** values, because the glue is strong when dry and
mostly gone when soaked:
- **c_dry = 18.5 kPa** (dry)
- **c_wet = 5 kPa** (soaked)

To feel the size of a kilopascal: **1 kPa is about 100 kg resting on a square metre.** So 18.5 kPa
is roughly 1.9 tonnes per square metre of grip. Real, but not huge.

### γ (gamma), how heavy the soil is
Fill a one-metre cube with soil and weigh it.
- **Our value:** 19 kN/m³, about 1.9 tonnes per cubic metre.
- **Normal range:** roughly 16–21. It never varies much, which makes it the easiest number to find.

### z, how thick the sliding layer is ← the most important one
Not how deep the soil goes, but **how deep the slip surface sits**: the thickness of what actually
moves. **This number matters most, and it's the hardest to find.**

Why it matters so much: the glue is a fixed amount, but weight grows with thickness.

Imagine sticking a poster to a wall with four pieces of tape. Now try hanging a mattress with the
same four pieces. The tape didn't change; the load did. A thin soil blanket is held by its glue.
A thick one isn't.

| Thickness of the sliding layer | Share of the grip coming from glue (dry, 35°) |
|---|---|
| 1 m | 67% |
| 3 m | 40% |
| 10 m | 17% |

And this is what that does to the answer at a 35° slope:

| z | Dry | Half soaked | Fully soaked |
|---|---|---|---|
| 1 m | 3.11 | 2.09 | 1.06 |
| 2 m | 2.07 | 1.43 | **0.78** |
| 3 m (our value) | 1.73 | 1.21 | **0.69** |
| 5 m | 1.45 | 1.03 | **0.61** |
| 10 m | 1.24 | **0.90** | **0.56** |

Going from 2 m to 5 m changes the answer more than almost anything else you could change.

### The two inputs you don't have to find
**Slope** comes from the terrain map. **Wetness** comes from the rainfall data. Both are automatic.

### Which numbers matter most?
Take one slope (35°, half soaked, Factor of Safety **1.21**) and change one number at a time:

| Change | New value |
|---|---|
| Thickness 3 → 2 m | 1.43 |
| Thickness 3 → 5 m | **1.03** |
| Dry glue 18.5 → 5 kPa | **0.96** (now failing) |
| Dry glue 18.5 → 30 kPa | 1.42 |
| Friction 36° → 30° | 1.05 |
| Friction 36° → 40° | 1.33 |
| Weight 19 → 17 | 1.23 |
| Weight 19 → 21 | 1.19 |

Now the real-world version. In July the project tested every plausible soil value on Vaishno Devi
(§42), and the result was startling:
- The map swung from **0 to 125 flagged zones**, using only values that were all "reasonable".
- Changing thickness from 3 m to **2 m deleted all 21 zones.**
- Even weight, which looks harmless in the table above, moved the count to 12 or 27, because many
  zones sit just barely on one side of the line.

So the soil numbers aren't a detail. **They decide what the map says.** That's why Tosh and Triund
can't simply borrow Ramban's values: their rock isn't Ramban's rock, so the borrowed map would be
confidently calculated from the wrong ingredients.

---

## 4. What a "soil pass" actually is

**The misconception:** "Find the correct numbers on some website."

**The reality:** nobody has measured Tosh. The correct numbers don't exist anywhere. The job is
**detective work**: gather the closest evidence, work out how far to trust each piece, and write
down how you reached your answer.

The result isn't a single number from a page. It's three things:
1. a **range** for each number ("friction is probably 30–38°");
2. a **chosen value** inside that range;
3. a **paper trail** saying where it came from and how close the evidence really is.

"Nothing exists for this site, and here is the nearest evidence" is a perfectly good result.
Vaishno Devi's soil pass ended with zero values changed, and it still succeeded, because the
borrowed numbers turned out to fall inside the site's own range.

### Soil is broken-down rock, so start with the rock
This is the idea that turns random searching into detective work. **Before looking for any
number, find out what rock is there**, because rock decides soil:

| Parent rock | Breaks down into | Tends to behave like | Your sites |
|---|---|---|---|
| Granite, gneiss | Coarse, sandy, gritty soil, little clay | High friction, little glue | **Tosh** (per our config; confirm on Bhukosh) |
| Sandstone | Sand with some silt | Same family; very little glue | **Triund's McLeod Ganj end** |
| Phyllite, schist, slate | Fine, flaky, slippery | Lower friction, weakens when wet | **Most of Triund's climb** |
| Limestone, dolomite | Rubble and scree in a sandy matrix | Strong dry, collapses wet | **Vaishno Devi** |
| Siltstone | Fine silt and clay | Moisture-sensitive | **Ramban** |

The second question is **how the soil got there**, because that decides how thick it is:

| Word in a report | Plain meaning |
|---|---|
| **Overburden** | Everything loose lying on the rock. The general word, and your best search term. |
| **Colluvium** | Soil that has crept or slid downhill and piled up |
| **Debris** | Loose mix of soil and rock fragments |
| **Scree / talus** | Broken rock pieces fallen from a cliff |
| **Residual soil** | Rock that rotted in place and never moved |
| **Moraine / glacial deposit** | Left behind by old glaciers. Likely around Tosh. Can be very thick. |
| **Slope wash** | Soil moved by surface water |
| **Regolith** | Scientists' word for all of the above |

So this is a much stronger search than "soil parameters Tosh": *"debris slide in colluvium over
gneiss, Parvati valley, direct shear test"*. Now you're asking for the right ground.

### How close is the evidence? The trust ladder

| Rung | What you've got | How to treat it |
|---|---|---|
| **A** | Measured on this very slope | Rare. Use it. |
| **B** | Same rock, same valley | Excellent |
| **C** | Same rock, neighbouring valley | Good. Sets the range. |
| **D** | Similar rock, elsewhere in the Himalaya | Usable, and must be labelled as borrowed |
| **E** | Textbook or global value | Last resort, always labelled |

A value on rung D isn't wrong to use. Using it without saying so is.

---

## 5. Reading a paper in five minutes

You don't need to read papers. Search inside them with Ctrl+F for: `cohesion`, `friction`, `shear`,
`kPa`, `kg/cm`, `Table`, `overburden`, `thickness`. Numbers live in tables with titles like
"geotechnical properties", "shear parameters" or "material properties".

For every number you find, ask **five questions**:

1. **Soil or rock?** Was this measured on the loose blanket, or on solid rock?
2. **How was it found?** A lab test, a calculation, or just assumed?
3. **Where?** Which rock, how far from my site?
4. **What unit?** Check it, then check it again.
5. **Wet or dry?**

Those five questions exist because each one has caught a real mistake. Here are the traps, all
from documents in this project.

### Trap 1: wrong units
The most common trap. Convert everything to our units:

| If you see | Multiply by | To get |
|---|---|---|
| kg/cm² | 98 | kPa |
| t/m² | 9.8 | kPa |
| MPa | 1000 | kPa |
| kN/m² | 1 | kPa (they're the same) |
| g/cm³ or g/cc | 9.8 | kN/m³ |
| MN/m³ | 1000 | kN/m³ |

**Real case, solved this session.** Since June the project has carried a warning about the GSI
Ramban report: its summary says cohesion averages "18.5 kg/cm²". Taken literally that's 1,814 kPa,
rock-hard and absurd for soil. We assumed it meant 18.5 kPa and flagged it. Reading deep inside
the same report (printed page 95), the authors give "0.051 and 0.35 kg/cm² (approximately 5.1 to
35 kPa)". So kPa-sized values were almost certainly intended, and the summary's label is wrong.

**Lesson: the executive summary is the least reliable page. Trust the body and the tables.**

**Second real case, still unsolved.** A paper on the Tiralines landslide near Dharamshala, in
Triund's rock unit, lists cohesion as 0.07, 0.02 and 0.17 under a column headed **kPa**. That's
practically zero. If the column should say kg/cm², they would be about 7, 2 and 17 kPa, which look
completely normal. I can't tell which from the paper. The right move is to **record the number as
printed, note both readings, and flag it.** Never silently fix it.

### Trap 2: rock numbers in a soil hunt
Rock has far higher values, and they don't describe the soil. The Vaishno Devi paper gives a
friction angle of 46°, which sounds wonderful, but it describes a crack in rock. Using it for soil
"would halve the hazard map using numbers that don't describe colluvium" (§37).

**Quick tells:** values in MPa, the words "joint", "rock mass", "wedge", "RMR", "SMR", "UCS".

Also beware the collision: **"GSI" usually means Geological Survey of India, but in a rock table it
means Geological Strength Index**, a rock rating. The NHPC Parbati paper's table uses it that way.

### Trap 3: a friction angle near zero
Your §86 search found Himachal values "scattering from 0 to 36°", which looked baffling. Here's
the likely explanation. Soil labs run different tests:

- **Slow / "drained" test:** lets water escape. Measures how soil behaves over long periods. **This
  is what our model wants.** Look for φ′ (with a little dash), "effective", "drained", "CD", or
  "direct shear".
- **Fast / "undrained" test (UU):** squeezes wet soil before water can leave. It reports nearly all
  its strength as c, with φ close to 0. A real measurement, but of a different situation.

So φ≈0 doesn't mean the soil has no friction; it usually means the wrong test for us. A summary of
a Kullu case study reports exactly this mix (φ near zero in most boreholes, with UU tests alongside).
I couldn't open that paper's full text, so treat that specific reading as unconfirmed.

### Trap 4: "thickness of the soil" is not "depth of the slide"
Tiralines reports debris **20–25 m** thick, yet the samples came from about 1 m down. GSI's Ramban
report gives overburden of 0.5 to over 20 m. Using 20 m as z would be wrong: slides usually peel
off the top few metres, not the whole pile.

What you want is **the depth of the sliding surface in shallow slides**. Search for: "depth of
failure", "slip surface", "scarp height", "shallow translational", "thickness of the slide mass".

Our model also only suits this shallow, blanket-style sliding. The NHPC paper's slip surface is
10–15 m deep, curving through a cut slope. That's a different kind of failure, so it's weak
evidence for z.

### Trap 5: disturbed samples
Tiralines tested samples "in a remolded form", meaning broken up and packed back into the test box.
That destroys natural structure, so glue reads low, while friction is less affected. Look for
"undisturbed" versus "remoulded".

### Trap 6: computer inputs presented as measurements
A table of "material properties" may hold assumed values, or values copied from elsewhere. In
**back-analysis**, authors assume the slope was exactly at the breaking point and solve for the
strength. That's useful, but it's a calculation rather than a measurement. Ask: *"did someone
actually test this?"* Also watch for one number repeated across five papers; that's still one
source.

### Trap 7: the source doubts itself
This one was found today. The same GSI Ramban report, a few pages after its lab results (printed
page 98), says its laboratory soil results "were both erroneous and insufficient for reliable
extrapolation". The authors mapped using field observations instead. So a measurement from a
government lab can still be shaky, and **the authors' own caveats are often the most valuable
sentences in a report.** It's also why ranges beat single numbers.

### Trap 8: AI-written summaries
Two "deep research" documents invented events in this project, including one dated in the future
(§36–§38). Use them only to find leads, and follow every number back to the original. The same goes
for my own search summaries. It's why this guide marks what I actually opened.

### Does this number look sane?
These aren't laws. They're the spread seen in this project's documents. Outside them, look closer
before using the value.

| Number | Usual | If you see this, investigate |
|---|---|---|
| φ | 25–40° | Under 20° (fast test or clay?), over 45° (rock?) |
| c | 0–35 kPa | Over 100 kPa (rock or unit error?), or tiny decimals (unit error?) |
| γ | 16–21 kN/m³ | Anything outside it. A value of 2.5–2.7 is the *specific gravity* of the grains, a different thing. |
| z | 1–5 m | Over 10 m (whole soil thickness, or a deep failure?) |

---

## 6. Where to look, and what you'll find

Search in this order:

| # | Where | What to look for |
|---|---|---|
| 1 | **Bhukosh**, GSI's map portal: https://bhukosh.gsi.gov.in/Bhukosh/Public | **Start here, for the rock name.** Click your site on the geology layer and note the formation name. That name becomes your best search keyword. It also holds landslide data. |
| 2 | **GSI district and landslide reports** | Like your Ramban report. Look at "slope forming material", "overburden", thickness maps, and annexures. |
| 3 | **Hydropower and road project studies** | The best hidden source: dams and tunnels pay for real ground testing. Search NHPC, Parbati, Malana, plus "EIA" or "DPR". Environmental filings are on the government's Parivesh portal. |
| 4 | **Indian PhD theses (Shodhganga)** | Theses print their full lab tables, which papers trim. Often the richest find. |
| 5 | **Google Scholar** | See search phrases below. |
| 6 | **Global soil maps** (SoilGrids and similar) | Last resort. They're poor on steep mountains. Rung E at best. |

### Search phrases that work
Place names have many spellings, so try several: **Parvati / Parbati, Manikaran / Manikarn, Barshaini,
Pulga, Kasol, Malana, Tosh, Kheerganga.**

```
"Parvati valley" landslide "direct shear"
"Parbati" overburden thickness colluvium geotechnical
Kullu debris slide "friction angle" cohesion gneiss
"Manikaran" landslide slope stability
"shallow translational" landslide Himachal "failure depth"
"<formation name from Bhukosh>" colluvium "shear strength"
Dharamshala "Dharamsala Group" debris slope cohesion
Kangra phyllite overburden "direct shear" landslide
```

The moment you find one good paper, **read its reference list.** That's the fastest route to the
next one, and often how you reach the original source.

### Starting points already checked

| Lead | Useful for | What it actually gave |
|---|---|---|
| **Sharma & Mahajan, "Geotechnical Characterization of Kangra Valley Landslide"**, *Disaster & Development* vol. 8 ([PDF](https://nidm.mha.gov.in/journal/PDF/Journal/Journal14-19/Journal14-19k.pdf)) | **Triund** (McLeod Ganj end, rung B–C) | **Opened and read.** Tiralines slide, Dharamsala Group sandstone, 40–45° slopes. φ 25–31° (direct shear, remoulded). Cohesion column disputed (Trap 1). Mostly sand. Debris 20–25 m estimated. Modelled weight 0.0205 MN/m³, i.e. 20.5 kN/m³. |
| **Ghosh Roy et al. 2024, *Int. J. Civil Infrastructure* 7** ([PDF](https://ijci.avestia.com/2024/PDF/006.pdf)) | **Tosh** (rung D at best) | **Opened and read.** NHPC's Parbati-II backslope. Different rock (metavolcanics), deep failure of 10–15 m. As extracted, slumped rock: 0.05 MPa = 50 kPa, φ 20°, 18 kN/m³. Check the table columns in the PDF. Mostly teaches traps 2, 4 and 6. |
| **"Analysis of Slope Stability and Mitigation Provision of Slope Failure at Kullu"** (on ResearchGate) | **Tosh** (rung C–D) | **Not opened** (blocked). Summary suggests direct shear and UU data. Worth you opening. |
| **GSI 2023 Kullu landslide report**, on the HP disaster authority site ([link](https://hpsdma.nic.in/admnis/admin/showimg.aspx?ID=3582)) | **Tosh**, both soil and inventory | **Not opened** (connection refused from here). Should cover Kullu and Banjar sub-divisions; try it in your browser. |
| **Sujeewon & Sarkar 2021**, Kullu susceptibility chapter ([DOI](https://doi.org/10.1007/978-981-16-6140-2_16)) | **Tosh** inventory | **Not opened** (paywalled). A summary says it built a Parvati inventory from 2002–2019 satellite images. |

**Honest status:** neither the §86 search nor today's found a measured soil value from Tosh or the
upper Parvati. Expect a borrowed, clearly labelled result unless a hydropower document or thesis
turns one up. That's fine.

### The best source of all: your own eyes
§42 called thickness "the single most valuable number a field visit could bring back", and you
don't need a lab. If you're ever in the area, photograph:
- **road cuts** showing soil sitting on rock, with something for scale (a person, a stick);
- **fresh landslide scars**: the height of the steep bare wall at the top is roughly the slide's
  thickness;
- the **location**, using your phone's GPS.

Five photos like that may beat a dozen papers for z.

---

## 7. The inventory: marking the exam

### What it is
A list of real landslides: where, when, what kind, and how we know. That's all. It's the
**answer sheet**.

### Why it's essential
A map with no inventory is an exam nobody marked. It looks authoritative and could be useless.
Vaishno Devi is the proof. Its map looked like a perfectly serious hazard map. When marked against
real landslide locations, it scored **worse than a coin flip** (§79). Only the inventory could
reveal that.

### How the marking works
1. Take every real landslide point. How many fall near a zone the map flagged?
2. Scatter random points over the same area. How many of *those* fall near a flagged zone?
3. If real landslides land near flags more often than random points do, the map knows something.

The score is called **AUC**:
- **0.5:** a coin flip.
- **Above 0.5:** better than chance. Ramban's is 0.68 on the status board.
- **Below 0.5:** pointing the wrong way.

### There are actually two exams
| Exam | Question | What each row needs |
|---|---|---|
| **WHERE** | Did the map flag the right places? | A good **location** |
| **WHEN** | Did the alarm fire on the right day? | An exact **date** |

An old landslide scar with no date still counts for WHERE. A dated news report with only a village
name still counts for WHEN. A row doesn't need to be perfect; it needs to be **honest about which
exam it can sit**.

### What ruined results before (the reasons for the rules)

**A wrong date can flip a conclusion.** The inventory once listed 27 April and 8 May events from
news reports, and the back-test concluded those failures weren't caused by rain. The real event was
the **20 April 2025 Ramban cloudburst**; a 27 April article had described it a week later. On the
correct date the score went from **0 of 4 to 4 of 4** (§12g). One wrong date had reversed a finding.

**So: a report's date isn't the event's date.** Find the sentence that says when it happened.

**Inventories record what people noticed, not all that happened.** Slides that block a highway get
reported; one on an empty hillside doesn't. So a map can score well simply by learning where the
roads are. When we tested this on Ramban, a terrain-only statistical map scored 0.731, and dropped
to 0.560 once it could no longer use elevation, because low ground simply tracks the valley highway
(§60). So **points
away from roads are especially valuable**, and satellite images can supply them.

**Invented events exist.** So rejected items get written down too, with the reason. An "exclusion"
note stops someone adding the same false event again next year.

### Where to look

| Source | Good for | Watch out |
|---|---|---|
| **Bhukosh** (GSI landslide layer) | Field-checked locations | Often no dates. A download may require accepting terms, and may arrive by email. |
| **GSI post-disaster reports** | Both: dated and precisely located | Few, but gold |
| **NRSC Landslide Atlas of India** | Satellite-mapped locations | National scale, so coarse |
| **NASA Global Landslide Catalog** | Dated events | Built from news, so it inherits news errors |
| **District disaster plans / HP disaster authority** | Lists of known problem sites | Usually undated |
| **Google Earth history slider** | Scars away from roads, and a date *window* (between two images) | You judge what's a landslide |
| **Newspapers** | Exact dates, details | **A lead only.** Needs 2+ independent outlets. |
| **Papers on the area** | Often print an inventory table | Check what years and method |

### How many do we need?
Ramban's exam used 138 points and Vaishno Devi's used 47. Too few and the score wobbles by luck. My
working target for Tosh is **30 or more located points**, with as many dated as possible. That's
my judgement, not a measured rule. Quality beats quantity, and dated events from 2025–2026 are the
most useful, because rainfall records for those years are already in the project.

### Your first row: a worked example
My search found this, right at your site:

> **Tribune, "Landslide blocks nullah flow in Manikaran valley"** ([article](https://www.tribuneindia.com/news/himachal/landslide-blocks-nullah-flow-in-manikaran-valley-poses-threat-to-village-downstream/amp))
> A slide in **Jeera Nullah, upstream of Tosh village**, dammed the stream and formed a small lake.
> The page is stamped **28 Feb 2025**, and the caption says it happened **"on Thursday"**. No casualties reported.

Now think like the detective:

| Question | Answer |
|---|---|
| When? | 28 Feb 2025 was a Friday, so Thursday means **27 Feb 2025**. That's **inferred**, not stated. |
| Is the date verified? | **Not yet.** One outlet only. It stays a *lead* until a second independent outlet agrees. |
| Where? | Jeera Nullah above Tosh. Find it on a map; a satellite image may show the scar. Location confidence: nullah-level. |
| Interesting? | **Yes: it's February.** A winter slide probably wasn't monsoon rain. Snowmelt? Freezing? Worth noting, because the "WHEN" exam depends on the trigger. |
| Useful for? | WHERE, and WHEN once verified |

That thinking took two minutes, and it's what the job actually is.

---

## 8. From robot to detective: the new routine

**You don't need to copy numbers any more.** Your job is finding and judging. Extraction, unit
conversion and calculating are mine.

**Step 1: identify the ground (15 minutes, once per site).** Open Bhukosh, click your site, and
write down the rock name. Then ask what the soil blanket is likely to be.

**Step 2: hunt (an hour or two).** Search using that rock name and the place spellings. For each
document, spend five minutes on Ctrl+F and the five questions. Then sort it:
- **Keep:** soil tests or slide depths, on similar ground.
- **Note and drop:** rock-only, or too far away. A one-line note saves re-reading it.

**Step 3: capture.** Send me the PDF and the page number. Or fill in a row, which is even better:

| Site / rock | Number | As printed | Test | Soil or rock? | Source + page | Rung | Doubts |
|---|---|---|---|---|---|---|---|
| Tiralines, Dharamsala sandstone debris | φ | 25–31° | Direct shear, remoulded | Soil | Sharma & Mahajan, Table 11.4 | B–C for Triund | Remoulded samples |
| Tiralines | c | 0.02–0.17 "kPa" | Same | Soil | Same | B–C | **Unit doubtful**: maybe kg/cm² |
| Tiralines | Debris thickness | 20–25 m | Field estimate | Soil | Same, site section | — | Whole cover, **not** slide depth |

For landslides, one line per event:

| Name | Date | How sure of date | Where | How sure of place | Type | Sources | Doubts |
|---|---|---|---|---|---|---|---|

**Step 4: stop.** It's easy to search forever. Stop when any of these is true:
- you have three independent sources for **z** and for **φ**;
- you've spent the time you set aside;
- two hours pass with nothing new. That's a result too: *"no local data; nearest evidence is X."*

**What happens next (my part).** I convert the units, build the ranges, propose values and note the
trust rung, and we agree on them together. They go into the site's config file with their paper
trail. Once the map exists, a sensitivity run shows which of those numbers the site's map really
stands on, and that tells you where more searching is worth it.

### Where to start
**Tosh**, in this order:
1. Bhukosh: get the rock name, and check its landslide layer.
2. Try the GSI 2023 Kullu report and the Kullu case study in your browser.
3. Verify the Jeera Nullah slide with a second outlet. That's your first inventory row.

### The one-page reminder

- **Soil pass = ingredients. Inventory = answer sheet.**
- **Rock first**, then numbers.
- **The five numbers:** φ friction, c_dry and c_wet glue, γ weight, z slide depth.
  **z matters most.**
- **The five questions:** soil or rock? tested how? where? what unit? wet or dry?
- **Our units:** kPa, degrees, kN/m³, metres. kg/cm² × 98 = kPa.
- **Summaries lie most.** Trust tables and bodies.
- **Event date ≠ article date.** Two independent outlets, or it's still a lead.
- **Rejected items get written down.**
- **"Nothing found" is an answer.** Unlabelled guesses aren't.

---

*Project references: soil split §20, Vaishno Devi soil values §37, sensitivity test §42, wrong-date
reversal §12g, reporting bias §60, below-chance result §79, this session's findings §89. Runbook:
`docs/runbooks/NEW_AOI_PLAYBOOK.md`, steps M2 and M4.*
