import { useState, type FormEvent } from "react";

export function CommandBox({
  onSubmit,
  placeholder = "Ask Helio about the market or give it a trading objective...",
  autoFocus,
}: {
  onSubmit: (text: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
}) {
  const [value, setValue] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const text = value.trim();
    if (!text) return;
    onSubmit(text);
    setValue("");
  };

  return (
    <form
      onSubmit={submit}
      className="w-full rounded-3xl border border-border bg-bg-glass p-5 backdrop-blur-xl transition-colors focus-within:border-border-strong"
    >
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            submit(e);
          }
        }}
        placeholder={placeholder}
        autoFocus={autoFocus}
        autoComplete="off"
        spellCheck={false}
        data-gramm="false"
        rows={2}
        className="w-full resize-none bg-transparent text-base text-ink placeholder:text-ink-faint focus:outline-none"
      />
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-border px-3 py-1 text-xs text-ink-muted">BTC-USDT</span>
          <span className="rounded-full border border-border px-3 py-1 text-xs text-ink-muted">Simulation</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-ink-faint">Trend Breakout v1</span>
          <button
            type="submit"
            aria-label="Send"
            className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-white transition-transform hover:scale-105 active:scale-95"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 13V3M8 3L3.5 7.5M8 3L12.5 7.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>
    </form>
  );
}
