# Configuring OKX Access

Helio itself never configures, reads, or stores OKX credentials — that is
entirely the job of the **OKX Agent Trade Kit**, which runs as a local MCP
server that Claude Code calls into. Follow the Trade Kit's own, current
documentation to:

1. Install the OKX Agent Trade Kit / its MCP server.
2. Connect your OKX account through its official local credential flow
   (typically an interactive step where you provide your OKX API key,
   secret, and passphrase directly into the Trade Kit's own local storage —
   never into Helio, a prompt, or a Helio config file).
3. Confirm the MCP server starts and is registered with Claude Code.

Do **not**:

- Put OKX credentials in `.env`, `.env.example`, or any Helio config file.
- Ask an LLM to read, paste, or repeat your OKX credentials.
- Point Helio at `~/.okx/config.toml` or any other Trade Kit credential
  path — Helio has no code that reads such a file, on purpose.

## How Helio checks the connection

Helio's own connectivity check is: ask Claude Code to call
`mcp__okx-agent-trade-kit__system_get_capabilities` and confirm the response
reports `hasAuth: true`. That's it — there's no separate Helio-side auth
check, because Helio has no separate auth of its own. See
[AGENT_PROTOCOL.md](AGENT_PROTOCOL.md) and
[VERIFICATION_PROTOCOL.md](VERIFICATION_PROTOCOL.md).

## Funding the demo/simulated account

OKX's simulated-trading (`simulatedTrading: true`) account is a separate
virtual account from your live one and starts **unfunded**. If
`spot_place_order` (or any order call) fails with `sCode 51008`
("insufficient balance"), it means the demo account has no virtual funds yet
— this is expected on a fresh setup, not a Helio bug. Fund it with virtual
balance from OKX's own demo-trading dashboard before running
[docs/runbooks/verify.md](runbooks/verify.md)'s SPOT EXECUTION step or
[docs/runbooks/simulate_trade.md](runbooks/simulate_trade.md).

## Simulation vs. live

The Trade Kit's tools generally accept a `simulatedTrading` boolean per call.
Helio's own `HELIO_MODE` setting (`simulation` by default) should always
match the `simulatedTrading` value Claude Code passes, and `risk_config.yaml`'s
`allow_live: false` is the hard gate that keeps a `mode="live"` intent from
ever being approved until you explicitly opt in. See the README's "Enable
live trading" section before ever flipping that on.
