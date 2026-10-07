# Brief — Ana

_Agreed: (filled in when the plan is approved)_

## What it is
Ana is a chat assistant that answers a brand's customers from that brand's own documents, in the brand's voice. One engine serves many brands: each brand is a folder of its content, and the engine does not change between them.

## Who it is for
- **Now:** Mohammed, as a public proof-of-work project on GitHub with a demo link anyone can open.
- **Also:** paying clients, each with their own private copy. A first client is being set up; their name and content stay outside this public project. Ana sits under the mblab.ai brand.

## In scope
What this round of work delivers — finishing what exists, not adding to it:

- Answers questions from a brand's documents, and says "I don't know" when the documents don't cover it.
- Works for more than one brand without code changes (English and Arabic demos included).
- A public demo link, locked to the fictional demo brand.
- Packaged so it can be moved to a server or a client's setup later without rework.
- A recorded quality score that is checked automatically on every change.

## Not doing
_Proposed by Claude from the existing roadmap — confirm or change at approval._

- No new features in this round. Everything on the old roadmap's "Next" list is parked.
- No taking actions on a customer's behalf (refunds, returns, order changes).
- No WhatsApp or other new channels.
- No real client's content or name in the public project.
- No rewrite of how Ana decides what a message means. The phrase-by-phrase rules are frozen as they are.

## Finished means
_Found in the project, not asked — these checks already exist._

1. All automated tests pass — the 8 on the main version (6 pass today) plus the 36 the audit work adds.
2. The quality check finds the right passage in the top five for at least 47 of the 50 answerable test questions — the score recorded on 30 September 2026 — and fails loudly if it drops below that.
3. A stranger can start Ana from the README in three commands.
4. The demo link answers a demo-brand question from a phone, and refuses a request with the wrong access token.
5. Mohammed asks ten plain questions himself, including in Arabic, and ticks each one.
