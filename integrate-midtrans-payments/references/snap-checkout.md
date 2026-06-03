# Snap Checkout Playbook

Use this when the merchant asks for Snap-only checkout, hosted checkout, Snap popup/redirect/embed, Snap token creation, Snap status polling, or Snap webhook debugging.

Always refresh current docs from `https://docs.midtrans.com/llms.txt`, especially Snap Integration Guide, Snap JS, request body parameters, advanced features, notifications, status cycle, sandbox testing, and switching to production. For concrete sandbox smoke commands and webhook replay, use [sandbox-interaction-helper.md](sandbox-interaction-helper.md).

Before building Snap code, complete [merchant-readiness-preflight.md](merchant-readiness-preflight.md). At minimum confirm account/MID state, sandbox keys, Snap method activation, display mode, dashboard notification URL, redirect URLs, and whether the expected flow is cart checkout, invoice collection, or another payment surface.

## Product Fit

Use Snap when the merchant accepts Midtrans-hosted payment UI, wants the fastest integration, wants card data off merchant servers, or wants broad payment method coverage without custom method UI.

Snap has two common checkout strategies:

- **Snap as the full payment page**: omit `enabled_payments`; Snap shows all active methods.
- **Merchant checkout + Snap method screen**: merchant collects cart/address/method, backend creates a Snap token with one or a few `enabled_payments` values, and frontend opens Snap for that selection.

## Backend Token Creation

Server-side only:

- Sandbox transaction endpoint: `https://app.sandbox.midtrans.com/snap/v1/transactions`
- Production transaction endpoint: `https://app.midtrans.com/snap/v1/transactions`
- Auth: `Authorization: Basic base64(serverKey + ":")`
- Keep server key only on the backend. Client key is for Snap JS.

Token request checks:

- `transaction_details.order_id` must be unique per transaction attempt.
- `transaction_details.gross_amount` is an integer IDR amount for Snap requests.
- If `item_details` is included, net item total must equal `gross_amount`; negative-price items can represent discounts if docs allow the use case.
- Use `enabled_payments` only when the merchant intentionally restricts payment methods.
- Include customer details when available, but do not collect/store unnecessary PII.
- Set expiry intentionally for async methods. `expiry` controls payment-method expiry; `page_expiry` controls Snap page/token lifetime.
- Consider a per-transaction `notification_url` only when the project needs route-specific callback handling; otherwise use dashboard Payment Notification URL.

## Frontend Display Modes

Display modes share the same backend token:

- Popup: load `snap.js`, call `window.snap.pay(token, callbacks)`.
- Redirect: send the customer to `redirect_url`.
- Embedded: call `window.snap.embed(token, { embedId, ...callbacks })`.

Use sandbox Snap JS in development and production Snap JS in production. Frontend callbacks are UX hints only:

- `onSuccess`: show success/pending UI, then verify server-side.
- `onPending`: show awaiting payment and recovery link.
- `onError`: show retry path.
- `onClose`: preserve recoverable order/token state; do not assume cancellation.

Gotchas:

- `uiMode: "deeplink"` or `"qr"` can influence e-wallet display in popup/embed flows, but linked GoPay tokenization can override this behavior.
- Redirect flows may use query parameters for GoPay deeplink behavior; verify current docs before relying on this.
- `window.snap.hide()` can close a popup programmatically, but local cancellation still needs provider/state reconciliation.
- Reusing the same Snap token can reopen an unpaid Snap page while the token is valid; once a payment attempt creates a transaction, retry semantics change.

## Webhook And Status Handling

Do not fulfill from Snap JS callbacks. Fulfillment requires verified notification and/or server-side status lookup.

Classic notification signature:

```text
SHA512(order_id + status_code + gross_amount + serverKey)
```

Use the raw `gross_amount` string from the notification payload. Do not parse and reformat it before hashing.

Status rules:

- `settlement`: paid.
- `capture`: paid only when fraud status is accepted; challenge usually remains pending.
- `pending`: awaiting payment.
- `deny`, `cancel`, `expire`, `failure`: failed/cancelled/expired according to project terminology.
- `refund`, `partial_refund`: refunded or partially refunded.

Guardrails:

- Notifications can be duplicated; processing must be idempotent.
- One Snap session/order can produce multiple deny/failure attempts before a final successful payment. Do not regress paid/fulfilled states.
- Get Status can return not found before the customer selects/confirms a method. Treat this as "not attempted yet", not a fatal order failure.
- Desktop GoPay/ShopeePay QR flows can appear as QRIS-related payment types while mobile deeplink flows can appear as e-wallet types. Reconcile by transaction status and order id, not display label alone.
- Snap session cancel/expire and Core API transaction cancel/expire are different. Use session endpoints before method selection; use transaction endpoints after a transaction exists.

## Snap Production Checklist

- Sandbox and production server/client keys are separated.
- Production dashboard methods are activated for every `enabled_payments` value.
- Production Payment Notification URL is public HTTPS and returns 2xx without redirects.
- Finish/unfinish/error redirects are UX redirects, not fulfillment signals.
- Signature verification uses the production server key in production.
- GoPay deeplink and QR behavior are tested on relevant desktop/mobile/iOS/Android paths.
- Order retry creates a new provider order id when required and keeps local order linkage clear.
