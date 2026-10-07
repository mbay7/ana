# Plan — Ana

Approved by Mohammed:

> No date on the line above means no code. Only Mohammed's own yes fills it in.

## Now
Waiting for approval. First up: Phase 1, step 1 — compare the server copy with this one.

## Steps

Each step is small enough to finish and check. "Done when" is something the owner could verify himself.

### Phase 1 — Stabilise (get back to a clean, working state)
1. **Compare the server copy with this one.** Mohammed (or Hermes) lists what is in the server's Ana folder and when it last changed; Claude compares it with GitHub. — **done when** there is a written list of what the server has that GitHub doesn't, or a clear "nothing". No code changes before this.
2. **Finish the function that was left unfinished** (`_bare()` and its word list in `src/generate.py`). — **done when** all 44 tests pass.
3. **Run the quality check and record today's score.** — **done when** the score is written in the Log below and is at least 47 of 50.
4. **Give the quality check a pass mark** so it fails when the score drops. — **done when** a deliberately lowered run fails and a normal run passes.
5. **Stop Ana borrowing Hermes's key file** (`src/generate.py` reads `$HERMES_HOME/.env`). — **done when** no mention of Hermes remains in `src/` and tests still pass.
6. **Merge the audit work into the main version and remove the branch.** — **done when** the main version on GitHub has all tests passing and the audit branch is gone.

### Phase 2 — Runnable where it needs to run
1. **Settings template** listing every setting by name, no values. — **done when** every setting the code reads is in `.env.example`.
2. **Fix the versions of the building blocks** Ana depends on, and make the two lists of them agree. — **done when** a fresh install passes all tests.
3. **Make the access check refuse by default.** Today anyone can call Ana when no access token is set. — **done when** a test proves a request without the token is refused.
4. **Package it as a container.** — **done when** one command on the Mac starts it, the health check answers, and one demo question gets an answer.
5. **Automatic checks on GitHub** that run the tests and the quality check on every change. — **done when** the main version shows a green tick.
6. **Put the demo online at its link.** Claude asks before publishing. — **done when** the link answers from Mohammed's phone and a wrong token is refused.

### Phase 3 — Ready to show
1. **Rewrite the README to match the brief.** — **done when** someone new can start Ana in three commands.
2. **Rewrite the roadmap as Shipped / Now / Parked.** — **done when** it matches this plan.
3. **Lock the public demo to the demo brand,** and decide whether the "build your own assistant" page stays public (it lets visitors spend Mohammed's key). — **done when** the decision is in `DECISIONS.md` and the demo behaves that way.
4. **Mohammed's own walk-through:** ten plain questions, including Arabic. — **done when** he ticks each one.

## Parked
Not being built in this round. An item moves into Steps only when Mohammed says so.

- **Open decision — licence.** Mohammed wants to change it from non-commercial; to what is undecided.
- **Open decision — a real client's name appears in this public project's history** (commit messages from 4 October). Whether to do anything about it is Mohammed's call.
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

- 2026-10-07 — Before the plan: unsaved audit work saved exactly as it was (commit `49b8546`) and uploaded as a backup. Tests unchanged: 30 pass, 14 fail.
