import { EmptyState } from "../../components/common/EmptyState";

const COLUMNS = ["Date", "Asset", "Side", "Entry", "Exit", "Result", "Return", "P&L", "Fees"];

export function Trades() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-9 gap-4 border-b border-border pb-3 opacity-30">
        {COLUMNS.map((col) => (
          <p key={col} className="text-xs uppercase tracking-wide text-ink-muted">
            {col}
          </p>
        ))}
      </div>
      <EmptyState title="No live trades yet." />
    </div>
  );
}
