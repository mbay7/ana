# Corpus — Haven & Hearth (fictional UK retailer)

This corpus powers the "Haven & Hearth" shop-assistant RAG: a customer-support
assistant that answers questions about a fictional UK homeware & lifestyle
retailer (HQ London, ships UK + selected EU destinations).

## Why fictional
A fictional store avoids scraping a real retailer's help pages (terms-of-service
and copyright risk) while letting us deliberately embed the *edge cases* that
make retrieval and evaluation genuinely hard.

## Files
| File | Role |
|------|------|
| `shipping-policy.md` | UK standard, UK furniture, EU delivery + DDU customs |
| `returns-policy.md` | 30-day vs 14-day statutory, faulty vs change-of-mind, final-sale, seasonal |
| `payments-policy.md` | methods, charge timing, Klarna, declined payments, gift cards |
| `accounts-privacy.md` | guest checkout, account closure, GDPR, retention, security |
| `order-tracking.md` | statuses, tracking timing, EU economy no-tracking, lost parcels |
| `product-guide.md` | furniture, personalised, seasonal, hygiene-sealed, electricals |
| `faq.md` | 26 paraphrased Q&A pairs spanning every policy above |

## Deliberate edge cases (what makes retrieval hard)
1. **14-day vs 30-day:** statutory cancellation (full refund incl. delivery) vs
   the store's change-of-mind window (customer pays postage) — a model must
   pick the right window for the right scenario.
2. **Final-sale exclusions** scattered across `returns-policy.md` and
   `product-guide.md` (personalised, hygiene-sealed, seasonal after cut-offs).
3. **EU vs UK shipping:** different carriers, thresholds (£50 UK vs £120 EU),
   and delivery-duty-unpaid customs for the EU.
4. **Faulty vs change-of-mind:** a faulty item returns free; a change-of-mind
   item does not.
5. **Pre-order charge timing** and **gift-card non-refundability** buried in the
   payments policy.

All distinct facts are placed in exactly one file (no duplication), so retrieval
must find the *right* source, and "I don't know" is a real, testable outcome.