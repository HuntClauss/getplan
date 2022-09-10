import re
import bs4
import requests

from secret import TIMETABLE_URL, STAFF_URL, TEACHERS_DUTY_URL
from duty import get_duty_plan

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


class Teacher:
    def __init__(self):
        self.display_name = ''
        self.true_name = ''
        self.teaching_subjects = []
        self.housemaster_of = None
        self.lessons: list[Lesson] = []

    def is_vacancy(self):
        return 'wakat' in self.display_name.lower()


def process_timetable(url: str) -> list[Lesson]:
    resp = requests.get(url)
    resp.encoding = 'utf-8'

    soup = bs4.BeautifulSoup(resp.text, 'html.parser')

    multiple_timetables = soup.find_all('div', class_='plan_plan')
    lessons: list[Lesson] = []
    for tt in multiple_timetables:
        lessons += extract_info(tt)
    return lessons


def process_staff_names(url: str) -> dict[str, str]:
    resp = requests.get(url)
    resp.encoding = 'utf-8'

    soup = bs4.BeautifulSoup(resp.text, 'html.parser')

    return map_teacher_names(soup)


def map_teacher_names(table: bs4.Tag) -> dict[str, str]:
    result: dict[str, str] = {}
    cells = table.find_all('td')
    for i in range(0, len(cells), 2):
        text = cells[i].get_text(strip=True)
        text = text.replace('dr', '').replace('hab.', '')
        text = text.replace('inż.', '').replace('ks.', '').strip()
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


def teacher_base_timetable(lessons: list[Lesson], names: dict[str, str]) -> dict[str, Teacher]:
    teachers: dict[str, Teacher] = {}
    for lesson in lessons:
        name = lesson.subject_teacher.strip('. \t\n')
        if name in names:
            name = names[name]  # TODO fix char encoding of lesson.subject_teacher

        if name not in teachers:
            teachers[name] = Teacher()

        teachers[name].lessons.append(lesson)
        teachers[name].display_name = name
        teachers[name].true_name = name

        if lesson.subject_name == 'zajęcia z wychowawcą':
            teachers[name].housemaster_of = lesson.class_name
        elif lesson.subject_name not in teachers[name].teaching_subjects:
            teachers[name].teaching_subjects.append(lesson.subject_name)

    return teachers


def vacancy_educated_guesses(teachers: dict[str, Teacher], mapped_names: dict[str, str]):
    names = list(mapped_names.values())

    targets: list[Teacher] = []
    for t in teachers.values():
        if t.is_vacancy() and '.' not in t.display_name:
            targets.append(t)

    # Wakat-UC .
    # Wakat-AS_NIEM .
    # Wakat-DS_INF .
    # Wakat PEL_INF.
    # Wakat-J.ANG_INF .
    # Wakat-MKRA_EDB_WF .
    # formats:
    #   [J]an [K]owalski -> JK
    #   Jan [Kow]alski -> KOW
    for t in targets:
        mark = t.display_name[6:]
        if '_' in mark:
            end = mark.index('_')
            mark = mark[:end]

        matches: list[str] = []
        if len(mark) == 2:
            matches = find_initials_matches(mark, names)
        else:
            matches = find_last_name_matches(mark, names)

        if len(matches) > 1:
            for m in matches:
                if not any(subject in teachers[m].teaching_subjects for subject in t.teaching_subjects):
                    matches.remove(m)

        if len(matches) == 1:
            t.true_name = matches[0]


def find_initials_matches(initials: str, names: list[str]) -> list[str]:
    result: list[str] = []
    for name in names:
        parts = name.split(' ')  # parts[0] = last_name, parts[1] = first_name
        s, f = parts[0][0], parts[1][0]
        if f == initials[0] and s == initials[1]:
            result.append(name)

    return result


def find_last_name_matches(part: str, names: list[str]) -> list[str]:
    result: list[str] = []
    for name in names:
        last_name = name.split(' ')[0]
        if last_name.startswith(part):
            result.append(name)

    return result


def resolve_teachers_names(lessons: list[Lesson], names: dict[str, str]) -> list[Lesson]:
    for lesson in lessons:
        if lesson.subject_teacher in names:
            lesson.subject_teacher = names[lesson.subject_teacher]
    return lessons


def main():
    get_duty_plan(TEACHERS_DUTY_URL)
    names_map = process_staff_names(STAFF_URL)
    lessons = process_timetable(TIMETABLE_URL)
    resolve_teachers_names(lessons, names_map)
    teachers = teacher_base_timetable(lessons, names_map)
    vacancy_educated_guesses(teachers, names_map)


if __name__ == '__main__':
    main()
