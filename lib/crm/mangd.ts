/**
 * Kör en ändring per post, några åt gången, och rapporterar förloppet. En post
 * som faller stoppar inte de andra: utfallet säger vilka som gick och vilka som
 * föll, med felet per post.
 */
export async function iMangd(
  ids: string[],
  gor: (id: string) => Promise<unknown>,
  framsteg: (klara: number) => void,
  samtidiga = 4
): Promise<{ klara: string[]; fall: { id: string; fel: unknown }[] }> {
  const klara: string[] = [];
  const fall: { id: string; fel: unknown }[] = [];
  let nasta = 0;
  let gjorda = 0;
  const arbetare = async () => {
    while (nasta < ids.length) {
      const id = ids[nasta++];
      try {
        await gor(id);
        klara.push(id);
      } catch (fel) {
        fall.push({ id, fel });
      }
      framsteg(++gjorda);
    }
  };
  await Promise.all(Array.from({ length: Math.min(samtidiga, ids.length) }, arbetare));
  return { klara, fall };
}
