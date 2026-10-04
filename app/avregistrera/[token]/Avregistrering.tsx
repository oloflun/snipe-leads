"use client";

import { useLocale, type Localized } from "@/lib/i18n";

/**
 * Det besökaren läser på avregistreringssidan. Sidan själv (page.tsx) är en
 * serverkomponent eftersom inlösen är en server action; språkvalet bor i
 * klienten, så texten renderas här.
 */

export type Utfall = "avregistrerad" | "redan_avregistrerad" | "okand_token" | "fel";

const BESKED: Record<Utfall, { rubrik: Localized; text: Localized }> = {
  avregistrerad: {
    rubrik: { sv: "Klart. Du hör inte av oss igen.", en: "Done. You will not hear from us again." },
    text: {
      sv: "Din adress är borttagen från utskicken. Det gäller omedelbart och för alla framtida utskick från avsändaren, inte bara den här kampanjen.",
      en: "Your address has been removed from the mailings. This applies immediately and to all future mailings from the sender, not just this campaign."
    }
  },
  redan_avregistrerad: {
    rubrik: { sv: "Du var redan avregistrerad.", en: "You were already unsubscribed." },
    text: {
      sv: "Adressen fanns redan i spärrlistan. Får du ändå ett mejl från oss är det ett fel vi vill veta om — svara på mejlet så tittar vi på det.",
      en: "The address was already on the block list. If you still get an email from us, that is a mistake we want to know about. Reply to the email and we will look into it."
    }
  },
  okand_token: {
    rubrik: { sv: "Länken går inte att känna igen.", en: "We do not recognise this link." },
    text: {
      sv: "Den kan ha blivit avklippt när mejlet vidarebefordrades. Svara på mejlet du fick och skriv att du vill bli avregistrerad, så gör vi det för hand.",
      en: "It may have been cut off when the email was forwarded. Reply to the email you received and say that you want to unsubscribe, and we will do it by hand."
    }
  },
  fel: {
    rubrik: { sv: "Något gick fel på vår sida.", en: "Something went wrong on our side." },
    text: {
      sv: "Din avregistrering blev inte sparad. Svara på mejlet du fick så gör vi det för hand — du ska inte behöva försöka igen.",
      en: "Your unsubscribe was not saved. Reply to the email you received and we will do it by hand. You should not have to try again."
    }
  }
};

const T = {
  fraga: { sv: "Vill du sluta få de här mejlen?", en: "Do you want to stop getting these emails?" },
  forklaring: {
    sv: "Tryck på knappen så tas din adress bort ur utskicken. Det gäller omedelbart och för alla framtida utskick från avsändaren.",
    en: "Press the button and your address will be removed from the mailings. This applies immediately and to all future mailings from the sender."
  },
  knapp: { sv: "Avregistrera mig", en: "Unsubscribe me" }
} satisfies Record<string, Localized>;

export function Avregistrering({
  utfall,
  token,
  action
}: Readonly<{
  utfall?: string;
  token: string;
  action: (formData: FormData) => Promise<void>;
}>) {
  const { text } = useLocale();
  const besked = utfall && Object.hasOwn(BESKED, utfall) ? BESKED[utfall as Utfall] : null;

  return (
    <main className="mx-auto flex min-h-screen max-w-[64ch] flex-col justify-center px-6 py-16">
      {besked ? (
        <>
          <h1 className="font-display text-[clamp(1.75rem,4vw,2.5rem)] font-semibold leading-tight tracking-[-0.02em]">
            {text(besked.rubrik)}
          </h1>
          <p className="mt-5 text-[1.0625rem] leading-[1.7] text-ink-muted">{text(besked.text)}</p>
        </>
      ) : (
        <>
          <h1 className="font-display text-[clamp(1.75rem,4vw,2.5rem)] font-semibold leading-tight tracking-[-0.02em]">
            {text(T.fraga)}
          </h1>
          <p className="mt-5 text-[1.0625rem] leading-[1.7] text-ink-muted">{text(T.forklaring)}</p>
          <form action={action} className="mt-9">
            <input type="hidden" name="token" value={token} />
            <button
              type="submit"
              className="focus-ring inline-flex min-h-12 items-center rounded-input bg-ink px-7 text-[1rem] font-semibold text-paper transition-colors hover:bg-ink2"
            >
              {text(T.knapp)}
            </button>
          </form>
        </>
      )}
    </main>
  );
}
