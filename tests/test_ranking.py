"""Tests the pure personal-ranking calculations and matchup selection rules."""

from ffguru.personal_rankings.ranking import RankedPlayer, choose_pair, elo_ratings, initial_rating


def test_initial_rating_uses_ecr_as_the_prior() -> None:
    assert initial_rating(1.0) == 2000.0
    assert initial_rating(11.0) == 1960.0


def test_elo_moves_winner_up_and_loser_down_by_equal_amounts() -> None:
    winner, loser = elo_ratings(1900.0, 1900.0)

    assert winner == 1912.0
    assert loser == 1888.0


def test_pair_is_close_to_the_least_seen_player_and_avoids_last_pair() -> None:
    players = [
        RankedPlayer(index, 2000.0 - index * 4, float(index), 2 if index != 10 else 0)
        for index in range(1, 21)
    ]
    last_pair = frozenset((10, 9))

    left_id, right_id = choose_pair(players, {}, last_pair, 0)

    assert 10 in (left_id, right_id)
    assert abs(left_id - right_id) <= 5
    assert frozenset((left_id, right_id)) != last_pair


def test_pair_selection_balances_three_appearances_per_player() -> None:
    players = [RankedPlayer(index, 2000.0 - index * 4, float(index), 0) for index in range(1, 21)]
    counts: dict[frozenset[int], int] = {}
    last_pair = None

    for completed in range(40):
        left_id, right_id = choose_pair(players, counts, last_pair, completed)
        pair = frozenset((left_id, right_id))
        counts[pair] = counts.get(pair, 0) + 1
        players = [
            RankedPlayer(
                player.player_id,
                player.personal_rating,
                player.ecr,
                player.appearances + int(player.player_id in pair),
            )
            for player in players
        ]
        last_pair = pair

    assert min(player.appearances for player in players) >= 3
