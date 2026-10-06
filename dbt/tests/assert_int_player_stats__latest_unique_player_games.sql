-- Ensures the latest player-stat view has one row per player and game.

select
    game_id,
    player_id,
    count(*) as row_count
from {{ ref('int_player_stats__latest') }}
group by game_id, player_id
having count(*) > 1
