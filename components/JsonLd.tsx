/**
 * Strukturerad data som ett JSON-LD-skript i sidans HTML.
 *
 * Serverkomponent: schemat ska stå i det första svaret, där en sökmotor och en
 * AI-crawler läser det, inte skrivas in av JavaScript efteråt.
 *
 * `<` escapas eftersom en sträng i datan som innehåller `</script>` annars
 * hade avslutat skripttaggen mitt i JSON:en.
 */
export function JsonLd({ data }: Readonly<{ data: Record<string, unknown> }>) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }}
    />
  );
}
