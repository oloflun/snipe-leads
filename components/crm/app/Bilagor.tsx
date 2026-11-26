"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CircleAlert, Download, File as Filikon, FileSpreadsheet, FileText, Image as Bildikon, Paperclip, Trash2, Upload, X, type LucideIcon } from "lucide-react";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { Objektikon, type Ton } from "@/components/crm/app/kit";
import { BILAGA_MAX, BILAGETYPER, CrmFel, crmAnrop, crmLaddaUpp, type Bilaga, type Sida } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

type Objekt = "companies" | "people" | "deals";

/** Fältet som knyter bilagan till posten. */
const KOPPLING: Record<Objekt, "company_id" | "person_id" | "deal_id"> = { companies: "company_id", people: "person_id", deals: "deal_id" };

/** En fil som laddas upp, eller som föll: står i listan tills den är klar eller avfärdas. */
type Pagaende = { nyckel: string; namn: string; storlek: number; fel: Localized | null };

/** "1,2 MB", "340 kB". */
export function filstorlek(byte: number, sprak: "sv" | "en"): string {
  const tal = (n: number, d: number) => n.toLocaleString(sprak === "sv" ? "sv-SE" : "en-GB", { maximumFractionDigits: d });
  if (byte >= 1024 * 1024) return `${tal(byte / (1024 * 1024), 1)} MB`;
  if (byte >= 1024) return `${tal(byte / 1024, 0)} kB`;
  return `${tal(byte, 0)} B`;
}

function ikonFor(typ: string | null): { ikon: LucideIcon; ton: Ton } {
  if (typ?.startsWith("image/")) return { ikon: Bildikon, ton: "mossa" };
  if (typ?.includes("spreadsheet") || typ === "text/csv") return { ikon: FileSpreadsheet, ton: "mossa" };
  if (typ === "application/pdf" || typ?.includes("word") || typ === "text/plain") return { ikon: FileText, ton: "bla" };
  return { ikon: Filikon, ton: "mineral" };
}

const andelse = (namn: string) => namn.slice(namn.lastIndexOf(".") + 1).toLowerCase();

/**
 * Postens filer (Twentys Files, i panelens form): bilagor knutna till bolaget,
 * personen eller affären. Ladda upp, hämta och ta bort.
 *
 * En uppladdning visar sitt förlopp på raden där filen sedan står, och en fil
 * som inte gick står kvar med skälet tills den avfärdas. Typ och storlek prövas
 * här innan filen skickas, med samma gränser som API:t (`BILAGETYPER`, 10 MB).
 */
