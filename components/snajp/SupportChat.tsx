"use client";

import { ImagePlus, Loader2, Send, ShieldAlert, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge, btnPrimary } from "@/components/ui";
import { useLocale } from "@/lib/i18n";
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

export function SupportChat() {
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
            customer_email: "demo@nordlyshandel.se",
            customer_name: "Demo Kund",
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
          const jobResponse = await fetch(`/api/snajp-support/jobs/${payload.job_id}`);
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

  const statusLabel =
    mode === "offline"
      ? text({ sv: "Offline", en: "Offline" })
      : mode === "simulation"
        ? text({ sv: "Online · Demo-läge", en: "Online · Demo mode" })
        : mode === "live"
          ? text({ sv: "Online · Live-AI", en: "Online · Live AI" })
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
        <span className="hidden text-sm text-ink/45 md:block">Nordlys Handel</span>
      </div>

      <div ref={scrollRef} className="h-[420px] space-y-4 overflow-y-auto px-5 py-6">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-5 text-center">
            <p className="max-w-md text-[0.9375rem] leading-6 text-ink/60">
              {text({
                sv: "Skriv som en kund till den påhittade butiken Nordlys Handel. Du kan också ladda upp en skärmdump eller en bild på en skadad vara.",
                en: "Write as a customer of the invented store Nordlys Handel. You can also upload a screenshot or a photo of a damaged item."
              })}
            </p>
            <div className="flex max-w-lg flex-wrap justify-center gap-2">
              {examplePrompts.map((prompt) => (
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
              <p className="whitespace-pre-wrap">{message.content}</p>
              {message.meta ? (
                <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-ink/10 pt-3">
                  {message.meta.category_label ? <Badge tone="neutral">{message.meta.category_label}</Badge> : null}
                  {typeof message.meta.sentiment === "number" ? (
                    <Badge tone={message.meta.sentiment < 0.3 ? "danger" : message.meta.sentiment > 0.6 ? "good" : "warn"}>
                      Sentiment {message.meta.sentiment.toFixed(1)}
                    </Badge>
                  ) : null}
                  {message.meta.escalated ? (
                    <Badge tone="danger">
                      <ShieldAlert className="h-3 w-3" />
                      {text({ sv: "Eskalerat till människa", en: "Escalated to human" })}
                    </Badge>
                  ) : null}
                  {message.meta.simulation ? (
                    <Badge tone="warn">{text({ sv: "Demo-läge", en: "Demo mode" })}</Badge>
                  ) : null}
                  {message.meta.kb_sources?.length ? (
                    <span className="text-xs text-ink/50">
                      {text({ sv: "Källa", en: "Source" })}: {message.meta.kb_sources[0].title}
                    </span>
                  ) : null}
                </div>
              ) : null}
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
          className="flex items-end gap-2"
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
            className="focus-ring inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-input bg-paper text-ink/60 transition-colors hover:text-ink"
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
            placeholder={text({ sv: "Skriv ditt meddelande…", en: "Type your message…" })}
            className="focus-ring min-h-11 flex-1 resize-none rounded-input bg-paper px-4 py-2.5 text-[1rem] outline-none placeholder:text-ink/35"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className={btnPrimary}
          >
            <Send className="h-4 w-4" />
            {text({ sv: "Skicka", en: "Send" })}
          </button>
        </form>
      </div>
    </div>
  );
}
