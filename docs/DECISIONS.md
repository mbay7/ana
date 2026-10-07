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
