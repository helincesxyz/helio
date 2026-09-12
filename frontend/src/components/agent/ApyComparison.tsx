import { formatPct } from "../../lib/format";
import { TechnicalDrawer } from "../decision/TechnicalDrawer";

interface Offer {
  product?: string;
  ccy?: string;
  apy?: number;
  term?: string;
}

/**
 * Renders the `apy_comparison` conversation-response kind — real current
 * OKX Earn offers, discovery only. This never renders a subscribe/redeem
 * action; there is no such call anywhere in the conversation bridge for
 * this intent (see docs/runbooks/conversation_fulfillment.md).
 */
export function ApyComparison({ comparison }: { comparison: Record<string, unknown> }) {
  const offers = (comparison.offers as Offer[] | undefined) ?? [];

  return (
    <div className="space-y-4">
      <p className="text-base leading-relaxed text-ink">
        Real current OKX Earn offers — this is discovery only, Helio hasn't subscribed you to anything.
      </p>
      {offers.length > 0 ? (
        <div className="flex flex-col gap-2">
          {offers.map((offer, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-xl border border-border bg-bg-glass px-4 py-3"
            >
              <div>
                <p className="text-sm text-ink">{offer.product ?? offer.ccy ?? "Offer"}</p>
                {offer.term && <p className="text-xs text-ink-faint">{offer.term}</p>}
              </div>
              {offer.apy !== undefined && (
                <p className="text-sm font-semibold text-positive">{formatPct(offer.apy * 100)} APY</p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-ink-muted">No matching offers found for your risk setting right now.</p>
      )}
      <TechnicalDrawer data={comparison} />
    </div>
  );
}
