"""Abonnemangsnivåer — en enda plats att justera.

Backenden äger TAKEN, eftersom det är här kvoten faktiskt upprätthålls. Stripes
pris-id:n ligger på Next-sidan (miljövariabler), eftersom det är där checkout
skapas. Varje sida äger alltså det den ansvarar för, och `id` nedan är nyckeln
som binder ihop dem.

Att justera en nivå: ändra `monthly_responses` här. Priset ändras i Stripe.
Att lägga till en nivå: lägg till i PLANS här och sätt STRIPE_PRICE_<ID> i Next.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    # Antal AI-svar per månad. None = obegränsat (används av interna nivåer).
    monthly_responses: int | None
    description: str


PLANS: tuple[Plan, ...] = (
    Plan(
        id="free",
        name="Prova",
        monthly_responses=50,
        description="För att testa agenten på riktiga frågor innan ni bestämmer er.",
    ),
    Plan(
        id="bas",
        name="Bas",
        monthly_responses=500,
        description="För mindre bolag med jämn ärendeström.",
    ),
    Plan(
        id="plus",
        name="Plus",
        monthly_responses=2000,
        description="För bolag där kundtjänst är en egen funktion.",
    ),
    Plan(
        id="pro",
        name="Pro",
        monthly_responses=10000,
        description="För hög volym och flera inkorgar.",
    ),
    # Intern nivå: demo, pilot och vår egen arbetsyta ska aldrig kvotstoppas.
    Plan(
        id="intern",
        name="Intern",
        monthly_responses=None,
        description="Obegränsad. Endast för egna arbetsytor.",
    ),
)

PLANS_BY_ID = {plan.id: plan for plan in PLANS}

# Nya tenants hamnar här tills något annat sätts.
DEFAULT_PLAN_ID = "free"

# Andel av taket där kunden ska varnas. Under detta sägs ingenting.
WARN_AT = 0.8


def get_plan(plan_id: str | None) -> Plan:
    """Okänt eller saknat plan-id faller tillbaka på gratisnivån.

    Medvetet konservativt: hellre en låg kvot än obegränsat om databasen
    innehåller ett plan-id vi inte känner igen.
    """
    return PLANS_BY_ID.get(plan_id or "", PLANS_BY_ID[DEFAULT_PLAN_ID])


def quota_state(plan_id: str | None, used: int) -> dict:
    """Var kunden befinner sig i förhållande till sitt tak."""
    plan = get_plan(plan_id)
    cap = plan.monthly_responses

    if cap is None:
        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "used": used,
            "cap": None,
            "remaining": None,
            "ratio": 0.0,
            "warn": False,
            "exceeded": False,
        }

    ratio = used / cap if cap else 1.0
    return {
        "plan_id": plan.id,
        "plan_name": plan.name,
        "used": used,
        "cap": cap,
        "remaining": max(cap - used, 0),
        "ratio": round(ratio, 3),
        "warn": ratio >= WARN_AT and used < cap,
        "exceeded": used >= cap,
    }
