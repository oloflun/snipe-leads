"use client";

import { ImagePlus, Loader2, Send, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { btnPrimary } from "@/components/ui";
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
};

type ChatMessage = {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  imagePreview?: string;
  meta?: AgentMeta;
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
function demoSessionId(): string {
  const KEY = "snajp.demo.session";
  let id = window.sessionStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.sessionStorage.setItem(KEY, id);
  }
  return id;
}

export function SupportChat({ tenant, session }: SupportChatProps = {}) {
  // Demons varumärke och exempelfrågor gäller demon. På en kunds supportsida är
  // "Nordlys Handel" och frågor om felkoder i kassan direkt vilseledande — de
  // namnger en påhittad butik och ett sortiment kunden inte har.
  const tenantConfig = tenant ? getTenant(tenant) : null;
  const brandLabel = tenantConfig?.name ?? "Nordlys Handel";
  const intro = tenantConfig?.supportIntro ?? null;
  const prompts = tenantConfig?.supportPrompts ?? examplePrompts;

  // The poll loop runs up to 90 iterations; without this it keeps writing state
  // after the component is gone.
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);
  const { text } = useLocale();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [attachment, setAttachment] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"unknown" | "simulation" | "live" | "offline">("unknown");
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);


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
        const response = await fetch("/api/snajp-support/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: trimmed,
            channel: "web",
            // En besökare identifieras av sitt session-id tills hen uppger något
            // mer. Demon får ett eget id per flik (demoSession) i stället för en
            // delad identitet, så att ingen ser spår av föregående besökare.
            customer_email: `${session ?? demoSessionId()}@session.snajp.se`,
            customer_name: session ? "Webbesökare" : "Demo Kund",
            session_key: session ?? demoSessionId(),
            tenant,
            attachments
          })
        });
        const payload = await response.json();
        if (payload.offline) {
          setMode("offline");
          setMessages((current) => [
            ...current,
            { id: crypto.randomUUID(), role: "system", content: payload.error }
          ]);
          return;
        }
        if (!response.ok || !payload.job_id) {
          throw new Error(payload.error ?? "Okänt fel");
        }

        for (let attempt = 0; attempt < 90; attempt += 1) {
          await new Promise((resolve) => setTimeout(resolve, attempt < 5 ? 800 : 2000));
          // Tenanten måste med: jobbet skapades med kundens nyckel, och utan
          // den pollar vi demo-tenanten där jobbet inte finns.
          const jobUrl = tenant
            ? `/api/snajp-support/jobs/${payload.job_id}?tenant=${encodeURIComponent(tenant)}`
            : `/api/snajp-support/jobs/${payload.job_id}`;
          const jobResponse = await fetch(jobUrl);
          const job = await jobResponse.json();
          if (job.offline) {
            setMode("offline");
            setMessages((current) => [
              ...current,
              { id: crypto.randomUUID(), role: "system", content: job.error }
            ]);
            return;
          }
          if (!alive.current) return;
          if (job.status === "completed" && job.result) {
            setMode(job.result.simulation ? "simulation" : "live");
            setMessages((current) => [
              ...current,
              {
                id: crypto.randomUUID(),
                role: "agent",
                content: job.result.reply,
                meta: job.result
              }
            ]);
            return;
          }
          if (job.status === "failed") {
            throw new Error(job.error ?? "Agentkörningen misslyckades");
          }
        }
        throw new Error("Svaret tog för lång tid. Försök igen.");
      } catch (error) {
        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "system",
            content: error instanceof Error ? error.message : "Något gick fel. Försök igen."
          }
        ]);
      } finally {
        setBusy(false);
      }
    },
    [attachment, busy]
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
        <span className="hidden text-sm text-ink/45 md:block">{brandLabel}</span>
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
                  sv: "Skriv som en kund till den påhittade butiken Nordlys Handel. Du kan också ladda upp en skärmdump eller en bild på en skadad vara.",
                  en: "Write as a customer of the invented store Nordlys Handel. You can also upload a screenshot or a photo of a damaged item."
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

        {messages.map((message) => (
          <div key={message.id} className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}>
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
          </div>
        ))}

        {busy ? (
          <div className="flex justify-start">
            <div className="inline-flex items-center gap-2 rounded-card bg-paper2/80 px-4 py-3 text-[0.9375rem] text-ink/60">
              <Loader2 className="h-4 w-4 animate-spin" />
              {text({ sv: "Agenten arbetar", en: "The agent is working" })}
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
