"use client";

import { Check, FileText, ImagePlus, Loader2, Send, ThumbsDown, ThumbsUp, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { btnPrimary, btnSecondary } from "@/components/ui";
import { AgentMenu } from "@/components/snajp/AgentMenu";
import { LÄSBARA, läsbar } from "@/components/settings/Kunskapsbas";
import { HttpJsonError, felmeddelande, readJsonBody } from "@/lib/http/json";
import { useLocale } from "@/lib/i18n";
import { getTenant } from "@/lib/tenants";
import { cn } from "@/lib/utils";

type KbSource = { title: string; similarity: number };

type AgentMeta = {
  category_label?: string;
  sentiment?: number | null;
  escalated?: boolean;
  escalation_reason?: string | null;
  kb_sources?: KbSource[];
  simulation?: boolean;
  ticket_id?: string | null;
  // Fas 5 (Testchatt, plan §6.2/6.3): utan run_id går ett agentsvar inte att
  // koppla till en rad i agent_runs, och feedbacken (tumme upp/ned) har
  // ingenstans att peka. Backenden skickar fältet sedan 2026-08-29; saknas
  // det (t.ex. gammal deploy) döljs bara feedback-raden för det svaret.
  run_id?: string | null;
};

type ChatMessage = {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  imagePreview?: string;
  meta?: AgentMeta;
};

/**
 * Testchatt-lägets två kortyper (Fas 5.4/5.5/5.6), i SAMMA flöde som
 * chattbubblorna och inte en parallell lista — de ska visas i den ordning de
 * tillkom, mellan meddelandena, och en andra array att sammanfläta vid
 * rendering är bara en plats till att få ordningen fel.
 */
type KbForhandsvisningKort = {
  id: string;
  role: "kb-forhandsvisning";
  kalla: "textfil" | "pdf";
  filnamn: string;
  titel: string;
  innehall: string;
  sidor?: number;
  varning?: string | null;
  status: "extraherar" | "forhandsvisning" | "sparar" | "sparad" | "fel";
  fel?: string | null;
};

type ForslagKort = {
  id: string;
  role: "forslag-kort";
  suggestionId: string;
  kind: string;
  rubrik: string;
  brodtext: string;
  status: "oppet" | "sparar" | "sparat" | "avfardar" | "avfardat" | "fel";
  fel?: string | null;
};

type FeedItem = ChatMessage | KbForhandsvisningKort | ForslagKort;

/** Rått svar från GET /api/agent/forslag — se components/leads/AgentLarande.tsx,
 * som listar samma resurs i lärande-vyn och tolkar samma content-form. */
type RaForslag = {
  id: string;
  kind: string;
  title: string;
  content:
    | { title?: string; content?: string; gap?: string; icp_adjustment?: string }
    | string;
  status: string;
  created_at: string;
};

function tolkaJson(s: string): Record<string, unknown> {
  try {
    return JSON.parse(s) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function forslagsInnehall(f: RaForslag): { rubrik: string; brodtext: string } {
  const c = typeof f.content === "string" ? tolkaJson(f.content) : f.content;
  if (f.kind === "kb_article") {
    return { rubrik: (c.title as string) || f.title, brodtext: (c.content as string) || "" };
  }
  return {
    rubrik: f.title,
    brodtext: [c.gap, c.icp_adjustment].filter(Boolean).join("\n\n")
  };
}

type FeedbackLage = {
  fas: "vila" | "rattar" | "skickar" | "skickad" | "fel";
  verdict?: "good" | "bad";
  text?: string;
  fel?: string;
};

const examplePrompts = [
  "Min faktura drogs två gånger från kortet, vad gör jag?",
  "Mitt paket är försenat och spårningen har inte uppdaterats på fyra dagar.",
  "Jag får felkod E-101 i kassan när jag försöker betala.",
  "Varan kom fram trasig. Jag vill ha pengarna tillbaka NU!"
];

async function downscaleImage(file: File, maxSize = 1024): Promise<string> {
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Kunde inte läsa filen"));
    reader.readAsDataURL(file);
  });

  const image = await new Promise<HTMLImageElement>((resolve, reject) => {
    const element = new Image();
    element.onload = () => resolve(element);
    element.onerror = () => reject(new Error("Kunde inte tolka bilden"));
    element.src = dataUrl;
  });

  const scale = Math.min(1, maxSize / Math.max(image.width, image.height));
  if (scale === 1 && dataUrl.length < 1_500_000) {
    return dataUrl;
  }
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(image.width * scale);
  canvas.height = Math.round(image.height * scale);
  canvas.getContext("2d")?.drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.85);
}

/**
 * `tenant` och `session` sätts av den publika supportlänken
 * (/chat/<kund>/<session>). Utan dem beter sig komponenten som demon på
 * marknadsföringssidan gjorde tidigare — samma kod, två användningar.
 */
export type SupportChatProps = {
  tenant?: string;
  session?: string;
  /**
   * Testchatt-fliken (Fas 5, plan 2026-08-28 §6, bd snipe-0r9): samma
   * komponent mot den INLOGGADE tenanten i stället för demo eller en publik
   * länk. Default AV, av flit — den PUBLIKA widgeten (denna komponent utan
   * props, och /chat/[tenant]/[session]) ska aldrig få tummar, filbilaga
   * mot kunskapsbasen eller förslagskort. Slår på fyra saker tillsammans:
   * autentiserad routning (session avgör tenant, ingen slug behövs),
   * is_test: true i chattkroppen, feedback-UI (6.3), och
   * KB-filbilaga/PDF-extraktion/förslagskort (6.4-6.6).
   */
  testMode?: boolean;
  /** Bara i testMode: namnet som visas i chatthuvudet i stället för ett
   * kundvarumärke — det finns inget varumärke i test, bara arbetsytan. */
  workspaceLabel?: string;
};

