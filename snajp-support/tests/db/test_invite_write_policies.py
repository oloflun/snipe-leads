"""Migration 032: skrivpolicyerna på workspace_invites.

Kör mot en riktig databas — hoppas över utan WEB_DATABASE_URL (samma mönster
som test_rls_isolation.py).

VARFÖR TESTET ÄR SÅ NOGGRANT MED SIN UPPSTÄLLNING: policyn har TVÅ villkor
(rätt arbetsyta OCH ägarroll), och ett slarvigt negativtest bekräftar den utan
att pröva den. Två falska utfall inträffade när den här kontrollen gjordes för
hand första gången:

1. `update public.profiles set role='member'` för att degradera testanvändaren
   träffade NOLL rader — profiles har bara en SELECT-policy, så en UPDATE utan
   policy är inte ett fel, den matchar bara ingenting. Rollen ändrades aldrig,
   och "nekad" var därför inget bevis.
2. En ny användare skapad via `auth.users` fick en EGEN arbetsyta av triggern
   `on_auth_user_created`. Insert:en nekades då för fel workspace, inte för fel
   roll — testet mätte det ena villkoret och trodde det mätte det andra.

Båda måste alltså ställas upp med en priviligierad anslutning, och testet
kontrollerar uttryckligen att medlemmen hamnat i RÄTT arbetsyta innan det
drar någon slutsats av ett avslag.
"""

from __future__ import annotations

import os
import uuid

import asyncpg
import pytest

WEB_URL = os.environ.get("WEB_DATABASE_URL", "")
ADMIN_URL = os.environ.get("ADMIN_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not (WEB_URL and ADMIN_URL),
    reason="Kräver WEB_DATABASE_URL (snajp_web) och ADMIN_DATABASE_URL (ägarroll).",
)


async def _owner(admin: asyncpg.Connection) -> tuple[str, str]:
    row = await admin.fetchrow(
        "select id, workspace_id from public.profiles where role = 'owner' limit 1"
    )
    if row is None:
        pytest.skip("Kräver minst en ägare i databasen.")
    return str(row["id"]), str(row["workspace_id"])


@pytest.mark.anyio
async def test_agare_far_bjuda_in_i_egen_arbetsyta():
    """Positivkontrollen. Utan den kan alla negativtest nedan vara gröna för
    att INGEN kan skriva — vilket också vore ett fel, bara ett annat."""
    admin = await asyncpg.connect(ADMIN_URL)
    web = await asyncpg.connect(WEB_URL)
    try:
        owner_id, workspace_id = await _owner(admin)
        tx = web.transaction()
        await tx.start()
        try:
            await web.execute("select set_config('app.user_id', $1, true)", owner_id)
            await web.execute(
                "insert into public.workspace_invites (email, workspace_id, role) "
                "values ($1, $2, 'member')",
                f"positiv-{uuid.uuid4().hex[:8]}@example.test",
                workspace_id,
            )
        finally:
            await tx.rollback()  # ALDRIG lämna testdata i en riktig databas
    finally:
        await web.close()
        await admin.close()


@pytest.mark.anyio
async def test_agare_kan_inte_bjuda_in_i_frammande_arbetsyta():
    admin = await asyncpg.connect(ADMIN_URL)
    web = await asyncpg.connect(WEB_URL)
    try:
        owner_id, _ = await _owner(admin)
        tx = web.transaction()
        await tx.start()
        try:
            await web.execute("select set_config('app.user_id', $1, true)", owner_id)
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await web.execute(
                    "insert into public.workspace_invites (email, workspace_id, role) "
                    "values ('angripare@example.test', $1, 'owner')",
                    str(uuid.uuid4()),
                )
        finally:
            await tx.rollback()
    finally:
        await web.close()
        await admin.close()


@pytest.mark.anyio
async def test_medlem_i_ratt_arbetsyta_kan_varken_bjuda_in_eller_ta_bort():
    """Det avgörande testet: samma arbetsyta, fel roll.

    Medlemmen flyttas uttryckligen till ägarens arbetsyta, eftersom triggern
    annars ger den en egen — och då hade avslaget kommit av fel skäl.
    """
    admin = await asyncpg.connect(ADMIN_URL)
    web = await asyncpg.connect(WEB_URL)
    member_id = str(uuid.uuid4())
    try:
        owner_id, workspace_id = await _owner(admin)
        await admin.execute(
            "insert into auth.users (id, email, raw_user_meta_data) "
            "values ($1, $2, jsonb_build_object('full_name', 'Testmedlem'))",
            member_id,
            f"medlem-{member_id[:8]}@example.test",
        )
        await admin.execute(
            "update public.profiles set workspace_id = $1, role = 'member' where id = $2",
            workspace_id,
            member_id,
        )

        tx = web.transaction()
        await tx.start()
        try:
            await web.execute("select set_config('app.user_id', $1, true)", member_id)

            same_workspace = await web.fetchval(
                "select public.current_workspace_id() = $1::uuid", workspace_id
            )
            assert same_workspace, (
                "Medlemmen hamnade i FEL arbetsyta. Ett avslag nedan hade då "
                "bevisat workspace-villkoret, inte rollvillkoret."
            )
            assert not await web.fetchval("select public.current_user_is_owner()")

            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await web.execute(
                    "insert into public.workspace_invites (email, workspace_id, role) "
                    "values ('smyg@example.test', $1, 'owner')",
                    workspace_id,
                )
        finally:
            await tx.rollback()

        # Radering: RLS ger noll träffar, inte ett fel. Därför mäts radantalet.
        tx2 = web.transaction()
        await tx2.start()
        try:
            await web.execute("select set_config('app.user_id', $1, true)", member_id)
            status = await web.execute(
                "delete from public.workspace_invites where workspace_id = $1", workspace_id
            )
            assert status.endswith(" 0"), (
                f"Medlem kunde radera inbjudningar: {status!r}. En DELETE utan "
                f"policy felar inte — den träffar bara ingenting, så radantalet "
                f"är det enda som avslöjar en läcka."
            )
        finally:
            await tx2.rollback()
    finally:
        await admin.execute("delete from public.profiles where id = $1", member_id)
        await admin.execute("delete from auth.users where id = $1", member_id)
        await web.close()
        await admin.close()
