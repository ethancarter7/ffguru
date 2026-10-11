-- Ranks quarterback passing, rushing, and PPR production by week and through the season.

select
    snapshot_date,
    player_id,
    player_display_name,
    position,
    headshot_url,
    season,
    week,
    season_type,
    game_id,
    team,
    opponent_team,
    played_this_week,
    season_to_date_games_played,
    {{ ranked_metric('fantasy_points_ppr') }},
    {{ ranked_metric('completions') }},
    {{ ranked_metric('attempts') }},
    {{ ranked_metric('passing_yards') }},
    {{ ranked_metric('passing_tds') }},
    {{ ranked_metric('passing_interceptions', direction='asc') }},
    {{ ranked_metric('sacks_suffered', direction='asc') }},
    {{ ranked_metric('sack_yards_lost', direction='asc') }},
    {{ ranked_metric('sack_fumbles', direction='asc') }},
    {{ ranked_metric('passing_air_yards') }},
    {{ ranked_metric('passing_yards_after_catch') }},
    {{ ranked_metric('passing_first_downs') }},
    {{ ranked_metric(
        'passing_epa',
        weekly_eligibility='played_this_week and attempts > 0',
        season_eligibility='season_to_date_attempts > 0'
    ) }},
    {{ ranked_metric(
        'passing_cpoe',
        weekly_eligibility='played_this_week and attempts > 0',
        season_eligibility='season_to_date_attempts > 0'
    ) }},
    {{ ranked_metric('passing_10') }},
    {{ ranked_metric('passing_16') }},
    {{ ranked_metric('passing_20') }},
    {{ ranked_metric('passing_40') }},
    {{ ranked_metric('carries') }},
    {{ ranked_metric('rushing_yards') }},
    {{ ranked_metric('rushing_tds') }},
    {{ ranked_metric('rushing_fumbles', direction='asc') }},
    {{ ranked_metric('rushing_first_downs') }},
    {{ ranked_metric(
        'rushing_epa',
        weekly_eligibility='played_this_week and carries > 0',
        season_eligibility='season_to_date_carries > 0'
    ) }},
    {{ ranked_metric('rushing_10') }},
    {{ ranked_metric('rushing_12') }},
    {{ ranked_metric('rushing_20') }},
    {{ ranked_metric('rushing_40') }}
from {{ ref('int_player_week__cumulative') }}
where position = 'QB'
