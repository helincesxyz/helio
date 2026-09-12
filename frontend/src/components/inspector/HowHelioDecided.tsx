import { useEffect, useState } from "react";
import { getExecutions, type ExecutionLifecycle, type GuardRecord, type ThesisRecord } from "../../api/client";
import { useHelioData } from "../../context/HelioDataContext";
import { formatBtcQuantity, formatRelativeTime, formatUsd, titleCase } from "../../lib/format";

function equity(balances: { ccy: string; total: string }[]): number {
  return balances
    .filter((b) => ["USD", "USDT", "USDC"].includes(b.ccy.toUpperCase()))
    .reduce((sum, b) => sum + parseFloat(b.total), 0);
}

interface Step {
  n: string;
  title: string;
  lines: string[];
  source: string;
  disabled?: boolean;
}

export function HowHelioDecided({ record, guardRecord }: { record: ThesisRecord; guardRecord: GuardRecord | null }) {
  const { account } = useHelioData();
  const { thesis, prepared_state } = record;
  const [execution, setExecution] = useState<ExecutionLifecycle | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    setExecution(undefined);
    getExecutions(record.decision_id)
      .then((rows) => {
        if (!cancelled) setExecution(rows[0] ?? null);
      })
      .catch(() => {
        if (!cancelled) setExecution(null);
      });
    return () => {
      cancelled = true;
    };
  }, [record.decision_id]);

  const executionStep: Step =
    execution === undefined
      ? { n: "06", title: "Execution", lines: ["Checking..."], source: "GATE 4 — ACT" }
      : execution === null
        ? { n: "06", title: "Execution", lines: ["No execution attempted"], source: "GATE 4 — ACT", disabled: true }
        : {
            n: "06",
            title: "Execution",
            lines: [
              `${execution.status ?? "AUTHORIZED"} (${execution.mode ?? "not yet prepared"})`,
              execution.origin === "execution_test" ? "Test run" : "Done automatically",
            ],
            source: "GATE 4 — ACT",
          };

  const verificationStep: Step =
    execution === undefined
      ? { n: "07", title: "Verification", lines: ["Checking..."], source: "GATE 4 — ACT" }
      : execution?.verified_at
        ? {
            n: "07",
            title: "Verification",
            lines: [
              execution.okx_order_id ? `Order ${execution.okx_order_id}` : "No order id",
              execution.filled_quantity ? `Filled ${formatBtcQuantity(execution.filled_quantity)} BTC` : "Not filled",
            ],
            source: "GATE 4 — ACT",
          }
        : { n: "07", title: "Verification", lines: ["Not verified yet"], source: "GATE 4 — ACT", disabled: true };

  const steps: Step[] = [
    {
      n: "01",
      title: "Account",
      lines: [account ? `${formatUsd(equity(account.balances))} available` : "Account not verified"],
      source: "via OKX",
    },
    {
      n: "02",
      title: "Market",
      lines: [
        `${record.thesis.symbol} · $${Number(prepared_state.tf_15m.price).toLocaleString()}`,
        formatRelativeTime(prepared_state.prepared_at),
      ],
      source: "via OKX MCP / Agent Trade Kit",
    },
    {
      n: "03",
      title: "Strategy",
      lines: [`${titleCase(thesis.strategy)} ${thesis.strategy_version}`],
      source: "deterministic evaluator",
    },
    {
      n: "04",
      title: "Decision",
      lines: [thesis.action, `${Math.round(thesis.confidence * 100)}%`],
      source: "GATE 2 — THINK",
    },
    {
      n: "05",
      title: "Risk",
      lines: guardRecord
        ? [guardRecord.decision.decision, `${guardRecord.decision.checks.filter((c) => c.status === "PASS").length}/${guardRecord.decision.checks.length} checks`]
        : ["No execution proposed", "Deterministic guard — not engaged"],
      source: "GATE 3 — PROTECT",
    },
    executionStep,
    verificationStep,
  ];

  return (
    <div className="flex flex-col gap-4" data-testid="how-helio-decided">
      {steps.map((step) => (
        <div key={step.n} className={`flex items-start gap-4 ${step.disabled ? "opacity-40" : ""}`}>
          <span className="w-6 shrink-0 pt-0.5 font-mono text-xs text-ink-faint">{step.n}</span>
          <div>
            <p className="text-sm font-medium text-ink">{step.title}</p>
            {step.lines.map((line, i) => (
              <p key={i} className="text-sm text-ink-muted">
                {line}
              </p>
            ))}
            <p className="text-xs text-ink-faint">{step.source}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
