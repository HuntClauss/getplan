day_to_index = {'Poniedziałek': 0, 'Wtorek': 1, 'Środa': 2, 'Czwartek': 3, 'Piątek': 4}
raw_place_to_index = {
    'bufet#toaleta': 0,
    'bufet#jadalnia': 1,
    'korytarz#02#021': 2,
    'korytarz#06#09#013': 3,
    'parter#wejście': 4,
    'parter#2': 5,
    'piętro1#toaleta': 6,
    'piętro1#2osoba': 7,
    'piętro2#toaleta': 8,
    'piętro2#2osoba': 9,
    'szatnia#tech': 10,
}
index_to_formatted_place = [
    'bufet - łazienka',
    'bufet - jadalnia',
    'korytarz 02 - 021',
    'korytarz 06 - 013',
    'główne wejście',
    'hol przy wejściu',
    'piętro 1 - łazienka',
    'piętro 1 - narożnik',
    'piętro 2 - łazienka',
    'piętro 2 - narożnik',
    'szatnia przy muzeum',
]