/**
 * Ett id per flik för demon, som saknar session i URL:en.
 *
 * Alla demobesökare delade tidigare EN kundidentitet hos backenden. Så länge
 * agenten bara fick ANTALET tidigare kontakter var det ofarligt. Nu följer
 * utskriften av samtalet med in i prompten, och då hade nästa besökare fått
 * föregående besökares repliker som kontext.
 *
 * Läses vid utskick och inte i en effekt, så att det aldrig finns ett fönster
 * där identiteten är null och adressen blir "null@session.snajp.se".
 */
/**
 * Fel visas som en mening en människa kan agera på — aldrig `error.message`
 * från ett kastat undantag. Den vägen visade tidigare stringifierade
 * Python-undantag ("'ascii' codec can't encode character…") och webbläsarens
 * "Failed to fetch" i den publika chattens röda bubbla. Små pooler i stället
 * för en konstant, så att tre fel i rad inte läser som en papegoja.
 */
const FELTEXTER = [
  "Jag fick inte fram ett svar den här gången. Prova gärna att skicka frågan igen om en liten stund.",
  "Något hakade upp sig på vägen — frågan kom aldrig hela vägen fram. Skicka den gärna en gång till.",
  "Där tappade jag tråden. Ställ gärna frågan igen, eller formulera den på ett annat sätt så gör jag ett nytt försök."
];

const TIMEOUT_TEXTER = [
  "Det här svaret tog längre tid än det borde. Skicka gärna frågan igen — andra försöket brukar gå fortare.",
  "Svaret hann inte bli klart. Prova igen om en liten stund, så tar jag det därifrån."
];

function slumpad(texter: string[]): string {
  return texter[Math.floor(Math.random() * texter.length)];
}

/** Ett fel vars text är skriven för kunden och därför FÅR visas ordagrant. */
class VisbartFel extends Error {}

function demoSessionId(): string {
  const KEY = "snajp.demo.session";
  let id = window.sessionStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.sessionStorage.setItem(KEY, id);
  }
  return id;
}

/** Samma mönster som demoSessionId, EGEN nyckel: en testchatt-flik ska inte
 * dela identitet med demon på marknadssidan (skilda sessionStorage-poster i
 * samma webbläsare), och tenanten är ändå alltid den inloggades — sessionen
 * avgör det, inte det här id:t. */
function testchattSessionId(): string {
  const KEY = "snajp.testchatt.session";
  let id = window.sessionStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.sessionStorage.setItem(KEY, id);
  }
  return id;
}

//: R1.5 — pollningen mot jobbet ska tåla ett transient 5xx/nätfel under en
//: deploy (Railway rullar en ny container, ett anrop hinner slå fel mitt i)
//: i stället för att direkt ge upp på EN missad kontroll av 90. Tre extra
//: försök, 1/2/4 sekunder, innan felet får gå vidare till den vanliga
//: felhanteringen i send().
const JOBBPOLL_BACKOFF_MS = [1000, 2000, 4000];

type JobbSvar = {
  offline?: boolean;
  error?: string;
  status?: string;
  result?: { simulation?: boolean; reply: string; run_id?: string | null };
};

async function hamtaJobbstatusMedRetry(url: string): Promise<JobbSvar> {
  for (let forsok = 0; ; forsok += 1) {
    try {
      const response = await fetch(url);
      return (await readJsonBody<JobbSvar>(response)) ?? {};
    } catch (fel) {
      const transient =
        fel instanceof TypeError ||
        (fel instanceof DOMException && fel.name === "AbortError") ||
        (fel instanceof HttpJsonError && fel.status >= 500);
      if (!transient || forsok >= JOBBPOLL_BACKOFF_MS.length) {
        throw fel;
      }
      await new Promise((resolve) => setTimeout(resolve, JOBBPOLL_BACKOFF_MS[forsok]));
    }
  }
}

