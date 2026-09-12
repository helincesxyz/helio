export function TechnicalDrawer({ data }: { data: unknown }) {
  return (
    <details className="group rounded-2xl border border-border">
      <summary className="cursor-pointer list-none px-4 py-3 text-xs text-ink-muted hover:text-ink">
        Technical detail (raw JSON)
      </summary>
      <pre className="max-h-96 overflow-auto border-t border-border px-4 py-3 text-xs text-ink-faint">
        {JSON.stringify(data, null, 2)}
      </pre>
    </details>
  );
}
