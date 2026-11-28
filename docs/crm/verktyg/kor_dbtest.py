"""Kör tests/db/test_crm_lagring.py mot PGlite genom psycopg2.

asyncpg hänger sig mot PGlites socketserver, så här byts asyncpg.connect mot
ett skal runt psycopg2 med samma metoder. SQL:en är densamma: `$n` görs om
till namngivna parametrar och skickas som den står. Det som INTE provas här
är asyncpgs egen typhärledning av parametrar; den provas mot en riktig
Postgres (CI-jobbet databastester, eller Docker lokalt).
"""
import os
import re
import sys

import asyncpg
import psycopg2
import psycopg2.extras

DSN = "postgresql://postgres:postgres@127.0.0.1:54329/postgres?sslmode=disable"
_FEL = {"23514": asyncpg.CheckViolationError, "42501": asyncpg.InsufficientPrivilegeError}


class DbFel(Exception):
    def __init__(self, kod, text):
        super().__init__(text)
        self.sqlstate = kod


def _om(sql, args):
    if not args:
        return sql, None
    return re.sub(r"\$(\d+)", lambda m: f"%(p{m.group(1)})s", sql.replace("%", "%%")), {
        f"p{i + 1}": psycopg2.extras.Json(a) if isinstance(a, dict) else a for i, a in enumerate(args)}


class Tx:
    def __init__(self, conn):
        self.conn, self.namn = conn, None

    async def start(self):
        self.conn.djup += 1
        self.namn = f"sp{self.conn.djup}"
        self.conn.kor("begin" if self.conn.djup == 1 else f"savepoint {self.namn}")

    async def rollback(self):
        self.conn.kor("rollback" if self.conn.djup == 1 else f"rollback to savepoint {self.namn}")
        self.conn.djup -= 1

    async def __aenter__(self):
        await self.start()

    async def __aexit__(self, typ, fel, tb):
        if typ is not None:
            await self.rollback()
        else:
            self.conn.kor("commit" if self.conn.djup == 1 else f"release savepoint {self.namn}")
            self.conn.djup -= 1
        return False


class Conn:
    def __init__(self):
        self.pg = psycopg2.connect(DSN, connect_timeout=8)
        self.pg.autocommit = True
        self.djup = 0

    def kor(self, sql, *args):
        cur = self.pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(*[x for x in _om(sql, args) if x is not None])
        except psycopg2.Error as fel:
            raise _FEL.get(fel.pgcode, lambda t: DbFel(fel.pgcode, t))(str(fel)) from None
        return cur

    def transaction(self):
        return Tx(self)

    async def execute(self, sql, *args):
        return self.kor(sql, *args).statusmessage

    async def executemany(self, sql, rader):
        for rad in rader:
            self.kor(sql, *rad)

    async def fetch(self, sql, *args):
        return self.kor(sql, *args).fetchall()

    async def fetchrow(self, sql, *args):
        return self.kor(sql, *args).fetchone()

    async def fetchval(self, sql, *args):
        rad = self.kor(sql, *args).fetchone()
        return next(iter(rad.values())) if rad else None

    async def close(self):
        self.pg.close()


async def _anslut(dsn=None, **kw):
    return Conn()


asyncpg.connect = _anslut
os.environ["DATABASE_URL"] = DSN
import pytest  # noqa: E402

sys.exit(pytest.main(["tests/db/test_crm_lagring.py", "-q", "--no-header", "-p", "no:cacheprovider", *sys.argv[1:]]))
