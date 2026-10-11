-- Ensures PPR ranks are positive for games, blank on byes, and cumulative for every row.

with all_positions as (
    select * from {{ ref('mart_qb_week_rankings') }}
    union all by name select * from {{ ref('mart_rb_week_rankings') }}
    union all by name select * from {{ ref('mart_wr_week_rankings') }}
    union all by name select * from {{ ref('mart_te_week_rankings') }}
    union all by name select * from {{ ref('mart_k_week_rankings') }}
)

select *
from all_positions
where (played_this_week and coalesce(fantasy_points_ppr_week_rank, 0) < 1)
    or (not played_this_week and fantasy_points_ppr_week_rank is not null)
    or coalesce(season_to_date_fantasy_points_ppr_rank, 0) < 1
