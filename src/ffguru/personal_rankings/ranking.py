"""Contains the deterministic rating and matchup-selection rules."""

from dataclasses import dataclass

INITIAL_RATING = 2000.0
ECR_RATING_STEP = 4.0
ELO_K_FACTOR = 24.0
OPPONENT_WINDOW = 5
COVERAGE_TARGET = 3


@dataclass(frozen=True)
class RankedPlayer:
    player_id: int
    personal_rating: float
    ecr: float
    appearances: int


def initial_rating(ecr: float) -> float:
    return INITIAL_RATING - ECR_RATING_STEP * (ecr - 1.0)


def elo_ratings(winner_rating: float, loser_rating: float) -> tuple[float, float]:
    expected_winner = 1.0 / (1.0 + 10.0 ** ((loser_rating - winner_rating) / 400.0))
    change = ELO_K_FACTOR * (1.0 - expected_winner)
    return winner_rating + change, loser_rating - change


def choose_pair(
    players: list[RankedPlayer],
    pair_counts: dict[frozenset[int], int],
    last_pair: frozenset[int] | None,
    completed_count: int,
) -> tuple[int, int]:
    if len(players) < 2:
        raise ValueError("At least two players are required to create a matchup.")

    ordered = sorted(players, key=lambda player: (-player.personal_rating, player.ecr, player.player_id))
    focal_index = min(
        range(len(ordered)),
        key=lambda index: (ordered[index].appearances, index),
    )
    lower = max(0, focal_index - OPPONENT_WINDOW)
    upper = min(len(ordered), focal_index + OPPONENT_WINDOW + 1)
    candidates = [index for index in range(lower, upper) if index != focal_index]

    if last_pair is not None and len(candidates) > 1:
        alternatives = [
            index
            for index in candidates
            if frozenset((ordered[focal_index].player_id, ordered[index].player_id)) != last_pair
        ]
        if alternatives:
            candidates = alternatives

    opponent_index = min(
        candidates,
        key=lambda index: (
            pair_counts.get(
                frozenset((ordered[focal_index].player_id, ordered[index].player_id)),
                0,
            ),
            ordered[index].appearances,
            abs(ordered[focal_index].personal_rating - ordered[index].personal_rating),
            abs(focal_index - index),
            index,
        ),
    )
    left_id = ordered[focal_index].player_id
    right_id = ordered[opponent_index].player_id
    return (right_id, left_id) if completed_count % 2 else (left_id, right_id)
