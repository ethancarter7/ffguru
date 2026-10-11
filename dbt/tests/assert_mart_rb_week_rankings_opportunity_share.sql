-- Ensures running back opportunity shares are bounded, complete, and arithmetically correct.

with invalid_rows as (
    select
        'bounds_or_formula' as failure,
        season,
        season_type,
        week,
        team,
        player_id
    from {{ ref('mart_rb_week_rankings') }}
    where opportunity_share < 0
        or opportunity_share > 1
        or season_to_date_opportunity_share < 0
        or season_to_date_opportunity_share > 1
        or abs(
            season_to_date_opportunity_share
            - season_to_date_opportunities / nullif(season_to_date_team_rb_opportunities, 0)
        ) > 0.000001
),

invalid_team_weeks as (
    select
        'team_week_sum' as failure,
        season,
        season_type,
        week,
        team,
        cast(null as varchar) as player_id
    from {{ ref('mart_rb_week_rankings') }}
    where team_rb_opportunities > 0
    group by season, season_type, week, team
    having abs(sum(coalesce(opportunity_share, 0)) - 1) > 0.000001
)

select * from invalid_rows
union all
select * from invalid_team_weeks