export function SupportChat({
  tenant,
  session,
  testMode = false,
  workspaceLabel
}: SupportChatProps = {}) {
  // Demons varumärke och exempelfrågor gäller demon. På en kunds supportsida är
  // "Nordlys Handel" och frågor om felkoder i kassan direkt vilseledande — de
  // namnger en påhittad butik och ett sortiment kunden inte har. I testMode
  // finns inget varumärke att visa — bara arbetsytans eget namn, om det gavs.
  const tenantConfig = tenant ? getTenant(tenant) : null;
  const brandLabel = testMode ? (workspaceLabel ?? "Din arbetsyta") : (tenantConfig?.name ?? "Nordlys Handel");
  const intro = testMode
    ? "Testa agenten mot din egen kunskapsbas. Körningar här märks som test och räknas inte som kundtrafik."
    : (tenantConfig?.supportIntro ?? null);
  const prompts = tenantConfig?.supportPrompts ?? examplePrompts;

  // The poll loop runs up to 90 iterations; without this it keeps writing state
  // after the component is gone.
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);
  const { text } = useLocale();
  const [messages, setMessages] = useState<FeedItem[]>([]);
  const [input, setInput] = useState("");
  const [attachment, setAttachment] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Sant medan vi ger backenden en andra chans att vakna ur viloläge — då
  // byter arbetsindikatorn text så att väntan har en förklaring.
  const [vaknar, setVaknar] = useState(false);
  const [mode, setMode] = useState<"unknown" | "simulation" | "live" | "offline">("unknown");
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  // Testchatt-läget bara nedanför:
  const kbFileRef = useRef<HTMLInputElement>(null);
  const [feedbackByMsg, setFeedbackByMsg] = useState<Record<string, FeedbackLage>>({});
  // Tidpunkten fliken öppnades: förslag som fanns SEDAN INNAN ska inte dyka
  // upp som om agenten just hittade dem (6.6, "tillkommit sedan chatten
  // öppnades"). ID:n för redan visade förslag hindrar dubbletter vid nästa
  // uppdatering.
  const testchattOppnadRef = useRef<number>(Date.now());
  const kandaForslagRef = useRef<Set<string>>(new Set());


  useEffect(() => {
    // Bara när det finns meddelanden att scrolla till. På en tom chatt scrollade
    // detta förbi introtexten och startfrågorna, vilket på smala skärmar såg ut
    // som att sidan var avklippt i överkant.
    if (messages.length === 0) {
      return;
    }
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  const send = useCallback(
    async (messageText: string) => {
      const trimmed = messageText.trim();
      if (!trimmed || busy) {
        return;
      }
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
        imagePreview: attachment ?? undefined
      };
      setMessages((current) => [...current, userMessage]);
      setInput("");
      const attachments = attachment ? [{ data_url: attachment }] : [];
      setAttachment(null);
      setBusy(true);

      try {
        const posta = async () => {
          // Testchatt går via en EGEN, autentiserad proxy: tenanten kommer
          // ur sessionen (proxyAsTenant), inte ur en slug som klienten
          // skickar — den publika /chat-routen är anonym med flit
          // (INV-SEC-010) och löser bara kända, konfigurerade tenants.
          const chatUrl = testMode ? "/api/snajp-support/testchatt" : "/api/snajp-support/chat";
          const sessionId = testMode ? testchattSessionId() : (session ?? demoSessionId());
          const response = await fetch(chatUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              message: trimmed,
              channel: "web",
              // En besökare identifieras av sitt session-id tills hen uppger något
              // mer. Demon får ett eget id per flik (demoSession) i stället för en
              // delad identitet, så att ingen ser spår av föregående besökare.
              // Testchatten har sin egen sessionsnyckel av samma skäl.
              customer_email: `${sessionId}@session.snajp.se`,
              customer_name: testMode ? "Testchatt" : session ? "Webbesökare" : "Demo Kund",
              session_key: sessionId,
              tenant,
              attachments,
              // Fas 5.1/6.1: märker körningen i agent_runs, se
              // app/api/schemas.ChatRequest.is_test. Alltid false utanför
              // testMode — ingen annan anropare ska kunna sätta den.
              is_test: testMode
            })
          });
          // readJsonBody behåller offline-läget (503 med `offline: true`) som ett
          // läge i UI:t, men kastar läsbart om kroppen är tom eller inte JSON.
          const payload =
            (await readJsonBody<{
              offline?: boolean;
              error?: string;
              /** FastAPI:s HTTPException lägger texten i `detail`, inte `error`.
               *  Rate limit-429:an (chat.py) går den vägen; LLM-kvotens 429 går
               *  via `error`. Båda ska nå användaren — se throw nedan. */
              detail?: string;
              job_id?: string;
            }>(response)) ?? {};
          return { response, payload };
        };

        let { response, payload } = await posta();

        // Offline betyder oftast kallstart, och den läker av sig själv inom en
        // minut. En andra chans i det tysta — med en förklarande arbetstext —
        // är bättre än att direkt be besökaren försöka själv.
        if (payload.offline) {
          setVaknar(true);
          try {
            await new Promise((resolve) => setTimeout(resolve, 5000));
            if (!alive.current) return;
            ({ response, payload } = await posta());
          } finally {
            setVaknar(false);
          }
        }

        if (payload.offline) {
          setMode("offline");
          setMessages((current) => [
            ...current,
            {
              id: crypto.randomUUID(),
              role: "system",
              content: payload.error ?? "Assistenten är inte tillgänglig just nu. Försök gärna igen om en liten stund."
            }
          ]);
          return;
        }
        if (!response.ok || !payload.job_id) {
          // 429 bär backendens egen, väl formulerade text. Allt annat får en
          // kuraterad mening — payload.error kan i värsta fall vara teknisk.
          // Uppmätt i drift 2026-08-27: rate limit-429:an kommer som `detail`
          // (FastAPI HTTPException), LLM-kvotens som `error` — utan båda
          // fälten visades "Okänt fel" i stället för kvottexten.
          const kvottext = payload.error ?? payload.detail;
          throw new VisbartFel(
            response.status === 429 && kvottext ? kvottext : slumpad(FELTEXTER)
          );
        }

        for (let attempt = 0; attempt < 90; attempt += 1) {
          await new Promise((resolve) => setTimeout(resolve, attempt < 5 ? 800 : 2000));
          // Tenanten måste med: jobbet skapades med kundens nyckel, och utan
          // den pollar vi demo-tenanten där jobbet inte finns. Testchatten
          // har sin egen, autentiserade pollningsroute (session avgör
          // tenanten, ingen ?tenant= behövs eller godtas där).
          const jobUrl = testMode
            ? `/api/snajp-support/testchatt/jobb/${payload.job_id}`
            : tenant
              ? `/api/snajp-support/jobs/${payload.job_id}?tenant=${encodeURIComponent(tenant)}`
              : `/api/snajp-support/jobs/${payload.job_id}`;
          // R1.5: retry med backoff INUTI varje pollningsförsök — en enstaka
          // transient 5xx/nätfel under en deploy ska inte avsluta hela
          // väntan, bara den här kontrollen.
          const job = await hamtaJobbstatusMedRetry(jobUrl);
          if (job.offline) {
            setMode("offline");
            setMessages((current) => [
              ...current,
              {
                id: crypto.randomUUID(),
                role: "system",
                content: job.error ?? "Supporten är inte tillgänglig just nu. Försök igen om en stund."
              }
            ]);
            return;
          }
          if (!alive.current) return;
          if (job.status === "completed" && job.result) {
            // Lokal bindning: inuti setMessages-callbacken kan TS inte behålla
            // avsmalningen av job.result.
            const resultat = job.result;
            setMode(resultat.simulation ? "simulation" : "live");
            setMessages((current) => [
              ...current,
              {
                id: crypto.randomUUID(),
                role: "agent",
                content: resultat.reply,
                meta: resultat
              }
            ]);
            // Fas 5.6: agentens föreslagna KB-ändringar dyker upp som kort
            // strax efter svaret. En bakgrundshämtning som inte blockerar
            // eller kan fela chatten — förslag är en bonus i flödet.
            if (testMode) {
              void uppdateraForslag();
            }
            return;
          }
          if (job.status === "failed") {
            // job.error var tidigare det stringifierade Python-undantaget och
            // visades ordagrant. Diagnosen finns i backend-loggen; besökaren
            // får en mening som pekar framåt.
            throw new VisbartFel(slumpad(FELTEXTER));
          }
        }
        throw new VisbartFel(slumpad(TIMEOUT_TEXTER));
      } catch (error) {
        // VisbartFel är skrivet för kunden. HttpJsonError/AbortError/TypeError
        // får sina svenska texter via felmeddelande. Allt annat — okända
        // undantag med tekniska meddelanden — blir en kuraterad mening, och
        // detaljen går till konsolen i stället för till chattbubblan.
        if (!(error instanceof VisbartFel)) {
          console.error("SupportChat:", error);
        }
        const content =
          error instanceof VisbartFel
            ? error.message
            : error instanceof HttpJsonError || (error instanceof DOMException && error.name === "AbortError") || error instanceof TypeError
              ? felmeddelande(error, slumpad(FELTEXTER))
              : slumpad(FELTEXTER);
        setMessages((current) => [
          ...current,
          { id: crypto.randomUUID(), role: "system", content }
        ]);
      } finally {
        setBusy(false);
      }
    },
    // uppdateraForslag är MEDVETET inte med här: den deklareras längre ned i
    // komponenten (efter send), så en referens till den i den här arrayen
    // hade evaluerats innan den konstanten är initierad — en TDZ-krasch vid
    // varje rendering, inte bara en saknad lint-rad. send() anropar den
    // ändå korrekt, eftersom anropet sker långt efter att hela komponenten
    // (och därmed uppdateraForslag) har initierats klart.
    [attachment, busy, testMode]
  );

  const onFile = useCallback(async (file: File | undefined) => {
    if (!file) {
      return;
    }
    if (!file.type.startsWith("image/")) {
      return;
    }
    try {
      setAttachment(await downscaleImage(file));
    } catch {
      setAttachment(null);
    }
  }, []);

  // -- Testchatt-läget: KB-filbilaga (6.4/6.5) -----------------------------

  const laggTillIKb = useCallback(
    async (kortId: string) => {
      const kort = messages.find((item) => item.id === kortId);
      if (!kort || kort.role !== "kb-forhandsvisning") return;
      setMessages((current) =>
        current.map((item) =>
          item.id === kortId && item.role === "kb-forhandsvisning" ? { ...item, status: "sparar", fel: null } : item
        )
      );
      try {
        // Samma väg Kunskapsbas-inställningarna använder (POST /api/kb, se
        // components/settings/Kunskapsbas.tsx) — människans klick HÄR är
        // godkännandet, INV-LEARN-001 hålls: agenten skriver ingenting själv.
        const response = await fetch("/api/snajp-support/kb", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ articles: [{ title: kort.titel, content: kort.innehall }] })
        });
        const kropp = await readJsonBody<{ error?: string; detail?: string }>(response);
        if (!response.ok) {
          throw new Error(kropp?.detail ?? kropp?.error ?? `Kunde inte spara (${response.status}).`);
        }
        setMessages((current) =>
          current.map((item) =>
            item.id === kortId && item.role === "kb-forhandsvisning" ? { ...item, status: "sparad" } : item
          )
        );
      } catch (cause) {
        setMessages((current) =>
          current.map((item) =>
            item.id === kortId && item.role === "kb-forhandsvisning"
              ? { ...item, status: "fel", fel: felmeddelande(cause) }
              : item
          )
        );
      }
    },
    [messages]
  );

  const hanteraPdf = useCallback(async (file: File) => {
    // Kunden ser gränsen direkt, före uppladdningen — backendens
    // MAX_PDF_BYTES (app/api/kb.py) är den exakta, verkställda kontrollen.
    if (file.size > 8 * 1024 * 1024) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "system",
          content: `${file.name} är för stor. Taket för PDF är ungefär 8 MB.`
        }
      ]);
      return;
    }
    const kortId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      {
        id: kortId,
        role: "kb-forhandsvisning",
        kalla: "pdf",
        filnamn: file.name,
        titel: file.name.replace(/\.[^.]+$/, ""),
        innehall: "",
        status: "extraherar"
      }
    ]);
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () => reject(new Error("Kunde inte läsa filen."));
        reader.readAsDataURL(file);
      });
      const response = await fetch("/api/snajp-support/kb/extrahera", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: file.name, data_url: dataUrl })
      });
      const kropp = await readJsonBody<{
        text?: string;
        sidor?: number;
        varning?: string | null;
        error?: string;
        detail?: string;
      }>(response);
      if (!response.ok) {
        throw new Error(kropp?.detail ?? kropp?.error ?? `Kunde inte läsa PDF:en (${response.status}).`);
      }
      setMessages((current) =>
        current.map((item) =>
          item.id === kortId && item.role === "kb-forhandsvisning"
            ? {
                ...item,
                status: "forhandsvisning",
                innehall: kropp?.text ?? "",
                sidor: kropp?.sidor,
                varning: kropp?.varning ?? null
              }
            : item
        )
      );
    } catch (cause) {
      setMessages((current) =>
        current.map((item) =>
          item.id === kortId && item.role === "kb-forhandsvisning"
            ? { ...item, status: "fel", fel: felmeddelande(cause) }
            : item
        )
      );
    }
  }, []);

  const onKbFile = useCallback(
    async (file: File | undefined) => {
      if (!file) return;
      const namn = file.name;
      if (namn.toLowerCase().endsWith(".pdf")) {
        await hanteraPdf(file);
        return;
      }
      if (!läsbar(namn)) {
        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "system",
            content: `Filformatet stöds inte. Läsbara format är ${LÄSBARA.join(", ")} samt PDF.`
          }
        ]);
        return;
      }
      // KLIENTSIDIG läsning, exakt som components/settings/Kunskapsbas.tsx —
      // innehållet går ALDRIG in i chattmeddelandet, bara till förhands-
      // visningskortet nedan.
      const innehall = (await file.text()).trim();
      if (!innehall) {
        setMessages((current) => [
          ...current,
          { id: crypto.randomUUID(), role: "system", content: `${namn} verkar vara tom och lades inte till.` }
        ]);
        return;
      }
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "kb-forhandsvisning",
          kalla: "textfil",
          filnamn: namn,
          titel: namn.replace(/\.[^.]+$/, ""),
          innehall,
          status: "forhandsvisning"
        }
      ]);
    },
    [hanteraPdf]
  );

  // -- Testchatt-läget: agentens förslag (6.6) -----------------------------

  const uppdateraForslag = useCallback(async () => {
    try {
      const response = await fetch("/api/snajp-support/agent/forslag?status=ny", { cache: "no-store" });
      if (!response.ok) return;
      const kropp = await readJsonBody<{ suggestions?: RaForslag[] }>(response);
      const nya = (kropp?.suggestions ?? []).filter((f) => {
        if (kandaForslagRef.current.has(f.id)) return false;
        const tid = new Date(f.created_at).getTime();
        return Number.isFinite(tid) && tid > testchattOppnadRef.current;
      });
      if (nya.length === 0 || !alive.current) return;
      nya.forEach((f) => kandaForslagRef.current.add(f.id));
      setMessages((current) => [
        ...current,
        ...nya.map((f): ForslagKort => {
          const { rubrik, brodtext } = forslagsInnehall(f);
          return {
            id: crypto.randomUUID(),
            role: "forslag-kort",
            suggestionId: f.id,
            kind: f.kind,
            rubrik,
            brodtext,
            status: "oppet"
          };
        })
      ]);
    } catch {
      // Förslag är en bonus i flödet, inte en kritisk väg — chatten ska
      // fungera precis lika bra om den här hämtningen misslyckas tyst.
    }
  }, []);

  const avgorForslag = useCallback(async (kortId: string, suggestionId: string, handling: "godkann" | "avfard") => {
    setMessages((current) =>
      current.map((item) =>
        item.id === kortId && item.role === "forslag-kort"
          ? { ...item, status: handling === "godkann" ? "sparar" : "avfardar", fel: null }
          : item
      )
    );
    try {
      const response = await fetch(`/api/snajp-support/agent/forslag/${suggestionId}/${handling}`, {
        method: "POST"
      });
      if (!response.ok) {
        throw new Error();
      }
      setMessages((current) =>
        current.map((item) =>
          item.id === kortId && item.role === "forslag-kort"
            ? { ...item, status: handling === "godkann" ? "sparat" : "avfardat" }
            : item
        )
      );
    } catch {
      setMessages((current) =>
        current.map((item) =>
          item.id === kortId && item.role === "forslag-kort"
            ? { ...item, status: "fel", fel: "Kunde inte spara. Försök igen." }
            : item
        )
      );
    }
  }, []);

  // -- Testchatt-läget: feedback per svar (6.3) ----------------------------

  const uppdateraFeedback = useCallback((messageId: string, patch: Partial<FeedbackLage>) => {
    setFeedbackByMsg((current) => ({
      ...current,
      [messageId]: { ...(current[messageId] ?? { fas: "vila" }), ...patch }
    }));
  }, []);

  const skickaFeedback = useCallback(
    async (messageId: string, runId: string, verdict: "good" | "bad", correctedOutput?: string) => {
      uppdateraFeedback(messageId, { fas: "skickar", verdict });
      try {
        const response = await fetch("/api/snajp-support/agent/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            run_id: runId,
            verdict,
            corrected_output: correctedOutput?.trim() ? correctedOutput.trim() : undefined
          })
        });
        if (!response.ok) {
          throw new Error();
        }
        uppdateraFeedback(messageId, { fas: "skickad", verdict });
      } catch {
        uppdateraFeedback(messageId, { fas: "fel", verdict, fel: "Kunde inte skicka. Försök igen." });
      }
    },
    [uppdateraFeedback]
  );

  // Bara uppe eller nere. Om svaret kom från en riktig modell eller en simulering
  // är vår information, inte kundens — "Online · Live-AI" bredvid företagsnamnet
  // säger ingenting kunden kan använda och avslöjar hur vi kör tjänsten.
  const statusLabel =
    mode === "offline"
      ? text({ sv: "Offline", en: "Offline" })
      : text({ sv: "Online", en: "Online" });

  return (
    <div className="overflow-hidden rounded-card bg-paper">
      <div className="flex items-center justify-between gap-4 bg-paper2/70 px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="relative flex h-2.5 w-2.5">
            <span
              className={cn(
                "absolute inline-flex h-full w-full animate-ping rounded-full opacity-60",
                mode === "offline" ? "bg-danger" : "bg-moss"
              )}
            />
            <span
              className={cn(
                "relative inline-flex h-2.5 w-2.5 rounded-full",
                mode === "offline" ? "bg-danger" : "bg-moss"
              )}
            />
          </span>
          <p className="text-sm font-semibold">
            Snajp Support
            <span className="ml-2 font-normal text-ink/50">{statusLabel}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-ink/45 md:block">{brandLabel}</span>
          {/* Menyn sitter i chattens huvud och inte i sidfoten: den som vill
              anmäla ett felaktigt svar eller läsa dataskyddstexten letar
              uppåt, inte nedanför en scrollande meddelandelista. */}
          <AgentMenu yta="kundservice" kontext={tenant ? `tenant=${tenant}` : "demo"} />
        </div>
      </div>

      <div ref={scrollRef} className="h-[420px] space-y-4 overflow-y-auto px-5 py-6">
        {messages.length === 0 ? (
          // m-auto i stället för justify-center: i en scrollcontainer gör
          // justify-center att överskottet ovanför blir oåtkomligt, och vid 320px
          // kapades introtextens första rad. Auto-marginaler centrerar när det
          // finns plats och släpper taget när det inte gör det.
          <div className="flex min-h-full flex-col items-center text-center">
            <div className="m-auto flex flex-col items-center gap-5 py-2">
            <p className="max-w-md text-[0.9375rem] leading-6 text-ink/60">
              {intro ??
                text({
                  sv: "Du kan också ladda upp en skärmdump eller en bild på en skadad vara.",
                  en: "You can also upload a screenshot or a photo of a damaged item."
                })}
            </p>
            <div className="flex max-w-lg flex-wrap justify-center gap-2">
              {prompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => send(prompt)}
                  className="focus-ring min-h-11 rounded-input bg-paper2/80 px-3 py-2 text-left text-[0.8125rem] leading-5 text-ink/75 transition-colors hover:bg-paper2 hover:text-ink"
                >
                  {prompt}
                </button>
              ))}
            </div>
            </div>
          </div>
        ) : null}

        {messages.map((message) => {
          if (message.role === "kb-forhandsvisning") {
            return <KbForhandsvisningKortVy key={message.id} kort={message} onLaggTill={() => void laggTillIKb(message.id)} />;
          }
          if (message.role === "forslag-kort") {
            return (
              <ForslagKortVy
                key={message.id}
                kort={message}
                onGodkann={() => void avgorForslag(message.id, message.suggestionId, "godkann")}
                onAvfard={() => void avgorForslag(message.id, message.suggestionId, "avfard")}
              />
            );
          }
          return (
            <div key={message.id} className={cn("flex flex-col", message.role === "user" ? "items-end" : "items-start")}>
              <div
                className={cn(
                  "max-w-[85%] rounded-card px-4 py-3 text-[0.9375rem] leading-6",
                  message.role === "user"
                    ? "bg-ink text-paper"
                    : message.role === "system"
                      ? "bg-danger/10 text-ink/80"
                      : "bg-paper2/80 text-ink"
                )}
              >
                {message.imagePreview ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={message.imagePreview}
                    alt="Bifogad bild"
                    className="mb-2 max-h-40 rounded-input"
                  />
                ) : null}
                {/* Ren chattbubbla. Kategori, sentiment, eskaleringsflagga, demo-märke
                    och källartikel renderades här tidigare — allt tillsammans en
                    intern bedömning av kunden, visad FÖR kunden. "Sentiment 0.1"
                    bredvid ett svar om ett dödsfall är det tydligaste exemplet.

                    Datat finns kvar i message.meta och används av den interna vyn
                    (components/snajp/Dashboard.tsx:497-536) och av admin-spårningen.
                    Ingen prop styr det här: en kundvänd komponent ska inte gå att
                    konfigurera till att läcka. */}
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
              {/* Feedback (6.3) — BARA i testMode och BARA på ett svar som bär
                  ett run_id. Den publika widgeten ska aldrig få tummar. */}
              {testMode && message.role === "agent" && message.meta?.run_id ? (
                <FeedbackRad
                  messageId={message.id}
                  lage={feedbackByMsg[message.id] ?? { fas: "vila" }}
                  onBra={() => void skickaFeedback(message.id, message.meta!.run_id as string, "good")}
                  onDaligOppna={() => uppdateraFeedback(message.id, { fas: "rattar" })}
                  onTextAndring={(varde) => uppdateraFeedback(message.id, { text: varde })}
                  onDaligSkicka={() =>
                    void skickaFeedback(
                      message.id,
                      message.meta!.run_id as string,
                      "bad",
                      feedbackByMsg[message.id]?.text
                    )
                  }
                  onDaligHoppaOver={() => void skickaFeedback(message.id, message.meta!.run_id as string, "bad")}
                />
              ) : null}
            </div>
          );
        })}

        {busy ? (
          <div className="flex justify-start">
            <div className="inline-flex items-center gap-2 rounded-card bg-paper2/80 px-4 py-3 text-[0.9375rem] text-ink/60">
              <Loader2 className="h-4 w-4 animate-spin" />
              {vaknar
                ? text({
                    sv: "Assistenten vaknar — det kan ta upp till en minut",
                    en: "The assistant is waking up — this can take up to a minute"
                  })
                : text({ sv: "Agenten arbetar", en: "The agent is working" })}
            </div>
          </div>
        ) : null}
      </div>

      <div className="bg-paper2/40 px-5 py-4">
        {attachment ? (
          <div className="mb-3 inline-flex items-center gap-2 rounded-input bg-paper p-1.5 pr-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={attachment} alt="Förhandsvisning" className="h-10 w-10 rounded-[6px] object-cover" />
            <span className="text-xs text-ink/60">{text({ sv: "Bild bifogad", en: "Image attached" })}</span>
            <button
              type="button"
              onClick={() => setAttachment(null)}
              className="focus-ring rounded-full p-1 text-ink/50 hover:text-danger"
              aria-label={text({ sv: "Ta bort bild", en: "Remove image" })}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : null}
        <form
          // Bryter till två rader under 360px. Uppmätt vid 320: formuläret har
          // 198px att dela på, knapparna tar 44 + 56 + 16 i mellanrum, och
          // textfältet blev 82px — innehållsytan 50px efter px-4. Platshållaren
          // radbröts och andra raden kapades (scrollHeight 68 mot clientHeight 44).
          // Vid 360px och uppåt är raden oförändrad; det är bara den smalaste
          // skärmen som inte rymmer allt bredvid varandra.
          //
          // Omordningen ligger på max-[359px] och inte på det breda läget, så att
          // tabbordningen följer den synliga ordningen överallt utom på den
          // smalaste skärmen. DOM-ordningen är oförändrad.
          className="flex flex-wrap items-end gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            void send(input);
          }}
        >
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(event) => {
              void onFile(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="focus-ring inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-input bg-paper text-ink/60 transition-colors hover:text-ink max-[359px]:order-2"
            aria-label={text({ sv: "Bifoga bild", en: "Attach image" })}
          >
            <ImagePlus className="h-4 w-4" />
          </button>
          {testMode ? (
            <>
              <input
                ref={kbFileRef}
                type="file"
                accept={[...LÄSBARA, ".pdf"].join(",")}
                className="hidden"
                onChange={(event) => {
                  void onKbFile(event.target.files?.[0]);
                  event.target.value = "";
                }}
              />
              <button
                type="button"
                onClick={() => kbFileRef.current?.click()}
                className="focus-ring inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-input bg-paper text-ink/60 transition-colors hover:text-ink max-[359px]:order-2"
                aria-label="Lägg till dokument i kunskapsbasen"
                title="Textfil eller PDF till kunskapsbasen"
              >
                <FileText className="h-4 w-4" />
              </button>
            </>
          ) : null}
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void send(input);
              }
            }}
            rows={1}
            maxLength={2000}
            // Kort med flit: fältet är en textarea med fast höjd, så en längre
            // platshållare radbryts och andra raden kapas på mobil.
            placeholder={text({ sv: "Skriv här…", en: "Type here…" })}
            // 16px floor: iOS Safari force-zooms a focused input below it, which throws
            // the whole demo layout off on the device most visitors arrive on.
            className="focus-ring min-h-11 flex-1 resize-none rounded-input bg-paper px-4 py-2.5 text-[1rem] outline-none placeholder:text-ink/35 max-[359px]:order-1 max-[359px]:w-full max-[359px]:flex-none"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            // Ordet "Skicka" åt sig 120px av 327 vid 375px bredd, så textfältet
            // krympte till 114px och platshållaren kapades mitt i ordet. Ikonen
            // ensam räcker på små skärmar; aria-label bär betydelsen.
            aria-label={text({ sv: "Skicka", en: "Send" })}
            className={cn(btnPrimary, "max-[359px]:order-3 max-[359px]:ml-auto")}
          >
            <Send className="h-4 w-4" />
            <span className="hidden sm:inline">{text({ sv: "Skicka", en: "Send" })}</span>
          </button>
        </form>
      </div>
    </div>
  );
}

