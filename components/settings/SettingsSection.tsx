import { notFound } from "next/navigation";
import { SettingsView } from "@/components/WorkspaceViews";
import { resolveDashboardState } from "@/lib/data/dashboard";
import { productForSettingsSection, sektionDoldIDemo, settingsSectionForSlug } from "@/lib/routes";

/**
 * Inställningarnas dispatcher — EN sida, två ytor.
 *
 * Samma mönster som `WorkspaceSection`, och av samma skäl: sidorna låg som sex
 * nästan identiska `page.tsx` som alla anropade `SettingsView` med ett annat
 * `section`-värde. Varje ny inställning krävde en sjunde fil, och
 * entitlement-kontrollen — som fanns i noll av dem — hade behövt skrivas i var
 * och en.
 *
 * Anroparna är tunna med flit:
 *   app/settings/[[...slug]]/page.tsx              — kunden
 *   app/admin/installningar/[[...slug]]/page.tsx   — samma sidor inuti adminytan
 *
 * Att den andra finns är hela poängen med den här filen: `/settings` renderar
 * KUNDENS skal, så när adminytans flik "Inställningar" pekade dit försvann
 * plattformsraden och admin stod plötsligt i en annan yta. Nu ligger sidorna
 * under /admin och skalet står kvar.
 */
export async function SettingsSection({ slug = [] }: Readonly<{ slug?: string[] }>) {
  const section = settingsSectionForSlug(slug);
  if (!section) {
    notFound();
  }

  // Grinden. Att gruppen inte renderas i menyn för en supportkund hindrar
  // ingen från att skriva /settings/soul i adressfältet — det här är det lager
  // som faktiskt säger nej, och det körs på servern.
  const state = await resolveDashboardState();

  const product = productForSettingsSection(section);
  if (product && !state.products.includes(product)) {
    notFound();
  }

  // Demovyn döljer Team i menyn. Att bara dölja den hade lämnat adressen öppen,
  // och den sidan listar VÅRA mejladresser för någon vi visar produkten för.
  if (state.vy === "demo" && sektionDoldIDemo(section)) {
    notFound();
  }

  return <SettingsView section={section} />;
}
