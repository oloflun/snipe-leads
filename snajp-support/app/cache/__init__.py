"""Fas R2 (bd snipe-cku, plans/2026-08-29-redis-agentarkitektur.md §2.3+§4):
hastighetslagret. Embeddingcache, semantisk svarscache och versionering av
KB/konfiguration — allt bakom Memory/Redis-par (INV-STORE-mönstret), så
sviten är grön utan Redis.

Medvetet TOM i övrigt: submodulerna importerar varandra och `app.agent.
embeddings` sinsemellan (svarscache -> agent.embeddings, embeddings ->
cache.embeddingcache), och ett `__init__.py` som eagerly importerar alla tre
hade gjort den kedjan cirkulär vid paketimport. Importera submodulerna
explicit (`from app.cache import embeddingcache`), inte via det här namnet.
"""
