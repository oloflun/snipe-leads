"use client";

import { useState } from "react";
import { ArrowRight, CalendarClock, Clock, FilePlus2, Send, Undo2 } from "lucide-react";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Drawer, DrawerHeader } from "@astryxdesign/core/Drawer";
import { Icon } from "@astryxdesign/core/Icon";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { HStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { delaMejl } from "@/components/leads/IrisGranskning";
import { Mejlsvans, Mejlvisning, Utkastredigerare } from "@/components/crm/app/iris/Utkastredigerare";
import { Prick, tonFor, tonklass, utanBolagsform } from "@/components/crm/app/kit";
import { SKICKATLAGE, signalUr, skickatlage, skickatton, type Besked, type Kopost, type Signatur, type SkickatRad } from "@/lib/crm/iris/utkast";
import { sandtid } from "@/lib/crm/iris/lead";
import { delaCitat } from "@/lib/leads/konversation";
import { useLocale } from "@/lib/i18n";

/** Posten panelen visar: ett utkast i kön, ett schemalagt eller ett skickat mejl. */
export type Utkastpost = { slag: "granska"; ko: Kopost } | { slag: "snart" | "skickat"; rad: SkickatRad };

/** Hela konversationen för ett utskick som fått svar (LU-082): våra mejl med signatur, svaren med citatet hopfällt. */
function Konversation({ rad, signatur }: Readonly<{ rad: SkickatRad; signatur: Signatur | null }>) {
  const { text } = useLocale();
  const [citat, setCitat] = useState<Set<string>>(new Set());
  const mejl = rad.konversation ?? [];
  const flerUtskick = mejl.filter((m) => m.direction === "outbound").length > 1;
  const bolag = rad.company_name ?? rad.prospect_email ?? text({ sv: "bolaget", en: "the company" });
  return (
    <ol className="flex flex-col gap-3" aria-label={text({ sv: "Konversationen", en: "The conversation" })}>
      {mejl.map((m) => {
        const in_ = m.direction === "inbound";
        const [svar, citerat] = in_ ? delaCitat(m.body) : ["", ""];
        const [brod, svans] = in_ ? ["", ""] : delaMejl(m.body, signatur);
        const visas = citat.has(m.id);
        return (
          <li key={m.id} className={`flex flex-col gap-2 rounded-[16px] px-4 py-3.5 ${in_ ? "crm-kallkort crm-ton-bla" : "border border-ink/[0.08]"}`}>
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5">
              <span className="min-w-0 break-words text-[0.875rem] font-semibold text-ink">
                {in_ ? text({ sv: `Svar från ${bolag}`, en: `Reply from ${bolag}` }) : text({ sv: `Vårt mejl till ${rad.prospect_email ?? bolag}`, en: `Our email to ${rad.prospect_email ?? bolag}` })}
                {!in_ && flerUtskick && m.id === rad.id ? <span className="font-normal text-ink-muted">{text({ sv: ", det här utskicket", en: ", this email" })}</span> : null}
              </span>
              <Timestamp value={m.sent_at} format="date_time" color="secondary" />
            </div>
            {!in_ && m.subject ? <span className="text-[0.8125rem] text-ink2">{m.subject}</span> : null}
            {in_ ? (
              <>
                <p className="whitespace-pre-wrap break-words text-[0.9375rem] leading-7 text-ink">{svar || text({ sv: "Svaret har ingen text.", en: "The reply has no text." })}</p>
                {citerat ? (
                  <>
                    <div>
                      <Button
                        size="sm"
                        variant="ghost"
                        label={visas ? text({ sv: "Dölj citerad text", en: "Hide quoted text" }) : text({ sv: "Visa citerad text", en: "Show quoted text" })}
                        onClick={() =>
                          setCitat((c) => {
                            const ny = new Set(c);
                            if (ny.has(m.id)) ny.delete(m.id);
                            else ny.add(m.id);
                            return ny;
                          })
                        }
                      />
                    </div>
                    {visas ? <p className="whitespace-pre-wrap break-words border-l-2 border-ink/15 pl-3 text-[0.8125rem] leading-6 text-ink-muted">{citerat}</p> : null}
                  </>
                ) : null}
              </>
            ) : (
              <>
                <p className="whitespace-pre-wrap break-words text-[0.9375rem] leading-7 text-ink">{brod}</p>
                <Mejlsvans signatur={signatur} svans={svans} />
              </>
            )}
          </li>
        );
      })}
    </ol>
  );
}

/**
 * Utkastets panel i Iris › Utkast, byggd som leadets (LeadPanel): en Drawer från
 * höger med huvud, innehåll och fot. Öppnas med `?utkast=<id>` i adressen.
 *
 * - Att granska: utkastredigeraren med Godkänn och skicka, Avvisa, AI:n och provmejlet.
 * - Skickas snart: mejlet som det går ut, när det skickas, och Skicka nu, Ändra tid
 *   och Tillbaka till Iris i foten (samma handlingar som listans markering).
 * - Skickat: mejlet, eller hela konversationen när bolaget svarat, provmejlet och
 *   Skapa uppföljning när leadet väntar på svar.
 *
 * Handlingarna utför vyn (UtkastVy): panelen visar dem och deras utfall.
 */
export function UtkastPanel({
  post,
  signatur,
  offer,
  bas,
  skriv,
  stang,
  spara,
  godkann,
  avvisa,
  skickaNu,
  andraTid,
  tillbaka,
  uppfoljning
}: Readonly<{
  post: Utkastpost | null;
  signatur: Signatur | null;
  offer: string | null;
  bas: string;
  skriv: { far: boolean; skal: string | null };
  stang: () => void;
  spara: (ko: Kopost, amne: string, brodtext: string) => Promise<void>;
  godkann: (ko: Kopost) => Promise<Besked | null>;
  avvisa: (ko: Kopost) => Promise<Besked | null>;
  skickaNu: (rad: SkickatRad) => void;
  andraTid: (rad: SkickatRad) => void;
  tillbaka: (rad: SkickatRad) => void;
  uppfoljning: (rad: SkickatRad) => void;
}>) {
  const { text, locale } = useLocale();
  const ko = post?.slag === "granska" ? post.ko : null;
  const rad = post && post.slag !== "granska" ? post.rad : null;
  const namn = (ko?.company_name ?? rad?.company_name) || (ko?.prospect_email ?? rad?.prospect_email) || text({ sv: "Okänt bolag", en: "Unknown company" });
  const prospekt = ko?.prospect_id ?? rad?.prospect_id ?? null;
  const av = { isDisabled: !skriv.far, tooltip: skriv.skal ?? undefined };

  const huvudrad = post ? (
    <span className="mt-1 inline-flex flex-wrap items-center gap-2">
      {post.slag === "granska" ? <Badge variant="yellow" label={text({ sv: "Väntar på granskning", en: "Awaiting review" })} /> : null}
      {post.slag === "snart" && rad ? (
        <Badge
          variant="neutral"
          icon={<Icon icon={Clock} size="xsm" color="inherit" />}
          label={rad.skickas_tidigast ? text({ sv: `Skickas ${sandtid(rad.skickas_tidigast, locale)}`, en: `Sends ${sandtid(rad.skickas_tidigast, locale)}` }) : text({ sv: "Skickas snart", en: "Sending soon" })}
        />
      ) : null}
      {post.slag === "skickat" && rad ? <Badge variant="neutral" icon={<Prick ton={skickatton(rad)} />} label={text(SKICKATLAGE[skickatlage(rad)])} /> : null}
    </span>
  ) : undefined;

  return (
    <Drawer isOpen={post != null} onOpenChange={(o) => !o && stang()} label={text({ sv: `Utkastet till ${namn}`, en: `The draft to ${namn}` })} width={600} hasScrim={false}>
      <Layout
        header={
          <DrawerHeader
            hasDivider={false}
            startContent={<Avatar name={utanBolagsform(namn)} size={48} shape="rounded" tooltip={false} className={`crm-avatar crm-avatar-stor ${tonklass(tonFor(utanBolagsform(namn)))}`} />}
            title={<span className="crm-postnamn">{namn}</span>}
            subtitle={huvudrad}
            onOpenChange={(o) => !o && stang()}
          />
        }
        content={
          <LayoutContent padding={0}>
            <div data-autofocus tabIndex={-1} className="crm-autofokus px-5 pb-6 pt-2">
              {ko ? (
                <Utkastredigerare
                  nyckel={ko.id}
                  amne={ko.subject ?? null}
                  brodtext={ko.brodtext ?? ko.body ?? ""}
                  svans={ko.svans ?? null}
                  signatur={signatur}
                  mottagare={ko.prospect_email ?? null}
                  redigerbar
                  kontext={{ companyName: ko.company_name, contactName: ko.contact_name, signal: signalUr(ko.lagesbeskrivning, ko.signaler), offer }}
                  spara={(a, b) => spara(ko, a, b)}
                  godkann={{ gor: () => godkann(ko) }}
                  avvisa={{ gor: () => avvisa(ko) }}
                  provmejl={{ queueItemId: ko.id }}
                  skriv={skriv}
                />
              ) : rad ? (
                <div className="flex flex-col gap-4">
                  <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[0.8125rem]">
                    <dt className="text-ink-muted">{text({ sv: "Till", en: "To" })}</dt>
                    <dd className="min-w-0 break-all text-ink2">{rad.prospect_email ?? "-"}</dd>
                    <dt className="text-ink-muted">{rad.schemalagt ? text({ sv: "Skickas", en: "Sends" }) : text({ sv: "Skickat", en: "Sent" })}</dt>
                    <dd className="text-ink2">
                      {rad.sent_at ? (
                        <Timestamp value={rad.sent_at} format="date_time" color="primary" />
                      ) : rad.skickas_tidigast ? (
                        <span>
                          <Timestamp value={rad.skickas_tidigast} format="date_time" color="primary" />{" "}
                          <span className="text-ink-muted">{text({ sv: "(nästa sändfönster, vardagar 08 till 16)", en: "(next sending window, weekdays 08 to 16)" })}</span>
                        </span>
                      ) : (
                        "-"
                      )}
                    </dd>
                  </dl>
                  {rad.konversation?.some((m) => m.direction === "inbound") ? (
                    <Konversation rad={rad} signatur={signatur} />
                  ) : (
                    (() => {
                      const [brod, svans] = delaMejl(rad.body, signatur);
                      return <Mejlvisning amne={rad.subject} brodtext={brod} svans={svans} signatur={signatur} />;
                    })()
                  )}
                  {/* Provmejlet: på köposten för ett schemalagt, på meddelandet för ett skickat (LU-087). Utan fält: redigeraren visar bara knappen och utfallet. */}
                  <Utkastredigerare
                    nyckel={`prov-${rad.id}`}
                    amne={rad.subject}
                    brodtext=""
                    svans={null}
                    signatur={null}
                    redigerbar={false}
                    visaText={false}
                    provmejl={rad.schemalagt ? { queueItemId: rad.queue_item_id ?? null } : { messageId: rad.id }}
                    skriv={skriv}
                  />
                </div>
              ) : null}
            </div>
          </LayoutContent>
        }
        footer={
          post ? (
            <LayoutFooter hasDivider>
              <HStack gap={2} vAlign="center" justify="between" wrap="wrap">
                {prospekt ? (
                  <Button label={text({ sv: "Öppna leadet", en: "Open the lead" })} variant="ghost" icon={<Icon icon={ArrowRight} size="sm" />} href={`${bas}/iris/leads?lead=${encodeURIComponent(prospekt)}`} />
                ) : (
                  <Text type="supporting" color="secondary">
                    {ko?.created_at ? (
                      <>
                        {text({ sv: "Skrivet ", en: "Written " })}
                        <Timestamp value={ko.created_at} format="relative" />
                      </>
                    ) : null}
                  </Text>
                )}
                {rad && post.slag === "snart" ? (
                  <HStack gap={1} vAlign="center" wrap="wrap">
                    <Button label={text({ sv: "Tillbaka till Iris", en: "Back to Iris" })} variant="ghost" icon={<Icon icon={Undo2} size="sm" />} {...av} onClick={() => tillbaka(rad)} />
                    <Button label={text({ sv: "Ändra tid", en: "Change time" })} variant="ghost" icon={<Icon icon={CalendarClock} size="sm" />} {...av} onClick={() => andraTid(rad)} />
                    <Button label={text({ sv: "Skicka nu", en: "Send now" })} variant="primary" icon={<Icon icon={Send} size="sm" />} {...av} onClick={() => skickaNu(rad)} />
                  </HStack>
                ) : null}
                {rad && post.slag === "skickat" && skickatlage(rad) === "vantar" && rad.prospect_id ? (
                  <Button label={text({ sv: "Skapa uppföljning", en: "Create follow-up" })} variant="secondary" icon={<Icon icon={FilePlus2} size="sm" />} {...av} onClick={() => uppfoljning(rad)} />
                ) : null}
              </HStack>
            </LayoutFooter>
          ) : undefined
        }
      />
    </Drawer>
  );
}
