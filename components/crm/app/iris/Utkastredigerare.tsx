"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Check, Mail, RefreshCw, Send, Sparkles, TriangleAlert, Undo2, X } from "lucide-react";
import { AlertDialog } from "@astryxdesign/core/AlertDialog";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { DropdownMenu } from "@astryxdesign/core/DropdownMenu";
import { Icon } from "@astryxdesign/core/Icon";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { Selector } from "@astryxdesign/core/Selector";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { HStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import { TextArea } from "@astryxdesign/core/TextArea";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Prick } from "@/components/crm/app/kit";
import { StrukturVal } from "@/components/crm/app/iris/StrukturVal";
import { delaMejl } from "@/lib/crm/iris/mejl";
import { CrmFel } from "@/lib/crm/api";
import {
  DIREKTA,
  STUDIOVAL,
  provmejlAdresser,
  provmejlFel,
  simuleringsorsak,
  studio,
  type Besked,
  type Signatur,
  type Studiokontext,
  type Studioresultat,
  type Studioval
} from "@/lib/crm/iris/utkast";
import { irisAnrop } from "@/lib/crm/iris/anrop";
import { lasStruktur, sparaStruktur, type Struktur } from "@/lib/leads/struktur";
import { useLocale, type Localized } from "@/lib/i18n";

/** Gränserna backenden håller (leads.spara_utkasttext): ämnet 200 tecken, texten 8 000. */
const AMNE_MAX = 200;
const TEXT_MAX = 8000;
/** Medan Iris skriver läses utkastet om så här ofta, högst så här många gånger (cirka tre minuter), som i dagens Leads. */
const POLL_MS = 4000;
const POLL_MAX = 45;

const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : { sv: "Okänt fel.", en: "Unknown error." });

/**
 * Svansen, uppdelad som mottagaren ser den: signaturen (den aktuella, även när
 * ett äldre block står i texten, som vid utskicket) och den lagstadgade foten.
 * Samma delning som backendens signatur.dela_utkast, via dagens `delaMejl`.
 */
function delaSvans(svans: string, signatur: Signatur | null): { sig: Signatur | null; fot: string } {
  if (!signatur) return { sig: null, fot: svans.trim() };
  if (signatur.text && svans.startsWith(signatur.text)) return { sig: signatur, fot: svans.slice(signatur.text.length).trim() };
  // Börjar svansen med ett (äldre) signaturblock är delningens brödtext tom: blocket ersätts av den aktuella signaturen.
  const [fore] = delaMejl(svans, signatur);
  if (!fore.trim()) {
    const i = svans.indexOf("\n--\n");
    return { sig: signatur, fot: i >= 0 ? svans.slice(i + 1).trim() : "" };
  }
  return { sig: null, fot: svans.trim() };
}

/**
 * Det som står efter brödtexten i det skickade mejlet (LU-038): signaturen med
 * logotypen och den lagstadgade foten, så som mottagaren ser dem. Kodens text:
 * den redigeras aldrig och AI:n skriver aldrig om den.
 */
export function Mejlsvans({ signatur, svans }: Readonly<{ signatur: Signatur | null; svans: string | null }>) {
  const { text } = useLocale();
  const { sig, fot } = delaSvans(svans ?? "", signatur);
  // Loggan följer med i varje mejl även när blocket inte står ordagrant (signatur.bygg_html).
  const logga = sig?.logotyp_url ?? signatur?.logotyp_url ?? null;
  if (!sig && !fot && !logga) return null;
  const webb = sig?.webb ? (sig.webb.startsWith("http") ? sig.webb : `https://${sig.webb}`) : null;
  return (
    <section className="crm-kallkort flex flex-col gap-3 rounded-[16px] px-4 py-3.5" aria-label={text({ sv: "Signatur och fot", en: "Signature and footer" })}>
      <span className="text-[0.75rem] text-ink-muted">{text({ sv: "Läggs till sist i mejlet, så som mottagaren ser det", en: "Added at the end of the email, as the recipient sees it" })}</span>
      {sig ? (
        <div className="text-[0.8125rem] leading-[1.55] text-ink">
          <p className="font-semibold">{sig.namn}</p>
          {sig.titel ? <p className="font-semibold">{sig.titel}</p> : null}
          {sig.verksamhet ? <p>{sig.verksamhet}</p> : null}
          {sig.telefon ? <p className="tabular-nums">{sig.telefon}</p> : null}
          {sig.epost ? <p>{sig.epost}</p> : null}
          {logga ? (
            // eslint-disable-next-line @next/next/no-img-element -- samma externa adress som i mejlets HTML-del
            <img src={logga} alt={sig.bolag ?? sig.namn} width={120} className="my-3 block h-auto w-[120px]" />
          ) : (
            <span aria-hidden className="block h-2" />
          )}
          {sig.ort ? <p className="font-semibold">{sig.ort}</p> : null}
          {sig.webb && webb ? (
            <p>
              <a href={webb} target="_blank" rel="noreferrer" className="crm-tidslinje-lank">
                {sig.webb}
              </a>
            </p>
          ) : null}
          {sig.bolag ? <p className="mt-2">{sig.bolag}</p> : null}
        </div>
      ) : logga ? (
        // eslint-disable-next-line @next/next/no-img-element -- samma externa adress som i mejlet
        <img src={logga} alt={signatur?.bolag ?? signatur?.namn ?? ""} width={120} className="block h-auto w-[120px]" />
      ) : null}
      {fot ? <p className="whitespace-pre-wrap break-words text-[0.75rem] leading-5 text-ink-muted">{fot}</p> : null}
    </section>
  );
}