/**
 * Textfil eller PDF på väg in i kunskapsbasen (6.4/6.5) — förhandsvisning
 * FÖRST, godkännande av en människa sist. Det är den synliga motsvarigheten
 * till den tysta risken components/settings/Kunskapsbas.tsx beskriver: en
 * halvläst PDF citerad av agenten som om den vore korrekt. Här ser kunden
 * exakt vad som lästes ut, inklusive varningen när textlagret är tunt, och
 * texten går ingenstans förrän knappen nedan trycks.
 */
function KbForhandsvisningKortVy({
  kort,
  onLaggTill
}: Readonly<{ kort: KbForhandsvisningKort; onLaggTill: () => void }>) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] rounded-card border border-ink/12 bg-paper2/60 px-4 py-3 text-[0.875rem] leading-6">
        <p className="kicker text-mineral">
          {kort.kalla === "pdf" ? "PDF" : "Textfil"} · {kort.filnamn}
        </p>
        {kort.status === "extraherar" ? (
          <p className="mt-2 flex items-center gap-2 text-ink/60">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            Läser ut texten…
          </p>
        ) : kort.status === "fel" ? (
          <p className="mt-2 text-danger">{kort.fel}</p>
        ) : (
          <>
            <p className="mt-2 font-semibold text-ink">{kort.titel}</p>
            {kort.varning ? (
              <p className="mt-1.5 max-w-[65ch] text-ochre">{kort.varning}</p>
            ) : null}
            <div className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap rounded-input bg-paper px-3 py-2 text-ink/75">
              {kort.innehall || "(ingen text hittades i filen)"}
            </div>
            {kort.sidor ? (
              <p className="mt-1 text-[0.75rem] text-ink/45">
                {kort.sidor} {kort.sidor === 1 ? "sida" : "sidor"}
              </p>
            ) : null}
            <div className="mt-3">
              {kort.status === "sparad" ? (
                <p className="text-moss">Tillagt i kunskapsbasen.</p>
              ) : (
                <button
                  type="button"
                  disabled={kort.status === "sparar"}
                  onClick={onLaggTill}
                  className={cn(btnSecondary, "min-h-9 disabled:opacity-50")}
                >
                  <Check className="h-3.5 w-3.5" aria-hidden />
                  {kort.status === "sparar" ? "Sparar…" : "Lägg till i kunskapsbasen"}
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/**
 * Agentens föreslagna kunskapsartikel (6.6), i chattflödet i stället för
 * bara på lärande-sidan. Godkännandeklicket ligger HÄR, i chatten — det
 * känns live, och en människa är ändå kvar i loopen (INV-LEARN-001):
 * artikeln skapas av backendens egen endpoint, aldrig av agenten själv.
 */
function ForslagKortVy({
  kort,
  onGodkann,
  onAvfard
}: Readonly<{ kort: ForslagKort; onGodkann: () => void; onAvfard: () => void }>) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] rounded-card border border-ochre/30 bg-ochre/5 px-4 py-3 text-[0.875rem] leading-6">
        <p className="kicker text-mineral">Agenten föreslår en kunskapsartikel</p>
        <p className="mt-2 font-semibold text-ink">{kort.rubrik}</p>
        {kort.brodtext ? <p className="mt-1 whitespace-pre-wrap text-ink/75">{kort.brodtext}</p> : null}
        {kort.status === "sparat" ? (
          <p className="mt-3 text-moss">
            Tillagt i kunskapsbasen. Nästa meddelande använder den nya texten, instruktionerna läses om per körning.
          </p>
        ) : kort.status === "avfardat" ? (
          <p className="mt-3 text-ink/50">Avfärdat.</p>
        ) : (
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              disabled={kort.status === "sparar" || kort.status === "avfardar"}
              onClick={onGodkann}
              className="focus-ring inline-flex min-h-9 items-center gap-1.5 rounded-input bg-ink px-3 text-[0.8125rem] font-medium text-paper disabled:opacity-50"
            >
              <Check className="h-3.5 w-3.5" aria-hidden />
              {kort.status === "sparar" ? "Lägger till…" : "Lägg till"}
            </button>
            <button
              type="button"
              disabled={kort.status === "sparar" || kort.status === "avfardar"}
              onClick={onAvfard}
              className="focus-ring inline-flex min-h-9 items-center gap-1.5 rounded-input bg-paper2 px-3 text-[0.8125rem] font-medium disabled:opacity-50"
            >
              <X className="h-3.5 w-3.5" aria-hidden />
              {kort.status === "avfardar" ? "Avfärdar…" : "Avfärda"}
            </button>
          </div>
        )}
        {kort.fel ? <p className="mt-2 text-danger">{kort.fel}</p> : null}
      </div>
    </div>
  );
}

/**
 * Feedbackraden under ett agentsvar (6.3). Tumme upp skickar direkt — inget
 * att korrigera på ett bra svar. Tumme ned öppnar en rättningsruta i
 * stället för att skicka direkt: den TOMMA domen ("bad", inget rättat) är
 * en svagare signal än en med corrected_output, och kunden ska hinna skriva
 * den innan något går iväg.
 */
function FeedbackRad({
  messageId,
  lage,
  onBra,
  onDaligOppna,
  onTextAndring,
  onDaligSkicka,
  onDaligHoppaOver
}: Readonly<{
  // Går in i rättningsrutans id/htmlFor. Utan den delade flera samtidigt
  // öppna rättningsrutor SAMMA id — ogiltig HTML, och en label-klick hade
  // fokuserat fel textarea.
  messageId: string;
  lage: FeedbackLage;
  onBra: () => void;
  onDaligOppna: () => void;
  onTextAndring: (varde: string) => void;
  onDaligSkicka: () => void;
  onDaligHoppaOver: () => void;
}>) {
  if (lage.fas === "skickad") {
    return (
      <p className="mt-1.5 text-[0.75rem] text-ink/45">
        {lage.verdict === "good" ? "Tack för feedbacken." : "Tack, rättningen sparades."}
      </p>
    );
  }

  return (
    <div className="mt-1.5 max-w-[85%]">
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={onBra}
          disabled={lage.fas === "skickar"}
          aria-label="Bra svar"
          className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded-input text-ink/40 transition-colors hover:bg-paper2 hover:text-moss disabled:opacity-50"
        >
          <ThumbsUp className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={onDaligOppna}
          disabled={lage.fas === "skickar"}
          aria-label="Dåligt svar"
          aria-expanded={lage.fas === "rattar"}
          className={cn(
            "focus-ring inline-flex h-8 w-8 items-center justify-center rounded-input transition-colors hover:bg-paper2 hover:text-danger disabled:opacity-50",
            lage.fas === "rattar" ? "text-danger" : "text-ink/40"
          )}
        >
          <ThumbsDown className="h-3.5 w-3.5" />
        </button>
      </div>
      {lage.fas === "rattar" ? (
        <div className="mt-2 rounded-input border border-ink/12 bg-paper p-3">
          <label className="text-[0.75rem] font-medium text-ink/60" htmlFor={`feedback-rattning-${messageId}`}>
            Vad borde agenten ha svarat? (frivilligt)
          </label>
          <textarea
            id={`feedback-rattning-${messageId}`}
            value={lage.text ?? ""}
            onChange={(event) => onTextAndring(event.target.value)}
            rows={2}
            maxLength={4000}
            className="focus-ring mt-1.5 w-full resize-y rounded-input border border-ink/12 bg-paper2/40 px-2.5 py-2 text-[0.8125rem] leading-5 outline-none"
          />
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={onDaligSkicka}
              className="focus-ring inline-flex min-h-8 items-center rounded-input bg-ink px-3 text-[0.75rem] font-medium text-paper"
            >
              Skicka rättning
            </button>
            <button
              type="button"
              onClick={onDaligHoppaOver}
              className="focus-ring inline-flex min-h-8 items-center rounded-input px-3 text-[0.75rem] font-medium text-ink/50 hover:text-ink"
            >
              Hoppa över
            </button>
          </div>
        </div>
      ) : null}
      {lage.fas === "fel" ? <p className="mt-1 text-[0.75rem] text-danger">{lage.fel}</p> : null}
    </div>
  );
}
