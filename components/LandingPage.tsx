"use client";

import Link from "next/link";
import { Logo } from "@/components/Logo";
import { companies } from "@/lib/mock-data";

const customerBand = [
  "Bergslagens Plåt",
  "Fjord Fastigheter",
  "Havre Restauranggrupp",
  "Lyft Gymkedja",
  "Klaravik Fastighet",
  "Care Nordic",
  "Måleri & Skala",
  "Sundsval Logistik",
  "Granér Revision",
  "Södra Dataateljén"
];

const fieldRows = [
  ["Bergslagens Plåt", "Bygg · Skåne", "Ny offertchef", "416", "15,0 %", "Stark"],
  ["Klaravik Fastighet", "Fastighet · Uppsala", "Nya lokaler", "283", "11,6 %", "Lugn"],
  ["Ateljé Måltid", "Restaurang · Göteborg", "B2B-catering", "192", "12,5 %", "Tydlig"],
  ["Nordic Sweat Studios", "Friskvård · Stockholm", "Ny studio", "248", "11,7 %", "Lugn"],
  ["Södra Dataateljén", "B2B SaaS · Linköping", "Säkerhetspartner", "166", "14,9 %", "Stark"],
  ["Care Nordic", "Vårdsteknik · Stockholm", "Nya tjänstesidor", "211", "13,3 %", "Lugn"]
];

const pricingRows = [
  {
    name: "Pilot",
    text: "För ett team som vill pröva Snipra på ett tydligt segment innan arbetsflödet kopplas till mailbox och CRM.",
    detail: "1 segment · 400 konton · manuell review",
    price: "24 800 kr",
    suffix: "/ pilot"
  },
  {
    name: "Operativ",
    text: "För säljteam som vill ha en svensk AI-SDR i vardagen: discovery, research, sekvenser, inbox och veckolärande.",
    detail: "obegränsade kampanjer · bokade möten · veckorapport",
    price: "18 400 kr",
    suffix: "/ mån",
    accent: true
  },
  {
    name: "Hus",
    text: "För bolag där outbound är en ledningsfråga. Vi bygger arbetssättet, granskar tonen och följer reply rate varje vecka.",
    detail: "en dag på plats per månad · direktnummer",
    price: "42 000 kr",
    suffix: "/ mån"
  }
];

