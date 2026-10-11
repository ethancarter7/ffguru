-- Ensures weekly and cumulative PPR columns use dense position rankings.

with all_positions as (
    select * from {{ ref('mart_qb_week_rankings') }}
    union all by name select * from {{ ref('mart_rb_week_rankings') }}
    union all by name select * from {{ ref('mart_wr_week_rankings') }}
    union all by name select * from {{ ref('mart_te_week_rankings') }}
    union all by name select * from {{ ref('mart_k_week_rankings') }}
),

expected as (
    select
        *,
        dense_rank() over (
            partition by season, season_type, week, position
            order by case when played_this_week then fantasy_points_ppr end desc nulls last
        ) as expected_week_rank,
        dense_rank() over (
            partition by season, season_type, week, position
            order by season_to_date_fantasy_points_ppr desc nulls last
        ) as expected_season_rank
    from all_positions
)

select *
from expected
where (played_this_week and fantasy_points_ppr_week_rank != expected_week_rank)
    or season_to_date_fantasy_points_ppr_rank != expected_season_rank
