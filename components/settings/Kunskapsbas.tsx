"use client";

import { FileText, Loader2, Upload } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { hamtaAffarskontext } from "@/lib/actions/affarskontext";
import { btnPrimary, btnSecondary } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

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

const LÄSBARA = [".txt", ".md", ".markdown", ".csv", ".json", ".html", ".htm"];

function läsbar(namn: string): boolean {
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
  const [antal, setAntal] = useState<number | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [meddelande, setMeddelande] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // null = inte hämtad än. Kortet lovar både affärskontext och kunskapsbas i
  // rubriken; utan det här talade det bara om det ena.
  const [kontextIfylld, setKontextIfylld] = useState<boolean | null>(null);
  const filväljare = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let avbruten = false;
    void hamtaAffarskontext().then((rad) => {
      if (!avbruten) setKontextIfylld(Boolean(rad?.product.trim()));
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
          throw new Error(kropp?.detail ?? kropp?.error ?? `Kunde inte spara (${response.status}).`);
        }
        setAntal((tidigare) => (tidigare ?? 0) + nya.length);
        setMeddelande(`${nya.length} dokument tillagda.`);
      }
      if (avvisade.length) {
        setFel(`Hoppade över ${avvisade.join(", ")} — läsbara format är ${LÄSBARA.join(", ")}.`);
      }
    } catch (cause) {
      setFel(felmeddelande(cause));
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
            Affärskontext och kunskapsbas
          </h2>
          <p className="mt-1 max-w-[62ch] text-[14px] leading-6 text-ink/65">
            {antal === 0
              ? "Tom. Agenterna svarar bara ur det ni lagt in — utan underlag eskalerar kundtjänstagenten varje ärende."
              : `${antal ?? "—"} dokument. Ladda upp villkor, vanliga frågor och rutiner så svarar agenterna ur dem.`}
          </p>
          {/* Rubriken lovar två saker. Utan den här raden svarade kortet bara
              på den ena, och affärskontexten var något man fick hitta själv. */}
          <p className="mt-2 text-[13px] text-ink/55">
            Affärskontext:{" "}
            {kontextIfylld === null ? (
              "hämtar…"
            ) : kontextIfylld ? (
              <span className="text-moss">ifylld</span>
            ) : (
              <span className="text-ochre">inte ifylld ännu</span>
            )}{" "}
            ·{" "}
            <Link
              href={vag("/settings/affarskontext")}
              className="focus-ring rounded-input underline underline-offset-4 hover:text-ochre"
            >
              {kontextIfylld ? "Ändra" : "Fyll i"}
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
            Ladda upp dokument
          </button>
          <Link
            href={vag("/settings/kunskapsbas")}
            className="focus-ring inline-flex min-h-11 items-center rounded-input px-3 text-[14px] font-medium text-ink/55 hover:text-ink"
          >
            Hantera
          </Link>
        </div>
      </div>
      {meddelande ? <p className="mt-3 text-[14px] text-moss">{meddelande}</p> : null}
      {fel ? (
        <p role="alert" className="mt-3 max-w-[70ch] break-words text-[14px] text-danger">
          {fel}
        </p>
      ) : null}
    </section>
  );
}

export function KunskapsbasPanel() {
  const [artiklar, setArtiklar] = useState<Artikel[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [meddelande, setMeddelande] = useState<string | null>(null);
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
        throw new Error(kropp?.error ?? `Kunde inte hämta kunskapsbasen (${response.status}).`);
      }
      setArtiklar(kropp?.articles ?? []);
    } catch (cause) {
      setFel(felmeddelande(cause));
      setArtiklar([]);
    }
  }, []);

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
            kropp?.detail ?? kropp?.error ?? `Kunde inte spara (${response.status}).`
          );
        }
        setMeddelande(
          nya.length === 1
            ? "Sparat. Agenterna kan svara ur texten från nästa ärende."
            : `${nya.length} dokument sparade. Agenterna kan svara ur dem från nästa ärende.`
        );
        setRubrik("");
        setText("");
        await ladda();
      } catch (cause) {
        setFel(felmeddelande(cause));
      } finally {
        setBusy(false);
      }
    },
    [ladda]
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
      setFel(
        `Hoppade över ${avvisade.join(", ")}. Textfiler läses direkt (${LÄSBARA.join(", ")}); ` +
          "för PDF och Word: klistra in texten i rutan nedan i stället."
      );
    }
    await spara(nya);
    if (filväljare.current) filväljare.current.value = "";
  }

  return (
    <div className="grid gap-8">
      <section>
        <div className="rounded-card border border-dashed border-ink/25 bg-paper2/40 p-6 text-center">
          <FileText className="mx-auto h-6 w-6 text-ink/35" aria-hidden />
          <p className="mt-3 text-[15px] text-ink/70">
            Ladda upp era villkor, vanliga frågor, garantitexter och rutiner.
          </p>
          <p className="mt-1 text-[13px] text-ink/45">
            Textfiler ({LÄSBARA.join(", ")}). PDF och Word: klistra in texten nedan.
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
            Välj filer
          </button>
        </div>
      </section>

      <section className="border-t border-ink/15 pt-6">
        <h3 className="text-[15px] font-semibold">Skriv eller klistra in</h3>
        <div className="mt-4 grid gap-3">
          <input
            value={rubrik}
            onChange={(e) => setRubrik(e.target.value)}
            placeholder="Rubrik — t.ex. Ångerrätt och returer"
            className="w-full rounded-input border border-ink/15 bg-paper px-3 py-2 text-[15px] focus-ring"
          />
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            placeholder="Texten agenterna ska svara ur. Skriv som ni skulle svarat en kund."
            className="w-full resize-y rounded-input border border-ink/15 bg-paper px-3 py-2 text-[15px] leading-6 focus-ring"
          />
          <div>
            <button
              type="button"
              disabled={busy || !rubrik.trim() || !text.trim()}
              onClick={() => void spara([{ title: rubrik.trim(), content: text.trim() }])}
              className={btnSecondary}
            >
              {busy ? "Sparar…" : "Spara i kunskapsbasen"}
            </button>
          </div>
        </div>
      </section>

      {fel ? (
        <p role="alert" className="max-w-[70ch] break-words text-[15px] text-danger">
          {fel}
        </p>
      ) : null}
      {meddelande ? <p className="text-[15px] text-moss">{meddelande}</p> : null}

      <section className="border-t border-ink/15 pt-6">
        <h3 className="text-[15px] font-semibold">
          I kunskapsbasen {artiklar ? `(${artiklar.length})` : ""}
        </h3>
        {artiklar === null ? (
          <p className="mt-4 text-[15px] text-ink/50">Hämtar…</p>
        ) : artiklar.length === 0 ? (
          <p className="mt-4 max-w-[65ch] text-[15px] leading-7 text-ink/60">
            Tom. Agenterna eskalerar varje ärende de inte kan grunda — det är rätt beteende, men
            det betyder också att den inte kan svara på något förrän det ligger något här.
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-ink/10">
            {artiklar.map((artikel, index) => (
              <li key={artikel.id ?? `${artikel.title}-${index}`} className="py-4">
                <p className="text-[15px] font-medium">{artikel.title}</p>
                <p className="mt-1 line-clamp-2 max-w-[80ch] text-[14px] leading-6 text-ink/60">
                  {artikel.content}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
