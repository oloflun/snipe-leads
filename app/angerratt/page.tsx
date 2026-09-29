import type { Metadata } from "next";
import Link from "next/link";
import { JuridiskSida } from "@/components/marketing/JuridiskSida";
import { BOLAG } from "@/lib/bolag";
import { KONTAKT_MEJL } from "@/components/marketing/copy";
import { notFoundOnTenant } from "@/lib/tenants/server";

export const metadata: Metadata = {
  title: "Distansavtal och ångerrätt — Snajp",
  description:
    "Vad distansavtalslagen innebär för avtal med Snajp: lagen skyddar konsumenter, Snajps tjänster tecknas av företag — och vad som gäller i stället.",
  alternates: { canonical: "/angerratt" }
};

/**
 * Informationen om distansavtalslagen som onboardingens villkorskryssruta
 * länkar till (OnboardingWizard, steg 4).
 *
 * ## Rättsläget som texten bygger på (kontrollerat 2026-09-29)
 *
 * Lag (2005:59) om distansavtal och avtal utanför affärslokaler ger KONSUMENTER
 * 14 dagars ångerrätt vid distansavtal. En konsument är en fysisk person som
 * handlar huvudsakligen för ändamål utanför näringsverksamhet — ett företag
 * som tecknar avtal om Snajps agenter omfattas alltså inte, och det gäller
 * även enskilda näringsidkare som tecknar för sin verksamhet.
 *
 * Texten säger det RAKT UT i stället för att gömma det: en sida som räknar
 * upp lagens rättigheter utan att säga att de inte gäller köparen vore
 * vilseledande åt andra hållet. Konsumentfallet beskrivs ändå, eftersom
 * gränsdragningen (huvudsakligen privat bruk) inte är vår att avgöra ensidigt.
 *
 * Sidan är enspråkigt svensk av samma skäl som övriga juridiska sidor — se
 * JuridiskSida.
 */
export default async function Page() {
  await notFoundOnTenant();

  return (
    <JuridiskSida
      rubrik="Distansavtal och ångerrätt"
      ingress={`Så här förhåller sig avtal med ${BOLAG.namn} ("Snajp") till lagen om distansavtal och avtal utanför affärslokaler (2005:59), ofta kallad distansavtalslagen.`}
    >
      <h2>Vad distansavtalslagen är</h2>
      <p>
        Distansavtalslagen ger <strong>konsumenter</strong> ett särskilt skydd när avtal ingås på
        distans, till exempel via en webbplats: rätt till tydlig förhandsinformation och som
        huvudregel 14 dagars ångerrätt räknat från den dag avtalet ingicks. Med konsument menar
        lagen en fysisk person som handlar huvudsakligen för ändamål som ligger utanför
        näringsverksamhet.
      </p>

      <h2>Vad som gäller för avtal med Snajp</h2>
      <p>
        Snajps tjänster riktar sig till <strong>företag</strong>. Avtalet tecknas av en
        näringsidkare, för användning i näringsverksamhet, och vid registreringen anges
        organisationsnummer. För sådana företagsavtal gäller distansavtalslagen inte, och det
        finns därför <strong>ingen lagstadgad ångerrätt</strong>. Det gäller även enskilda
        näringsidkare som tecknar avtalet för sin verksamhet.
      </p>
      <p>
        Skulle en fysisk person ändå ha ingått avtalet huvudsakligen för privat bruk räknas den
        personen som konsument, och då gäller lagens ångerrätt: 14 dagar från avtalsdagen att
        ångra sig genom ett tydligt meddelande till oss, till exempel via e-post.
        Konsumentverkets standardformulär för ångerrätt går också bra att använda. Har tjänsten
        med konsumentens uttryckliga samtycke börjat utföras under ångerfristen kan ersättning
        för den utförda delen tas ut, och när tjänsten fullgjorts upphör ångerrätten.
      </p>

      <h2>Vad som gäller i stället — oavsett ångerrätt</h2>
      <p>
        Vi har medvetet byggt avtalet så att frågan sällan behöver ställas på sin spets:
      </p>
      <ul>
        <li>
          <strong>Två månader gratis.</strong> Varje nytt konto börjar med en fri provperiod på
          två kalendermånader från kontoskapandet. Inga betalningsuppgifter lämnas vid
          registreringen, och vi hör av oss i god tid innan perioden tar slut.
        </li>
        <li>
          <strong>Ingen bindningstid.</strong> Avtalet kan avslutas när som helst — under
          gratisperioden utan någon kostnad alls.
        </li>
        <li>
          <strong>Fakturering i efterhand.</strong> Betalning sker mot faktura först efter
          gratisperioden. Det dras aldrig pengar automatiskt från något kort.
        </li>
      </ul>
      <p>
        Vill ni avsluta, eller åberopa ångerrätt i konsumentfallet ovan, skriv till{" "}
        <a href={`mailto:${KONTAKT_MEJL}`}>{KONTAKT_MEJL}</a>.
      </p>

      <h2>Övriga villkor</h2>
      <p>
        Den här sidan är information enligt distansavtalslagen, inte hela avtalet. Avtalet i
        övrigt framgår av <Link href="/villkor">användarvillkoren</Link>, och hur personuppgifter
        behandlas av <Link href="/integritetspolicy">integritetspolicyn</Link>.
      </p>
    </JuridiskSida>
  );
}
