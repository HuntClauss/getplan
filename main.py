import bs4
import requests
from secret import TIMETABLE_URL, STAFF_URL
import re
from bs4 import BeautifulSoup

POLISH_UPPERCASE = 'ĄĆĘŁŃÓŚÓŻŹ'
POLISH_LOWERCASE = 'ąćęłńóśóżź'
POLISH_MIXCASE = POLISH_LOWERCASE + POLISH_UPPERCASE


class Lesson:
    def __init__(self):
        self.class_name = ''
        self.day_index = 0
        self.time_index = 0
        self.subject_name = ''
        self.subject_teacher = ''
        self.subject_classroom = ''
        self.subject_group = ''


def process_timetable(url: str) -> list[Lesson]:
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')

    multiple_timetables = soup.find_all('div', class_='plan_plan')
    lessons: list[Lesson] = []
    for tt in multiple_timetables:
        lessons += extract_info(tt)
    return lessons


def process_staff_names(url: str) -> dict[str, str]:
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')

    return map_teacher_names(soup)


def map_teacher_names(table: bs4.Tag) -> dict[str, str]:
    result: dict[str, str] = {}
    cells = table.find_all('td')
    for i in range(0, len(cells), 2):
        text = cells[i].get_text(strip=True)
        text = text.replace('dr', '').replace('hab.', '').replace('inż.', '').replace('ks.', '').strip()
        end = text.index(' ') + 2
        result[f'{text[:end]}.'] = text
    return result


def extract_info(timetable: bs4.Tag) -> list[Lesson]:
    class_name = timetable.find('h1').get_text()[6:-14]
    lessons: list[Lesson] = []

    rows = timetable.find_all('tr')[1:]  # skip first row, because it is header
    for time_index, row in enumerate(rows):
        # skip first two, because first one is sequence number and second is lesson interval
        cols = row.find_all('td')[2:]
        for day_index, col in enumerate(cols):
            text = col.get_text('\n', strip=True)
            if text == '':
                continue

            parts = text.split('\n')
            for i in range(0, len(parts), 2):
                lesson = Lesson()
                lesson.subject_name = parts[i]
                group, teacher, classroom = lesson_details(parts[i + 1])

                lesson.subject_group = group
                lesson.subject_teacher = teacher
                lesson.subject_classroom = classroom
                lesson.day_index = day_index
                lesson.time_index = time_index
                lesson.class_name = class_name
                lessons.append(lesson)

    return lessons


def lesson_details(s: str) -> (str, str, str):
    # 1 TT (22)                                                  | only class name
    # 1 TT a1 (15)                                               | without teacher's name
    # 1 TT - Wakat-EK . (208 historyczna)                        | without group name
    # 3 ET/TT g1 - Adamek A. (102a informatyczna)                | with group name and teacher's name
    # 4 PTT - Konieczny M. (sala gimnastyczna_1)                 | '_' in classroom name
    # 4 4PI2T h2 4PTT h2 - Wierzbińska K. (04 językowa)          | multiple class names and groups
    # 4 PAT a1 - Wakat-J.ANG_INF . (022 multimedialna)           | '.' inside teacher's name

    details_group_name = re.search(rf'[A-Z][A-Za-z0-9{POLISH_LOWERCASE}/]+ ([a-z0-9]+)', s)
    details_classroom = re.search(r'\((.*)\)', s)
    details_teachers_name = re.search(r'- (.*) \(', s)

    group, teacher, classroom = 'all', 'unknown', 'unknown1'
    if details_group_name is not None:
        group = details_group_name.group(1)
    if details_classroom is not None:
        classroom = details_classroom.group(1)
    if details_teachers_name is not None:
        teacher = details_teachers_name.group(1)

    return group, teacher, classroom


def main():
    names = process_staff_names(STAFF_URL)
    lessons = process_timetable(TIMETABLE_URL)


if __name__ == '__main__':
    main()
