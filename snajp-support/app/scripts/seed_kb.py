"""Seedar kunskapsbasen (+ demo-API-nyckel) i Postgres.

Körs bara i Postgres-läget (kräver DATABASE_URL). Embeddings beräknas endast
om en riktig OpenAI-nyckel finns; annars lämnas kolumnen NULL och tjänsten
använder svensk fulltextsökning tills embeddings fyllts på.

Kör:  python -m app.scripts.seed_kb
"""

import asyncio

from ..config import DEFAULT_TENANT_ID, get_settings
from ..kb_articles import KB_ARTICLES


async def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL saknas — in-memory-läget seedar sig självt. Inget att göra.")
        return

    from ..storage.postgres import PostgresStorage

    storage = await PostgresStorage.connect(settings.database_url)
    try:
        existing = await storage.list_kb(DEFAULT_TENANT_ID)
        if existing:
            print(f"Default-tenantens kunskapsbas har redan {len(existing)} artiklar — hoppar över.")
        else:
            embeddings: list[list[float] | None] = [None] * len(KB_ARTICLES)
            if not settings.is_simulation():
                from ..agent.embeddings import embed_text

                print("Beräknar embeddings via OpenAI ...")
                embeddings = [
                    await embed_text(f"{a['title']}\n{a['content']}") for a in KB_ARTICLES
                ]
            for article, embedding in zip(KB_ARTICLES, embeddings):
                await storage.add_kb_article(
                    DEFAULT_TENANT_ID,
                    title=article["title"],
                    content=article["content"],
                    category=article["category"],
                    embedding=embedding,
                )
            print(f"Seedade {len(KB_ARTICLES)} artiklar till default-tenanten.")

        await storage.create_api_key(
            DEFAULT_TENANT_ID, tenant_name="Nordlys Handel", raw_key=settings.snajp_demo_api_key
        )
        print("Demo-API-nyckel registrerad.")
    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
