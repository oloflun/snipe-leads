import { Overview } from "@/components/dashboard/Overview";

export const dynamic = "force-dynamic";

/**
 * Adminens EGEN arbetsyta — samma översikt som en kund ser på /dashboard.
 *
 * Routen finns för att den saknades. `workspaceTabs()` mappade `/dashboard` till
 * `/admin`, vilket är portföljvyn (alla kunders siffror), så fliken "Min
 * arbetsyta" ledde till plattformsöversikten och kundöversikten gick inte att nå
 * inifrån adminytan alls. `WorkspaceSection` kan inte heller rendera den:
 * `app/admin/[...slug]/page.tsx` är en icke-optional catch-all och får aldrig
 * ett tomt slug.
 *
 * Ingen egen datahämtning: `Overview` läser `useDashboard()`, och providern
 * sitter i `app/admin/layout.tsx`.
 */
export default function Page() {
  return <Overview />;
}
