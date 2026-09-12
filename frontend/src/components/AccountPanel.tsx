import type { AccountState } from "../types";

export function AccountPanel({ account }: { account: AccountState | null }) {
  if (!account) {
    return <p data-testid="account-panel-empty">No account state posted yet.</p>;
  }

  return (
    <div data-testid="account-panel">
      <h3>Balances</h3>
      <ul>
        {account.balances.map((b) => (
          <li key={b.ccy}>
            {b.ccy}: {b.avail} avail / {b.total} total
          </li>
        ))}
      </ul>
      <h3>Positions</h3>
      <ul>
        {account.positions.map((p) => (
          <li key={p.instId}>
            {p.instId} {p.posSide} {p.pos} @ {p.avgPx} (uPL {p.upl})
          </li>
        ))}
      </ul>
    </div>
  );
}
