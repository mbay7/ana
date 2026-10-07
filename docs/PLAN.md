# Plan — Ana

Approved by Mohammed:

> No date on the line above means no code. Only Mohammed's own yes fills it in.

## Now
Waiting for approval. First up: Phase 1, step 2 — bring the Mac's copy up to date with GitHub.

## Important to know before approving
- **Anything saved to the main version on GitHub goes live.** The public site `ana.mblab.ai` picks up the main version on a timer (about every 15 minutes, per Hermes). Nothing checks the tests first.
- **This plan was rewritten on 7 October 2026** after the comparison in step 1. The first draft was written from a Mac copy that was four saves behind GitHub, so it listed work that was already done.

## Steps

Each step is small enough to finish and check. "Done when" is something the owner could verify himself.

### Phase 1 — Catch up and stabilise
1. ~~**Compare the server copy with this one.**~~ Done 7 October — see Log.
2. **Bring the Mac's copy up to date with GitHub.** — **done when** the Mac's main version and GitHub's are the same save.
3. **Fix the two out-of-date tests on the main version.** They still expect Ana to recognise a customer from what they type; that was switched off on purpose on 4 October for privacy. — **done when** all 8 tests on the main version pass.
4. **Combine the unfinished audit work with the newer main version.** The two changed the same parts of two files (`chat.py`, `src/generate.py`) and clash. Go through each clash, keep the safety fixes already live, bring across the audit's extra tests, and finish the function that was left unfinished (`_bare()`). All on a side branch, not the main version. — **done when** every test passes on the side branch and nothing live has changed.
5. **Run the quality check and record today's score.** — **done when** the score is in the Log below and is at least 47 of 50.
6. **Give the quality check a pass mark** so it fails when the score drops. — **done when** a deliberately lowered run fails and a normal run passes.
7. **Make GitHub run the tests before anything is built.** Today it builds the package without testing it. — **done when** a deliberately broken test stops the build.
8. **Move the combined work into the main version.** Claude asks first, because this goes live. — **done when** the main version has all tests passing, the live site still answers a demo question, and the audit branch is removed.

### Phase 2 — Tidy how it runs
1. **Settings template** listing every setting by name, no values. — **done when** every setting the code reads is in `.env.example`.
2. **Fix the versions of the building blocks** Ana depends on. — **done when** a fresh install passes all tests.
3. **Limit which websites may call Ana.** Today any site may. — **done when** a call from an unlisted site is refused in a test.
4. **Finish moving the live site onto the container.** The container is built; the live server has not been switched to it. This is server work: Claude writes the steps, Mohammed or Hermes runs them. — **done when** the live site runs from the container and answers a demo question.
5. **Agree how a change reaches the live site** — who may save to the main version, and what must pass first. — **done when** it is one line in `DECISIONS.md`.

### Phase 3 — Ready to show
1. **Rewrite the README to match the brief.** — **done when** someone new can start Ana in three commands.
2. **Rewrite the roadmap as Shipped / Now / Parked.** — **done when** it matches this plan.
3. **Lock the public demo to the demo brand,** and decide whether the "build your own assistant" page stays public (it lets visitors spend Mohammed's key). — **done when** the decision is in `DECISIONS.md` and the demo behaves that way.
4. **Mohammed's own walk-through:** ten plain questions, including Arabic. — **done when** he ticks each one.

## Parked
Not being built in this round. An item moves into Steps only when Mohammed says so.

- **Open decision — licence.** Mohammed wants to change it from non-commercial; to what is undecided.
- **Open decision — where real clients' folders are kept.** Today they exist only on the server, with no backup. Claude's suggestion: one private GitHub project just for client folders, never this public one.
- **Open decision — a real client's name appears in this public project:** in commit messages from 4 October, and in two files (`.dockerignore`, `eval/run_llm_eval.py`). The two files are a small fix; the history is not. Mohammed's call.
- Replace the phrase-by-phrase chat rules with a single decision step (TypeSafe is set up for this). The existing intent tests would be its acceptance check.
- Order-status lookup, and returns/refunds with human approval.
- WhatsApp connector.
- Shareable link and a widget to embed on a site.
- Hand-off to a human with the full conversation.
- Photos and voice.
- Proactive outreach and cart recovery.
- A real database instead of files.

## Log
One dated line per finished step: what changed, and the test result.

- 2026-10-07 — Before the plan: unsaved audit work saved exactly as it was (commit `49b8546`) and uploaded as a backup. Tests on that branch unchanged: 30 pass, 14 fail.
- 2026-10-07 — Phase 1, step 1 done. Hermes listed the server's copy: no unsaved changes, same save as GitHub's main version (`acc0318`, 5 October). The Mac was four saves behind. Already on GitHub and so removed from this plan: Ana no longer borrows Hermes's key file; the access check refuses by default; container packaging; an automatic build. Not on GitHub, on the server only: brand files, the site prototype, one real client's folder. Tests on GitHub's main version: 6 pass, 2 fail.
