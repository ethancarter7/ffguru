{# Emits weekly and season-to-date values with dense position ranks. #}

{% macro ranked_metric(
    metric,
    season_metric=none,
    direction='desc',
    weekly_eligibility='played_this_week',
    season_eligibility='season_to_date_games_played > 0'
) -%}
    {%- set cumulative_metric = season_metric or 'season_to_date_' ~ metric -%}
    {{ metric }},
    case when {{ weekly_eligibility }} then
        dense_rank() over (
            partition by season, season_type, week, position
            order by
                case when {{ weekly_eligibility }} then {{ metric }} end {{ direction }} nulls last
        )
    end as {{ metric }}_week_rank,
    {{ cumulative_metric }},
    case when {{ season_eligibility }} then
        dense_rank() over (
            partition by season, season_type, week, position
            order by
                case when {{ season_eligibility }} then {{ cumulative_metric }} end {{ direction }} nulls last
        )
    end as {{ cumulative_metric }}_rank
{%- endmacro %}
