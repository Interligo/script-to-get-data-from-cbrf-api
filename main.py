import os
from datetime import date
from datetime import timedelta

import xmltodict
import requests
from requests.exceptions import InvalidURL
from requests.exceptions import MissingSchema


class DataParser:
    """Парсер для извелечения данных из API Центробанка."""
    def __init__(self) -> None:
        self.session = requests.Session()
        self.headers = {
            'Accept': '*/*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/88.0.4324.190 Safari/537.36'
        }

    def get_data_from_api(self, url_to_parse: str) -> dict:
        """Функция получает на вход полную ссылку на XML-страницу и возвращает словарь с данными за этот день."""
        try:
            response = self.session.get(url_to_parse, headers=self.headers)
            if response.status_code == 200:
                dict_data = xmltodict.parse(response.content)
                return dict_data
            else:
                raise SystemExit(f'{url_to_parse} не отвечает.')
        except (InvalidURL, MissingSchema):
            raise SystemExit(f'Не удалось подключиться к {url_to_parse}.')


class RubleConversionScrapper:
    """
    Класс для анализа данных по переводу различных валют в рубли за последние Х дней
    Получает на вход количество дней для аназиза. По умолчанию, получает данные за 90 дней.
    Точка входа == analyze_data().
    """
    def __init__(self, days_to_parse: int = 90) -> None:
        self.parser = DataParser()
        self.base_url = 'http://www.cbr.ru/scripts/XML_daily_eng.asp?date_req='  # Протестировать
        self.current_date = date.today()
        self.days_to_parse = days_to_parse
        self.dates_to_parse_list = []
        self.max_value_currency = {
            'value': -1.0,
            'name': None,
            'date': None,
        }
        self.min_value_currency = {
            'value': 99.0 ** 99,
            'name': None,
            'date': None,
        }
        self.avg_conversion_into_rubles = {}

    def __str__(self) -> str:
        return f'Данные по переводу различных валют в рубли за {self.days_to_parse} дней.'

    def __repr__(self) -> str:
        return f'Данные по переводу различных валют в рубли за {self.days_to_parse} дней.'

    def get_dates_to_make_parse_list(self) -> None:
        """Функция записывает в список даты для парсинга."""
        for day in range(self.days_to_parse):
            self.dates_to_parse_list.append(str(self.current_date - timedelta(days=day)))

    def normalize_date_to_parse(self, date_to_normalize: date) -> str:
        """Функция переводит дату в необходимый для парсинга формат (из гггг-мм-дд в дд/мм/гггг)."""
        str_date = str(date_to_normalize)
        split_date = str_date.split('-')
        normalize_date = split_date[::-1]
        return '/'.join(normalize_date)

    def change_value_to_equal_nominal(self, value: float, nominal: int) -> float:
        """Функция приводит ценность валюты к единому номиналу."""
        return value/nominal

    def calculate_avg_each_currency(self) -> None:
        """Функция переводит общее количество обмена каждой валюты к среднему количеству."""
        for key, value in self.avg_conversion_into_rubles.items():
            self.avg_conversion_into_rubles[key] = value / self.days_to_parse

    def analyze_one_day_data(self, data: dict) -> None:
        """Функция считает значение максимальной валюты, минимальной валюты и среднее значение перевода за день."""
        for element in data['ValCurs']['Valute']:
            currency_name = element['Name']
            currency_nominal = int(element['Nominal'])
            current_currency_value = float(element['Value'].replace(',', '.'))
            current_currency_value = self.change_value_to_equal_nominal(current_currency_value, currency_nominal)

            if current_currency_value > self.max_value_currency['value']:
                self.max_value_currency['value'] = current_currency_value
                self.max_value_currency['name'] = currency_name
                self.max_value_currency['date'] = data['ValCurs']['@Date']

            if current_currency_value < self.min_value_currency['value']:
                self.min_value_currency['value'] = current_currency_value
                self.min_value_currency['name'] = currency_name
                self.min_value_currency['date'] = data['ValCurs']['@Date']

            if currency_name in self.avg_conversion_into_rubles:
                self.avg_conversion_into_rubles[currency_name] += current_currency_value
            else:
                self.avg_conversion_into_rubles[currency_name] = current_currency_value

    def analyze_data(self) -> None:
        """Функция-агрегатор, которая запускает цикл работы класса. Результат анализа выводит в консоль."""
        print("Приступаю к анализу данных по переводу различных валют в рубли...")

        self.get_dates_to_make_parse_list()

        for date in self.dates_to_parse_list:
            date_to_parse = self.normalize_date_to_parse(date)
            full_url_to_parse = os.path.join(self.base_url + date_to_parse)
            data_from_api = self.parser.get_data_from_api(full_url_to_parse)
            self.analyze_one_day_data(data_from_api)

        self.calculate_avg_each_currency()

        print(f"Значение максимальной валюты: "
              f"{self.max_value_currency['value']} "
              f"{self.max_value_currency['name']} "
              f"от {self.max_value_currency['date']} г.")

        print(f"Значение минимальной валюты: "              
              f"{self.min_value_currency['value']} "
              f"{self.min_value_currency['name']} "
              f"от {self.min_value_currency['date']} г.")

        print(f"Cреднее значение перевода в рубли каждой валюты за {self.days_to_parse} дней составляет:")
        for currency, value in self.avg_conversion_into_rubles.items():
            print(f'{currency}: {value}')

        print("Работа скрипта завершена.")


if __name__ == '__main__':
    days_to_parse = input('Введите количество дней для анализа или нажмите Enter для анализа за последние 90 дней: ')

    if len(days_to_parse) == 0:
        parser = RubleConversionScrapper()
        parser.analyze_data()
    else:
        try:
            days_to_parse = int(days_to_parse)
            parser = RubleConversionScrapper(days_to_parse)
            parser.analyze_data()
        except ValueError:
            raise SystemExit(f'Вы ввели не целое число.')
