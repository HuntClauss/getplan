import bs4
import requests
from bs4 import BeautifulSoup
from secret import TEACHERS_DUTY_URL


class Duty:
    def __init__(self, day_index, time_index, place):
        self.day_index = day_index
        self.time_index = time_index
        self.place = place


def get_duty_plan(url: str) -> dict[str, list[Duty]]:
    resp = requests.get(url)
    resp.encoding = 'utf-8'

    soup = BeautifulSoup(resp.text, 'html.parser')
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

    if decision != 'y' and decision != 'yes':
        print('terminating... possibility of malicious code')
        exit(1)

    loc = {}
    exec(js_code, {"__builtins__": {}}, loc)  # loc['p']
    rows = loc['p']

    mapped_days = {'Poniedziałek': 0, 'Wtorek': 1, 'Środa': 2, 'Czwartek': 3, 'Piątek': 4}
    mapped_place = {
        'bufet#toaleta': 'bufet - łazienka',
        'bufet#jadalnia': 'bufet - jadalnia',
        'korytarz#02#021': 'korytarz 02 - 021',
        'korytarz#06#09#013': 'korytarz 06 - 013',
        'parter#wejście': 'główne wejście',
        'parter#2': 'hol przy wejściu',
        'piętro1#toaleta': 'piętro 1 - łazienka',
        'piętro1#2osoba': 'piętro 1 - narożnik',
        'piętro2#toaleta': 'piętro 2 - łazienka',
        'piętro2#2osoba': 'piętro 2 - narożnik',
        'szatnia#tech': 'szatnia tech',  # gdzie to jest?
    }

    duty_map: dict[str, list[Duty]] = {}
    initials_to_name: dict[str, str] = {}

    for row in rows:
        if len(row) < 3:
            continue

        if len(row[-2]) != len(row[-3]) != 3:
            continue
        initials = row[-2][1]
        fullname = row[-3][1]
        initials_to_name[initials] = fullname

        if len(row[1]) != len(row[2]) != 3:
            continue

        if row[1][1] not in mapped_days or row[2][1] not in mapped_place:
            continue

        time_index = -1
        day_index = mapped_days[row[1][1]]
        place = mapped_place[row[2][1]]

        curr_index = 2
        while time_index < 10:
            curr_index += 1
            cell = row[curr_index]
            if len(cell) != 3:
                time_index += cell[0]
                continue

            if cell[1] not in duty_map:
                duty_map[cell[1]] = []

            for i in range(cell[0]):
                time_index += 1
                duty_map[cell[1]].append(Duty(day_index, time_index, place))

    final_duty_map: dict[str, list[Duty]] = {}
    for k, v in duty_map.items():
        final_duty_map[initials_to_name[k]] = v

    return final_duty_map







