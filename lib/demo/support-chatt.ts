/**
 * Kundchattens förladdade samtal för /demo/support. Påhittat, och märkt som
 * påhittat.
 *
 * Samma mönster som bokföringsdemons FRAGOR (lib/demo/bokforing.ts): besökaren
 * väljer fråga och svaret fälls ut — samtalet drivs av den som läser, men ingen
 * modell körs. Sidan är publik och anonym, och en LLM-körning per besökare
 * kostar pengar och kan svara olika varje gång.
 *
 * Butiken är exempelbutiken Nordlys Handel, samma fiktiva bolag som
 * exempelärendena i lib/demo/support-inbox.ts. Svaren är skrivna som om de
 * kom ur butikens kunskapsbas, och en av frågorna eskalerar med flit: en demo
 * som bara visar det agenten KAN lovar mer än produkten håller.
 */

export type Chattfraga = {
  fraga: string;
  svar: string;
  /** Sant för frågan som visar eskaleringen i stället för ett svar. */
  eskalerar?: boolean;
};

export const CHATTFRAGOR: Chattfraga[] = [
  {
    fraga: "Var är min beställning?",
    svar:
      "Din order skickades från vårt lager i går och är hos ombudet inom " +
      "1 till 3 vardagar. Du fick ett spårningsnummer i bekräftelsemejlet — " +
      "klicka på det så ser du exakt var paketet är just nu.\n\n" +
      "Hittar du inte mejlet kan jag skicka spårningslänken igen, säg bara till."
  },
  {
    fraga: "Kan jag returnera en vara jag öppnat?",
    svar:
      "Ja. Du har 30 dagars öppet köp, och det gäller även om förpackningen är " +
      "öppnad — så länge varan är oskadad och komplett.\n\n" +
      "Registrera returen under Mina sidor så får du en fraktsedel per mejl. " +
      "Återbetalningen görs till samma betalsätt inom 14 dagar från att vi " +
      "tagit emot varan."
  },
  {
    fraga: "Vad kostar frakten?",
    svar:
      "Frakt till ombud kostar 49 kr, och den är fri när ordern är över " +
      "499 kr. Hemleverans finns i de flesta postnummer för 99 kr.\n\n" +
      "Alla priser visas också i kassan innan du betalar, så det kommer inga " +
      "tillägg i efterhand."
  },
  {
    fraga: "Jag vill häva köpet och kräva skadestånd",
    eskalerar: true,
    svar:
      "Det här behöver en människa titta på. Jag har samlat ihop ärendet — " +
      "din fråga, orderhistoriken och det du skrivit — och skickat det till " +
      "kundservice med hög prioritet.\n\n" +
      "Du får svar av en kollega senast nästa vardag. Jag gissar aldrig i " +
      "juridiska frågor: ett fel svar där är dyrare än en timmes väntan."
  },
  {
    fraga: "Har ni butik i Göteborg?",
    svar:
      "Nej, Nordlys Handel säljer bara på nätet. Däremot kan du hämta din " +
      "beställning hos något av våra ombud i Göteborg, ofta redan dagen efter " +
      "att du beställt.\n\n" +
      "Vill du prova en vara först har du alltid 30 dagars öppet köp."
  }
];
