"""Aura redistribution when a bet closes.

Reward formula (per characterization):
- Total losing pool = sum(stake) of all losers.
- Distributed proportionally among winners by their stake share.
- Difficulty multiplier: Easy x1.25, Medium x1.5, Hard x2.0.
- Final reward per winner = (user_stake / total_winner_stake) * losing_pool * difficulty_mult.
- No creator fee.
"""
from app.models import Bet, Difficulty, Participation, User


DIFFICULTY_MULTIPLIER = {
    Difficulty.EASY: 1.25,
    Difficulty.MEDIUM: 1.5,
    Difficulty.HARD: 2.0,
}


def redistribute_aura(bet: Bet) -> None:
    """Settle a closed bet: set is_winner from winning_side, then redistribute Aura.

    Caller must have set bet.status = CLOSED, bet.winning_side, and bet.closed_at.
    """
    participations = list(bet.participations.all())
    if not participations:
        return

    winning_side = (bet.winning_side or "").strip().lower()
    if winning_side not in ("yes", "no"):
        return

    for p in participations:
        side = (p.side or "yes").strip().lower()
        p.is_winner = side == winning_side

    winners = [p for p in participations if p.is_winner]
    losers = [p for p in participations if not p.is_winner]

    losing_pool = sum(p.stake for p in losers)
    total_winner_stake = sum(p.stake for p in winners)
    mult = DIFFICULTY_MULTIPLIER.get(bet.difficulty, Difficulty.MEDIUM) or 1.0

    for p in winners:
        if total_winner_stake > 0:
            proportion = p.stake / total_winner_stake
            reward = round(proportion * losing_pool * mult)
            u = p.user
            if u:
                u.aura += p.stake + reward  # stake back + share of losing pool
                u.wins += 1
                u.open_bets = max(0, (u.open_bets or 0) - 1)

    for p in losers:
        u = p.user
        if u:
            u.losses += 1
            u.open_bets = max(0, (u.open_bets or 0) - 1)

    # Caller commits
