# Plan — Ana

Approved by Mohammed: 2026-10-12

> No date on the line above means no code. Only Mohammed's own yes fills it in.

## Now
Stage 1, step 6 — make GitHub run the tests (and the quality check) before anything is built, and lock the build's outside helpers to exact versions. Work is on the side branch `stage1/combine`; nothing is in the main version yet.

## Important to know
- **Anything saved to the main version on GitHub goes live.** The public site `ana.mblab.ai` follows the main version on a timer (per Hermes). Claude asks Mohammed before every save to the main version.
- **Order is promised, dates are not.** A stage starts only when the one before it is finished. One exception is marked.
- This plan replaces the 7 October draft. It follows the assessment of 12 October 2026.

## Stages

### Stage 0 — Decide (no code)
Each is finished when it is one dated line in `DECISIONS.md`.
- ~~How Ana is sold~~ — decided 12 Oct: people set it up themselves, reached in steps.
- ~~Who it is for~~ — decided 12 Oct: any small business.
- Plan names and prices.
- Licence.
- Whether Ana says it is an AI (Claude's advice: yes).
- Where real clients' folders are kept (Claude's advice: one private project).
- The first client's facts: signed? launch date? website first or WhatsApp? who answers hand-offs?

### Stage 1 — A trustworthy base
1. ✅ **Bring the Mac's copy up to date with GitHub.** — **done when** the Mac's main version and GitHub's are the same save.
2. ✅ **Fix the two out-of-date tests.** They expect Ana to recognise a customer from typed text; that was switched off on purpose. — **done when** all 8 tests on the main version pass.
3. ✅ **Combine the unfinished audit work with the newer main version**, on a side branch. Keep the safety fixes already live; bring across the audit's tests; finish the function left unfinished. — **done when** every test passes on the side branch.
4. ✅ **Run the quality check and record the score.** — **done when** the score is in the Log and is at least 47 of 50.
5. ✅ **Give the quality check a pass mark, and count "I don't know" answers.** — **done when** a deliberately lowered run fails.
6. **Make GitHub run the tests before anything is built**, and lock the build's outside helpers to exact versions (today they follow whatever their makers publish next). — **done when** a deliberately broken test stops the build and every helper in the build file is fixed to one exact version.
7. **Limits:** messages per visitor, message length, and a monthly spend ceiling per brand. — **done when** a flood of messages is refused in a test.
   - *Partly done 16 Oct (in the app):* message length (500 characters), messages per chat, a server-wide limit per minute, per-visitor limits per minute and per hour kept on the server (a reload does not reset them), and a monthly spend ceiling per brand worked out from word-pieces (tokens), with each message's likely cost held before the model is called. A flood is refused in a test. **Still to do:** a limit at Cloudflare in front of the server (the in-app visitor limit only works when Cloudflare passes on the visitor's address); the same limits for the programmable access (API); checking the price settings match the model really used.
8. **One access code per brand; only listed websites may call Ana.** — **done when** brand A's code is refused for brand B in a test.
9. **Put the programmable access (API) inside the container** and fix the versions of the building blocks. — **done when** one command starts both the chat page and the API, and the health check answers.
10. **Move the combined work into the main version.** Claude asks first. — **done when** the main version has all tests passing and the live site still answers a demo question.

### Stage 2 — A conversation that works
1. **Memory of the last few turns.** — **done when** "yes" and "the second one" are answered correctly in tests.
2. **One decision step replaces the phrase rules.** — **done when** the existing intent tests pass and "Hi, can I return this?" gets its answer.
3. **A real hand-off:** takes a name and contact, emails the brand's team a summary, tells the shopper the wait. — **done when** a test hand-off arrives in an inbox.
4. **Says it is an AI** (if decided in Stage 0) and the medical rule matches whole words. — **done when** tests cover both.
5. **Keep shopper text and document text apart** in what goes to the model. — **done when** the planted-instruction tests pass.
6. **Store less:** hide phone numbers and names in logs; delete after a fixed period. — **done when** a test shows both.
   - *Partly done 16 Oct:* phone and order numbers are hidden and logs are kept 30 days, with tests. **Still to do:** hiding names.
7. **Arabic test questions** added to the quality check. — **done when** Arabic has its own recorded score.
8. **Mohammed's walk-through:** ten turns in English and ten in Arabic. — **done when** he ticks each one with no dropped question.

### Stage 2b — Ana's public page (may overlap with waiting on the first client's content)
One page in the `ana-site` project, phone first, Arabic and English. First screen: one promise, a real chat example, one contact button. Then: who it is for · what it does · how it works · try the demo · the weekly report · prices · about · contact. — **done when** it opens cleanly on a phone in both languages and Mohammed approves it before it is published.

