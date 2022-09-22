import collections
import json
from pprint import pprint

import bs4
import requests

import const


class Duty:
    def __init__(self, day_index, time_index, place_index):
        self.day_index = day_index
        self.time_index = time_index
        self.place_index = place_index


class DutyEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__


def get_duty_plan(url: str) -> dict[str, list[Duty]]:
    resp = requests.get(url)
    resp.encoding = 'utf-8'

    soup = bs4.BeautifulSoup(resp.text, 'html.parser')
    iframe = soup.find('iframe', id='result')

    return parse_duty_plan(iframe)


def parse_duty_plan(body: bs4.Tag) -> dict[str, list[Duty]]:
    js_code = body.get('srcdoc')
    start = js_code.find('id="rendered-js"')
    start = js_code.find('\n', start) + 1

    end = js_code.find('\n', js_code.find('let p = ', start))
    js_code = js_code[start:end]
    js_code = '\n'.join([line[4:].rstrip('; \n\r\t') for line in js_code.splitlines()])

    # primitive protection against evil eval code
    js_code = js_code.replace('_', '#').replace('.', '#').replace('lambda', '#')
    js_code = js_code.replace('(', '#').replace(')', '#').replace('{', '#').replace('}', '#')

    print(js_code, '\n\n')
    print('#' * 100)
    print('Code above is going to be executed in python context by exec function.')
    print('For safety measures review it in terms of malicious code.')
    decision = str(input('> Execute code? [y/N]: ')).lower().strip()

    if decision not in ('y', 'yes'):
        print('terminating... possibility of malicious code')
        exit(1)

    loc = {}
    exec(js_code, {"__builtins__": {}}, loc)  # loc['p']
    rows = loc['p']

    duty_map: dict[str, list[Duty]] = {}
    initials_to_name: dict[str, str] = {}

    for row in rows:
        if len(row) < 3:
            continue

        if row[-1][0] > 1 or len(row[-2]) != len(row[-3]) != 3:
            continue
        initials = row[-2][1]
        fullname = row[-3][1]
        initials_to_name[initials] = fullname

        if len(row[1]) != len(row[2]) != 3:
            continue

        if row[1][1] not in const.day_to_index or row[2][1] not in const.raw_place_to_index:
            continue

        time_index = -1
        day_index = const.day_to_index[row[1][1]]
        place = const.raw_place_to_index[row[2][1]]

        curr_index = 2
        while time_index < 10:
            curr_index += 1
            cell = row[curr_index]
            if len(cell) != 3:
                time_index += cell[0]
                continue

            if cell[1] not in duty_map:
                duty_map[cell[1]] = []

            for _ in range(cell[0]):
                time_index += 1
                duty_map[cell[1]].append(Duty(day_index, time_index, place))

    final_duty_map: dict[str, list[Duty]] = {}
    for k, v in duty_map.items():
        final_duty_map[initials_to_name[k]] = v

    return final_duty_map


def duty_map_to_json(duties: dict[str, list[Duty]]):
    reformat = {}
    for k, v in duties.items():
        for elem in v:
            if elem.day_index not in reformat:
                reformat[elem.day_index] = {}
            if elem.time_index not in reformat[elem.day_index]:
                reformat[elem.day_index][elem.time_index] = [None] * len(const.index_to_formatted_place)

            reformat[elem.day_index][elem.time_index][elem.place_index] = {
                'place': const.index_to_formatted_place[elem.place_index],
                'person': k
            }

    reformat = remove_empty_elements(reformat)
    with open('out/duties.json', 'w', encoding='utf-8') as f:
        json.dump(reformat, f, ensure_ascii=False, cls=DutyEncoder)


def remove_empty_elements(d):
    """recursively remove empty lists, empty dicts, or None elements from a dictionary"""

    def empty(x):
        return x is None or x == {} or x == []

    if not isinstance(d, (dict, list)):
        return d
    elif isinstance(d, list):
        return [v for v in (remove_empty_elements(v) for v in d) if not empty(v)]
    else:
        return {k: v for k, v in ((k, remove_empty_elements(v)) for k, v in d.items()) if not empty(v)}
