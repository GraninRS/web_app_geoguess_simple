import sys
import os
import requests
import time
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from main import app, db, City

continents = {
    "Россия": "Европа", "Франция": "Европа", "Германия": "Европа", "Италия": "Европа",
    "Испания": "Европа", "Великобритания": "Европа", "Нидерланды": "Европа",
    "Бельгия": "Европа", "Швейцария": "Европа", "Австрия": "Европа",
    "Польша": "Европа", "Чехия": "Европа", "Словакия": "Европа", "Венгрия": "Европа",
    "Румыния": "Европа", "Болгария": "Европа", "Греция": "Европа", "Португалия": "Европа",
    "Швеция": "Европа", "Норвегия": "Европа", "Дания": "Европа", "Финляндия": "Европа",
    "Ирландия": "Европа", "Хорватия": "Европа", "Сербия": "Европа", "Украина": "Европа",
    "США": "Северная Америка", "Канада": "Северная Америка", "Мексика": "Северная Америка",
    "Бразилия": "Южная Америка", "Аргентина": "Южная Америка",
    "Китай": "Азия", "Япония": "Азия", "Индия": "Азия", "Южная Корея": "Азия",
    "Таиланд": "Азия", "Вьетнам": "Азия", "Индонезия": "Азия", "Малайзия": "Азия",
    "Филиппины": "Азия", "Турция": "Азия", "ОАЭ": "Азия", "Сингапур": "Азия",
    "Австралия": "Австралия", "Новая Зеландия": "Австралия",
    "Египет": "Африка", "ЮАР": "Африка", "Нигерия": "Африка", "Кения": "Африка",
    "Марокко": "Африка",
}


def geocode(name, api_key):
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {"apikey": api_key, "geocode": name, "format": "json", "lang": "ru_RU", "results": 1}
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        members = data["response"]["GeoObjectCollection"]["featureMember"]
        if not members:
            return None, None, None, None
        geo = members[0]["GeoObject"]
        lon, lat = map(float, geo["Point"]["pos"].split())
        country = None
        for comp in geo.get("metaDataProperty", {}).get("GeocoderMetaData", {}).get("Address", {}).get("Components",
                                                                                                       []):
            if comp["kind"] == "country":
                country = comp["name"]
                break
        return lat, lon, country, name
    except:
        return None, None, None, None


with app.app_context():
    db.create_all()
    with open("cities_list.txt", "r", encoding="utf-8") as f:
        names = [line.strip() for line in f if line.strip()]

    print(f"Городов в файле: {len(names)}")
    api_key = app.config['YANDEX_GEOCODE_KEY']
    added = 0

    for i, name in enumerate(names, 1):
        if City.query.filter_by(name=name).first():
            continue

        lat, lon, country, _ = geocode(name, api_key)
        if not lat or not country:
            print(f"[{i}] {name} - не найден")
            continue

        continent = continents.get(country, "Другое")
        city = City(name=name, country=country, continent=continent, lat=lat, lon=lon)
        db.session.add(city)
        added += 1

        print(f"[{i}] {name} -> {country}, {continent}")

        if added % 20 == 0:
            db.session.commit()
        time.sleep(0.3)

    db.session.commit()
    print(f"\nЗагружено: {added}. Всего в базе: {City.query.count()}")
