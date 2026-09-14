import { StartView } from "@/components/dashboard/StartView";

export const dynamic = "force-dynamic";

/**
 * Adminens EGEN arbetsyta — samma startsida som en kund ser på /dashboard.
 *
 * Routen finns för att den saknades. `tillAdminvag()` mappar `/dashboard` hit
 * och inte till `/admin`, som är portföljvyn (alla kunders siffror): fliken
 * "Min arbetsyta" ledde dit förut, och kundöversikten gick därför inte att nå
 * inifrån adminytan alls. `WorkspaceSection` kan inte heller rendera den:
 * `app/admin/[...slug]/page.tsx` är en icke-optional catch-all och får aldrig
 * ett tomt slug.
 *
 * Ingen egen datahämtning: `StartView` läser `useDashboard()`, och providern
 * sitter i `app/admin/layout.tsx`.
 */
export default function Page() {
  return <StartView />;
}