/** Mejlets text som mottagaren ser den, utan fält: för skickade och schemalagda mejl, och när utkastet inte går att ändra. */
export function Mejlvisning({ amne, brodtext, svans, signatur }: Readonly<{ amne: string | null; brodtext: string; svans: string | null; signatur: Signatur | null }>) {
  const { text } = useLocale();
  return (
    <>
      <article className="flex flex-col gap-3 rounded-[16px] border border-ink/[0.08] px-4 py-3.5" aria-label={text({ sv: "Mejlet som mottagaren ser det", en: "The email as the recipient sees it" })}>
        <p className="text-[0.9375rem] font-semibold text-ink">{amne || text({ sv: "Utan ämnesrad", en: "No subject line" })}</p>
        <p className="whitespace-pre-wrap break-words text-[0.9375rem] leading-7 text-ink">{brodtext}</p>
      </article>
      <Mejlsvans signatur={signatur} svans={svans} />
    </>
  );
}

/** Provmejlet (LU-037, LU-087) på ett utkast (`queueItemId`) eller ett skickat mejl (`messageId`). */
export type Provmejlmal = { queueItemId?: string | null; messageId?: string | null };

type Upptagen = "spara" | "godkann" | "avvisa" | "skriv" | "prov" | null;

/**
 * NYTT MÖNSTER (steg 4.3): utkastredigeraren. En komponent för varje yta där ett
 * mejl från Iris granskas: leadets panel, Iris › Utkast, körningarna,
 * konversationerna och Kundtjänst. Ytan säger vad som går (props), redigeraren
 * gör resten på samma sätt överallt:
 *
 * - Ämne och text som går att redigera (`redigerbar`), med fältfel vid rätt fält.
 *   Signatur, logga och lagstadgad fot står under, så som mottagaren ser dem,
 *   och redigeras aldrig (`Mejlsvans`).
 * - Spara före godkänn: Godkänn, provmejl och Skriv om sparar en osparad ändring
 *   först, så att det som skickas är det som står i rutan (LU-033).
 * - Handlingskontrollen (`handlingar`, LU-014): påstår texten att något redan är
 *   gjort måste det bekräftas innan Godkänn går att trycka på.
 * - Bearbeta texten med AI (`kontext`, AP15, Email Studio): kortare, förbättra,
 *   personalisera och mer. Ett förskrivet svar skriver aldrig över texten.
 * - Skriv om (`skrivOm`): Iris skriver ett nytt utkast, med struktur A eller B och
 *   ett önskemål där ytan tar emot ett.
 * - Provmejl (`provmejl`) till kundens egna adresser.
 * - Förlopp medan Iris skriver (`skrivs`), och med `lasOm` läser redigeraren om
 *   utkastet var fjärde sekund som dagens Leads, högst tre minuter.
 *
 * Utfallet av varje handling står i en region som finns hela tiden. Ytan
 * levererar handlingen och dess besked (`Besked`); redigeraren visar dem.
 *
 * Ge redigeraren `key={utkastets id}` där ytan kan byta post medan en handling
 * pågår (en panel utan scrim): då kan ett sent svar aldrig hamna i fel utkast.
 * Redigeraren kastar dessutom själv ett utfall som kommer efter att `nyckel` bytts.
 */
