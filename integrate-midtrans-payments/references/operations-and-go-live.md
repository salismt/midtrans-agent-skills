# Operations And Go-Live

Use this for sandbox testing, live cutover, callback setup, observability, secret management, and production readiness for any Midtrans product path.

Refresh current Midtrans product/API details from `https://docs.midtrans.com/llms.txt` before sandbox or live cutover work.

## Environment And Secrets

Keep sandbox and production isolated:

- server key/client key for Snap/Core,
- BI-SNAP client id, partner id, channel id, client secret, private/public keys,
- merchant ids/handles,
- callback/redirect base URLs,
- product feature flags and activation gates.

Every required runtime variable should be represented in:

- example env file,
- typed env validation or startup validation,
- deployment/secret manager wiring,
- CI drift checks when the project has them,
- operator handoff docs.

Fail fast on missing production secrets. Avoid silent fallback from production to sandbox values.

## Callback URLs

Dashboard/server-to-server notification URLs must be:

- public internet reachable,
- HTTPS in production,
- not localhost,
- not behind auth, VPN, IP blocks, or unusual ports unless Midtrans explicitly supports it,
- not redirecting through 301/302/303 before the handler,
- returning provider-expected 2xx only after verification/acceptance.

Keep these concepts separate:

- payment notification URL: server-to-server state updates,
- recurring/account-linking notification URLs: product-specific callbacks,
- finish/unfinish/error redirects: customer browser UX,
- GoPay/tokenization return URL: browser return and state validation.

## Structured Logging

Log enough to debug without leaking secrets:

- route/action,
- order id,
- merchant/provider order id,
- provider reference,
- payment method,
- provider,
- status/result,
- response code,
- request id/correlation id,
- latency,
- safe error code/message.

Redact:

- server key,
- client secret,
- private key,
- access token,
- customer authorization token,
- auth code,
- payment option token,
- signatures,
- cookies/session tokens,
- full unrestricted customer PII,
- full unrestricted provider payloads.

## Sandbox Smoke

Use [sandbox-interaction-helper.md](sandbox-interaction-helper.md) when the merchant wants concrete commands, webhook replay fixtures, BI-SNAP signing dry-runs, status polling, or a copy-safe sandbox evidence report.

For every enabled method:

1. Create a sandbox transaction.
2. Confirm customer-facing instruction/recovery page after refresh.
3. Complete or simulate payment in sandbox.
4. Verify notification updates local state exactly once.
5. Replay the notification and confirm idempotency.
6. Poll status and confirm mapping matches local state.
7. Test expiry/cancel/retry behavior.

For Snap:

- test popup/redirect/embed path chosen by merchant,
- test Get Status before method selection,
- test GoPay QR/deeplink paths if enabled,
- test duplicate/failure attempts within one Snap session.

For BI-SNAP:

- test access-token refresh,
- test signature failure handling,
- test each callback type,
- test stale callback after paid,
- test disabled/unactivated method gating.

For GoPay tokenization:

- test link, return, binding, inquiry, linked payment, unlink,
- test missing/changed payment option token,
- test PayLater unavailable path.

## Go-Live Checklist

- Production credentials installed and sandbox credentials removed from production.
- Production callback URLs configured in Midtrans dashboard.
- Payment methods activated in production account.
- Feature flags match activation state.
- Logs visible in production runtime.
- Alerting or dashboard exists for provider 4xx/5xx and webhook failures.
- Refund/cancel/manual reconciliation runbook exists if those actions are supported.
- First live transaction is monitored end-to-end with order id and provider reference.
- Any final live transaction test is explicitly approved by the merchant and is not presented as a normal sandbox smoke.
