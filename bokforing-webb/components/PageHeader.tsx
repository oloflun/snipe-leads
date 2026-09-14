/**
 * Sidhuvudet varje flik delar: rubrik i Fraunces, en rad som säger vad sidan
 * gör, och plats för åtgärder till höger (periodväljare, knappar).
 */
export function PageHeader({
  rubrik,
  beskrivning,
  actions
}: Readonly<{ rubrik: string; beskrivning?: string; actions?: React.ReactNode }>) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4 border-b border-ink/15 pb-5">
      <div className="min-w-0">
        <h1 className="font-display tighten text-[1.75rem] leading-tight text-ink">{rubrik}</h1>
        {beskrivning ? (
          <p className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink/60">{beskrivning}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-end gap-2">{actions}</div> : null}
    </header>
  );
}
