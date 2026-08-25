"""Страна в подсказке места — на языке приложения.

Владелец, 25.08.2026: «на русском место рождения по-русски, и на любом
другом языке — на нём». До этого профиль хранил «Moscow, Russia» на всех
семи языках, и русский экран настроек показывал английскую страну.
"""

from alma import geo


def test_the_country_speaks_the_readers_language():
    assert geo.localized_country("RU", "Russia", "ru") == "Россия"
    assert geo.localized_country("DE", "Germany", "de") == "Deutschland"
    assert geo.localized_country("BR", "Brazil", "pt-BR") == "Brasil"
    assert geo.localized_country("FR", "France", "it") == "Francia"


def test_us_in_russian_is_the_living_abbreviation():
    # CLDR пишет «Соединенные Штаты»; живой экран пишет «США».
    assert geo.localized_country("US", "United States", "ru") == "США"


def test_english_and_the_unknown_fall_back_to_the_index_name():
    assert geo.localized_country("RU", "Russia", "en") == "Russia"
    assert geo.localized_country("RU", "Russia", "tlh") == "Russia"
    assert geo.localized_country("XX", "Atlantis", "ru") == "Atlantis"
