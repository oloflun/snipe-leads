"""Fas R3 (bd snipe-7mk, plans/2026-08-29-redis-agentarkitektur.md §3+§5):
arbetsminnet. Rullande samtalssummering med TTL, bakom samma Memory/Redis-par
(INV-STORE-mönstret) som `app/cache/` — sviten är grön utan Redis.

Medvetet TOM i övrigt, av samma skäl som `app/cache/__init__.py`: importera
submodulen explicit (`from app.minne import arbetsminne`), inte via det här
namnet.
"""