export function LandingPage() {
  return (
    <main className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-30 border-b border-ink/15 bg-paper/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1480px] items-baseline justify-between px-6 py-5 md:px-8">
          <Link href="/" className="focus-ring">
            <Logo />
          </Link>
          <nav className="kicker hidden items-baseline gap-10 text-ink/75 md:flex">
            <a href="#metod" className="transition hover:text-ochre">Metod</a>
            <a href="#bevis" className="transition hover:text-ochre">Bevis</a>
            <a href="#prislista" className="transition hover:text-ochre">Prislista</a>
            <a href="#falt" className="transition hover:text-ochre">På fältet</a>
          </nav>
          <Link
            href="/onboarding"
            className="hidden items-center gap-3 bg-ink px-5 py-3 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors duration-500 hover:bg-ochre hover:text-ink md:inline-flex"
          >
            Starta utvärdering
            <span aria-hidden className="font-mono">↗</span>
          </Link>
        </div>
      </header>

      <section className="relative overflow-hidden">
        <div className="blob pointer-events-none absolute -left-40 -top-40 h-[680px] w-[680px] rounded-full bg-ochre/30" />
        <div className="blob pointer-events-none absolute right-0 top-60 h-[420px] w-[420px] rounded-full bg-ink/10" />
        <div className="relative mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 pb-28 pt-16 md:px-8 md:pb-32 md:pt-20">
          <div className="col-span-12 lg:col-span-2 lg:pt-2">
            <div className="kicker text-mineral">Utgåva 04 · vår 2026</div>
            <div className="rule mt-3 text-ink" />
            <div className="kicker mt-3 leading-snug text-mineral">
              Outbound,<br />
              i en svensk takt.
            </div>
          </div>

          <div className="reveal col-span-12 mt-12 min-w-0 lg:col-span-7 lg:mt-0">
            <h1 className="break-words font-display text-[clamp(3.2rem,9vw,9rem)] leading-[0.92] tighten">
              <span className="block">En</span>
              <span className="block italic-disp text-ochre">säljare</span>
              <span className="block">som <span className="italic-disp text-ink2">skriver</span></span>
              <span className="block">i <span className="italic-disp text-ink2">ditt</span> tonläge.</span>
            </h1>
          </div>

          <div className="reveal reveal-delay-1 col-span-12 mt-12 min-w-0 border-ink/15 lg:col-span-3 lg:mt-0 lg:border-l lg:pl-8">
            <p className="max-w-[36ch] text-[17px] leading-[1.55] text-ink/85">
              Snipra läser svenska bolag på riktigt: regional täthet, signaler i text, lokala
              nyheter och kontaktbarhet. Sedan skriver systemet outreach som inte luktar mall.
              Inga aggressiva sekvenser. Bara mejl någon faktiskt vill läsa på en pendel till Hyllie.
            </p>

            <dl className="num mt-10 space-y-5">
              {[
                ["Open rate, jan→apr", "51,3 %", true],
                ["Reply rate, manuellt mätt", "14,8 %", false],
                ["Möten bokade, q1", "217", false]
              ].map(([label, value, accent]) => (
                <div key={String(label)}>
                  <div className="block md:grid md:grid-cols-[minmax(0,1fr)_auto] md:items-baseline md:gap-3">
                    <dt className="kicker min-w-0 text-mineral">{label}</dt>
                    <dd className={`mt-2 block font-display text-2xl italic-disp md:mt-0 md:text-right ${accent ? "text-ochre" : ""}`}>{value}</dd>
                  </div>
                  <div className="rule mt-5 text-ink" />
                </div>
              ))}
            </dl>
          </div>
        </div>

        <div className="mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 pb-6 md:px-8">
          <div className="rule col-span-12 text-ink" />
        </div>
        <div className="kicker mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 pb-12 text-mineral md:px-8">
          <div className="col-span-12 md:col-span-3">Skriven i Malmö</div>
          <div className="col-span-12 mt-2 md:col-span-3 md:mt-0">Tränad på svenska bolagssignaler</div>
          <div className="col-span-12 mt-2 md:col-span-3 md:mt-0">GDPR · RLS · audit logs</div>
          <div className="col-span-12 mt-2 md:col-span-3 md:mt-0 md:text-right">↘ Scrolla för metoden</div>
        </div>
      </section>

      <section className="overflow-hidden border-y border-ink/15 py-7">
        <div className="marquee whitespace-nowrap font-display text-[28px] italic-disp text-ink/45 tighten">
          {[...customerBand, ...customerBand].map((name, index) => (
            <span key={`${name}-${index}`} className="px-6">
              {name}<span className="pl-12 text-ochre">·</span>
            </span>
          ))}
        </div>
      </section>

      <section id="metod" className="mx-auto max-w-[1480px] px-6 pb-24 pt-28 md:px-8 md:pt-32">
        <div className="mb-16 grid grid-cols-12 gap-x-8">
          <div className="col-span-12 md:col-span-3">
            <div className="kicker text-mineral">Sektion 01</div>
            <div className="rule mt-3 text-ink" />
          </div>
          <div className="col-span-12 mt-8 md:col-span-8 md:mt-0">
            <h2 className="font-display text-[clamp(2.4rem,5vw,4.4rem)] leading-[0.98] tighten">
              En outboundmotor ska inte ropa högre. Den ska förstå mer innan den skriver.
            </h2>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-x-8 gap-y-14">
          {[
            ["i", "Signalen sätter tonen", "Nya lokaler, rekrytering, uppdaterade tjänstesidor och lokala nyheter blir konkreta öppningar, inte generiska första meningar."],
            ["ii", "Tonen är din, inte vår", "Produkt, målgrupp, erbjudande, CTA och svensk lågmäld tonalitet lagras som business context och följer varje sida."],
            ["iii", "Inbox-domänen sköts", "Mailbox-hälsa, suppression och stop-on-reply ligger nära sekvensen så utskick inte blir ett separat sidoprojekt."],
            ["iv", "Lärningen är revisionsbar", "Varje rekommendation har källa, signal, variant och utfall. Säljchefen kan se varför något skickades."]
          ].map(([number, title, body]) => (
            <article key={number} className="col-span-12 grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-8 md:col-span-6">
              <div className="col-span-3 font-display text-[112px] leading-[0.7] italic-disp text-ochre/80">{number}</div>
              <div className="col-span-9">
                <h3 className="mb-3 font-display text-2xl tighten">{title}</h3>
                <p className="max-w-[48ch] text-[16px] leading-[1.65] text-ink/75">{body}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section id="bevis" className="relative overflow-hidden bg-ink text-paper">
        <div className="blob pointer-events-none absolute right-[-200px] top-40 h-[600px] w-[600px] rounded-full bg-ochre/20" />
        <div className="relative mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-24 md:px-8">
          <div className="col-span-12 md:col-span-3">
            <div className="kicker text-paper/55">Sektion 02 · Bevis</div>
            <p className="kicker mt-3 leading-snug text-paper/55">Två emailutkast, samma system. Inte en mall.</p>
          </div>
          <div className="col-span-12 mt-10 grid gap-6 md:col-span-9 md:mt-0 md:grid-cols-2">
            {[
              {
                meta: "Bygg · Skåne · 47 anställda",
                title: "Till Karin på Bergslagens Plåt",
                body: "Jag såg att ni söker en offertchef samtidigt som flera kommunala projekt i Skåne öppnar för nya underentreprenörer. Det brukar vara ett läge där rätt första lista sparar mer tid än ännu en generell prospektering.",
                bridge: "Bryggor: lokal projektsignal · ICP-likhet · ej automatisk"
              },
              {
                meta: "Restaurang · Göteborg · 12 enheter",
                title: "Till Marcus på Havre",
                body: "Ni verkar flytta cateringdelen närmare företagsevent. Om målet är fler återkommande kontorsluncher kan Snipra hitta HR- och office-roller där tajmingen redan syns i öppna signaler.",
                bridge: "Bryggor: nyöppning · branschspecifik datapunkt"
              }
            ].map((mail) => (
              <article key={mail.title} className="border border-paper/15 p-6 md:p-8">
                <span className="kicker text-ochre">{mail.meta}</span>
                <h3 className="mb-4 mt-8 font-display text-xl text-paper tighten">{mail.title}</h3>
                <p className="text-[16px] leading-[1.7] text-paper/82">{mail.body}</p>
                <div className="kicker mt-8 text-paper/55">{mail.bridge}</div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="falt" className="mx-auto max-w-[1480px] px-6 py-24 md:px-8">
        <div className="grid grid-cols-12 gap-x-8">
          <div className="col-span-12 md:col-span-3">
            <div className="kicker text-mineral">Sektion 03 · på fältet</div>
            <div className="rule mt-3 text-ink" />
          </div>
          <div className="col-span-12 mt-8 md:col-span-7 md:mt-0">
            <h2 className="font-display text-[clamp(2.2rem,4.4vw,3.6rem)] leading-[1.02] tighten">
              Produktens UI ska kännas som ett arbetsblad, inte som en stapel SaaS-kort.
            </h2>
          </div>
        </div>

        <div className="mt-16 hidden grid-cols-12 gap-x-6 border-b border-ink/15 pb-4 md:grid">
          {["Bolag", "Segment", "Signal", "Konton", "Reply", "Status"].map((head) => (
            <div key={head} className="kicker col-span-2 text-mineral first:col-span-3 last:col-span-1 last:text-right">{head}</div>
          ))}
        </div>
        <div className="divide-y divide-ink/15">
          {fieldRows.map((row) => (
            <Link key={row[0]} href="/leads" className="row grid grid-cols-12 gap-x-6 py-5 transition hover:bg-ochre/5">
              <div className="ticker col-span-12 flex items-center gap-3 font-display text-2xl italic-disp tighten md:col-span-3">{row[0]}</div>
              <div className="kicker col-span-6 mt-2 text-mineral md:col-span-2 md:mt-0">{row[1]}</div>
              <div className="col-span-6 mt-2 text-[15px] text-ink/75 md:col-span-2 md:mt-0">{row[2]}</div>
              <div className="num col-span-4 mt-2 font-mono text-[15px] text-ink/70 md:col-span-2 md:mt-0">{row[3]}</div>
              <div className="num col-span-4 mt-2 font-display text-xl italic-disp text-ochre md:col-span-2 md:mt-0">{row[4]}</div>
              <div className="kicker col-span-4 mt-2 text-right text-ochre md:col-span-1 md:mt-0">{row[5]}</div>
            </Link>
          ))}
        </div>
      </section>

      <section id="prislista" className="border-t border-ink/15">
        <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-8">
          <div className="grid grid-cols-12 gap-x-8">
            <div className="col-span-12 md:col-span-3">
              <div className="kicker text-mineral">Sektion 04 · Prislista</div>
              <div className="rule mt-3 text-ink" />
              <p className="kicker mt-3 leading-snug text-mineral">Prisplaceholder · ersätts med billing senare</p>
            </div>
            <div className="col-span-12 mt-10 md:col-span-9 md:mt-0">
              <ul className="space-y-10">
                {pricingRows.map((tier) => (
                  <li key={tier.name} className="grid grid-cols-12 items-baseline gap-x-6 border-b border-ink/15 pb-8">
                    <div className="col-span-12 md:col-span-5">
                      <h3 className={`font-display text-3xl italic-disp tighten ${tier.accent ? "text-ochre" : ""}`}>{tier.name}</h3>
                      <p className="mt-2 max-w-[42ch] text-[15px] leading-relaxed text-ink/75">{tier.text}</p>
                    </div>
                    <div className="kicker col-span-12 mt-3 leading-snug text-mineral md:col-span-3 md:mt-0">{tier.detail}</div>
                    <div className="col-span-12 mt-3 text-left font-display text-5xl italic-disp tighten md:col-span-4 md:mt-0 md:text-right">
                      {tier.price}<span className="kicker ml-3 text-mineral">{tier.suffix}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section id="start" className="relative overflow-hidden bg-ink text-paper">
        <div className="blob pointer-events-none absolute -bottom-40 -right-40 h-[700px] w-[700px] rounded-full bg-ochre/25" />
        <div className="relative mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-24 md:px-8 md:py-28">
          <div className="col-span-12 md:col-span-7">
            <h2 className="font-display text-[clamp(3rem,7vw,7rem)] leading-[0.92] tighten">
              Skicka <span className="italic-disp text-ochre">ett mejl</span>,<br />
              så svarar någon.<br />
              <span className="italic-disp">På riktigt.</span>
            </h2>
          </div>
          <div className="col-span-12 mt-8 flex flex-col justify-between border-paper/15 md:col-span-5 md:mt-0 md:border-l md:pl-10">
            <p className="max-w-[44ch] text-[17px] leading-[1.6] text-paper/85">
              Börja med onboardingflödet eller gå direkt till arbetsytan. Den visuella riktningen är
              redaktionell, svensk och källbunden hela vägen in i produktens UI.
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-5">
              <Link href="/onboarding" className="inline-flex items-center gap-3 bg-paper px-6 py-4 font-mono text-[13px] uppercase tracking-[0.18em] text-ink transition-colors duration-500 hover:bg-ochre">
                Starta utvärdering <span className="font-mono">↗</span>
              </Link>
              <Link href="/dashboard" className="inline-flex items-center gap-3 border border-paper/35 px-6 py-4 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors hover:border-ochre hover:text-ochre">
                Öppna arbetsyta
              </Link>
            </div>
          </div>
        </div>
        <div className="border-t border-paper/15">
          <div className="kicker mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-8 text-paper/55 md:px-8">
            <div className="col-span-12 md:col-span-3">Snipra · Malmö</div>
            <div className="col-span-12 mt-2 md:col-span-3 md:mt-0">AI-SDR · sv-SE</div>
            <div className="col-span-12 mt-2 md:col-span-3 md:mt-0">hej@snipra.se · 040-220 814</div>
            <div className="col-span-12 mt-2 md:col-span-3 md:mt-0 md:text-right">MMXXVI · tryckt i en webbläsare</div>
          </div>
        </div>
      </section>
    </main>
  );
}
