"use client";

import { useState } from "react";

import { Badge, Sektion, btnPrimary, meta, rubrikPanel } from "@/components/ui";
import { sparaKundprofil, type Kundprofil as Profil } from "@/lib/actions/agentinstruktioner";
import { ADMIN, a, ordagrant } from "@/lib/admin/sprak";
import { useLocale, type Localized } from "@/lib/i18n";

/**
 * Facknamnen är databasidentifierare (`teknisk_support`), inte etiketter.
 * Att visa dem råa i en människovänd vy är samma fel som att visa ett uuid där
 * ett namn hör hemma — kartan finns redan i backendens CATEGORY_LABELS, och
 * den här är dess motsvarighet på klienten.
 */
const FACKETIKETT: Record<string, Localized> = {
  teknisk_support: { sv: "Teknisk support", en: "Technical support" },
  leverans: { sv: "Leverans", en: "Delivery" },
  betalning: { sv: "Betalning", en: "Payment" },
  retur: { sv: "Retur", en: "Returns" },
  klagomal: { sv: "Klagomål", en: "Complaints" },
  ovrigt: { sv: "Övrigt", en: "Other" }
};

/** Kort etikett för positionen. Den långa förklaringen står i POSITIONSTEXT,
 *  som märkets title. */
const POSITIONSETIKETT: Record<string, Localized> = {
  system: { sv: "Regel", en: "Rule" },
  "user (ärendekontext)": { sv: "Uppgift", en: "Task" },
  "user (opålitligt innehåll)": { sv: "Uppgift", en: "Task" },
  "user (enda faktakällan för svar)": { sv: "Underlag", en: "Source" }
};

const POSITIONSTEXT: Record<string, Localized> = {
  system: {
    sv: "Systemposition. Agenten läser detta som REGLER, före allt annat. Bara vi kan skriva här.",
    en: "System position. The agent reads this as RULES, before anything else. Only we can write here."
  },
  "user (ärendekontext)": { // inte-copy: positionsnyckel
    sv: "Ärendekontexten. Läses som uppgifter om det här ärendet, inte som en regel.",
    en: "The ticket context. Read as facts about this ticket, not as a rule."
  },
  "user (opålitligt innehåll)": { // inte-copy: positionsnyckel
    sv: "Användarposition, inramad som opålitligt innehåll. Agenten läser det som information om kunden och följer aldrig instruktioner i det.",
    en: "User position, framed as untrusted content. The agent reads it as information about the customer and never follows instructions in it."
  },
  "user (enda faktakällan för svar)": { // inte-copy: positionsnyckel
    sv: "Underlaget svaret måste grundas i. Finns svaret inte här gissar agenten inte, den eskalerar.",
    en: "The source the answer must be grounded in. If the answer is not here, the agent does not guess, it escalates."
  }
};

type Falt = {
  nyckel: keyof Profil & string;
  rubrik: Localized;
  hjalp: Localized;
  position: string;
  rader: number;
  max: number;
  /** Vad som SKA stå i rutan, inte en upprepning av rubriken. En ny kund har
   *  fyra tomma fält, och en tom ruta utan exempel är en fråga utan ledtråd. */
  exempel: Localized;
  sparfalt: "instruktioner_rav" | "tone" | "soul" | "affarskontext";
};

