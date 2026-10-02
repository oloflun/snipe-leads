"use client";

import { FileText, Loader2, Upload } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { hamtaAffarskontext } from "@/lib/actions/affarskontext";
import { Rad, Radlista, btnPrimary, btnSecondary } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";
import { useLocale, type Localized } from "@/lib/i18n";

const ord = (s: string): Localized => ({ sv: s, en: s });

/**
 * Kunskapsbasen — dokumenten agenten svarar ur.
 *
 * ## Varför den behövde en yta
 *
 * Backenden har haft `GET/POST /api/kb` hela tiden, och kundtjänstagentens
 * grundningsregel läser därifrån: hittar den ingen artikel i ärendets fack
 * ESKALERAR den i stället för att gissa (`processor.py` steg 2). Det är rätt
 * beteende, men ingen kundvänd yta kunde fylla på basen. Följden var mätbar i
 * dev: sex av sex testmail eskalerades, och skärmen såg ut som en produkt som
 * inte fungerar — när den i själva verket vägrade gissa, korrekt.
 *
 * ## Filer
 *
 * Textfiler läses i webbläsaren och skickas som artiklar. PDF och Word görs
 * INTE om här: en halvläst PDF ger tyst sönderhackad text som agenten sedan
 * citerar som om den vore korrekt, och det är sämre än att be om en urklippt
 * text. Filnamnet blir rubrik, innehållet blir texten.
 */

type Artikel = {
  id?: string;
  title: string;
  content: string;
  category?: string | null;
  created_at?: string;
};

/**
 * Exporterade: Testchatt-fliken (components/snajp/SupportChat.tsx, Fas 5.4)
 * återanvänder EXAKT samma lista och samma test i stället för att kopiera
 * den — två kopior av "vilka filer läser vi klientsidan" glider isär första
 * gången någon utökar den ena.
 */
export const LÄSBARA = [".txt", ".md", ".markdown", ".csv", ".json", ".html", ".htm"];

export function läsbar(namn: string): boolean {
  const lägre = namn.toLowerCase();
  return LÄSBARA.some((ändelse) => lägre.endsWith(ändelse));
}

/**
 * Uppladdningen på STARTSIDAN, i kort format.
 *
 * Samma endpoint och samma filhantering som panelen nedan — kortet är en
 * genväg, inte en andra implementation. Den finns för att kunskapsbasen är det
 * enda som måste vara på plats innan någon av agenterna kan göra sitt jobb, och
 * att gömma det steget tre klick in i inställningarna gör att det hoppas över.
 * Kunden ser då en agent som eskalerar allt och drar slutsatsen att den inte
 * fungerar.
 */
