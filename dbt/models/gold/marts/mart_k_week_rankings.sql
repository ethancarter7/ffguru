-- Ranks kicker field-goal and PPR production by week and through the season.

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
    {{ ranked_metric('fg_made') }},
    {{ ranked_metric('fg_att') }},
    {{ ranked_metric('fg_missed', direction='asc') }},
    {{ ranked_metric('fg_blocked', direction='asc') }},
    {{ ranked_metric(
        'fg_long',
        weekly_eligibility='played_this_week and fg_made > 0',
        season_eligibility='season_to_date_fg_made > 0'
    ) }},
    {{ ranked_metric(
        'fg_pct',
        weekly_eligibility='played_this_week and fg_att > 0',
        season_eligibility='season_to_date_fg_att > 0'
    ) }}
from {{ ref('int_player_week__cumulative') }}
where position = 'K'
