# 🧭 Would the "method route" be a pivot away from the project we set out to build?

*(2026-08-11. Written because §80 left the Vaishno Devi WHERE map unusable and two routes forward
were proposed. This answers only the second one: **should slope ranking stop depending on measured
movement?** Evidence: the original plan `docs/guides/InSAR_hazard_forecasting_Context.md`, and the
ledger — §60, §80, §81, §82.)*

---

## The short answer

**Building the susceptibility model is not a deviation — it was always in the plan. Promoting it
to the primary ranker would be, and the evidence says don't.**

Three reasons, in order of weight:

1. **We already ran this experiment (§60) and it failed for an instructive reason.** A terrain-only
   statistical model scored AUC **0.731** — until elevation was removed, whereupon it collapsed to
   **0.560**, statistically indistinguishable from the physics score it was meant to beat (0.575).
   Its skill was mostly **where people report landslides** (low, near the road), not where slopes
   fail. The ledger already carries this as "a caution against training susceptibility models on
   corridor inventories."
2. **Someone else already publishes that product, better.** GSI's meso-scale susceptibility map for
   the neighbouring NH-244 corridor scores **AUC 0.84** with 35 field-verified instabilities. Our
   biased 0.731 would be a worse copy of an official map.
3. **It would spend the project's actual novelty to buy a product we can't validate.** The stated
   novelty was never "InSAR detects creep" — see below — but measured movement is the thing that
   makes this more than another susceptibility map.

---

## 1. What the original plan actually committed to

The novelty claim is explicit, and it is **not** about InSAR:

> "Current government and academic models largely operate in silos… They usually only combine these
> datasets *after* a disaster occurs… The novelty here is to build an **Autonomous Agentic
> Orchestrator** — a multi-agent system where distinct Python 'agents' handle specific domains,
> audit each other's data, and reason through cascading effects."

The differentiator is **multi-domain fusion before the event**: movement + weather + hydrology +
physics, arguing with each other. Three agents were specified; two of them (weather, cascading
reasoner) are untouched by anything in §80–§82.

**And the plan explicitly anticipated the failure we hit.** Agent 1's specification:

> "If γ drops below a strict threshold (0.4) due to heavy Himalayan vegetation, it masks that data
> out and **refuses to pass noise downstream**."

Plus the closing Guiding Principle:

> "By auditing noise *before* trusting any deformation map, this pipeline avoids the
> 'garbage in, garbage out' failure that plagues remote-sensing hazard work."

**So §80 is the design working, not the design failing.** We asked whether the movement signal was
real; it wasn't; the system refused to publish it. That is the single most-stated commitment in the
whole document, and it held under pressure — including pressure from us, twice (we declined to tune
thresholds until zones reappeared, §80/§82).

## 2. The method route is already in the plan — twice, and both times subordinate

| Where | What it says | Role assigned |
|---|---|---|
| **Area 4 — Validation** | "Susceptibility model (logistic regression / random forest on conditioning factors) trained + validated on the inventory → **independent corroboration of the physics**" | a **check on** the core |
| **Area 5 — Multi-sensor** | "Inventory + large-area susceptibility … → susceptibility over the whole NH-44 corridor, **then focus InSAR where high**" | a **targeting aid for** the core |

So: **writing the model = zero scope deviation.** It is planned work, and
`workflows/susceptibility_crosscheck.py` already exists. What would deviate is changing its *role*
from corroborator/targeting to **the thing that decides which slopes are flagged**.

## 3. What would actually change (the honest deviation inventory)

Smaller than it sounds in two places, larger in one.

**Barely a change — the fusion rule is already partly an OR.** The hazard raster is already
`WATCH = low FS **OR** creep`; only the ALERT tier demands `low FS **AND** creep`. "Creep as one
clue rather than a requirement" is therefore a change to **one tier's gate**, not a new philosophy.

**No change at all — the WHEN arm.** Rainfall, burst and flash-flood grading are independent of
this and remain validated. Whatever we decide, that half stands.

**The real change — what the product claims, and how it must be validated.** Today the claim is
*"physics + measured movement, and note that it cannot learn where landslides were reported."*
A statistical ranker's claim is *"terrain patterns resembling places landslides were recorded"* —
which inherits the recording bias by construction. §60 measured exactly that inheritance here.
Different claim, different validation burden, and a much more crowded field to be judged against.