export function Bilagor({ objekt, id, andrat }: Readonly<{ objekt: Objekt; id: string; andrat?: (antal: number) => void }>) {
  const { text, locale } = useLocale();
  const visa = useToast();
  const [filer, setFiler] = useState<Bilaga[] | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [pagaende, setPagaende] = useState<Pagaende[]>([]);
  const [omgang, setOmgang] = useState(0);
  const [over, setOver] = useState(false);
  const valjare = useRef<HTMLInputElement>(null);
  const andratRef = useRef(andrat);
  andratRef.current = andrat;

  useEffect(() => {
    let aktuell = true;
    setFel(null);
    crmAnrop<Sida<Bilaga>>(`/v1/attachments?${new URLSearchParams({ [KOPPLING[objekt]]: id, limit: "200", sort: "-updated" })}`)
      .then((s) => {
        if (!aktuell) return;
        setFiler(s.data);
        andratRef.current?.(s.data.length);
      })
      .catch((e) => aktuell && setFel(e));
    return () => {
      aktuell = false;
    };
  }, [objekt, id, omgang]);

  useEffect(() => {
    setFiler(null);
    setPagaende([]);
  }, [objekt, id]);

  /** Vad som är fel med filen, eller null. Samma gränser som API:t, så att beskedet kommer direkt. */
  const hinder = useCallback((f: File): Localized | null => {
    if (!BILAGETYPER.includes(andelse(f.name))) {
      return { sv: "Filtypen går inte att ladda upp. Tillåtna: PDF, bilder, text, CSV, Word, Excel och PowerPoint.", en: "The file type cannot be uploaded. Allowed: PDF, images, text, CSV, Word, Excel and PowerPoint." };
    }
    if (f.size > BILAGA_MAX) return { sv: "Filen är större än 10 MB.", en: "The file is larger than 10 MB." };
    if (f.size === 0) return { sv: "Filen är tom.", en: "The file is empty." };
    return null;
  }, []);

  async function laddaUpp(lista: File[]) {
    if (!lista.length) return;
    const stamp = Date.now();
    const nya = lista.map((f, i) => ({ fil: f, rad: { nyckel: `${stamp}-${i}-${f.name}`, namn: f.name, storlek: f.size, fel: hinder(f) } }));
    setPagaende((forr) => [...nya.map((n) => n.rad), ...forr]);
    let klara = 0;
    // En fil i taget: kvoten räknas per kund, och två stora filer samtidigt ger inget snabbare.
    for (const { fil, rad } of nya) {
      if (rad.fel) continue;
      try {
        await crmLaddaUpp(fil, { [KOPPLING[objekt]]: id });
        klara += 1;
        setPagaende((forr) => forr.filter((p) => p.nyckel !== rad.nyckel));
        setOmgang((n) => n + 1);
      } catch (orsak) {
        const skal: Localized = orsak instanceof CrmFel ? orsak.text : { sv: "Uppladdningen gick inte fram. Försök igen.", en: "The upload did not go through. Try again." };
        setPagaende((forr) => forr.map((p) => (p.nyckel === rad.nyckel ? { ...p, fel: skal } : p)));
      }
    }
    const fall = nya.length - klara;
    if (klara > 0 || fall > 0) {
      visa({
        type: fall ? "error" : "info",
        body: fall
          ? text({ sv: `${klara} av ${nya.length} filer laddades upp. Skälet står vid varje fil som inte gick.`, en: `${klara} of ${nya.length} files were uploaded. The reason is shown at each file that failed.` })
          : klara === 1
            ? text({ sv: `${nya[0].fil.name} är uppladdad.`, en: `${nya[0].fil.name} is uploaded.` })
            : text({ sv: `${klara} filer är uppladdade.`, en: `${klara} files are uploaded.` }),
        uniqueID: "crm-bilagor"
      });
    }
  }

  async function taBort(b: Bilaga) {
    try {
      await crmAnrop<null>(`/v1/attachments/${encodeURIComponent(b.id)}`, { method: "DELETE" });
    } catch (orsak) {
      visa({ type: "error", body: text(orsak instanceof CrmFel ? orsak.text : { sv: "Filen gick inte att ta bort.", en: "The file could not be removed." }), uniqueID: "crm-bilagor" });
      return;
    }
    setOmgang((n) => n + 1);
    const angra = async () => {
      try {
        await crmAnrop<Bilaga>(`/v1/attachments/${encodeURIComponent(b.id)}/restore`, { method: "POST" });
        visa({ body: text({ sv: "Filen är tillbaka.", en: "The file is back." }), uniqueID: "crm-bilagor" });
      } catch (orsak) {
        visa({ type: "error", body: text(orsak instanceof CrmFel ? orsak.text : { sv: "Filen gick inte att ta tillbaka.", en: "The file could not be restored." }), uniqueID: "crm-bilagor" });
      }
      setOmgang((n) => n + 1);
    };
    visa({
      body: text({ sv: `${b.filename ?? "Filen"} är borttagen och töms om 30 dagar.`, en: `${b.filename ?? "The file"} is removed and is emptied in 30 days.` }),
      endContent: <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void angra()} />,
      autoHideDuration: 10000,
      uniqueID: "crm-bilagor"
    });
  }

  const laddar = pagaende.some((p) => !p.fel);
  const tom = filer != null && filer.length === 0 && pagaende.length === 0;

  return (
    <div
      className="crm-bilagor flex flex-col gap-4"
      data-over={over || undefined}
      onDragOver={(e) => {
        if (!e.dataTransfer.types.includes("Files")) return;
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOver(false);
      }}
      onDrop={(e) => {
        if (!e.dataTransfer.files.length) return;
        e.preventDefault();
        setOver(false);
        void laddaUpp([...e.dataTransfer.files]);
      }}
    >
      <input
        ref={valjare}
        type="file"
        multiple
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        accept={BILAGETYPER.map((t) => `.${t}`).join(",")}
        onChange={(e) => {
          const valda = [...(e.target.files ?? [])];
          e.target.value = "";
          void laddaUpp(valda);
        }}
      />

      {fel && !filer ? (
        <div className="flex flex-col items-start gap-3 py-2">
          <Text color="secondary">{text(fel instanceof CrmFel ? fel.text : { sv: "Filerna gick inte att hämta.", en: "The files could not be loaded." })}</Text>
          <Button size="sm" variant="secondary" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => setOmgang((n) => n + 1)} />
        </div>
      ) : !filer ? (
        <div className="flex flex-col gap-4 py-1" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar filerna", en: "Loading the files" })}>
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton width={32} height={32} radius={2} index={i} />
              <span className="flex flex-1 flex-col gap-2">
                <Skeleton width={`${40 + ((i * 19) % 35)}%`} height={10} radius="rounded" index={i} />
                <Skeleton width="25%" height={8} radius="rounded" index={i} />
              </span>
            </div>
          ))}
        </div>
      ) : tom ? (
        <EmptyState
          isCompact
          icon={<Icon icon={Paperclip} size="lg" color="secondary" />}
          title={text({ sv: "Inga filer här än", en: "No files here yet" })}
          description={text({
            sv: "Offerter, avtal och bilder som hör till posten. Dra hit en fil eller välj en. Högst 10 MB per fil.",
            en: "Quotes, contracts and images that belong to the record. Drop a file here or choose one. At most 10 MB per file."
          })}
          actions={<Button variant="secondary" label={text({ sv: "Ladda upp fil", en: "Upload file" })} icon={<Icon icon={Upload} size="sm" />} onClick={() => valjare.current?.click()} />}
        />
      ) : (
        <>
          {/* På telefon bryts raden: texten först, knappen under med hela sin etikett. */}
          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
            <Text type="supporting" color="secondary">
              {text({ sv: "Dra hit en fil eller välj en. Högst 10 MB per fil.", en: "Drop a file here or choose one. At most 10 MB per file." })}
            </Text>
            <span className="shrink-0">
              <Button size="sm" variant="secondary" label={text({ sv: "Ladda upp fil", en: "Upload file" })} icon={<Icon icon={Upload} size="sm" />} isDisabled={laddar} onClick={() => valjare.current?.click()} />
            </span>
          </div>
          <ul className="flex flex-col" aria-label={text({ sv: "Filer", en: "Files" })}>
            {pagaende.map((p) => (
              <li key={p.nyckel} className="crm-filrad flex items-start gap-3 py-2.5">
                <Objektikon ikon={p.fel ? CircleAlert : Upload} ton={p.fel ? "mineral" : "ockra"} storlek={32} />
                <span className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="truncate text-[0.875rem] font-semibold text-ink">{p.namn}</span>
                  {p.fel ? (
                    <span role="alert" className="text-[0.8125rem] text-danger">
                      {text(p.fel)}
                    </span>
                  ) : (
                    <span className="flex flex-col gap-1.5" role="status">
                      <span className="text-[0.8125rem] text-ink-muted">{text({ sv: `Laddar upp, ${filstorlek(p.storlek, locale)}`, en: `Uploading, ${filstorlek(p.storlek, locale)}` })}</span>
                      <ProgressBar label={text({ sv: `Laddar upp ${p.namn}`, en: `Uploading ${p.namn}` })} isLabelHidden isIndeterminate />
                    </span>
                  )}
                </span>
                {p.fel ? (
                  <IconButton
                    label={text({ sv: `Ta bort ${p.namn} ur listan`, en: `Remove ${p.namn} from the list` })}
                    icon={<Icon icon={X} size="sm" />}
                    variant="ghost"
                    onClick={() => setPagaende((forr) => forr.filter((x) => x.nyckel !== p.nyckel))}
                  />
                ) : null}
              </li>
            ))}
            {filer.map((b) => {
              const bild = ikonFor(b.content_type);
              const namn = b.filename ?? text({ sv: "Namnlös fil", en: "Unnamed file" });
              return (
                <li key={b.id} className="crm-filrad flex items-center gap-3 py-2.5">
                  <Objektikon ikon={bild.ikon} ton={bild.ton} storlek={32} />
                  <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="truncate text-[0.875rem] font-semibold text-ink" title={namn}>
                      {namn}
                    </span>
                    <span className="flex min-w-0 items-center gap-x-1.5 whitespace-nowrap text-[0.8125rem] text-ink-muted">
                      <span className="tabular-nums">{filstorlek(b.size ?? 0, locale)}</span>
                      {b.created_at ? (
                        <>
                          <span aria-hidden>·</span>
                          <span className="min-w-0 truncate">
                            <Timestamp value={b.created_at} format="relative" />
                          </span>
                        </>
                      ) : null}
                    </span>
                  </span>
                  <IconButton
                    label={text({ sv: `Hämta ${namn}`, en: `Download ${namn}` })}
                    icon={<Icon icon={Download} size="sm" />}
                    variant="ghost"
                    // Backenden svarar med Content-Disposition: attachment, så länken hämtar filen i stället för att öppna den.
                    href={`/api/snajp-support/crm/v1/attachments/${encodeURIComponent(b.id)}/content`}
                  />
                  <IconButton label={text({ sv: `Ta bort ${namn}`, en: `Remove ${namn}` })} icon={<Icon icon={Trash2} size="sm" />} variant="ghost" className="crm-farlig" onClick={() => void taBort(b)} />
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
