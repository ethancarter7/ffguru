-- Ranks running back rushing, receiving, usage, and PPR production by week and season.

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
    {{ ranked_metric('rushing_40') }},
    {{ ranked_metric('receptions') }},
    {{ ranked_metric('targets') }},
    {{ ranked_metric('receiving_yards') }},
    {{ ranked_metric('receiving_tds') }},
    {{ ranked_metric('receiving_fumbles', direction='asc') }},
    {{ ranked_metric('receiving_air_yards') }},
    {{ ranked_metric('receiving_yards_after_catch') }},
    {{ ranked_metric('receiving_first_downs') }},
    {{ ranked_metric(
        'receiving_epa',
        weekly_eligibility='played_this_week and targets > 0',
        season_eligibility='season_to_date_targets > 0'
    ) }},
    {{ ranked_metric('receiving_10') }},
    {{ ranked_metric('receiving_16') }},
    {{ ranked_metric('receiving_20') }},
    {{ ranked_metric('receiving_40') }},
    {{ ranked_metric(
        'target_share',
        season_metric='season_to_date_avg_target_share',
        weekly_eligibility='played_this_week and targets > 0',
        season_eligibility='season_to_date_targets > 0'
    ) }},
    {{ ranked_metric(
        'wopr',
        season_metric='season_to_date_avg_wopr',
        weekly_eligibility='played_this_week and targets > 0',
        season_eligibility='season_to_date_targets > 0'
    ) }},
    {{ ranked_metric('opportunities') }},
    team_rb_opportunities,
    season_to_date_team_rb_opportunities,
    {{ ranked_metric(
        'opportunity_share',
        weekly_eligibility='played_this_week and opportunities > 0',
        season_eligibility='season_to_date_opportunities > 0'
    ) }}
from {{ ref('int_player_week__cumulative') }}
where position = 'RB'