## 4. The measured evidence against promotion — from this project, not from theory

§60 3a, on the frame106 grid, 112 GSI positives vs 2,000 seeded random negatives, 5-fold CV:

| model | AUC |
|---|---:|
| Terrain-only logistic regression | **0.731 ± 0.046** |
| …the same model with **elevation removed** | **0.560 ± 0.039** |
| Raw physics score (−FS_saturated) | 0.575 |
| Ensemble | 0.691 (no gain) |

Elevation carried a weight of **−0.98**. The inventory hugs the low-elevation NH-44 valley, so the
model largely learned *"landslides are reported near the road"*. **The Vaishno Devi inventory is a
narrower corridor still** — 47 points strung along a pilgrimage track — so the bias there should be
**equal or worse**, not better.

This is the crux: the method route's appeal is that it "doesn't depend on detecting movement". But
what it depends on instead — an inventory of *reported* failures along a transport corridor — is a
**known-contaminated** predictor in this exact project.

## 5. The external benchmark makes duplication a poor trade

GSI has already published a **1:10,000 meso-scale susceptibility map** for the adjacent NH-244
corridor: **AUC 0.84**, ~30% of the area "High", 35 field-verified instabilities. If our WHERE
product becomes a susceptibility map, it competes directly with that — with a smaller inventory, a
measured bias problem, and no field verification of our own.

Whereas the *fusion* product does not compete with it at all: GSI's map is static susceptibility;
ours would add measured movement and a live weather trigger on top. **That complementarity is the
project's position, and it only exists while movement is in the product.**

## 6. What this costs us — the honest case FOR the pivot

Stating the other side fairly:

- **We have no usable WHERE product today.** ALERT is empty; WATCH scores below chance (§80). A
  terrain ranker would produce *something* defensible-looking immediately.
- **The NISAR route has an external dependency** — NASA's cadence and reprocessing (§82). We cannot
  schedule it.
- **It is planned work anyway** (Area 4), so effort is not wasted whichever role it ends up in.
- **A bias-controlled version is possible**: report the elevation-ablated AUC as the headline, train
  with elevation excluded, or use spatially-blocked cross-validation. §60 shows the ablation
  collapses it to ≈ the physics score — which is itself an honest finding, not a failure.

The strongest version of the pivot argument: *"a modest, bias-controlled terrain ranker that beats
chance is worth more than an empty map."* That is true. It is just **not worth swapping the core
thesis for**, because a corroborator can deliver the same value without the swap.

## 7. Verdict

**Do not pivot. Do build it — in the role the plan already gave it.**

| Question | Answer |
|---|---|
| Are we moving away from the original plan? | **Only if it replaces the core.** As a corroborator/targeting layer it *is* the plan (Area 4/5). |
| Is §80 evidence the plan was wrong? | **No** — it is Agent 1's noise-refusal working exactly as specified. |
| Is the pivot worth it? | **Not as a replacement.** Measured bias here (§60), an existing better official product (GSI 0.84), and it spends the novelty. |
| What fixes the core? | **The sensor route.** §81 proves L-band recovers 86.5% of the ground C-band cannot see — on our own slopes. |

**Recommended shape:**

1. **Keep the WHERE map withdrawn** and the WHEN arm published. That is already true and already
   stated honestly on the dashboard.
2. **Finish the susceptibility model as a CORROBORATOR**, with the §60 bias control mandatory: the
   **elevation-ablated AUC is the headline number**, never the raw one. Cheap — the script exists.
3. **Use it for targeting** (Area 5's role): rank the corridor, then point scarce radar/field effort
   at the top. This is genuinely useful *without* any claim that it replaces measured movement.
4. **Put the product weight on NISAR** (`docs/references/NISAR_INGESTION_DESIGN.md`), which fixes
   the cause rather than routing around it.
5. **Revisit this decision if** NISAR's monsoon void persists past NASA's reprocessing window *and*
   a spatially-blocked, elevation-ablated susceptibility model clears ~0.70 on the VD inventory.
   Then the trade genuinely changes, and this document should be re-opened rather than assumed.

**One-line summary for the record:** the project set out to prove that *fusing* measured movement,
weather and physics beats looking at any one of them alone. §80 showed one input is unreadable at
one site with one sensor. That is a sensor problem with a sensor fix — not a reason to abandon the
thesis and rebuild a map that GSI already publishes better.
