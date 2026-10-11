-- Calculates season-to-date player metrics through every available week.

with cumulative as (
    select
        *,
        sum(cast(played_this_week as integer)) over player_window
            as season_to_date_games_played,
        sum(fantasy_points_ppr) over player_window as season_to_date_fantasy_points_ppr,
        sum(completions) over player_window as season_to_date_completions,
        sum(attempts) over player_window as season_to_date_attempts,
        sum(passing_yards) over player_window as season_to_date_passing_yards,
        sum(passing_tds) over player_window as season_to_date_passing_tds,
        sum(passing_interceptions) over player_window as season_to_date_passing_interceptions,
        sum(sacks_suffered) over player_window as season_to_date_sacks_suffered,
        sum(sack_yards_lost) over player_window as season_to_date_sack_yards_lost,
        sum(sack_fumbles) over player_window as season_to_date_sack_fumbles,
        sum(passing_air_yards) over player_window as season_to_date_passing_air_yards,
        sum(passing_yards_after_catch) over player_window
            as season_to_date_passing_yards_after_catch,
        sum(passing_first_downs) over player_window as season_to_date_passing_first_downs,
        sum(passing_epa) over player_window as season_to_date_passing_epa,
        sum(passing_cpoe * attempts) over player_window
            / nullif(sum(attempts) over player_window, 0) as season_to_date_passing_cpoe,
        sum(passing_10) over player_window as season_to_date_passing_10,
        sum(passing_16) over player_window as season_to_date_passing_16,
        sum(passing_20) over player_window as season_to_date_passing_20,
        sum(passing_40) over player_window as season_to_date_passing_40,
        sum(carries) over player_window as season_to_date_carries,
        sum(rushing_yards) over player_window as season_to_date_rushing_yards,
        sum(rushing_tds) over player_window as season_to_date_rushing_tds,
        sum(rushing_fumbles) over player_window as season_to_date_rushing_fumbles,
        sum(rushing_first_downs) over player_window as season_to_date_rushing_first_downs,
        sum(rushing_epa) over player_window as season_to_date_rushing_epa,
        sum(rushing_10) over player_window as season_to_date_rushing_10,
        sum(rushing_12) over player_window as season_to_date_rushing_12,
        sum(rushing_20) over player_window as season_to_date_rushing_20,
        sum(rushing_40) over player_window as season_to_date_rushing_40,
        sum(receptions) over player_window as season_to_date_receptions,
        sum(targets) over player_window as season_to_date_targets,
        sum(receiving_yards) over player_window as season_to_date_receiving_yards,
        sum(receiving_tds) over player_window as season_to_date_receiving_tds,
        sum(receiving_fumbles) over player_window as season_to_date_receiving_fumbles,
        sum(receiving_air_yards) over player_window as season_to_date_receiving_air_yards,
        sum(receiving_yards_after_catch) over player_window
            as season_to_date_receiving_yards_after_catch,
        sum(receiving_first_downs) over player_window as season_to_date_receiving_first_downs,
        sum(receiving_epa) over player_window as season_to_date_receiving_epa,
        sum(receiving_10) over player_window as season_to_date_receiving_10,
        sum(receiving_16) over player_window as season_to_date_receiving_16,
        sum(receiving_20) over player_window as season_to_date_receiving_20,
        sum(receiving_40) over player_window as season_to_date_receiving_40,
        sum(fg_made) over player_window as season_to_date_fg_made,
        sum(fg_att) over player_window as season_to_date_fg_att,
        sum(fg_missed) over player_window as season_to_date_fg_missed,
        sum(fg_blocked) over player_window as season_to_date_fg_blocked,
        max(fg_long) over player_window as season_to_date_fg_long,
        sum(fg_made) over player_window
            / nullif(sum(fg_att) over player_window, 0) as season_to_date_fg_pct,
        avg(case when played_this_week then target_share end) over player_window
            as season_to_date_avg_target_share,
        avg(case when played_this_week then wopr end) over player_window
            as season_to_date_avg_wopr,
        sum(opportunities) over player_window as season_to_date_opportunities,
        sum(team_rb_opportunities) over player_window
            as season_to_date_team_rb_opportunities
    from {{ ref('int_player_week__spine') }}
    window player_window as (
        partition by season, season_type, player_id
        order by week
        rows between unbounded preceding and current row
    )
)

select
    *,
    case
        when position = 'RB' and season_to_date_team_rb_opportunities > 0
            then season_to_date_opportunities / season_to_date_team_rb_opportunities
    end as season_to_date_opportunity_share
from cumulative
