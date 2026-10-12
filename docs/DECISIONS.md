# Decisions — Ana

One line per decision. Newest at the bottom. If a decision changes, add a new line; do not rewrite the old one.

| Date | Decision | Why |
|---|---|---|
| 2026-10-03 | **Name:** Ana (earlier names: shopassist, Noor) | Found in the project history. |
| 2026-10-07 | **Brand:** Ana sits under mblab.ai | Mohammed, 7 Oct 2026. |
| 2026-10-07 | **Where it runs:** a public demo link anyone can open, and packaged so it can move to a server or a client's setup later | Mohammed chose this on 7 Oct 2026: proof project now, clients later. Changeable. |
| 2026-10-07 | **What it needs there:** a container setup (Docker) and automatic checks on GitHub — neither exists yet | So "where it runs" is settled before launch this time, not after. |
| 2026-10-07 | **Data:** brand content is plain files in `clients/<name>/`; usage logs and saved assistants are plain files under `data/`, which is not uploaded. No database. | Found in the project. File storage does not survive a restart on some hosts — to be handled in Phase 2. |
| 2026-10-07 | **Client content:** real client folders stay out of the public project; only the fictional demo, the Arabic demo and the blank template are uploaded | Found in `.gitignore` and `clients/README.md`. |
| 2026-10-07 | **Secrets (names only):** `OPENROUTER_API_KEY`, `ANA_API_TOKEN`, `ANA_VAULT_KEY`, `ANA_VAULT_KEY_FILE`, `SHOPIFY_ACCESS_TOKEN`. Values live in `.env`, which is not uploaded. | Found in the code. A settings template listing them is a Phase 2 step. |
| 2026-10-07 | **Licence:** currently PolyForm Noncommercial. Mohammed wants to change it; to what is not yet decided. | Mohammed, 7 Oct 2026. Open decision — see Parked in the plan. The licence file is not touched until he decides. |
| 2026-10-07 | **Who writes code:** Claude writes and saves code. Hermes proposes changes as text and does not upload. | Hermes currently cannot save to GitHub or run containers. Changeable. |
| 2026-10-07 | **Built with:** Python; Streamlit for the chat page; FastAPI for the programmable access; a local model for finding passages; OpenRouter for writing answers | Found in the project. No change proposed. |
| 2026-10-07 | **Another copy exists on the server** that may hold changes not on GitHub | Mohammed, 7 Oct 2026. Must be compared before any code changes here — Phase 1, step 1. |
| 2026-10-07 | **Unsaved work saved:** the in-progress audit was saved exactly as it was (commit `49b8546`, branch `audit/intent-and-injection`) and uploaded to GitHub as a backup | Mohammed approved the upload on 7 Oct 2026. |
| 2026-10-07 | **How the assistants pass work:** through Mohammed's private notes vault — Claude leaves briefs for Hermes in one note, Hermes answers in another. Nothing project-specific is copied there; this project's plan stays in `docs/PLAN.md`. | Both assistants already share that vault; no new access or passwords needed. |
| 2026-10-07 | **Correction — the server copy holds no unsaved changes.** It matches GitHub's main version (`acc0318`). The Mac copy was four saves behind. | Hermes's inventory, checked by Claude against GitHub on 7 Oct 2026. |
| 2026-10-07 | **Correction — where it runs today:** Ana is already live at `ana.mblab.ai`, and that site follows GitHub's main version automatically. Container packaging and an automatic build exist; the live server has not been switched to the container yet. | Hermes's inventory; the address answered when Claude checked. The automatic follow is Hermes's report, not checked by Claude. |
| 2026-10-07 | **Correction — who writes code:** Hermes *can* save to GitHub and did so on 4–5 October. From now on it proposes and Claude saves, by choice, not because it is unable. | The earlier line said "cannot", which was wrong. Hermes confirmed the new arrangement in its notes on 7 Oct 2026. Changeable. |
| 2026-10-07 | **Saving to the main version is a go-live step.** Claude asks Mohammed each time before doing it. | The live site follows the main version and nothing tests it first. |
| 2026-10-12 | **Plan approved.** | Mohammed, 12 Oct 2026, after the assessment. |
| 2026-10-12 | **How Ana is sold:** a product people set up themselves. MBLab, the consultancy, sets it up for those who want help. Reached in steps: first brands set up with help; repeated steps become dashboard screens; public sign-up opens after three brands are live. | Mohammed, 12 Oct 2026. Building sign-up and payments first would delay the first real customer conversation by months. |
| 2026-10-12 | **Who it is for:** any small business. | Mohammed, 12 Oct 2026. Claude noted this is the most crowded position; the page leads with Arabic and English, a demo to try, a real hand-off, and help with set-up. |
| 2026-10-12 | **Ana and MBLab are separate projects.** This one holds the engine and the fictional demo. The marketing page is its own project. Real client folders go in a private project (not yet created). | Mohammed, 12 Oct 2026: Ana is a product, MBLab a consultancy. |
| 2026-10-12 | **Reference sites for look, wording and pricing structure:** two sites Mohammed chose, recorded in his private notes, not here. Ana keeps its own colours. | Mohammed, 12 Oct 2026. |
