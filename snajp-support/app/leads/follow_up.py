"""Leads Fas D (Del H): uppföljningar drivs av VILKEN SPAK i värdeekvationen
som är svagast i just det här erbjudandet (mk:offers diagnos, 1-10 per
spak), inte av mejlets POSITION i en generisk tabell. Se plan Del H för den
fulla motiveringen och Livrustnings-exemplet.

Fyra förbättringar nämns i planen som "alla obyggda tills du säger till":
signalstyrd tajming, avbryt på negativ signal, en bredare svensk
dödperiod-kalender (hela juli, veckorna kring midsommar/jul — inte bara de
enskilda dagarna i app/leads/timing_gate.py), och lärande per kund. De
byggs INTE i den här ökningen — planen är explicit om att de kräver ett
uttryckligt ja, inte en gissning. Se ARCHITECTURE_INVARIANTS.md Roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass

LEVERS = ("dream_outcome", "perceived_likelihood", "time_delay", "effort_sacrifice")


class FollowUpSequenceError(ValueError):
    pass


@dataclass(frozen=True)
class FollowUpStep:
    sequence_number: int  # 0 = initial, 1..len(LEVERS)-1 = uppföljning, sist = breakup
    lever: str | None  # None för breakup-mejlet
    is_breakup: bool = False


def build_follow_up_sequence(value_equation_scores: dict[str, int]) -> list[FollowUpStep]:
    """Ordnar spakarna svagast (lägst poäng) -> starkast och lägger ett
    breakup-mejl sist. Svagast poäng anfalls FÖRST — 'tystnad har alltid en
    orsak, och orsaken är nästan alltid en av dessa spakar' (Del H)."""
    missing = [lever for lever in LEVERS if lever not in value_equation_scores]
    if missing:
        raise FollowUpSequenceError(f"value_equation_scores saknar spakar: {missing}")

    ordered_levers = sorted(LEVERS, key=lambda lever: value_equation_scores[lever])
    steps = [
        FollowUpStep(sequence_number=i, lever=lever) for i, lever in enumerate(ordered_levers)
    ]
    steps.append(FollowUpStep(sequence_number=len(steps), lever=None, is_breakup=True))
    return steps


def weakest_lever(value_equation_scores: dict[str, int]) -> str:
    """Det mk:offers självt kallar 'weakest_lever' — samma fält som lagras i
    offers.weakest_lever (migration 010)."""
    missing = [lever for lever in LEVERS if lever not in value_equation_scores]
    if missing:
        raise FollowUpSequenceError(f"value_equation_scores saknar spakar: {missing}")
    return min(LEVERS, key=lambda lever: value_equation_scores[lever])
