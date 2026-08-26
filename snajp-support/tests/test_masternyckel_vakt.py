"""Startvakten mot den incheckade dev-masternyckeln.

Vakten finns för att `deps.require_master_key` accepterar fältets default
rakt av, och bakom nyckeln ligger hela /api/admin/* — cross-tenant-läsning
av varje kunds data. En miljö som glömt sätta SNAJP_MASTER_API_KEY ska dö
vid deploy (Railway behåller föregående version), inte stå öppen tills
någon provar nyckeln som står på GitHub.

Se app/config.py: Settings.master_key_fault och app/main.py: lifespan.
"""

from app.config import Settings

DEV_DEFAULT = "snajp_master_dev_key_change_me"


def _settings(**kwargs) -> Settings:
    # _env_file=None: annars läses snajp-support/.env in och testet mäter
    # utvecklarens maskin i stället för koden.
    return Settings(_env_file=None, **kwargs)


def test_databas_med_dev_default_vagras():
    fel = _settings(
        database_url="postgresql://snajp_app:x@db.example:5432/railway",
        snajp_master_api_key=DEV_DEFAULT,
    ).master_key_fault()
    assert fel is not None
    assert "SNAJP_MASTER_API_KEY" in fel


def test_riktig_nyckel_slapper_igenom():
    fel = _settings(
        database_url="postgresql://snajp_app:x@db.example:5432/railway",
        snajp_master_api_key="snajp_master_e2e0000000000000000000000",
    ).master_key_fault()
    assert fel is None


def test_utan_databas_far_dev_defaulten_leva():
    """Lokal körning och testsviten kör MemoryStorage utan DATABASE_URL —
    där finns ingen kunddata att skydda, och ett krav på nyckel hade bara
    lärt folk att sätta en låtsasnyckel."""
    fel = _settings(database_url="", snajp_master_api_key=DEV_DEFAULT).master_key_fault()
    assert fel is None
