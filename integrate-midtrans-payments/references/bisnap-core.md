# BI-SNAP Core Playbook

Use this when the merchant asks for BI-SNAP, SNAP-standard Core API, QRIS MPM, virtual account, one-time Direct Debit, custom payment UI, BI-SNAP signatures, BI-SNAP notifications, or BI-SNAP status reconciliation.

Always refresh current docs from `https://docs.midtrans.com/llms.txt`, especially BI-SNAP security architecture, signature generation, access token, QRIS MPM, Direct Debit, virtual account, notification setup, status APIs, and sandbox testing. For concrete sandbox smoke, signing dry-runs, status polling, and webhook replay, use [sandbox-interaction-helper.md](sandbox-interaction-helper.md).

## Contents

- Product Fit
- Required Project Boundaries
- Credentials And Environment
- Hosts
- Signing Model
- Payment Method Playbooks (QRIS MPM, Virtual Account, One-Time Direct Debit)
- Notifications
- Status Mapping

## Product Fit

Use BI-SNAP when the merchant needs app-owned payment UI and is ready to own:

- B2B access token retrieval and caching,
- asymmetric and symmetric signatures,
- product-specific request payloads,
- one or more public notification URLs,
- status mapping and reconciliation,
- sandbox/live credential and certificate/key lifecycle.

If the merchant only wants a hosted payment page, prefer Snap.

## Required Project Boundaries

Keep these concerns separate:

- Route/controller: auth, input validation, HTTP response.
- Domain/use-case: payment method routing, order state transitions, idempotency.
- Provider client: BI-SNAP headers, signing, fetch/SDK transport, provider payloads.
- Repository/model: payment/order persistence only.
- UI: method selection, instructions, redirect/open actions, status display.

Do not put BI-SNAP private keys, client secrets, access tokens, or `Authorization-Customer` values in browser code.

## Credentials And Environment

Exact names differ by merchant, but the integration usually needs:

- client id/client key,
- partner id,
- channel id,
- client secret,
- private key for access-token signing,
- Midtrans public key for notification verification when applicable,
- merchant id,
- product-specific merchant handles or service ids,
- sandbox/production base URL switch.

Wire new env vars through every environment surface: example env, typed validation, deployment secrets, CI/drift tests, and operator docs.

## Hosts

Two distinct hosts are used by BI-SNAP. Verify against current docs because Midtrans can introduce regional or product-specific variants:

| Use | Sandbox | Production |
| --- | --- | --- |
| Transactional BI-SNAP APIs (access-token, QRIS, VA, Direct Debit, status, binding, inquiry, unbind) | `https://merchants.sbx.midtrans.com` | `https://merchants.midtrans.com` |
| GoPay Get Auth Code (account linking only) | `https://merchants-app.sbx.midtrans.com` | `https://merchants-app.midtrans.com` |

The `merchants-app` host is only for the Get Auth Code redirect step. Binding, inquiry, unbind, and tokenized Direct Debit return to the regular `merchants` host.

## Signing Model

Keep signature helpers separate:

- **Access token**: asymmetric signing for B2B token request.
- **Transaction request**: HMAC signing over method, endpoint path, access token, request body hash, timestamp, and secret per current docs.
- **Notification**: verify incoming provider signatures with the appropriate public key or product-specific verification rule.

Practical signing rules:

- Generate timestamps in the required ISO-8601 format and timezone (Asia/Jakarta, e.g., `2026-05-27T14:30:00+07:00`). Do not rely on the local machine timezone.
- Serialize the JSON body once, hash that exact byte string with lowercase-hex SHA-256, sign, and send the same byte string as the request body.
- Do not let HTTP clients reformat (re-serialize, re-order keys, change spacing) a signed body after signature generation.
- Cache B2B access tokens with an expiry buffer and handle refresh races.
- Per current docs, the transactional string-to-sign is typically `${method}:${endpointPath}:${accessToken}:${bodyHashHex}:${timestamp}` and is signed with HMAC-SHA512 keyed on `clientSecret`, base64-encoded. The notification signature is RSA verified over `POST:${endpointPath}:${bodyHashHex}:${timestamp}` using the Midtrans public key. Confirm exact format against the current Midtrans docs before shipping.

## Payment Method Playbooks

### QRIS MPM

- Create payment server-side.
- Persist provider reference, QR content or QR image URL, expiry, amount, and method.
- Render QR/instructions from persisted payment state.
- Poll or reconcile via status API while waiting for notification.

### Virtual Account

- Build bank-specific VA payloads from current docs.
- Persist VA number, bank, expiry, provider reference, and amount.
- Show a recovery page for pending payments.
- Reconcile expiry locally and with provider status.

**`partnerServiceId` formatting gotcha**: the field must be exactly 8 characters in the create-VA payload. Numeric service ids shorter than 8 digits must be **left-padded with spaces** to 8 characters (e.g., `"   12345"`). Sending the raw, unpadded value returns a 400 with a non-obvious validation error. Centralize the padding logic in the provider client, not in callers.

**`customerNo` and `virtualAccountNo` relationship**: `virtualAccountNo` is typically `partnerServiceId + customerNo`. Status callbacks may report `partnerServiceId`, `customerNo`, and `virtualAccountNo` separately; reconciliation should join on `trxId` (the order id) as the primary key, not the VA number.

### One-Time Direct Debit

- Do not confuse one-time GoPay/ShopeePay/DANA Direct Debit with GoPay tokenized wallet.
- Persist redirect/deeplink URL, provider reference, expiry, and status payload.
- Treat frontend return as a UX hint; verify via status/notification.

**Header contrast with tokenized Direct Debit**:

| Header | One-time Direct Debit | Tokenized GoPay Direct Debit |
| --- | --- | --- |
| `Authorization: Bearer <accessToken>` | ✓ | ✓ |
| `X-SIGNATURE` (transactional HMAC) | ✓ | ✓ |
| `Authorization-Customer: Bearer <customer_authorization_token>` | ✗ must be absent | ✓ required |
| `chargeToken` field in body | access token | customer authorization token |

Sending `Authorization-Customer` on a one-time charge or omitting it on a tokenized charge causes the provider to reject the request. See [gopay-tokenization.md](gopay-tokenization.md) for the tokenized flow.

## Notifications

Dashboard constraints can require one BI-SNAP URL. Prefer a single public dispatcher route when the dashboard offers one field, then route internally by payload/type.

Notification handling must:

- read raw body where signature verification needs it,
- verify authenticity before mutation,
- log safe business identifiers,
- persist enough receipt data for audit/replay if useful,
- be idempotent,
- return the provider-expected 2xx response only after accepting or safely recording the callback.

## Status Mapping

Do not copy a status map blindly across products. For each method, load the current status docs and define:

- provider status/code,
- local status,
- terminal/non-terminal behavior,
- allowed regressions,
- ignored stale updates,
- refund/partial refund handling.

Production-learned rule: do not allow late pending/cancelled provider updates to overwrite paid, fulfilled, shipped, delivered, or refunded local states unless the provider event is a valid refund/chargeback transition.