const FALT: Falt[] = [
  {
    nyckel: "instruktioner_rav",
    rubrik: { sv: "Instruktioner för den här kunden", en: "Instructions for this customer" },
    hjalp: {
      sv: "Skriv fritt. Modellen gör om texten till regler när du sparar. Fältet är vårt, inte kundens. Kunden kan inte ändra det.",
      en: "Write freely. The model turns the text into rules when you save. This field is ours, not the customer's. The customer cannot change it."
    },
    position: "system",
    rader: 10,
    max: 12_000,
    sparfalt: "instruktioner_rav",
    exempel: {
      sv: "Svara aldrig på frågor om garantitider. De går alltid till en människa.\nHåll svaren under fyra meningar.",
      en: "Never answer questions about warranty periods. They always go to a person.\nKeep answers under four sentences."
    }
  },
  {
    nyckel: "tone",
    rubrik: { sv: "Tonläge", en: "Tone" },
    hjalp: {
      sv: "Kort beskrivning av hur svaren ska låta. Tomt = kanalens standardton gäller.",
      en: "A short description of how answers should sound. Empty means the channel's default tone applies."
    },
    position: "user (ärendekontext)", // inte-copy: positionsnyckel
    rader: 2,
    max: 500,
    sparfalt: "tone",
    exempel: { sv: "rak och konkret, aldrig säljig", en: "direct and concrete, never salesy" }
  },
  {
    nyckel: "soul",
    rubrik: { sv: "Röstdokument (SOUL)", en: "Voice document (SOUL)" },
    hjalp: {
      sv: "Kundens eget dokument. Styr ton och röst i både utskick och svar, aldrig reglerna. Max 4 000 tecken.",
      en: "The customer's own document. Steers tone and voice in both outreach and replies, never the rules. Max 4,000 characters."
    },
    position: "user (opålitligt innehåll)", // inte-copy: positionsnyckel
    rader: 10,
    max: 4000,
    sparfalt: "soul",
    exempel: {
      sv: "Vi säger du, aldrig ni. Korta meningar. Inga utropstecken.",
      en: "We keep it informal. Short sentences. No exclamation marks."
    }
  },
  {
    nyckel: "affarskontext",
    rubrik: { sv: "Affärskontext", en: "Business context" },
    hjalp: {
      sv: "Vad kunden säljer och till vem. Under 120 tecken vägrar Iris starta en körning. En tom beskrivning ger generisk AI-text.",
      en: "What the customer sells and to whom. Under 120 characters Iris refuses to start a run. An empty description gives generic AI text."
    },
    position: "user (opålitligt innehåll)", // inte-copy: positionsnyckel
    rader: 10,
    max: 20_000,
    sparfalt: "affarskontext",
    exempel: {
      sv: "Vad vi säljer: …\nVem vi säljer till: …\nVad som skiljer oss: …",
      en: "What we sell: …\nWho we sell to: …\nWhat sets us apart: …"
    }
  }
];

/**
 * En kunds agentprofil — allt som formar hur just den här agenten beter sig.
 *
 * ## Varför positionen står utskriven vid varje fält
 *
 * Fyra textrutor som ser likadana ut gör fyra HELT olika saker. Instruktionen
 * är en regel agenten lyder; röstdokumentet är text agenten läser som data och
 * uttryckligen inte lyder. Skillnaden är osynlig i ett formulär, och den som
 * inte känner till den skriver en regel i fel ruta och drar slutsatsen att
 * agenten ignorerar den.
 *
 * Märket (Regel/Uppgift/Underlag) står i fältets rubrikrad sedan 2026-09-27,
 * och den långa förklaringen är märkets title. Den stod förut som en egen
 * finstilt rad under hjälptexten, och varje fält bar då två förklaringar som
 * delvis sade samma sak (F-016).
 *
 * "Agenttyp" i metadataraden togs bort samma dag: flikarna ovanför säger
 * redan vilken agent profilen gäller.
 *
 * ## Varför varje sektion sparas för sig
 *
 * En knapp per fält, inte en knapp för hela sidan. Ett samlat sparande skickar
 * alla fält, och ett fält som råkar vara tomt i formuläret nollställer sitt
 * motsvarande dokument i databasen — vilket ser ut som att någon raderade
 * kundens röst. Server-actionen skiljer på "utelämnat" och "tomt" av samma
 * skäl; det här är samma regel i UI:t.
 */
