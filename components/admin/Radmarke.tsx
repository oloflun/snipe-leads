import { Badge } from "@/components/ui";

/**
 * Märke bredvid ett kundnamn: "Testarbetsyta", "Inaktiv", "Exempel".
 *
 * En neutral `Badge` och inget eget märke. Tills 2026-09-27 var det spärrad
 * mono i 10 px, alltså samma viskande kicker som F-016 tog bort från
 * appytorna. Tonen är neutral och inte ochre: accenten i adminytan är
 * reserverad för avvikelser man ska agera på, och en testarbetsyta är inte en
 * avvikelse utan ett faktum om raden.
 *
 * `title` bärs av ett omslag eftersom `Badge` inte tar attributet.
 */
export function Radmarke({
  children,
  title
}: Readonly<{ children: React.ReactNode; title?: string }>) {
  return (
    <span title={title} className="shrink-0">
      <Badge>{children}</Badge>
    </span>
  );
}