### Stage 3 — First client live on their website
Private project for client folders · 30 questions written by the client as the acceptance test · chat bubble on their site · weekly report · backups · live server moved to the container. — **done when** the client's 30 questions pass at the agreed mark, a hand-off reaches their inbox, and the first weekly report is sent.

### Stage 4 — Prove it is worth paying for
Four to six weeks of real numbers; compare shoppers who used the chat with those who did not. — **done when** there is a one-page case study with real figures, approved by the client.

### Stage 5 — WhatsApp
Through an approved WhatsApp provider. Work out the cost per conversation before building. — **done when** a shopper gets an answer and a hand-off on WhatsApp and the cost per conversation is known.

### Stage 6 — Repeatable
An onboarding checklist; each repeated step is noted as a future dashboard screen. — **done when** the second and third brands are live using only the checklist.

### Stage 7 — The dashboard
The repeated steps become screens: upload documents, set the tone, test, see the weekly numbers. A login per brand and a real database. — **done when** a brand owner changes their own content and sees their own numbers without Mohammed.

### Stage 8 — Public sign-up
Sign-up, card payments, plans and limits, help pages, terms, privacy and refund pages, self-connect for WhatsApp. — **done when** a stranger signs up, pays, and has a working assistant with no help.

## Parked
Not being built until Mohammed moves it into a stage.

- **Open decision — a real client's name appears in this public project:** in save messages from 4 October. The two files were fixed on 16 October; the history is not rewritten.
- Clients bringing their own model keys.
- Order-status lookup, and returns or refunds with human approval.
- Shareable link.
- Photos and voice.
- Proactive outreach and cart recovery.

## Log
One dated line per finished step: what changed, and the test result.

- 2026-10-07 — Before the plan: unsaved audit work saved exactly as it was (save `49b8546`) and uploaded as a backup. Tests on that branch: 30 pass, 14 fail.
- 2026-10-07 — Compared the server copy with GitHub (Hermes's inventory): no unsaved changes on the server, same save as GitHub's main version (`acc0318`). The Mac was four saves behind. Tests on the main version: 6 pass, 2 fail.
- 2026-10-12 — Plan approved by Mohammed after the assessment. Found the live page showing owner-only pages; reported to Hermes for a fix on the server.
- 2026-10-12 — Stage 1 steps 1–4 done on the side branch `stage1/combine`. Mac's main version now equals GitHub's (`acc0318`). Audit work combined with the newer main version; the unfinished function finished, so "Hi, can I return this?" is no longer treated as a greeting. Two out-of-date tests rewritten to match the privacy change. Tests: 45 pass, 0 fail. Quality check: 47 of 50 (94%), unchanged. Not checked: a live model reply (no model key on the Mac). Nothing saved to the main version.
- 2026-10-16 — Security fixes from the audit, approved by Mohammed, on the side branch `stage1/combine`: shoppers can no longer break out of the message wrapper with capital letters or spaces; every reply drops links that are not the store's own and all pictures; logs hide phone and order numbers and keep 30 days; limits per chat, per visitor and a monthly spend ceiling per brand (step 7, partly); owner pages need a password; the website reader refuses the server's own network; past orders need a signed-in customer; `.env.*` files are ignored; the client's name removed from two files. Tests: 106 pass, 0 fail. Quality check: 47 of 50 (94%), unchanged. Not checked: a live model reply (no model key on the Mac), and the build image (Docker not running). Nothing saved to the main version.
- 2026-10-16 — Second round after an automated review of the first: the visitor's address is trusted only when Cloudflare is switched on, and a reload no longer resets the limits; the spend check refuses if its file cannot be read, written or locked, and holds each message's cost before the model is called so a burst cannot overshoot; limit storage is bounded; the owner password box locks after repeated wrong guesses; the website reader connects only to the address it checked. Tests: 133 pass, 0 fail. Nothing saved to the main version.
- 2026-10-16 — Stage 1 step 5 done on `stage1/combine`: the quality check (`eval/run_eval.py`) now has a pass mark in `eval/thresholds.json` and exits with an error below it. It also counts "I don't know": 0 of 50 answerable questions (good) and only 2 of 10 unanswerable ones declined. Deliberately lowered runs fail as they should (top-1 only: 22/50; threshold 0.6: 24 wrong "I don't know"). Finding for Mohammed: raising the "I don't know" threshold from 0.32 to 0.38 would decline 5 of 10 unanswerable questions with no loss on answerable ones — not changed; his call.
