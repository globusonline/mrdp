"""Climate Data Online aggregation and graphing"""

from csv import reader as csv_reader
from datetime import date
from pygal import Box, Line

__all__ = [
    'render_graphs',
    'aggregate_monthly_data',
    'monthly_total_precip_line',
    'monthly_avg_min_max_temp_line',
    'monthly_max_temps_box',
]


# 12-member list of the names of the months, i.e. ["January", "February", ...]

MONTH_NAMES = [date(2016, month, 1).strftime('%B') for month in range(1, 13)]


def render_graphs(csv_data, append_titles=""):
    """
    Convenience function. Gets the aggregated `monthlies` data from
    `aggregate_monthly_data(csv_data)` and returns a dict of graph
    titles mapped to rendered SVGs from `monthly_total_precip_line()`
    and `monthly_avg_min_max_temp_line()` using the `monthlies` data.
    """

    monthlies = aggregate_monthly_data(csv_data)

    return {
        graph.config.title: graph.render()
        for graph in [
            monthly_total_precip_line(monthlies, append_titles),
            monthly_avg_min_max_temp_line(monthlies, append_titles),
            monthly_max_temps_box(monthlies, append_titles),
        ]
    }


def aggregate_monthly_data(csv_data):
    """
    Pass your `csv_data` as an iterable whose members are individual
    lines of data (e.g. using a generator returned by the `iter_lines()`
    method of a `requests` library `Response` object) from a Climate
    Data Online (CDO)-style CSV file. Your CSV file must include the
    date (`DATE`), precipitation (`PRCP`), minimum temperature (`TMIN`),
    and maximum temperature (`TMAX`). The first line of your data file
    must be a header line.

    Returns a 12-member list of structured monthly data, each of which
    is a dict containing

    - `days_of_data`,
    - `precipitation_total`,
    - `min_temperature_total`,
    - `max_temperature_total`,
    - `all_min_temperatures`, and
    - `all_max_temperatures`.
    """

    csv_data = csv_reader(csv_data)

    header_row = next(csv_data)
    date_index = header_row.index('DATE')
    prcp_index = header_row.index('PRCP')
    tmin_index = header_row.index('TMIN')
    tmax_index = header_row.index('TMAX')

    monthlies = [dict(days_of_data=0, precipitation_total=0,
                      min_temperature_total=0, max_temperature_total=0,
                      all_min_temperatures=[], all_max_temperatures=[])
                 for _ in range(12)]

    for data_row in csv_data:
        row_month = int(data_row[date_index][4:6])
        row_prcp = int(data_row[prcp_index])
        row_tmin = int(data_row[tmin_index])
        row_tmax = int(data_row[tmax_index])

        monthly = monthlies[row_month - 1]
        monthly['days_of_data'] += 1
        monthly['precipitation_total'] += row_prcp
        monthly['min_temperature_total'] += row_tmin
        monthly['max_temperature_total'] += row_tmax
        monthly['all_min_temperatures'].append(row_tmin)
        monthly['all_max_temperatures'].append(row_tmax)

    return monthlies


def monthly_total_precip_line(monthlies, append_title=""):
    """
    Given `monthlies` data as returned by `aggregate_monthly_data()`,
    returns a Pygal line graph of precipitation totals for each month.
    """

    graph = Line(title="Precipitation" + append_title,
                 x_labels=MONTH_NAMES, x_label_rotation=90)

    graph.add("Precip(mm)", [monthly['precipitation_total'] / 10.
                             for monthly in monthlies])

    return graph


def monthly_avg_min_max_temp_line(monthlies, append_title=""):
    """
    Given `monthlies` data as returned by `aggregate_monthly_data()`,
    returns a Pygal line graph of average minimum and average maximum
    temperatures for each month.
    """

    graph = Line(title="Average High-Low Temperature" + append_title,
                 x_labels=MONTH_NAMES, x_label_rotation=90)

    graph.add("Avg High(C)", [monthly['max_temperature_total'] / 10. /
                              monthly['days_of_data']
                              for monthly in monthlies])

    graph.add("Avg Low(C)", [monthly['min_temperature_total'] / 10. /
                             monthly['days_of_data']
                             for monthly in monthlies])

    return graph


def monthly_max_temps_box(monthlies, append_title=""):
    """
    Given `monthlies` data as returned by `aggregate_monthly_data()`,
    returns a Pygal box-and-whisker plot graph of the range of high
    temperatures for each month.
    """

    graph = Box(title="High Temperature Ranges" + append_title,
                show_legend=False, x_labels=MONTH_NAMES, x_label_rotation=90,
                y_title=u"\u00b0C")

    for i, month_name in enumerate(MONTH_NAMES):
        graph.add(month_name, monthlies[i]['all_max_temperatures'])

    return graph