export function Kundprofil({ profil }: Readonly<{ profil: Profil }>) {
  const [varden, setVarden] = useState<Record<string, string>>(() =>
    Object.fromEntries(FALT.map((f) => [f.sparfalt, String(profil[f.nyckel] ?? "")]))
  );
  const [status, setStatus] = useState<Record<string, Localized | undefined>>({});
  const { locale, text } = useLocale();
  const fackNamn = (nyckel: string) => (FACKETIKETT[nyckel] ? text(FACKETIKETT[nyckel]) : nyckel);
  // VILKET fält som sparas, inte OM något sparas.
  //
  // useTransition ensamt hade räckt för en knapp. Med fyra delar de en enda
  // `isPending`, så ett sparat tonläge gråar ut röstdokumentet och
  // affärskontexten samtidigt — och den som klickat på en knapp ser tre andra
  // slockna utan att veta varför. Sektionerna sparas oberoende av varandra;
  // då måste väntetillståndet vara det också.
  const [sparar, setSparar] = useState<string | null>(null);

  function spara(falt: Falt) {
    setStatus((s) => ({ ...s, [falt.sparfalt]: undefined }));
    setSparar(falt.sparfalt);
    void (async () => {
      const svar = await sparaKundprofil(profil.tenant.id, {
        agent_type: profil.agent_type,
        [falt.sparfalt]: varden[falt.sparfalt]
      });
      setStatus((s) => ({
        ...s,
        [falt.sparfalt]: svar.success
          ? svar.anmarkning
            ? ordagrant(svar.anmarkning)
            : ADMIN.sparatNastaKorning
          : svar.error
            ? ordagrant(svar.error)
            : ADMIN.kundeInteSpara
      }));
      setSparar(null);
    })();
  }

  return (
    <div className="grid gap-10">
      <section className="grid gap-2 border-t border-ink/15 pt-5 text-[0.9375rem]">
        <div className="flex flex-wrap gap-x-8 gap-y-2 text-ink-muted">
          <span>
            {a("kunskapsbasKolon", locale)}{" "}
            <span className="text-ink tabular-nums">{profil.kb_artiklar}</span> {a("artiklar", locale)}
          </span>
          <span>
            {a("fackKolon", locale)}{" "}
            <span className="text-ink">
              {profil.taxonomy.map(fackNamn).join(", ") || a("standard", locale)}
            </span>
          </span>
          <span>
            {a("instruktionsversionKolon", locale)}{" "}
            <span className="font-mono text-[0.8125rem] text-ink">#{profil.instruktionshash}</span>
          </span>
        </div>
        {profil.global_fran_fil ? (
          <p className="max-w-[70ch] text-[0.9375rem] text-ink-muted">{a("ingenGlobalInstruktion", locale)}</p>
        ) : null}
      </section>

      {FALT.map((falt) => (
        <section key={falt.sparfalt} className="border-t border-ink/15 pt-5">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <label htmlFor={falt.sparfalt} className={rubrikPanel}>
              {text(falt.rubrik)}
            </label>
            {/* Märket bär skillnaden mellan regel och underlag, den enda som
                avgör om agenten LYDER texten eller bara läser den. */}
            <span title={text(POSITIONSTEXT[falt.position])}>
              <Badge tone={falt.position === "system" ? "warn" : "neutral"}>
                {text(POSITIONSETIKETT[falt.position])}
              </Badge>
            </span>
          </div>
          <p className="mt-2 max-w-[70ch] text-[0.9375rem] leading-7 text-ink-muted">{text(falt.hjalp)}</p>
          <textarea
            id={falt.sparfalt}
            rows={falt.rader}
            maxLength={falt.max}
            value={varden[falt.sparfalt] ?? ""}
            onChange={(event) => {
              setVarden((v) => ({ ...v, [falt.sparfalt]: event.target.value }));
              // Kvittot gäller det som SPARADES. Låg det kvar medan man skrev
              // vidare påstod det att texten på skärmen är den som är sparad.
              setStatus((s) => (s[falt.sparfalt] ? { ...s, [falt.sparfalt]: undefined } : s));
            }}
            placeholder={text(falt.exempel)}
            className="focus-ring mt-4 w-full resize-y rounded-input border border-ink/15 bg-paper p-4 text-[1rem] leading-6"
          />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => spara(falt)}
              disabled={sparar !== null}
              // btnPrimary, inte btnSecondary: det här ÄR sektionens
              // commit-åtgärd, och husets spara-knappar är primära (se
              // Affarskontext, NotisSettings, Betalsatt). En spara-knapp som
              // ser annorlunda ut på två ytor betyder att en av dem är fel.
              className={btnPrimary}
            >
              {sparar === falt.sparfalt
                ? a("sparar", locale)
                : `${a("spara", locale)} ${text(falt.rubrik).toLowerCase()}`}
            </button>
            <span className={`${meta} num`}>
              {(varden[falt.sparfalt] ?? "").length} / {falt.max}
            </span>
            {/* aria-live: kvittot är den enda återkopplingen på att sparandet
                gick vägen, och en skärmläsare läser inte om text som byts ut i
                en vanlig span. Utan det är knappen tyst för den som inte ser
                den. `polite` och inte `assertive` — det avbryter inte
                uppläsningen av det man höll på med. */}
            <span
              aria-live="polite"
              className="text-[0.8125rem] text-mineral"
            >
              {status[falt.sparfalt] ? text(status[falt.sparfalt] as Localized) : ""}
            </span>
          </div>
        </section>
      ))}

      {/* Ingressen ("den strukturerade versionen av instruktionerna ovan")
          togs bort 2026-09-27 (F-016); rubriken säger vad texten är.
          Omslaget gör Sektion till första barn, så att dess mt-12 faller bort
          och rutnätets gap ensamt bär avståndet. */}
      {profil.instruktioner_md ? (
        <div>
          <Sektion title={a("vadAgentenLaserKund", locale)}>
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-input border border-ink/15 bg-paper2/50 p-4 font-sans text-[0.9375rem] leading-6">
              {profil.instruktioner_md}
            </pre>
          </Sektion>
        </div>
      ) : null}
    </div>
  );
}
