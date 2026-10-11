-- Adds missing player-week rows so cumulative rankings persist through byes and inactivity.

with weeks as (
    select distinct
        snapshot_date,
        season,
        season_type,
        week
    from {{ ref('fct_player_week_stats') }}
),

players as (
    select
        season,
        season_type,
        player_id,
        max(player_display_name) as player_display_name,
        position,
        max(headshot_url) as headshot_url,
        min(week) as first_week
    from {{ ref('fct_player_week_stats') }}
    group by season, season_type, player_id, position
),

player_weeks as (
    select
        weeks.snapshot_date,
        players.player_id,
        players.player_display_name,
        players.position,
        players.headshot_url,
        weeks.season,
        weeks.week,
        weeks.season_type
    from players
    inner join weeks
        on players.season = weeks.season
        and players.season_type = weeks.season_type
        and weeks.week >= players.first_week
),

joined as (
    select
        player_weeks.snapshot_date,
        player_weeks.player_id,
        player_weeks.player_display_name,
        player_weeks.position,
        player_weeks.headshot_url,
        player_weeks.season,
        player_weeks.week,
        player_weeks.season_type,
        stats.game_id,
        stats.team,
        stats.opponent_team,
        stats.player_id is not null as played_this_week,
        coalesce(stats.completions, 0) as completions,
        coalesce(stats.attempts, 0) as attempts,
        coalesce(stats.passing_yards, 0) as passing_yards,
        coalesce(stats.passing_tds, 0) as passing_tds,
        coalesce(stats.passing_interceptions, 0) as passing_interceptions,
        coalesce(stats.sacks_suffered, 0) as sacks_suffered,
        coalesce(stats.sack_yards_lost, 0) as sack_yards_lost,
        coalesce(stats.sack_fumbles, 0) as sack_fumbles,
        coalesce(stats.passing_air_yards, 0) as passing_air_yards,
        coalesce(stats.passing_yards_after_catch, 0) as passing_yards_after_catch,
        coalesce(stats.passing_first_downs, 0) as passing_first_downs,
        stats.passing_epa,
        stats.passing_cpoe,
        coalesce(stats.passing_10, 0) as passing_10,
        coalesce(stats.passing_16, 0) as passing_16,
        coalesce(stats.passing_20, 0) as passing_20,
        coalesce(stats.passing_40, 0) as passing_40,
        coalesce(stats.carries, 0) as carries,
        coalesce(stats.rushing_yards, 0) as rushing_yards,
        coalesce(stats.rushing_tds, 0) as rushing_tds,
        coalesce(stats.rushing_fumbles, 0) as rushing_fumbles,
        coalesce(stats.rushing_first_downs, 0) as rushing_first_downs,
        stats.rushing_epa,
        coalesce(stats.rushing_10, 0) as rushing_10,
        coalesce(stats.rushing_12, 0) as rushing_12,
        coalesce(stats.rushing_20, 0) as rushing_20,
        coalesce(stats.rushing_40, 0) as rushing_40,
        coalesce(stats.receptions, 0) as receptions,
        coalesce(stats.targets, 0) as targets,
        coalesce(stats.receiving_yards, 0) as receiving_yards,
        coalesce(stats.receiving_tds, 0) as receiving_tds,
        coalesce(stats.receiving_fumbles, 0) as receiving_fumbles,
        coalesce(stats.receiving_air_yards, 0) as receiving_air_yards,
        coalesce(stats.receiving_yards_after_catch, 0) as receiving_yards_after_catch,
        coalesce(stats.receiving_first_downs, 0) as receiving_first_downs,
        stats.receiving_epa,
        coalesce(stats.receiving_10, 0) as receiving_10,
        coalesce(stats.receiving_16, 0) as receiving_16,
        coalesce(stats.receiving_20, 0) as receiving_20,
        coalesce(stats.receiving_40, 0) as receiving_40,
        coalesce(stats.fg_made, 0) as fg_made,
        coalesce(stats.fg_att, 0) as fg_att,
        coalesce(stats.fg_missed, 0) as fg_missed,
        coalesce(stats.fg_blocked, 0) as fg_blocked,
        stats.fg_long,
        stats.fg_pct,
        stats.target_share,
        stats.wopr,
        coalesce(stats.fantasy_points_ppr, 0) as fantasy_points_ppr
    from player_weeks
    left join {{ ref('fct_player_week_stats') }} as stats
        on player_weeks.season = stats.season
        and player_weeks.season_type = stats.season_type
        and player_weeks.week = stats.week
        and player_weeks.player_id = stats.player_id
),

carried_team as (
    select
        * exclude (team),
        last_value(team ignore nulls) over (
            partition by season, season_type, player_id
            order by week
            rows between unbounded preceding and current row
        ) as team
    from joined
),

team_rb_opportunities as (
    select
        season,
        season_type,
        week,
        team,
        sum(carries + targets) as team_rb_opportunities
    from {{ ref('fct_player_week_stats') }}
    where position = 'RB'
    group by season, season_type, week, team
)

select
    carried_team.*,
    carried_team.carries + carried_team.targets as opportunities,
    coalesce(team_rb_opportunities.team_rb_opportunities, 0) as team_rb_opportunities,
    case
        when carried_team.position = 'RB'
            and coalesce(team_rb_opportunities.team_rb_opportunities, 0) > 0
            then (carried_team.carries + carried_team.targets)
                / team_rb_opportunities.team_rb_opportunities
    end as opportunity_share
from carried_team
left join team_rb_opportunities
    on carried_team.season = team_rb_opportunities.season
    and carried_team.season_type = team_rb_opportunities.season_type
    and carried_team.week = team_rb_opportunities.week
    and carried_team.team = team_rb_opportunities.team
