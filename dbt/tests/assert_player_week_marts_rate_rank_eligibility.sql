-- Ensures efficiency rankings require the corresponding player activity.

select 'qb_passing_cpoe' as failure, *
from {{ ref('mart_qb_week_rankings') }}
where attempts = 0 and passing_cpoe_week_rank is not null

union all by name

select 'rb_target_share' as failure, *
from {{ ref('mart_rb_week_rankings') }}
where targets = 0 and target_share_week_rank is not null

union all by name

select 'wr_target_share' as failure, *
from {{ ref('mart_wr_week_rankings') }}
where targets = 0 and target_share_week_rank is not null

union all by name

select 'te_target_share' as failure, *
from {{ ref('mart_te_week_rankings') }}
where targets = 0 and target_share_week_rank is not null

union all by name

select 'k_fg_pct' as failure, *
from {{ ref('mart_k_week_rankings') }}
where fg_att = 0 and fg_pct_week_rank is not null