export function KunskapsbasKort() {
  const vag = useArbetsvag();
  const loc = useLocale();
  const [antal, setAntal] = useState<number | null>(null);
  const [fel, setFel] = useState<Localized | null>(null);
  const [meddelande, setMeddelande] = useState<Localized | null>(null);
  const [busy, setBusy] = useState(false);
  // null = inte hämtad än. Kortet lovar både affärskontext och kunskapsbas i
  // rubriken; utan det här talade det bara om det ena.
  const [kontextIfylld, setKontextIfylld] = useState<boolean | null>(null);
  const filväljare = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let avbruten = false;
    hamtaAffarskontext()
      .then((rad) => {
        if (!avbruten) setKontextIfylld(Boolean(rad?.product.trim()));
      })
      // Samma filosofi som kb-hämtningen nedan: kortet är en genväg och ska
      // inte visa felbanners. Men utan catch stod "hämtar…" kvar för evigt
      // vid nätverksfel. Falskt "inte ifylld ännu" kostar bara att länken
      // säger "Fyll i" i stället för "Ändra" — den leder rätt oavsett.
      .catch(() => {
        if (!avbruten) setKontextIfylld(false);
      });
    fetch("/api/snajp-support/kb", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data: { articles?: Artikel[] } | null) => {
        if (!avbruten && data) setAntal(data.articles?.length ?? 0);
      })
      .catch(() => {
        /* Kortet är en genväg. Att det inte kunde räkna artiklar ska inte
           lägga ett felmeddelande överst på startsidan. */
      });
    return () => {
      avbruten = true;
    };
  }, []);

  async function väljFiler(filer: FileList | null) {
    if (!filer || filer.length === 0) return;
    setBusy(true);
    setFel(null);
    setMeddelande(null);
    try {
      const nya: Artikel[] = [];
      const avvisade: string[] = [];
      for (const fil of Array.from(filer)) {
        if (!läsbar(fil.name)) {
          avvisade.push(fil.name);
          continue;
        }
        const innehåll = (await fil.text()).trim();
        if (!innehåll) {
          avvisade.push(fil.name);
          continue;
        }
        nya.push({ title: fil.name.replace(/\.[^.]+$/, ""), content: innehåll });
      }
      if (nya.length) {
        const response = await fetch("/api/snajp-support/kb", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ articles: nya })
        });
        const kropp = await readJsonBody<{ error?: string; detail?: string }>(response);
        if (!response.ok) {
          throw new Error(
            kropp?.detail ??
              kropp?.error ??
              loc.text({ sv: `Kunde inte spara (${response.status}).`, en: `Could not save (${response.status}).` })
          );
        }
        setAntal((tidigare) => (tidigare ?? 0) + nya.length);
        setMeddelande({ sv: `${nya.length} dokument tillagda.`, en: `${nya.length} documents added.` });
      }
      if (avvisade.length) {
        setFel({
          sv: `Hoppade över ${avvisade.join(", ")} — läsbara format är ${LÄSBARA.join(", ")}.`,
          en: `Skipped ${avvisade.join(", ")}. Readable formats are ${LÄSBARA.join(", ")}.`
        });
      }
    } catch (cause) {
      setFel(ord(felmeddelande(cause)));
    } finally {
      setBusy(false);
      if (filväljare.current) filväljare.current.value = "";
    }
  }

  return (
    <section className="rounded-card bg-paper2/50 p-5 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h2 className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
            {loc.text({ sv: "Affärskontext och kunskapsbas", en: "Business context and knowledge base" })}
          </h2>
          <p className="mt-1 max-w-[62ch] text-[14px] leading-6 text-ink-muted">
            {antal === 0
              ? loc.text({ sv: "Tom.", en: "Empty." })
              : loc.text({ sv: `${antal ?? "—"} dokument.`, en: `${antal ?? "—"} documents.` })}
          </p>
          {/* Rubriken lovar två saker. Utan den här raden svarade kortet bara
              på den ena, och affärskontexten var något man fick hitta själv. */}
          <p className="mt-2 text-[13px] text-ink-subtle">
            {loc.text({ sv: "Affärskontext:", en: "Business context:" })}{" "}
            {kontextIfylld === null ? (
              loc.text({ sv: "hämtar…", en: "loading…" })
            ) : kontextIfylld ? (
              <span className="text-moss">{loc.text({ sv: "ifylld", en: "filled in" })}</span>
            ) : (
              <span className="text-warning">{loc.text({ sv: "inte ifylld ännu", en: "not filled in yet" })}</span>
            )}{" "}
            ·{" "}
            <Link
              href={vag("/settings/affarskontext")}
              className="focus-ring rounded-input underline underline-offset-4 hover:text-ochre"
            >
              {kontextIfylld ? loc.text({ sv: "Ändra", en: "Edit" }) : loc.text({ sv: "Fyll i", en: "Fill in" })}
            </Link>
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <input
            ref={filväljare}
            type="file"
            multiple
            accept={LÄSBARA.join(",")}
            onChange={(e) => void väljFiler(e.target.files)}
            className="sr-only"
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => filväljare.current?.click()}
            className={btnSecondary}
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Upload className="h-4 w-4" aria-hidden />}
            {loc.text({ sv: "Ladda upp dokument", en: "Upload documents" })}
          </button>
          <Link
            href={vag("/settings/kunskapsbas")}
            className="focus-ring inline-flex min-h-11 items-center rounded-input px-3 text-[14px] font-medium text-ink-subtle hover:text-ink"
          >
            {loc.text({ sv: "Hantera", en: "Manage" })}
          </Link>
        </div>
      </div>
      {meddelande ? <p className="mt-3 text-[14px] text-moss">{loc.text(meddelande)}</p> : null}
      {fel ? (
        <p role="alert" className="mt-3 max-w-[70ch] break-words text-[14px] text-danger">
          {loc.text(fel)}
        </p>
      ) : null}
    </section>
  );
}