export function Utkastredigerare({
  nyckel,
  amne,
  brodtext,
  svans,
  signatur,
  mottagare,
  redigerbar,
  skrivs = false,
  lasOm,
  kontext,
  handlingar,
  spara,
  godkann,
  avvisa,
  skrivOm,
  provmejl,
  skriv,
  extra,
  fot,
  visaText = true
}: Readonly<{
  /** Utkastets id: ett nytt värde (annat utkast) börjar om från den sparade texten. */
  nyckel: string;
  amne: string | null;
  brodtext: string;
  svans: string | null;
  signatur: Signatur | null;
  mottagare?: string | null;
  /** Fälten går att ändra. Falskt: mejlet visas som mottagaren ser det. */
  redigerbar: boolean;
  /** Iris skriver ett nytt utkast just nu. */
  skrivs?: boolean;
  /** Läser om utkastet medan Iris skriver. Utan: ytan läser om själv. */
  lasOm?: () => void;
  /** Bakgrunden till AI:n (AP15). Utan: inga AI-val. */
  kontext?: Studiokontext | null;
  /** Meningar som påstår att något redan är gjort (LU-014). */
  handlingar?: string[] | null;
  /** Sparar ämne och brödtext. Kastar `CrmFel` med backendens mening. */
  spara?: (amne: string, brodtext: string) => Promise<void>;
  godkann?: { etikett?: string; gor: (bekraftatHandlingar: boolean) => Promise<Besked | null> };
  avvisa?: { fraga?: Localized; gor: () => Promise<Besked | null> };
  skrivOm?: { onskemal: boolean; struktur: boolean; gor: (onskemal: string | null, struktur: Struktur) => Promise<Besked | null> };
  provmejl?: Provmejlmal | null;
  /** `useSkrivratt("test")` hos ytan: läsrollen ändrar ingenting. */
  skriv: { far: boolean; skal: string | null };
  /** Ytans egna knappar, sist i raden. */
  extra?: React.ReactNode;
  /**
   * Panelens fot. Finns den står besluten (Godkänn och skicka, Spara, Avvisa) och utfallet där, så att
   * de syns utan att man rullar förbi signaturen. Verktygen för texten står kvar vid texten.
   */
  fot?: HTMLElement | null;
  /** Falskt: bara handlingarna och utfallet, när ytan redan visar mejlet (en skickad konversation). */
  visaText?: boolean;
}>) {
  const { text, locale } = useLocale();
  const [falt, setFalt] = useState({ amne: amne ?? "", text: brodtext });
  const [fel, setFel] = useState<{ amne?: string; text?: string }>({});
  const [upptagen, setUpptagen] = useState<Upptagen>(null);
  const [besked, setBesked] = useState<Besked | null>(null);
  const [kontrollerat, setKontrollerat] = useState(false);
  const [avvisas, setAvvisas] = useState(false);
  const [omskrivning, setOmskrivning] = useState<{ onskemal: string; struktur: Struktur } | null>(null);
  const [prov, setProv] = useState<{ adresser: string[] | null; vald: string; fel?: string | null } | null>(null);
  // `fore`: fälten före en direkt omskrivning, så att den går att ångra.
  const [ai, setAi] = useState<{ pagar: Studioval | null; resultat: Studioresultat | null; fore?: { amne: string; text: string } | null }>({ pagar: null, resultat: null });

  const andrad = falt.amne !== (amne ?? "") || falt.text !== brodtext;
  const andradRef = useRef(andrad);
  andradRef.current = andrad;
  const forraNyckel = useRef(nyckel);
  // Det utkast som visas nu: ett utfall som kommer efter ett byte gäller ett annat utkast och kastas.
  const nyckelRef = useRef(nyckel);
  nyckelRef.current = nyckel;
  // Efter en lyckad Spara tar fälten det backenden sparade (trimmat, hälsningen rättad), även om rutan skilde sig.
  const tvinga = useRef<{ amne: string; text: string; fore: { amne: string; text: string } } | null>(null);
  const [synk, setSynk] = useState(0);

  // Ett annat utkast börjar om. Samma utkast med ny sparad text (omskrivet, läst om) tar
  // den nya texten bara när inget är osparat: egen redigering skrivs aldrig över.
  useEffect(() => {
    const nytt = forraNyckel.current !== nyckel;
    forraNyckel.current = nyckel;
    const sparat = tvinga.current;
    tvinga.current = null;
    if (nytt) {
      setBesked(null);
      setAi({ pagar: null, resultat: null });
      setOmskrivning(null);
      setFel({});
      setUpptagen(null);
      setProv(null);
      setAvvisas(false);
    }
    if (nytt || !andradRef.current) setFalt({ amne: amne ?? "", text: brodtext });
    else if (sparat) {
      // Har den omlästa texten kommit visas den; annars det som skickades till servern.
      const omlast = (amne ?? "") !== sparat.fore.amne || brodtext !== sparat.fore.text;
      setFalt(omlast ? { amne: amne ?? "", text: brodtext } : { amne: sparat.amne, text: sparat.text });
    }
  }, [nyckel, amne, brodtext, synk]);

  const handlingslista = handlingar ?? [];
  const handlingsnyckel = handlingslista.join("\n");
  useEffect(() => {
    setKontrollerat(false);
  }, [handlingsnyckel]);

  // Förloppet medan Iris skriver: utkastet läses om tills det inte längre skrivs.
  const lasOmRef = useRef(lasOm);
  lasOmRef.current = lasOm;
  useEffect(() => {
    if (!skrivs || !lasOmRef.current) return;
    let varv = 0;
    const t = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      varv += 1;
      if (varv > POLL_MAX) {
        window.clearInterval(t);
        setBesked({ text: text({ sv: "Utkastet tog för lång tid. Försök igen om en stund.", en: "The draft took too long. Try again in a moment." }), fel: true });
        return;
      }
      lasOmRef.current?.();
    }, POLL_MS);
    return () => window.clearInterval(t);
  }, [skrivs, text]);

  /** Fälten prövas som backenden prövar dem, och felet står vid rätt fält. */
  function provaFalt(): boolean {
    const a = falt.amne.trim();
    const t = falt.text.trim();
    const nya: { amne?: string; text?: string } = {};
    if (!a) nya.amne = text({ sv: "Ämnesraden får inte vara tom.", en: "The subject line cannot be empty." });
    else if (a.length > AMNE_MAX) nya.amne = text({ sv: `Ämnesraden får vara högst ${AMNE_MAX} tecken.`, en: `The subject line can be at most ${AMNE_MAX} characters.` });
    if (!t) nya.text = text({ sv: "Texten får inte vara tom.", en: "The text cannot be empty." });
    setFel(nya);
    return !nya.amne && !nya.text;
  }

  /** Sparar en osparad ändring. Sant när det som står i rutan är det som är sparat. */
  async function sparaOmAndrat(): Promise<boolean> {
    if (!andrad || !spara) return true;
    if (!provaFalt()) return false;
    const a = falt.amne.trim();
    const t = falt.text.trim();
    const fore = { amne: amne ?? "", text: brodtext };
    const start = nyckelRef.current;
    try {
      await spara(a, t);
      if (nyckelRef.current !== start) return false;
      setFel({});
      tvinga.current = { amne: a, text: t, fore };
      setSynk((n) => n + 1);
      return true;
    } catch (e) {
      if (nyckelRef.current !== start) return false;
      const m = text(feltext(e));
      // Backendens 422 säger vilket fält: ämnesraden nämns, annars gäller det texten.
      if (e instanceof CrmFel && e.status === 422) setFel(/ämnes|subject/i.test(m) ? { amne: m } : { text: m });
      else setBesked({ text: text({ sv: `Ändringen kunde inte sparas: ${m}`, en: `The edit could not be saved: ${m}` }), fel: true });
      return false;
    }
  }

  async function gor(vad: Exclude<Upptagen, null>, fn: () => Promise<Besked | null>, sparaForst = true) {
    if (upptagen) return;
    const start = nyckelRef.current;
    setUpptagen(vad);
    setBesked(null);
    try {
      if (sparaForst && !(await sparaOmAndrat())) return;
      const ut = await fn();
      if (ut && nyckelRef.current === start) setBesked(ut);
    } catch (e) {
      if (nyckelRef.current === start) setBesked({ text: text(feltext(e)), fel: true });
    } finally {
      if (nyckelRef.current === start) setUpptagen(null);
    }
  }

  const sparaNu = () =>
    void gor(
      "spara",
      async () => {
        if (!(await sparaOmAndrat())) return null;
        return { text: text({ sv: "Sparat.", en: "Saved." }), fel: false };
      },
      false
    );

  // ---- AI (AP15) -------------------------------------------------------------
  async function korStudio(val: Studioval) {
    if (!kontext || ai.pagar) return;
    const start = nyckelRef.current;
    const fore = { amne: falt.amne, text: falt.text };
    setAi({ pagar: val, resultat: null });
    setBesked(null);
    try {
      const r = await studio(val, fore.amne, fore.text, kontext, locale, Boolean(svans || signatur));
      // Svaret gäller utkastet det begärdes för: har posten bytts kastas det.
      if (nyckelRef.current !== start) return;
      // Ett förskrivet svar skriver aldrig över texten: det visas, och du väljer.
      const direkt = !r.simulerat && DIREKTA.has(val);
      if (direkt) setFalt((f) => ({ amne: r.amnen[0] ?? f.amne, text: r.ny }));
      setAi({ pagar: null, resultat: r, fore: direkt ? fore : null });
    } catch (e) {
      if (nyckelRef.current !== start) return;
      setAi({ pagar: null, resultat: null });
      setBesked({ text: text(feltext(e)), fel: true });
    }
  }
  const anvandResultat = () => {
    const r = ai.resultat;
    if (!r) return;
    setFalt((f) => ({ amne: r.amnen[0] ?? f.amne, text: r.ny }));
    setAi({ pagar: null, resultat: null });
  };
  /** Ångrar en direkt omskrivning: ämnet och texten som stod i rutan före, även osparade ändringar. */
  const angraResultat = () => {
    const f = ai.fore;
    if (!f) return;
    setFalt(f);
    setAi({ pagar: null, resultat: null });
  };

  // ---- Provmejl ----------------------------------------------------------------
  async function oppnaProv() {
    setProv({ adresser: null, vald: "" });
    const lista = await provmejlAdresser();
    setProv((p) => (p ? { adresser: lista, vald: p.vald || lista[0] || "" } : p));
  }
  const skickaProv = () =>
    void gor(
      "prov",
      async () => {
      if (!prov?.vald || !provmejl) return null;
      setProv((p) => (p ? { ...p, fel: null } : p));
      // Spara först. Faller sparningen stängs dialogen, så att felet syns vid sitt fält.
      if (!(await sparaOmAndrat())) {
        setProv(null);
        return null;
      }
      try {
        const s = await irisAnrop<{ till?: string; saknar_fot?: boolean }>("/leads/provmejl", {
          method: "POST",
          body: JSON.stringify({ till: prov.vald, queue_item_id: provmejl.queueItemId ?? null, message_id: provmejl.messageId ?? null })
        });
        setProv(null);
        const till = s?.till ?? prov.vald;
        return {
          text:
            text({ sv: `Provmejlet är skickat till ${till}.`, en: `The test email was sent to ${till}.` }) +
            (s?.saknar_fot
              ? ` ${text({ sv: "Obs: sidfoten med organisationsnummer och adress saknas, så det riktiga utskicket stoppas. Fyll i dem under Kunder & Data.", en: "Note: the footer with company number and address is missing, so the real send is blocked. Add them under Customers & Data." })}`
              : ""),
          fel: Boolean(s?.saknar_fot)
        };
      } catch (e) {
        // Felet står i dialogen, som är öppen: bakom den syns det inte.
        setProv((p) => (p ? { ...p, fel: text(provmejlFel(e)) } : p));
        return null;
      }
      },
      false
    );

  // ---- Skriv om ------------------------------------------------------------------
  const startaOmskrivning = () => setOmskrivning({ onskemal: "", struktur: lasStruktur() });
  const skrivOmNu = () =>
    void gor(
      "skriv",
      async () => {
        if (!skrivOm || !omskrivning) return null;
        sparaStruktur(omskrivning.struktur);
        const ut = await skrivOm.gor(skrivOm.onskemal ? omskrivning.onskemal.trim() || null : null, omskrivning.struktur);
        setOmskrivning(null);
        return ut;
      },
      false
    );

  const lasning = { isDisabled: !skriv.far || upptagen != null || ai.pagar != null, tooltip: skriv.skal ?? undefined };
  const visaFalt = redigerbar && !skrivs;
  const rader = Math.min(22, Math.max(8, falt.text.split("\n").length + Math.floor(falt.text.length / 72) + 1));
  const aiNamn = (v: Studioval) => text(STUDIOVAL.find((s) => s.v === v)?.namn ?? { sv: v, en: v });

  const knappGodkann = godkann ? (
    <Button
      label={godkann.etikett ?? text({ sv: "Godkänn och skicka", en: "Approve and send" })}
      variant="primary"
      icon={<Icon icon={Send} size="sm" />}
      isLoading={upptagen === "godkann"}
      isDisabled={lasning.isDisabled || (handlingslista.length > 0 && !kontrollerat)}
      tooltip={skriv.skal ?? (handlingslista.length > 0 && !kontrollerat ? text({ sv: "Bekräfta först att det utkastet påstår är gjort.", en: "First confirm that what the draft claims is done." }) : undefined)}
      onClick={() => void gor("godkann", () => godkann.gor(handlingslista.length > 0 && kontrollerat))}
    />
  ) : null;
  const knappSpara =
    visaFalt && spara && andrad ? (
      <Button label={text({ sv: "Spara", en: "Save" })} variant="secondary" icon={<Icon icon={Check} size="sm" />} isLoading={upptagen === "spara"} {...lasning} onClick={sparaNu} />
    ) : null;
  const knappAvvisa = avvisa ? (
    <Button label={text({ sv: "Avvisa", en: "Reject" })} variant="ghost" icon={<Icon icon={X} size="sm" />} className="crm-farlig" isLoading={upptagen === "avvisa"} {...lasning} onClick={() => setAvvisas(true)} />
  ) : null;

  return (
    <div className="flex flex-col gap-4">
      {visaText && mottagare !== undefined ? (
        <dl className="flex gap-2 text-[0.8125rem]">
          <dt className="w-12 shrink-0 text-ink-muted">{text({ sv: "Till", en: "To" })}</dt>
          <dd className="min-w-0 truncate text-ink2">{mottagare || text({ sv: "Ingen mottagare än", en: "No recipient yet" })}</dd>
        </dl>
      ) : null}

      {skrivs ? (
        <div className="crm-kallkort flex flex-col gap-3 rounded-[16px] p-4">
          <span className="inline-flex items-center gap-2 text-[0.875rem] text-ink2">
            <Prick ton="ockra" pulserar />
            {text({ sv: "Iris skriver utkastet. Det visas här när det är klart, och du kan lämna sidan under tiden.", en: "Iris is writing the draft. It shows here when done, and you can leave the page meanwhile." })}
          </span>
          <Skeleton width="100%" height={10} radius="rounded" />
          <Skeleton width="85%" height={10} radius="rounded" />
          <Skeleton width="62%" height={10} radius="rounded" />
        </div>
      ) : visaFalt ? (
        <>
          <TextInput
            label={text({ sv: "Ämnesrad", en: "Subject line" })}
            value={falt.amne}
            onChange={(v) => {
              setFalt((f) => ({ ...f, amne: v }));
              if (fel.amne) setFel((x) => ({ ...x, amne: undefined }));
            }}
            width="100%"
            isDisabled={!skriv.far || upptagen != null}
            disabledMessage={skriv.skal ?? undefined}
            status={fel.amne ? { type: "error", message: fel.amne } : undefined}
          />
          <div className="flex flex-col gap-2">
            <TextArea
              label={text({ sv: "Mejltext", en: "Email text" })}
              description={text({ sv: "Hälsningen och texten. Signatur och fot läggs till av Snajp.", en: "The greeting and the text. Signature and footer are added by Snajp." })}
              value={falt.text}
              onChange={(v) => {
                setFalt((f) => ({ ...f, text: v }));
                if (fel.text) setFel((x) => ({ ...x, text: undefined }));
              }}
              rows={rader}
              maxLength={TEXT_MAX}
              width="100%"
              isDisabled={!skriv.far || upptagen != null || ai.pagar != null}
              disabledMessage={skriv.skal ?? undefined}
              status={fel.text ? { type: "error", message: fel.text } : undefined}
            />
            <Mejlsvans signatur={signatur} svans={svans} />
          </div>
        </>
      ) : visaText ? (
        <Mejlvisning amne={amne} brodtext={brodtext} svans={svans} signatur={signatur} />
      ) : null}

      {/* LU-014: texten påstår att något redan är gjort. Godkänn väntar på bekräftelsen. */}
      {!skrivs && handlingslista.length ? (
        <div className="crm-kallkort flex flex-col gap-2 rounded-[16px] p-4">
          <span className="inline-flex items-center gap-2 text-[0.875rem] font-semibold text-warning">
            <Icon icon={TriangleAlert} size="sm" color="inherit" />
            {text({ sv: "Kontrollera innan du skickar", en: "Check before you send" })}
          </span>
          <p className="text-[0.8125rem] text-ink2">{text({ sv: "Utkastet säger att något redan är gjort:", en: "The draft says something has already been done:" })}</p>
          <ul className="flex flex-col gap-1">
            {handlingslista.map((m) => (
              <li key={m} className="border-l-2 border-ink/15 pl-3 text-[0.8125rem] leading-5 text-ink2">
                {m}
              </li>
            ))}
          </ul>
          <CheckboxInput label={text({ sv: "Jag har kontrollerat att det är gjort", en: "I have checked that it is done" })} value={kontrollerat} onChange={setKontrollerat} />
        </div>
      ) : null}

      {/* AI:ns förslag: visas bredvid texten när det inte skrevs in direkt, och förklaringen alltid. */}
      {ai.resultat ? (
        <section className="crm-kallkort flex flex-col gap-3 rounded-[16px] p-4" aria-label={text({ sv: "Förslaget", en: "The suggestion" })}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-[0.875rem] font-semibold text-ink">
              {DIREKTA.has(ai.resultat.action) && !ai.resultat.simulerat
                ? text({ sv: `${aiNamn(ai.resultat.action)}: står nu i texten`, en: `${aiNamn(ai.resultat.action)}: now in the text` })
                : aiNamn(ai.resultat.action)}
            </span>
            <HStack gap={1}>
              {ai.fore && visaFalt ? (
                <Button size="sm" variant="secondary" icon={<Icon icon={Undo2} size="sm" />} label={text({ sv: "Ångra", en: "Undo" })} tooltip={text({ sv: "Tillbaka till texten som stod före", en: "Back to the text from before" })} onClick={angraResultat} />
              ) : null}
              {(!DIREKTA.has(ai.resultat.action) || ai.resultat.simulerat) && ai.resultat.action !== "analyze" && visaFalt ? (
                <Button size="sm" variant="secondary" label={text({ sv: "Använd förslaget", en: "Use the suggestion" })} onClick={anvandResultat} />
              ) : null}
              <Button size="sm" variant="ghost" label={text({ sv: "Stäng", en: "Close" })} onClick={() => setAi({ pagar: null, resultat: null })} />
            </HStack>
          </div>
          {ai.resultat.simulerat ? (
            <p className="text-[0.8125rem] text-ink-muted">
              {text({ sv: "Förskrivet förslag, ingen modell kördes.", en: "Pre-written suggestion, no model ran." })} {text(simuleringsorsak(ai.resultat.orsak))}
            </p>
          ) : null}
          {!DIREKTA.has(ai.resultat.action) || ai.resultat.simulerat ? (
            ai.resultat.action !== "analyze" ? <p className="whitespace-pre-wrap break-words text-[0.875rem] leading-6 text-ink">{ai.resultat.ny}</p> : null
          ) : null}
          {ai.resultat.forklaring ? <p className="text-[0.8125rem] leading-6 text-ink2">{ai.resultat.forklaring}</p> : null}
          {ai.resultat.amnen.length > 1 ? (
            <div className="flex flex-col gap-1">
              <span className="text-[0.75rem] text-ink-muted">{text({ sv: "Förslag på ämnesrad", en: "Subject line suggestions" })}</span>
              <ul className="flex flex-col gap-0.5 text-[0.8125rem] text-ink2">
                {ai.resultat.amnen.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {ai.resultat.tips ? <p className="text-[0.8125rem] leading-6 text-ink-muted">{ai.resultat.tips}</p> : null}
        </section>
      ) : null}

      {/* Skriv om: Iris skriver ett nytt utkast, med struktur och önskemål. */}
      {omskrivning ? (
        <div className="crm-skrivyta flex flex-col gap-3 rounded-[16px] p-4">
          {skrivOm?.struktur ? (
            <div className="max-w-[320px]">
              <StrukturVal value={omskrivning.struktur} onChange={(v) => setOmskrivning((o) => (o ? { ...o, struktur: v } : o))} />
            </div>
          ) : null}
          {skrivOm?.onskemal ? (
            <TextArea
              label={text({ sv: "Önskemål till Iris", en: "Request to Iris" })}
              isOptional
              placeholder={text({ sv: "Föreslå två tider nästa vecka", en: "Suggest two times next week" })}
              value={omskrivning.onskemal}
              onChange={(v) => setOmskrivning((o) => (o ? { ...o, onskemal: v } : o))}
              rows={2}
              maxLength={1000}
              width="100%"
            />
          ) : null}
          <p className="text-[0.8125rem] text-ink-muted">
            {text({ sv: "Det väntande utkastet ersätts och skickas aldrig. Det nya väntar på ditt ja.", en: "The pending draft is replaced and never sent. The new one waits for your yes." })}
          </p>
          <HStack gap={2} justify="end">
            <Button size="sm" variant="ghost" label={text({ sv: "Avbryt", en: "Cancel" })} isDisabled={upptagen === "skriv"} onClick={() => setOmskrivning(null)} />
            <Button size="sm" variant="primary" label={text({ sv: "Skriv om", en: "Rewrite" })} icon={<Icon icon={RefreshCw} size="sm" />} isLoading={upptagen === "skriv"} {...lasning} onClick={skrivOmNu} />
          </HStack>
        </div>
      ) : null}

      {!skrivs ? (
        <div className="flex flex-wrap items-center gap-2">
          {fot ? null : knappGodkann}
          {fot ? null : knappSpara}
          {skrivOm && !omskrivning ? (
            <Button label={text({ sv: "Skriv om", en: "Rewrite" })} variant="secondary" icon={<Icon icon={RefreshCw} size="sm" />} {...lasning} onClick={startaOmskrivning} />
          ) : null}
          {kontext && visaFalt ? (
            <DropdownMenu
              button={{
                label: ai.pagar ? text({ sv: `${aiNamn(ai.pagar)} pågår`, en: `${aiNamn(ai.pagar)} running` }) : text({ sv: "Bearbeta texten", en: "Edit the text" }),
                variant: "ghost",
                icon: <Icon icon={Sparkles} size="sm" />,
                isLoading: ai.pagar != null,
                isDisabled: lasning.isDisabled,
                tooltip: lasning.tooltip
              }}
              items={STUDIOVAL.map((s) => ({
                label: text(s.namn),
                description: DIREKTA.has(s.v) ? text({ sv: "Skrivs in i texten", en: "Written into the text" }) : text({ sv: "Visas bredvid, du väljer", en: "Shown beside it, you choose" }),
                onClick: () => void korStudio(s.v)
              }))}
            />
          ) : null}
          {provmejl && (provmejl.queueItemId || provmejl.messageId) ? (
            <Button label={text({ sv: "Skicka provmejl", en: "Send test email" })} variant="ghost" icon={<Icon icon={Mail} size="sm" />} {...lasning} onClick={() => void oppnaProv()} />
          ) : null}
          {extra}
          {fot ? null : knappAvvisa}
        </div>
      ) : null}

      {/* Utfallet sägs upp i en region som finns hela tiden. Med en fot står det där, ovanför besluten. */}
      {((utfall: React.ReactNode) =>
        fot
          ? createPortal(
              <div className="flex min-w-0 flex-col gap-3">
                {utfall}
                {!skrivs ? (
                  <div className="flex flex-wrap items-center gap-2">
                    {knappGodkann}
                    {knappSpara}
                    {knappAvvisa}
                  </div>
                ) : null}
              </div>,
              fot
            )
          : utfall)(
      <div role="status" aria-live="polite">
        {/* Förloppet medan Iris skriver sägs här; rutan ovanför visar det bara. */}
        {skrivs ? <span className="sr-only">{text({ sv: "Iris skriver utkastet.", en: "Iris is writing the draft." })}</span> : null}
        {ai.pagar ? <Text color="secondary" type="supporting">{text({ sv: `${aiNamn(ai.pagar)}: AI:n skriver om texten.`, en: `${aiNamn(ai.pagar)}: the AI is rewriting the text.` })}</Text> : null}
        {besked ? (
          <Banner
            status={besked.fel ? "error" : "success"}
            container="card"
            title={besked.text}
            description={
              besked.orsaker?.length ? (
                <ul className="mt-1 flex flex-col gap-1">
                  {besked.orsaker.map((o) => (
                    <li key={o}>{o}</li>
                  ))}
                </ul>
              ) : undefined
            }
          />
        ) : null}
      </div>
      )}

      <Dialog isOpen={prov != null} onOpenChange={(o) => !o && upptagen !== "prov" && setProv(null)} purpose="form" width={480}>
        <Layout
          header={<DialogHeader title={text({ sv: "Skicka provmejl", en: "Send test email" })} onOpenChange={(o) => !o && upptagen !== "prov" && setProv(null)} />}
          content={
            <LayoutContent>
              <div className="flex flex-col gap-4">
                {prov?.adresser == null ? (
                  <div role="status" aria-busy="true" aria-label={text({ sv: "Hämtar era adresser", en: "Loading your addresses" })}>
                    <Skeleton width="70%" height={36} radius={2} />
                  </div>
                ) : prov.adresser.length === 0 ? (
                  <Text color="secondary">
                    {text({ sv: "Det finns ingen egen adress att skicka provet till. Koppla en brevlåda eller fyll i e-post i signaturen under Inställningar.", en: "There is no address of your own to send the test to. Connect a mailbox or add an email to the signature under Settings." })}
                  </Text>
                ) : (
                  <Selector
                    label={text({ sv: "Skicka provet till", en: "Send the test to" })}
                    value={prov.vald}
                    onChange={(v) => v && setProv((p) => (p ? { ...p, vald: v } : p))}
                    options={prov.adresser.map((a) => ({ value: a, label: a }))}
                    width="100%"
                  />
                )}
                {/* Felet från provet står här, i dialogen, i en region som finns hela tiden. */}
                <div role="status">{prov?.fel ? <Banner status="error" container="card" title={prov.fel} /> : null}</div>
                <Text color="secondary" type="supporting">
                  {text({ sv: "Provet går bara till er, precis som leadet skulle få det. Utkastet och leadet påverkas inte.", en: "The test only goes to you, exactly as the lead would receive it. The draft and the lead are not affected." })}
                </Text>
              </div>
            </LayoutContent>
          }
          footer={
            <LayoutFooter>
              <HStack justify="end" gap={2}>
                <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" isDisabled={upptagen === "prov"} onClick={() => setProv(null)} />
                <Button label={text({ sv: "Skicka provet", en: "Send the test" })} variant="primary" icon={<Icon icon={Mail} size="sm" />} isLoading={upptagen === "prov"} isDisabled={!prov?.vald} onClick={skickaProv} />
              </HStack>
            </LayoutFooter>
          }
        />
      </Dialog>

      <AlertDialog
        isOpen={avvisas}
        onOpenChange={(o) => !o && upptagen !== "avvisa" && setAvvisas(false)}
        title={text({ sv: "Avvisa utkastet?", en: "Reject the draft?" })}
        description={text(avvisa?.fraga ?? { sv: "Utkastet skickas aldrig. Du kan skapa ett nytt efteråt.", en: "The draft is never sent. You can create a new one afterwards." })}
        actionLabel={text({ sv: "Avvisa", en: "Reject" })}
        cancelLabel={text({ sv: "Avbryt", en: "Cancel" })}
        isActionLoading={upptagen === "avvisa"}
        onAction={() => {
          if (!avvisa) return;
          void gor(
            "avvisa",
            async () => {
              // Dialogen stängs även när avvisningen faller, så att felet syns i regionen under knapparna.
              try {
                return await avvisa.gor();
              } finally {
                setAvvisas(false);
              }
            },
            false
          );
        }}
      />
    </div>
  );
}
