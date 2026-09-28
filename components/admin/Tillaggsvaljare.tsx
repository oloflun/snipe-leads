"use client";

import { useState } from "react";

import { Vaxel } from "@/components/settings/Vaxel";
import { Sektion } from "@/components/ui";
import { addonCatalog, type AddonKey } from "@/lib/addons";
import { sattTillagg } from "@/lib/actions/tillagg";

/**
 * Kundens tillägg, påslagna av oss.
 *
 * ## Varför växlar och inte kryssrutor med en Spara-knapp
 *
 * Se `Vaxel`s egen docstring: en kryssruta betyder "det här ingår i något
 * jag skickar in sedan", en växel betyder "det här händer nu". Ett tillägg
 * är en boolean per rad, och den farligaste utgången är att någon tror att
 * de tänt Leadslistor åt en pilotkund utan att ha gjort det. Varje växel
 * sparar därför direkt och säger vad som hände.
 *
 * Sidans andra sektioner har Spara-knappar, men de redigerar TEXT — där är
 * mellanläget verkligt och knappen är rätt. Här finns inget mellanläge.
 *
 * ## Optimistiskt, men bara tills databasen svarat
 *
 * Växeln slår om direkt (annars känns ytan trög), och listan ersätts sedan
 * av det `sattTillagg` LÄSER TILLBAKA ur kolumnen. Misslyckas skrivningen
 * återställs läget och felet skrivs ut — en växel som står kvar i påslaget
 * läge efter ett misslyckat anrop är en lögn om kundens entitlement.
 *
 * Raden som skrivs bär "(sparar…)" i etiketten under tiden. Det är statusen
 * som redan fanns i `sparar` och aldrig renderades: spårad, men osynlig.
 *
 * Ingressen under rubriken togs bort 2026-09-27 (F-016). Att ändringen
 * gäller direkt säger kvittot efter varje växling, och att tilläggen slås på
 * av oss och inte av kunden följer av att växlarna står i adminytan.
 */
export function Tillaggsvaljare({
  tenantId,
  initialaAddons,
  lasfel,
  migrationSaknas = false
}: Readonly<{
  tenantId: string;
  initialaAddons: AddonKey[];
  lasfel?: string;
  /** Migration 063 är inte körd. Växlarna visas men skriver inte — se tillagg.ts. */
  migrationSaknas?: boolean;
}>) {
  const [addons, setAddons] = useState<AddonKey[]>(initialaAddons);
  const [sparar, setSparar] = useState<AddonKey | null>(null);
  const [fel, setFel] = useState<string | null>(lasfel ?? null);
  const [kvitto, setKvitto] = useState<string | null>(null);
  const [saknas, setSaknas] = useState(migrationSaknas);

  async function vaxla(nyckel: AddonKey, pa: boolean) {
    // Grind i stället för `disabled` på knapparna. Att sätta `disabled` på
    // den växel som just klickats BLURRAR den — webbläsaren tar fokus från
    // ett inaktiverat element — så en tangentbordsanvändare tappar sin plats
    // vid varje påslag och får tabba ned igen. Guarden stoppar samma kapplöp-
    // ning utan att röra fokus.
    if (sparar !== null) return;

    // Utan funktionerna ur 063 kan ingen växel spara. Beskedet står redan
    // kvar under listan; ett nytt anrop hade bara gett samma fel igen och
    // fått växeln att hoppa fram och tillbaka.
    if (saknas) return;

    const fore = addons;
    const nasta = pa ? [...addons, nyckel] : addons.filter((a) => a !== nyckel);
    setAddons(nasta);
    setSparar(nyckel);
    setFel(null);
    setKvitto(null);

    const svar = await sattTillagg(tenantId, nasta);
    setSparar(null);

    if (!svar.success) {
      setAddons(fore);
      setFel(svar.error ?? "Tillägget kunde inte sparas.");
      if (svar.migrationSaknas) setSaknas(true);
      return;
    }

    setAddons(svar.addons ?? nasta);
    const namn = addonCatalog.find((spec) => spec.key === nyckel)?.name ?? nyckel;
    setKvitto(
      pa
        ? `${namn} är påslaget. Kunden ser vyn direkt.`
        : `${namn} är avstängt. Vyn är borta ur kundens meny.`
    );
  }

  return (
    <Sektion title="Tillägg">
      <div className="divide-y divide-ink/12 border-y border-ink/15">
        {addonCatalog.map((spec) => (
          // `why` är vad tillägget KOSTAR oss att sätta upp — den texten står i
          // kundens egen vy som skäl till att det inte ingår, och här som
          // påminnelse om vad ett påslag förbinder oss till (lib/addons.ts).
          // Som radens title sedan 2026-09-27: en andra finstilt rad under
          // växelns egen beskrivning var en förklaring för mycket (F-016).
          <div key={spec.key} className="py-5" title={spec.why}>
            <Vaxel
              etikett={sparar === spec.key ? `${spec.name} (sparar…)` : spec.name}
              beskrivning={spec.what}
              pa={addons.includes(spec.key)}
              onChange={(nytt) => void vaxla(spec.key, nytt)}
            />
          </div>
        ))}
      </div>

      {fel ? (
        <p role="alert" className="mt-5 max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}
      {kvitto && !fel ? (
        <p role="status" className="mt-5 text-[0.9375rem] text-moss">
          {kvitto}
        </p>
      ) : null}
    </Sektion>
  );
}
