# Merchant Decision Tree

Use this first when the merchant's target product or payment scope is unclear. Do not force any one merchant's prior provider split onto the next merchant; use observed splits as learned patterns, not universal requirements.

Refresh current Midtrans product/API details from `https://docs.midtrans.com/llms.txt` before final product routing.

Complete [merchant-readiness-preflight.md](merchant-readiness-preflight.md) before final product routing. Product fit depends on merchant account state, active methods, dashboard access, and expected proof level, not only on API shape.

## First Questions

Ask or infer:

- Does the merchant already have a Midtrans account/MID and sandbox dashboard access?
- Are sandbox credentials available through env/secrets, and are production credentials intentionally out of test paths?
- Does the merchant accept a Midtrans-hosted payment UI?
- Does the merchant need an app-owned checkout UI for each payment method?
- Which methods are required now: card, OTC, VA, QRIS, GoPay, ShopeePay, DANA, GoPay tokenization, GoPayLater, recurring, refunds?
- Is this web, mobile web, native app, POS/IoT, MiniApp, marketplace, or no-code collection?
- Does the merchant already have Midtrans activation for the requested methods?
- Does the app already have orders, users, payment state, webhooks, logs, and env/secret management?
- What customer flow is being implemented: cart checkout, locked invoice payment, renewal, deposit, marketplace order, or manual collection?
- What proof is expected in this session: design review, local deterministic checks, sandbox provider smoke, or production penny test?

## Route The Request

| Need | Recommend | Why |
| --- | --- | --- |
| Fastest checkout, hosted UI is fine | Snap | Midtrans owns payment UI, PCI-sensitive card UI, and method-specific screens. |
| Own checkout selects method, but hosted method screen is acceptable | Snap with `enabled_payments` | Merchant keeps a unified checkout while Snap handles the selected method flow. |
| No app or invoice/chat collection | Payment Link | Avoid building checkout code when a shareable link is enough. |
| Fully custom QRIS, VA, e-wallet, or SNAP-standard payment APIs | BI-SNAP | Merchant owns UI and must handle access tokens, signatures, callbacks, and status reconciliation. |
| GoPay tokenized wallet or GoPayLater | BI-SNAP tokenization | Requires account linking, Binding Inquiry, stored customer authorization token, and payment option tokens. |
| Custom card UI | Core API | Requires stricter card, PCI, and 3DS decisions. Prefer Snap unless custom card UX is a real requirement. |
| GoPay MiniApp container | MiniApp docs plus BI-SNAP payment docs | Different runtime and UX constraints from normal web checkout. |

## Hybrid Is Often Correct

A merchant can combine products if the ownership is explicit. One real merchant uses Snap for card/OTC and BI-SNAP for QRIS, VA, GoPay, and GoPayLater. Another merchant might use Snap for every method, or BI-SNAP only for QRIS and VA. The skill should help the agent choose and document a product owner per method.

## Decision Output

Before implementing, state:

- selected product per payment method,
- why each product fits the merchant need,
- activation/dashboard assumptions,
- account/sandbox readiness and any missing merchant answers,
- callback URLs required,
- server-side secrets required,
- local state needed to resume pending payments,
- tests and sandbox smoke needed before go-live.
