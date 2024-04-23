import json
import math
import os
import sys
from argparse import ArgumentParser
from collections import defaultdict
from functools import partial
from statistics import mean
from typing import Dict, List, Tuple, Set

from bokeh.models import ColumnDataSource
from bokeh.palettes import Category20
from bokeh.io import output_file, save
from bokeh.plotting import figure
from bokeh.transform import dodge


def get_argparser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="plot_perf_results",
        description="Simple graph plotter for performance results.",
    )
    parser.add_argument(
        'json_files',
        nargs='+',
        type=str,
        help="Paths to json files.",
    )
    parser.add_argument(
        '--html_out',
        type=str,
        default="perf-report.html",
    )
    return parser


def slurp_json(
    json_files: List[str],
) -> Tuple[str, Dict[str, List[Dict]], List[str]]:
    '''
    Parse JSON file of performance data.
    '''
    merged_dict = defaultdict(partial(defaultdict, list))
    tags = []
    for json_file in json_files:
        with open(json_file, "rt") as json_fh:
            perf_results : Dict[str, Dict[str, List[Dict]]] = json.loads(json_fh.read())
        for test_name, tags_and_results in perf_results.items():
            for tag, results in tags_and_results.items():
                # Maintain order of tags as added
                if tag not in tags:
                    tags.append(tag)
                merged_dict[test_name][tag] += results
    return merged_dict, tags


def plot_graphs(
    perf_results: Dict[str, Dict[str, List[Dict]]],
    tags: Set[str],
    html_out: str,
):
    '''
    Plot graphs of performance results.
    '''
    test_names = list(perf_results.keys())
    hz_averages_by_test_tag = defaultdict(dict)
    x_max = -1
    test_name_and_hz_average: List[Tuple] = []
    # Process raw test data
    for test_name, tagged_tests in perf_results.items():
        hz_sum = 0
        test_tag_count = 0
        for tag, test_list in tagged_tests.items():
            hz_average = mean([x['hz'] for x in test_list])
            hz_averages_by_test_tag[test_name][tag] = hz_average
            hz_sum += hz_average
            test_tag_count += 1
            if hz_average > x_max:
                x_max = hz_average
        # If missing data for this tag, use 0
        for tag in tags:
            if tag not in tagged_tests:
                hz_averages_by_test_tag[test_name][tag] = 0
        test_hz_average = hz_sum / test_tag_count
        test_name_and_hz_average.append((test_name, test_hz_average))
    # Sort according to averages
    test_name_and_hz_average.sort(key=lambda x: x[1])
    data = defaultdict(list)
    # Create data in a format bokeh likes, in the right order
    for test_name, _hz_average in test_name_and_hz_average:
        data['test_names'].append(test_name)
        for tag in tags:
            data[tag].append(hz_averages_by_test_tag[test_name][tag])
    source = ColumnDataSource(data=data)
    bar_height_px = 100
    total_height = bar_height_px * (len(test_names) + 1)
    plot = figure(
        x_range=(0, x_max*1.2),
        y_range=[name for name, _hz_average in test_name_and_hz_average],
        title="constrainedrandom test performance/Hz",
        height=total_height,
        width=1400,
    )
    plot.below[0].formatter.use_scientific = False
    num_colors = max(3, len(tags))
    assert num_colors < 20, "Too many tags..."
    colors = Category20[num_colors]
    bar_height = 1 / (len(tags) + 2)
    bar_padding = 1 * bar_height / len(tags)
    dodge_incr = bar_height + bar_padding
    for index, tag in enumerate(tags):
        plot.hbar(
            y=dodge('test_names', 0.4 - dodge_incr*index, range=plot.y_range),
            right=tag,
            height=bar_height,
            source=source,
            color=colors[index],
            legend_label=tag,
        )
    plot.y_range.group_padding = 0.1
    plot.ygrid.grid_line_color = None
    # Write out
    html_out = os.path.abspath(html_out)
    output_file(html_out, title="constrainedrandom performance plot")
    print(f"Writing performance graphs to '{html_out}'")
    save(plot)


def main() -> int:
    parser = get_argparser()
    args = parser.parse_args()
    perf_results, tags = slurp_json(args.json_files)
    plot_graphs(perf_results, tags, args.html_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
