# Security Policy

## Core rule

**Never commit OKX API credentials or local Trade Kit credential files.**

This includes, but is not limited to:

- OKX API key, secret key, or passphrase
- The OKX Agent Trade Kit's local credential store (e.g. any `~/.okx/` config file)
- Private keys or wallet seeds
- Session tokens or auth tokens for any connected service
- Any `.env` file containing real values (only `.env.example` with placeholders belongs in the repo)

## Why Helio is safe by design

Helio's own code (`backend/src/helio/`) never makes a network call to OKX and never
parses or reads any Trade Kit credential file. All OKX interaction — market data,
account state, and order placement — is performed exclusively by the Claude Code
agent process calling the OKX Agent Trade Kit's MCP tools. Helio only receives
already-fetched, non-secret JSON (prices, balances, order confirmations) over a
`127.0.0.1`-only local API. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/AGENT_PROTOCOL.md](docs/AGENT_PROTOCOL.md) for the full data flow.

As defense in depth:

- Every Helio API request schema uses `extra="forbid"`, so a field shaped like
  `apiKey`, `secretKey`, `passphrase`, `privateKey`, or `seed` is rejected at
  the boundary rather than silently accepted or stored.
- Helio's logger applies a redaction filter to any secret-shaped string before
  it is written out, even though no legitimate code path should ever produce one.
- The FastAPI service binds to `127.0.0.1` only — it is never exposed to the network.

## Reporting a vulnerability

If you find a security issue (including any path by which Helio could be made to
touch, log, or leak a credential), please open a private security advisory on the
repository (GitHub → Security → Report a vulnerability) rather than a public issue.
Include reproduction steps and the affected file(s). We'll acknowledge reports as
promptly as we can and coordinate a fix before public disclosure.

## Live trading safety

Helio ships in `simulation` mode by default. Enabling live trading requires an
explicit, deliberate two-step opt-in (`HELIO_MODE=live` **and** `allow_live: true`
in your risk config) — see the README's "Enable live trading" section. Treat live
mode as production: review your risk limits before flipping it on.
