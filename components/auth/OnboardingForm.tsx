"use client";

import { useState, useTransition } from "react";
import { saveBusinessContext } from "@/lib/actions/onboarding";
import { formateraOrgnr, orgnrFel } from "@/lib/orgnr";

/**
 * Affärskontext på fyra fält i stället för åtta.
 *
 * ## Vad som var fel med det gamla formuläret
 *
 * Åtta fritextfält — produkt, målgrupp, branscher, geografi, tonalitet,
 * erbjudande, CTA, roller — FÖRIFYLLDA med påhittade exempelvärden
 * ("AI-driven outbound för svenska B2B-team", "Skåne, Stockholm, Göteborg").
 *
 * Två problem, och det andra är värre:
 *
 *  1. Man måste skriva en uppsats innan agenten gör något alls.
 *  2. Defaultvärdena går att skicka in RAKT AV. Då får kunden en affärskontext
 *     som beskriver ett påhittat bolag, agenten researchar mot den, och
 *     mejlen säljer något kunden inte säljer. Ett tomt fält hade varit
 *     ärligare än ett förifyllt fel.
 *
 * ## Vad agenten behöver i stället
 *
 * Organisationsnumret och webbplatsen. Resten läser den själv: bolagets egen
 * sajt säger vad de gör, till vem och i vilken ton, bättre än vad någon orkar
 * skriva i ett formulär klockan fyra på eftermiddagen.
 *
 * Webbplatsen är INTE valfri, och det är värt att veta varför. Från ett
 * organisationsnummer ensamt går det inte att hitta ett bolags sajt utan
 * Näringslivsregistret, och den licensen har vi inte (se
 * `app/leads/sources/registry.py`). Numret identifierar och hamnar i mejlens
 * sidfot enligt lag; sajten är det agenten faktiskt läser.
 */

const PLACEHOLDER = {
  orgnr: "556824-9022",
  webbplats: "https://exempel.se",
  produkt: "Utbildning i hjärt-lungräddning och första hjälpen för arbetsplatser",
  fokus: "Vi vill helst nå bolag som redan köpt hjärtstartare men saknar utbildning"
};