export function KunskapsbasPanel() {
  const loc = useLocale();
  const [artiklar, setArtiklar] = useState<Artikel[] | null>(null);
  const [fel, setFel] = useState<Localized | null>(null);
  const [meddelande, setMeddelande] = useState<Localized | null>(null);
  const [busy, setBusy] = useState(false);
  const [rubrik, setRubrik] = useState("");
  const [text, setText] = useState("");
  const filväljare = useRef<HTMLInputElement | null>(null);

  const ladda = useCallback(async () => {
    setFel(null);
    try {
      const response = await fetch("/api/snajp-support/kb", { cache: "no-store" });
      const kropp = await readJsonBody<{ articles?: Artikel[]; error?: string }>(response);
      if (!response.ok) {
        throw new Error(
          kropp?.error ??
            loc.text({
              sv: `Kunde inte hämta kunskapsbasen (${response.status}).`,
              en: `Could not load the knowledge base (${response.status}).`
            })
        );
      }
      setArtiklar(kropp?.articles ?? []);
    } catch (cause) {
      setFel(ord(felmeddelande(cause)));
      setArtiklar([]);
    }
  }, [loc]);

  useEffect(() => {
    void ladda();
  }, [ladda]);

  const spara = useCallback(
    async (nya: Artikel[]) => {
      if (nya.length === 0) return;
      setBusy(true);
      setFel(null);
      setMeddelande(null);
      try {
        const response = await fetch("/api/snajp-support/kb", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ articles: nya })
        });
        const kropp = await readJsonBody<{ error?: string; detail?: string }>(response);
        if (!response.ok) {
          throw new Error(
            kropp?.detail ??
              kropp?.error ??
              loc.text({ sv: `Kunde inte spara (${response.status}).`, en: `Could not save (${response.status}).` })
          );
        }
        setMeddelande(
          nya.length === 1
            ? { sv: "Sparat.", en: "Saved." }
            : { sv: `${nya.length} dokument sparade.`, en: `${nya.length} documents saved.` }
        );
        setRubrik("");
        setText("");
        await ladda();
      } catch (cause) {
        setFel(ord(felmeddelande(cause)));
      } finally {
        setBusy(false);
      }
    },
    [ladda, loc]
  );

  async function väljFiler(filer: FileList | null) {
    if (!filer || filer.length === 0) return;
    const avvisade: string[] = [];
    const nya: Artikel[] = [];
    for (const fil of Array.from(filer)) {
      if (!läsbar(fil.name)) {
        avvisade.push(fil.name);
        continue;
      }
      const innehåll = (await fil.text()).trim();
      if (!innehåll) {
        avvisade.push(fil.name);
        continue;
      }
      nya.push({ title: fil.name.replace(/\.[^.]+$/, ""), content: innehåll });
    }
    if (avvisade.length) {
      setFel({
        sv: `Hoppade över ${avvisade.join(", ")}. PDF och Word: klistra in texten nedan.`,
        en: `Skipped ${avvisade.join(", ")}. PDF and Word: paste the text below.`
      });
    }
    await spara(nya);
    if (filväljare.current) filväljare.current.value = "";
  }

  return (
    <div className="grid gap-8">
      <section>
        <div className="rounded-card border border-dashed border-ink/25 bg-paper2/40 p-6 text-center">
          <FileText className="mx-auto h-6 w-6 text-ink-subtle" aria-hidden />
          <p className="mt-3 text-[13px] text-ink-subtle">
            {loc.text({
              sv: `Textfiler (${LÄSBARA.join(", ")}). PDF och Word: klistra in texten nedan.`,
              en: `Text files (${LÄSBARA.join(", ")}). PDF and Word: paste the text below.`
            })}
          </p>
          <input
            ref={filväljare}
            type="file"
            multiple
            accept={LÄSBARA.join(",")}
            onChange={(e) => void väljFiler(e.target.files)}
            className="sr-only"
            id="kb-filer"
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => filväljare.current?.click()}
            className={cn(btnPrimary, "mt-5")}
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Upload className="h-4 w-4" aria-hidden />}
            {loc.text({ sv: "Välj filer", en: "Choose files" })}
          </button>
        </div>
      </section>

      <section className="border-t border-ink/15 pt-6">
        <h3 className="text-[15px] font-semibold">{loc.text({ sv: "Skriv eller klistra in", en: "Write or paste" })}</h3>
        <div className="mt-4 grid gap-3">
          <input
            value={rubrik}
            onChange={(e) => setRubrik(e.target.value)}
            placeholder={loc.text({ sv: "Rubrik — t.ex. Ångerrätt och returer", en: "Title, e.g. Returns and cancellations" })}
            className="w-full rounded-input border border-ink/15 bg-paper px-3 py-2 text-[15px] focus-ring"
          />
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            placeholder={loc.text({ sv: "Texten agenterna ska svara ur", en: "The text the agents answer from" })}
            className="w-full resize-y rounded-input border border-ink/15 bg-paper px-3 py-2 text-[15px] leading-6 focus-ring"
          />
          <div>
            <button
              type="button"
              disabled={busy || !rubrik.trim() || !text.trim()}
              onClick={() => void spara([{ title: rubrik.trim(), content: text.trim() }])}
              className={btnSecondary}
            >
              {busy ? loc.text({ sv: "Sparar…", en: "Saving…" }) : loc.text({ sv: "Spara i kunskapsbasen", en: "Save to knowledge base" })}
            </button>
          </div>
        </div>
      </section>

      {fel ? (
        <p role="alert" className="max-w-[70ch] break-words text-[15px] text-danger">
          {loc.text(fel)}
        </p>
      ) : null}
      {meddelande ? <p className="text-[15px] text-moss">{loc.text(meddelande)}</p> : null}

      <section className="border-t border-ink/15 pt-6">
        <h3 className="text-[15px] font-semibold">
          {loc.text({ sv: "I kunskapsbasen", en: "In the knowledge base" })} {artiklar ? `(${artiklar.length})` : ""}
        </h3>
        {artiklar === null ? (
          <p className="mt-4 text-[15px] text-ink-subtle">{loc.text({ sv: "Hämtar…", en: "Loading…" })}</p>
        ) : artiklar.length === 0 ? (
          <p className="mt-4 text-[15px] leading-7 text-ink-muted">{loc.text({ sv: "Tom.", en: "Empty." })}</p>
        ) : (
          <Radlista ariaLabel={loc.text({ sv: "Dokument i kunskapsbasen", en: "Documents in the knowledge base" })} className="mt-4">
            {artiklar.map((artikel, index) => (
              <Rad key={artikel.id ?? `${artikel.title}-${index}`}>
                <p className="text-[15px] font-medium">{artikel.title}</p>
                <p className="mt-1 line-clamp-2 max-w-[80ch] text-[14px] leading-6 text-ink-muted">
                  {artikel.content}
                </p>
              </Rad>
            ))}
          </Radlista>
        )}
      </section>
    </div>
  );
}
