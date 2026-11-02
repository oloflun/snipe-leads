/**
 * Konversationen i Skickat. Kör: node --test "lib/leads/*.test.ts"
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { delaCitat, senasteSvar, type KonversationsMejl } from "./konversation.ts";

test("svar utan citat är hela texten", () => {
  assert.deepEqual(delaCitat("Hej!\n\nLåter bra, ring mig.\n"), ["Hej!\n\nLåter bra, ring mig.", ""]);
});

test("Gmails svenska citatrad skiljer svaret från vårt mejl, även radbruten", () => {
  const body = "Ja tack.\n\nDen tors 22 okt. 2026 kl. 08:00 skrev Sebastian B <seb@snajp.se>:\n> Hej,\n> Hur säkerställer ni";
  assert.deepEqual(delaCitat(body), ["Ja tack.", "Den tors 22 okt. 2026 kl. 08:00 skrev Sebastian B <seb@snajp.se>:\n> Hej,\n> Hur säkerställer ni"]);
  const bruten = "Nej tack.\n\nOn Thu, Oct 22, 2026 at 8:00 AM Sebastian B <\nseb@snajp.se> wrote:\n\nHej,";
  assert.equal(delaCitat(bruten)[0], "Nej tack.");
});

test("Outlooks Från/Skickat-block och avdelaren räknas som citat", () => {
  assert.equal(delaCitat("Återkommer.\n\nFrån: Sebastian B\nSkickat: den 22 oktober 2026\nÄmne: Hej")[0], "Återkommer.");
  assert.equal(delaCitat("Tack!\n-----Ursprungligt meddelande-----\nHej,")[0], "Tack!");
});

test("ett svar som bara är citat visas helt, inte tomt", () => {
  assert.deepEqual(delaCitat("> Hej,\n> text"), ["> Hej,\n> text", ""]);
});

test("senaste svaret är det sista inkomna", () => {
  const k: KonversationsMejl[] = [
    { id: "1", direction: "outbound", subject: "Hej", body: "Hej!", sent_at: "2026-10-22T06:00:00Z" },
    { id: "2", direction: "inbound", subject: null, body: "Först", sent_at: "2026-10-22T09:00:00Z" },
    { id: "3", direction: "inbound", subject: null, body: "Sen", sent_at: "2026-10-23T09:00:00Z" }
  ];
  assert.equal(senasteSvar(k)?.id, "3");
  assert.equal(senasteSvar(undefined), null);
  assert.equal(senasteSvar([k[0]]), null);
});
