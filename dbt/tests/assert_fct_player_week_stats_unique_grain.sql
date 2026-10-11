-- Ensures the gold fact contains one row per player and NFL week.

select
    season,
    season_type,
    week,
    player_id,
    count(*) as row_count
from {{ ref('fct_player_week_stats') }}
group by season, season_type, week, player_id
having count(*) > 1
