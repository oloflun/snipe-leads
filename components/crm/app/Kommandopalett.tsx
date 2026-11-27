"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { Ban, KeyRound, Plus, RefreshCw, type LucideIcon } from "lucide-react";
import { Avatar } from "@astryxdesign/core/Avatar";
import { CommandPalette, CommandPaletteInput } from "@astryxdesign/core/CommandPalette";
import { useHotkeys } from "@astryxdesign/core/hooks";
import { Icon } from "@astryxdesign/core/Icon";
import { HStack, StackItem } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import type { SearchSource, SearchableItem } from "@astryxdesign/core/Typeahead";
import { OBJEKT, Objektikon, tonFor, tonklass, utanBolagsform, type Objekt } from "@/components/crm/app/kit";
import { crmAnrop, type Bolag, type Sida } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

/** Varje träff bär sin grupp och vad ett val ska göra. */
type Traff = SearchableItem<{
  group: string;
  slag: "ga" | "skapa" | "bolag";
  mal: string;
  objekt?: Objekt;
  ikon?: LucideIcon;
  ort?: string | null;
}>;

const VYER: Objekt[] = ["oversikt", "bolag", "personer", "affarer", "uppgifter", "synk", "sparrar", "utvecklare"];

/** Gemener utan accenter, så att "oversikt" hittar Översikt. */
const enkel = (s: string) => s.toLocaleLowerCase("sv").normalize("NFD").replace(/[̀-ͯ]/g, "");

/**
 * Kommandopaletten (DESIGN-CRM.md § Skalet), Ctrl K och Cmd K: Gå till (de åtta
 * vyerna), Skapa (nytt bolag, ny affär, ny uppgift, ny anslutning, ny spärr, ny nyckel) och Bolag, som söks mot
 * `/v1/companies?q=` medan man skriver.
 *
 * Skapa och bolagsträffar beställer av vyn genom adressen (`?ny=1`,
 * `?bolag=<id>`, se `useBestallning` i kit.tsx), så att det fungerar från vilken
 * vy som helst.
 */
