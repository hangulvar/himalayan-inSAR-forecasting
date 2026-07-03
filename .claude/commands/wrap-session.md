---
description: End-of-session documentation ritual — one command updates all docs and drafts the commit message
---

Run the end-of-session documentation ritual for this repo. Work through the steps in order; **skip any step with nothing to record**. The guiding rule everywhere: every headline KPI/finding is stated ONCE, in `RESULTS_AND_KPIS.md` — every other file cites its § instead of restating the number.

1. **Gather the session's facts.** Run `git status`, `git log --oneline -10`, and diff any uncommitted work. From the conversation + diff, list: new/changed scripts, new headline numbers, bugs hit, phases/milestones completed, and dead-ends/abandoned approaches.

2. **`RESULTS_AND_KPIS.md` — APPEND, never overwrite.** Add every new headline KPI/finding: tag `[MOCK]` / `[REAL]` / `[MEASURED]`, with date + producing script; mark superseded rows *(superseded)* rather than deleting. This is the committed single source of truth for all numbers.

3. **`error_history_log.md` — append** one entry per bug hit this session (symptom → root cause → fix). Skip if no bugs.

4. **`session_journey.md` — append ONE slim entry:** heading `## Session N — YYYY-MM-DD (branch)`, then **5–10 bullets max**: what was done, why, and any dead-ends or abandoned approaches (dead-ends are this file's unique value — always record them). No KPI numbers — cite the `RESULTS_AND_KPIS.md` § instead.

5. **Only on a completed phase / major milestone:** append a plain-language, beginner-friendly entry to `milestone.md` (what we set out to do, what we found, the plain result), and update `Research/Foundations - Physics and Maths Primer.md` (new concepts in the house style + refresh Part D interview questions and Part E limitations).

6. **`SESSION_REVIEW.md` — regenerate ONLY the LIVE block** at the top: current state in ≤10 bullets citing KPI §s, recommended next step, uncommitted delta. Leave the STABLE block untouched unless a fact in it actually changed (environment gotcha, read order, roadmap).

7. **Finish by printing the recommended git commit message(s)** — concise one-liners, one per logical batch of the uncommitted delta. Do **NOT** run `git commit`: the user commits manually.
