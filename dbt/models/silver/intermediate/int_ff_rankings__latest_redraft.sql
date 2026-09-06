-- Filters the cleaned rankings to the newest overall redraft snapshot.

with redraft_overall as (
    select *
    from {{ ref('stg_nflverse__ff_rankings') }}
    where page_type = 'redraft-overall'
),

latest_snapshot as (
    select max(snapshot_date) as snapshot_date
    from redraft_overall
)

select
    snapshot_date,
    player_id,
    player,
    pos,
    team,
    bye,
    ecr,
    best,
    worst
from redraft_overall
where snapshot_date = (select snapshot_date from latest_snapshot)