export function Kommandopalett({
  oppen,
  setOppen,
  bas
}: Readonly<{ oppen: boolean; setOppen: (oppen: boolean) => void; bas: string }>) {
  const { text } = useLocale();
  const router = useRouter();

  // Ctrl K överallt och Cmd K på Mac. Den första träffen vinner, så inget körs två gånger.
  useHotkeys([
    { keys: "mod+k", onPress: () => setOppen(!oppen), allowInInputs: true },
    { keys: "ctrl+k", onPress: () => setOppen(!oppen), allowInInputs: true }
  ]);

  const kommandon = useMemo<Traff[]>(() => {
    const ga = text({ sv: "Gå till", en: "Go to" });
    const ny = text({ sv: "Skapa", en: "Create" });
    return [
      ...VYER.map<Traff>((v) => ({
        id: `ga:${v}`,
        label: text(OBJEKT[v].namn),
        auxiliaryData: { group: ga, slag: "ga", mal: `${bas}/${v}`, objekt: v }
      })),
      { id: "skapa:bolag", label: text({ sv: "Nytt bolag", en: "New company" }), auxiliaryData: { group: ny, slag: "skapa", mal: `${bas}/bolag?ny=1`, ikon: Plus } },
      { id: "skapa:affar", label: text({ sv: "Ny affär", en: "New deal" }), auxiliaryData: { group: ny, slag: "skapa", mal: `${bas}/affarer?ny=1`, ikon: Plus } },
      { id: "skapa:uppgift", label: text({ sv: "Ny uppgift", en: "New task" }), auxiliaryData: { group: ny, slag: "skapa", mal: `${bas}/uppgifter?ny=1`, ikon: Plus } },
      { id: "skapa:anslutning", label: text({ sv: "Ny anslutning", en: "New connection" }), auxiliaryData: { group: ny, slag: "skapa", mal: `${bas}/synk?ny=1`, ikon: RefreshCw } },
      { id: "skapa:sparr", label: text({ sv: "Ny spärr", en: "New block" }), auxiliaryData: { group: ny, slag: "skapa", mal: `${bas}/sparrar?ny=1`, ikon: Ban } },
      { id: "skapa:nyckel", label: text({ sv: "Ny nyckel", en: "New key" }), auxiliaryData: { group: ny, slag: "skapa", mal: `${bas}/utvecklare?ny=1`, ikon: KeyRound } }
    ];
  }, [text, bas]);

  // Stabil källa: en ny källa medan paletten är öppen kör om sökningen.
  const kalla = useMemo<SearchSource<Traff>>(() => {
    let styrning: AbortController | null = null;
    const bolagsgrupp = text({ sv: "Bolag", en: "Companies" });
    return {
      bootstrap: () => kommandon,
      // Paletten anropar cancel() före varje ny sökning och när den stängs.
      cancel: () => styrning?.abort(),
      async search(fraga) {
        const q = enkel(fraga.trim());
        const lokala = kommandon.filter((k) => enkel(k.label).includes(q));
        if (q.length < 2) return lokala;
        const denna = new AbortController();
        styrning = denna;
        // Paletten debouncar inte: vänta själv, och ge upp om nästa tangent hann före.
        await new Promise((klar) => window.setTimeout(klar, 180));
        if (denna.signal.aborted) return lokala;
        try {
          const sida = await crmAnrop<Sida<Bolag>>(`/v1/companies?${new URLSearchParams({ q: fraga.trim(), limit: "8", sort: "name" })}`, {
            signal: denna.signal
          });
          const bolag: Traff[] = sida.data.map((b) => ({
            id: `bolag:${b.id}`,
            label: b.name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" }),
            auxiliaryData: { group: bolagsgrupp, slag: "bolag", mal: `${bas}/bolag?bolag=${encodeURIComponent(b.id)}`, ort: b.address.city }
          }));
          return [...lokala, ...bolag];
        } catch {
          // Avbrutet eller fel: visa kommandona, inte en tom lista.
          return lokala;
        }
      }
    };
  }, [kommandon, text, bas]);

  return (
    <CommandPalette<Traff>
      isOpen={oppen}
      onOpenChange={setOppen}
      searchSource={kalla}
      label={text({ sv: "Kommandopalett", en: "Command palette" })}
      input={
        <CommandPaletteInput
          label={text({ sv: "Sök eller hoppa till", en: "Search or jump to" })}
          placeholder={text({ sv: "Sök bolag, eller skriv vart du vill", en: "Search companies, or type where to go" })}
        />
      }
      emptySearchText={text({ sv: "Inga träffar", en: "No results" })}
      emptyBootstrapText={text({ sv: "Skriv för att söka", en: "Type to search" })}
      renderItem={(item) => {
        const d = item.auxiliaryData;
        return (
          <HStack gap={3} vAlign="center">
            {d?.slag === "bolag" ? (
              <Avatar
                name={utanBolagsform(item.label)}
                size={24}
                shape="rounded"
                tooltip={false}
                className={`crm-avatar ${tonklass(tonFor(utanBolagsform(item.label)))}`}
              />
            ) : d?.objekt ? (
              <Objektikon objekt={d.objekt} storlek={24} />
            ) : (
              <span aria-hidden className="inline-flex size-6 shrink-0 items-center justify-center rounded-[6px] bg-ink/[0.06] text-ink-muted">
                {d?.ikon ? <Icon icon={d.ikon} size="sm" color="inherit" /> : null}
              </span>
            )}
            <StackItem size="fill">
              <Text maxLines={1} weight={d?.slag === "bolag" ? "semibold" : "normal"}>
                {item.label}
              </Text>
            </StackItem>
            {d?.ort ? (
              <Text type="supporting" color="secondary">
                {d.ort}
              </Text>
            ) : null}
          </HStack>
        );
      }}
      // Enter och klick landar båda här, och paletten stänger sig själv efteråt.
      onValueChange={(id) => {
        const vald = kommandon.find((k) => k.id === id);
        if (vald?.auxiliaryData) {
          router.push(vald.auxiliaryData.mal);
          return;
        }
        if (id.startsWith("bolag:")) router.push(`${bas}/bolag?bolag=${encodeURIComponent(id.slice("bolag:".length))}`);
      }}
    />
  );
}