export function OnboardingForm() {
  const [orgnr, setOrgnr] = useState("");
  const [webbplats, setWebbplats] = useState("");
  const [produkt, setProdukt] = useState("");
  const [fokus, setFokus] = useState("");

  const [orgnrVarning, setOrgnrVarning] = useState<string | null>(null);
  const [testkund, setTestkund] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  // Valideras när fältet lämnas, inte vid varje tangenttryck: ett fält som
  // säger "tio siffror krävs" efter första siffran är ett fält som skäller.
  function vidBlurOrgnr() {
    if (!orgnr.trim()) {
      setOrgnrVarning(null);
      return;
    }
    const fel = orgnrFel(orgnr);
    setOrgnrVarning(fel);
    if (!fel) setOrgnr(formateraOrgnr(orgnr));
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    // Testkund: organisationsnumret hoppas över helt. Det finns inget riktigt
    // bolag bakom en testarbetsyta, och att kräva ett giltigt nummer betyder i
    // praktiken att man klistrar in NÅGON ANNANS — vilket är sämre än att
    // markera arbetsytan som ett test.
    const fel = testkund ? null : orgnrFel(orgnr);
    if (fel) {
      setOrgnrVarning(fel);
      return;
    }
    if (!produkt.trim()) {
      setError("Skriv en rad om vad ni säljer. Det är det agenten ska sälja.");
      return;
    }
    if (!webbplats.trim()) {
      setError("Fyll i webbplatsen. Det är den agenten läser för att förstå er.");
      return;
    }

    startTransition(async () => {
      const result = await saveBusinessContext({
        orgnr: testkund ? "" : orgnr,
        webbplats,
        produkt,
        fokus,
        testkund
      });
      if (!result.success) {
        setError(result.error ?? "Kunde inte spara affärskontexten.");
      }
    });
  }

  return (
    <form onSubmit={handleSubmit}>
      <p className="mt-4 max-w-[62ch] text-[15px] leading-[1.65] text-ink/70">
        Fyll i fyra rader. Agenten läser er webbplats och tar reda på resten
        själv — bransch, tonläge och hur ni beskriver er.
      </p>

      <div className="mt-10 grid grid-cols-12 gap-y-6 md:gap-x-8">
        <Falt
          label="Organisationsnummer"
          hint="Identifierar er, och krävs enligt lag i sidfoten på varje utskick."
          span="md:col-span-6"
          value={orgnr}
          onChange={setOrgnr}
          onBlur={vidBlurOrgnr}
          placeholder={PLACEHOLDER.orgnr}
          varning={orgnrVarning}
          inputMode="numeric"
          autoComplete="off"
        />

        {/* Testarbetsyta.

            Utan den här rutan finns bara två vägar för att skapa en testkund:
            hitta på ett organisationsnummer som råkar klara Luhn, eller
            klistra in ett riktigt bolags. Det andra är sämre än det ser ut —
            numret hamnar i affärskontexten som agenten sedan säljer utifrån.

            Markeringen skrivs in i affärskontexten, inte bara som ett flaggfält,
            så att den syns för den som läser kunden i adminvyn. En testkund som
            ser ut som en riktig kund i portföljen är precis den sortens siffra
            som fattar beslut åt en. */}
        <label className="col-span-12 flex items-start gap-3 md:col-span-6">
          <input
            type="checkbox"
            checked={testkund}
            onChange={(e) => {
              setTestkund(e.target.checked);
              if (e.target.checked) setOrgnrVarning(null);
            }}
            className="focus-ring mt-1 h-4 w-4 shrink-0"
          />
          <span className="text-[14px] leading-6 text-ink/70">
            <span className="font-medium text-ink">Testarbetsyta</span> — hoppa över
            organisationsnumret. Använd bara för test; arbetsytan märks som
            testkund i affärskontexten.
          </span>
        </label>

        <Falt
          label="Webbplats"
          hint="Den här läser agenten. Utan den vet den bara ert nummer."
          span="md:col-span-6"
          value={webbplats}
          onChange={setWebbplats}
          placeholder={PLACEHOLDER.webbplats}
          type="url"
          autoComplete="url"
        />

        <Falt
          label="Vad ni säljer"
          hint="En rad räcker. Agenten fyller på från sajten."
          span="md:col-span-12"
          value={produkt}
          onChange={setProdukt}
          placeholder={PLACEHOLDER.produkt}
        />

        <Falt
          label="Något extra att fokusera på (valfritt)"
          hint="Till exempel en nisch, ett segment ni vill åt, eller något ni vill att agenten undviker."
          span="md:col-span-12"
          value={fokus}
          onChange={setFokus}
          placeholder={PLACEHOLDER.fokus}
        />
      </div>

      {error ? (
        <p role="alert" className="mt-6 text-[15px] text-danger">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={isPending}
        className="focus-ring mt-10 inline-flex min-h-12 items-center rounded-input bg-ink px-7 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2 disabled:opacity-60"
      >
        {isPending ? "Sparar…" : "Spara och läs in vår sajt"}
      </button>

      <p className="mt-4 max-w-[62ch] text-[13px] leading-[1.55] text-mineral">
        Inget skickas till någon mottagare av det här. Agenten läser er sajt och
        förbereder underlag — utskick kräver att ni själva slår på det, och de
        tre första granskas alltid av en människa.
      </p>
    </form>
  );
}

function Falt({
  label,
  hint,
  span,
  value,
  onChange,
  onBlur,
  placeholder,
  varning,
  type = "text",
  inputMode,
  autoComplete
}: Readonly<{
  label: string;
  hint: string;
  span: string;
  value: string;
  onChange: (v: string) => void;
  onBlur?: () => void;
  placeholder: string;
  varning?: string | null;
  type?: string;
  inputMode?: "numeric" | "text";
  autoComplete?: string;
}>) {
  return (
    // gap-x först vid md: under md är varje fält col-span-12, och 11 gap à
    // 32px blir då bredare än viewporten. body har overflow-x: clip, så
    // resultatet syns inte som scroll — fältens högerkant kapas bara bort.
    <label className={`col-span-12 grid gap-2 border-t border-ink/15 pt-4 ${span}`}>
      <span className="kicker text-mineral">{label}</span>
      <input
        className={`h-14 rounded-input border bg-paper2/70 px-4 text-[15px] focus:border-ochre ${
          varning ? "border-danger" : "border-ink/15"
        }`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={placeholder}
        type={type}
        inputMode={inputMode}
        autoComplete={autoComplete}
        aria-invalid={Boolean(varning)}
      />
      <span className={`text-[13px] leading-[1.5] ${varning ? "text-danger" : "text-mineral"}`}>
        {varning ?? hint}
      </span>
    </label>
  );
}
