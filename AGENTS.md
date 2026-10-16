# Working rules for this project

These rules apply to every assistant working here (Claude, Hermes, or any other). The owner, Mohammed, directs the work and does not write code.

## Before doing anything

1. Read `docs/BRIEF.md`, `docs/DECISIONS.md` and `docs/PLAN.md`.
2. Find the line starting `Approved by Mohammed:` near the top of `docs/PLAN.md`. If it has no date, **write no code**. Finish the plan with him instead.
3. Work only on the step listed under **Now**.

## While working

- One step at a time, on its own branch.
- A step is finished only when its "done when" is met and the checks below pass.
- When a step finishes: update **Now** and add a line to **Log** in `docs/PLAN.md`, then tell the owner in plain words what changed and what is next.
- A new idea — yours or his — goes under **Parked** in `docs/PLAN.md`. It becomes a step only when he says so. Do not build it in passing.
- A new decision (a tool, a place to run, a way to store data) gets a dated line in `docs/DECISIONS.md`.
- If you find unsaved or unfinished work, stop and ask before touching it.
- Do not add a new hand-written phrase rule for chat behaviour without a failing test case for it first.

## Switching between assistants

Mohammed works with Claude Code on the Mac and with Hermes on his phone. Both follow these four moves so each knows what the other did.

1. **Before starting:** pull the notes vault and read the other assistant's "Where I left off" (`Agent Knowledge/For-Claude.md` is written by Hermes, `Projects/vps-ops/For-Hermes.md` by Claude). Then fetch this project from GitHub and check your copy is not behind.
2. **Say it back** to Mohammed in one line, with how old the note is.
3. **After finishing anything that changed something:** rewrite your own "Where I left off" (replace it, never keep two).
4. **Upload straight away and confirm it arrived** before telling him the other assistant can see it.

The notes only point at the work. Where this project is up to is `docs/PLAN.md`, here.

## Never

- Never commit passwords, keys or client data. Settings are listed by name in `.env.example`; values stay in `.env`, which is not committed.
- Never put a real client's name or content in this public project — not in files, commit messages or examples. Real client folders stay out of it (`.gitignore`).
- Never leave code for the owner to write. No placeholders marked for him to complete.
- Never publish, deploy, spend money or delete without asking at that moment.
- Never change `docs/BRIEF.md` to fit what was built. If the build drifts from the brief, say so.

## Talking to the owner

Plain, everyday language. Say what it does and what he needs to do — usually nothing — before any detail. Explain a technical word the first time, or leave it out.

## Checks

- Run the tests: `.venv/bin/python -m pytest -q`
- Run the quality check: `.venv/bin/python eval/run_eval.py` — it now has a pass mark and exits with an error when Ana gets worse. The bar is in `eval/thresholds.json` ("never worse than today"): at least 47 of 50 answerable questions found in the top five, no "I don't know" on questions she can answer, and at least 2 of 10 unanswerable questions declined. Never lower a number in that file without Mohammed's yes; raise it when Ana genuinely improves.
- Run it locally: `streamlit run app.py` for the chat page, or `python chat.py "your question"` for one question. `CLIENT=<name>` picks the brand; the default is `demo`.

## Who writes code

Claude writes and saves code. Hermes proposes changes as text and does not upload them. Saving to the main version makes it live on the public site, so Claude asks Mohammed each time.
