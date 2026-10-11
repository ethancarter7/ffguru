-- Ensures cumulative PPR totals do not change during a player's missing week.

with all_positions as (
    select * from {{ ref('mart_qb_week_rankings') }}
    union all by name select * from {{ ref('mart_rb_week_rankings') }}
    union all by name select * from {{ ref('mart_wr_week_rankings') }}
    union all by name select * from {{ ref('mart_te_week_rankings') }}
    union all by name select * from {{ ref('mart_k_week_rankings') }}
),

with_previous as (
    select
        *,
        lag(season_to_date_fantasy_points_ppr) over (
            partition by season, season_type, player_id
            order by week
        ) as previous_fantasy_points_ppr
    from all_positions
)

select *
from with_previous
where not played_this_week
    and previous_fantasy_points_ppr is not null
    and season_to_date_fantasy_points_ppr != previous_fantasy_points_ppr
