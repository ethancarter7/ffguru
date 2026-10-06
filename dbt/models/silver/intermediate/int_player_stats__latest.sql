-- Filters player statistics to the newest snapshot and standard fantasy positions.

select *
from {{ ref('stg_nflverse__player_stats') }}
where position in ('QB', 'RB', 'WR', 'TE', 'K')
qualify dense_rank() over (order by snapshot_date desc) = 1
