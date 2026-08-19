"use client";

import { FileText, Loader2, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
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
            ? "Sparat. Agenten kan svara ur texten från nästa ärende."
            : `${nya.length} dokument sparade. Agenten kan svara ur dem från nästa ärende.`
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
            placeholder="Texten agenten ska svara ur. Skriv som ni skulle svarat en kund."
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
            Tom. Agenten eskalerar varje ärende den inte kan grunda — det är rätt beteende, men
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
