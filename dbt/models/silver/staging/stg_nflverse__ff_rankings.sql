-- Selects the useful ranking fields from every immutable draft-ranking snapshot.

select
    snapshot_date,
    id as player_id,
    player,
    pos,
    team,
    bye,
    page_type,
    ecr,
    best,
    worst
from {{ source('nflverse', 'ff_rankings') }}
