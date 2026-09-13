/**
 * Litet märke bredvid ett kundnamn: "Testarbetsyta", "Inaktiv".
 *
 * Samma form som Exempel-märket i Portfoljvy och Kundtabell — hairline och
 * mineral, inte ochre. Accenten i adminytan är reserverad för avvikelser man
 * ska agera på, och en testarbetsyta är inte en avvikelse utan ett faktum om
 * raden. Syns tydligt, ropar inte.
 */
export function Radmarke({
  children,
  title
}: Readonly<{ children: React.ReactNode; title?: string }>) {
  return (
    <span
      title={title}
      className="shrink-0 rounded-[3px] border border-ink/20 px-1.5 py-px font-mono text-[10px] uppercase tracking-[0.14em] text-mineral"
    >
      {children}
    </span>
  );
}
