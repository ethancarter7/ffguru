-- Ensures the latest player-stat view never mixes ingestion snapshots.

select count(distinct snapshot_date) as snapshot_count
from {{ ref('int_player_stats__latest') }}
having count(distinct snapshot_date) != 1
