const PROMPTS = ["BTC breakout", "Explain the market", "Trade conservatively", "What are you waiting for?"];

export function SuggestedPrompts({ onSelect }: { onSelect: (prompt: string) => void }) {
  return (
    <div className="mt-6 flex flex-wrap justify-center gap-2">
      {PROMPTS.map((prompt) => (
        <button
          key={prompt}
          onClick={() => onSelect(prompt)}
          className="rounded-full border border-border bg-bg-glass px-4 py-2 text-sm text-ink-muted transition-colors hover:border-border-strong hover:text-ink"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}
