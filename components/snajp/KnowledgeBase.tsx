"use client";

import { AlertTriangle, BookOpen, Loader2, Plus, Sparkles, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui";
import { cn } from "@/lib/utils";

type Article = {
  id: string;
  title: string;
  content: string;
  category: string;
  is_placeholder?: boolean;
};

type Category = { id: string; label: string; hint: string };

export function KnowledgeBase({ apiBase }: Readonly<{ apiBase: string }>) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState({ title: "", content: "", category: "ovrigt" });

  const api = useCallback(
    async (path: string, init?: RequestInit) => {
      const response = await fetch(`${apiBase}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...init
      });
      const payload = await response.json();
      if (payload.offline) throw new Error(payload.error);
      if (!response.ok) throw new Error(payload.detail ?? payload.error ?? "Okänt fel");
      return payload;
    },
    [apiBase]
  );

  const load = useCallback(async () => {
    try {
      setError(null);
      const [kb, cats] = await Promise.all([api("/kb"), api("/categories")]);
      setArticles(kb.articles);
      setCategories(cats.categories);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Kunde inte läsa kunskapsbasen.");
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  const act = async (label: string, run: () => Promise<unknown>) => {
    setBusy(label);
    setError(null);
    try {
      await run();
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Något gick fel.");
    } finally {
      setBusy(null);
    }
  };

  const seedTemplate = () =>
    act("template", async () => {
      const r = await api("/kb/template", { method: "POST" });
      setInfo(
        r.created > 0
          ? `${r.created} mallartiklar tillagda. De är märkta [PLATSHÅLLARE] — ersätt texten med era egna villkor.`
          : "Alla mallartiklar fanns redan."
      );
    });

  const addArticle = () =>
    act("add", async () => {
      await api("/kb", { method: "POST", body: JSON.stringify({ articles: [draft] }) });
      setDraft({ title: "", content: "", category: "ovrigt" });
      setAdding(false);
      setInfo("Artikeln är tillagd i kunskapsbasen.");
    });

  const grouped = useMemo(() => {
    return categories
      .map((c) => ({ ...c, items: articles.filter((a) => a.category === c.id) }))
      .filter((g) => g.items.length > 0);
  }, [categories, articles]);

  const placeholders = articles.filter((a) => a.is_placeholder).length;
  const labelOf = (id: string) => categories.find((c) => c.id === id)?.label ?? id;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => setAdding((v) => !v)}
          className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-[7px] bg-ink px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-copper hover:text-ink"
        >
          <Plus className="h-4 w-4" />
          Lägg till artikel
        </button>
        <button
          type="button"
          onClick={seedTemplate}
          disabled={busy !== null}
          title="Fyller kunskapsbasen med branschmallens rubriker som platshållare"
          className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-[7px] border border-ink/12 bg-paper2/70 px-4 py-2.5 text-sm font-semibold text-ink/70 transition hover:border-ochre hover:text-ink disabled:opacity-40"
        >
          {busy === "template" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          Hämta branschmall
        </button>
        <span className="ml-auto flex items-center gap-2 text-xs text-ink/55">
          <BookOpen className="h-4 w-4" />
          {articles.length} artiklar
        </span>
      </div>

      {error ? (
        <div className="rounded-[8px] border border-danger/25 bg-danger/5 px-4 py-3 text-sm text-ink/80">{error}</div>
      ) : null}
      {info ? (
        <div className="rounded-[8px] border border-moss/25 bg-moss/5 px-4 py-3 text-sm text-ink/80">{info}</div>
      ) : null}

      {placeholders > 0 ? (
        <div className="flex items-start gap-2 rounded-[8px] border border-copper/25 bg-copper/5 px-4 py-3 text-sm text-ink/75">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-copper" />
          <span>
            <strong>{placeholders} av {articles.length} artiklar är platshållare.</strong> Agenten svarar
            utifrån den här texten — ersätt den med era egna villkor innan ni svarar riktiga kunder.
          </span>
        </div>
      ) : null}

      {adding ? (
        <div className="space-y-3 rounded-[10px] border border-ink/12 bg-paper p-5 shadow-hairline">
          <div className="flex items-center justify-between">
            <p className="kicker text-mineral">Ny artikel</p>
            <button type="button" onClick={() => setAdding(false)} className="focus-ring rounded-full p-1 text-ink/40 hover:text-ink">
              <X className="h-4 w-4" />
            </button>
          </div>
          <input
            value={draft.title}
            onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            placeholder="Rubrik — t.ex. Garantitid och vad garantin omfattar"
            className="focus-ring w-full rounded-[7px] border border-ink/12 bg-paper px-3 py-2.5 text-sm outline-none placeholder:text-ink/35"
          />
          <select
            value={draft.category}
            onChange={(e) => setDraft({ ...draft, category: e.target.value })}
            className="focus-ring rounded-[7px] border border-ink/12 bg-paper px-3 py-2.5 text-sm"
          >
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
          <textarea
            value={draft.content}
            onChange={(e) => setDraft({ ...draft, content: e.target.value })}
            rows={6}
            placeholder="Skriv svaret som ni vill att kunden ska få det. Agenten använder enbart den här texten som underlag — den hittar aldrig på."
            className="focus-ring w-full resize-y rounded-[7px] border border-ink/12 bg-paper p-3 text-sm leading-6 outline-none placeholder:text-ink/35"
          />
          <button
            type="button"
            onClick={addArticle}
            disabled={busy !== null || draft.title.length < 3 || draft.content.length < 10}
            className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-[7px] bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:bg-moss disabled:opacity-40"
          >
            {busy === "add" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Spara artikel
          </button>
        </div>
      ) : null}

      {articles.length === 0 ? (
        <div className="rounded-[10px] border border-dashed border-ink/15 bg-paper/45 p-10 text-center">
          <BookOpen className="mx-auto h-6 w-6 text-mineral" />
          <h3 className="mt-4 font-semibold">Kunskapsbasen är tom</h3>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink/60">
            Agenten svarar bara utifrån den här texten och hittar aldrig på. Med tom kunskapsbas
            eskaleras därför varje ärende till en människa. Börja med <strong>Hämta branschmall</strong> för
            att få strukturen, och ersätt sedan texten med era egna villkor.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {grouped.map((group) => (
            <div key={group.id}>
              <div className="flex items-baseline gap-3">
                <h3 className="font-semibold">{group.label}</h3>
                <span className="text-xs text-ink/45">{group.hint}</span>
              </div>
              <div className="mt-2 divide-y divide-ink/10 overflow-hidden rounded-[10px] border border-ink/12 bg-paper shadow-hairline">
                {group.items.map((article) => (
                  <div key={article.id} className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => setOpen(open === article.id ? null : article.id)}
                      className="focus-ring flex w-full items-center justify-between gap-3 text-left"
                    >
                      <span className="truncate text-sm font-medium">{article.title}</span>
                      {article.is_placeholder ? <Badge tone="warn">Platshållare</Badge> : null}
                    </button>
                    {open === article.id ? (
                      <p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-ink/65">{article.content}</p>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
