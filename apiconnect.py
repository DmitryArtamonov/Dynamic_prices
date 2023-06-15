"""
Модуль создает класс Service для работы с отдельными сервисами - маркетплейсами, Isales, МойСклад.
А также функции запросов данных у этих сервисов
"""

import time
import requests
from log import log


class Service:
    def __init__(self, url, header, max_requests):
        self.url = url
        self.header = header
        self.max_requests = max_requests

# Вспомогательные функции:

    @staticmethod
    def ozon_datetime(date_time):
        '''
        Перевод даты/времени в формат Озона
        '''
        return date_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')

# Конец вспомогательных функций


    def connection(self, url2, body=None, method='get', params=''):
        """
            Функция соединения с API сервиса. Поддерживает get, post, put requests.
            В случае ошибки, работает в бесконечном цикле, добавляя паузу в запрос
        """
        pause = 10 # первая пауза в случае ошибки

        if body is None:
            body = {}
        full_url = self.url + url2

        while True:

            try:
                log.add(f'[i] Запрос API {method.upper()} {self.url + url2}', mode='f')
                if method == 'get':
                    response = requests.get(full_url, headers=self.header, params=params)
                elif method == 'post':
                    response = requests.post(full_url, headers=self.header, json=body)
                elif method == 'put':
                    response = requests.put(full_url, json=body)
                else:
                    raise Exception(f'Wrong request type: {method}')

                if response.status_code != 200:
                    raise Exception(f'Server error: {response.status_code} {response.reason}')

                log.add('[i] Ответ сервера получен', mode='f')
                pause = 10 # сброс паузы
                return response.json()

            except Exception as e:

                log.add(f'[!] {e}')
                log.add(f'[i] Пауза {pause} сек')
                time.sleep(pause)
                pause += 10


    def ozon_requests_loop(self, url2, body=None, method='get', params='', prefix="['result']"):

        """
        Функция обеспечивает последовательную отправку запросов в случае, если
        результат запроса превышает максимальный объем. А также объединяет результат в список.
        Для определения пути к списку, который будет объединяться используется аргумент prefix.
        Его значение зависит от конкретного запроса (см. документацию API Озона)
        """
        if body is None:
            body = {}
        offset = 0
        body['limit'] = self.max_requests
        body['offset'] = 0
        result = []

        while True:
            response = self.connection(url2=url2, body=body, method=method, params=params)
            data = eval("response"+prefix)
            result.extend(data)
            if len(data) < self.max_requests:
                return result
            offset += self.max_requests
            body['offset'] = offset


#Статичные функции с запросами на конкретный сервис:

    def get_ozon_skus(self, sku_list):
        """
        Функция принимает список артикулов и возвращает список sku озона. Каждый sku в формате строки.
        Если какой либо артикул не найден, выдается сообщение и возвращается None.
        """

        if len(sku_list) > 1000:
            log.add(f'[!] В функцию get_ozon_skus передано слишком много (более 1000) артикулов)')
            return None

        body = {
            "offer_id": sku_list
        }

        res = ozon.connection('/v2/product/info/list', body=body, method='post')['result']['items']

        if len(res) != len(sku_list):
            log.add(f'[i] Не все артикулы найдены на Озоне!')
            return None

        ozon_skus = [str(item['fbo_sku']) for item in res]

        return ozon_skus


    def get_ozon_orders_statistic(self, time_from, time_to):
        '''
        Статистика заказов за период. Возвращает список словарей:
        ozon_id, pcs_ordered: кол-во заказанных минус отмены,
        amount_ordered: сумма заказов уменьшенная пропорционально отменам)
        Не более 1000 товаров!!!
        '''

        body = {
            "date_from": time_from.strftime('%Y-%m-%d'),
            "date_to": time_to.strftime('%Y-%m-%d'),
            "metrics": ["revenue", "ordered_units", "cancellations"],
            "dimension": [
                "sku",
            ],
            "limit": 1000,
            "offset": 0
        }

        res = ozon.ozon_requests_loop(
            url2='/v1/analytics/data',
            method='post',
            body=body,
            prefix="['result']['data']"
        )

        ozon_statistic = []

        for product in res:
            ozon_statistic.append({'sku_oz': product['dimensions'][0]['id'],
                                   'pcs_ordered': product['metrics'][1] - product['metrics'][2],  # заказы минус отмены
                                   'amount_ordered': product['metrics'][0]})

        return ozon_statistic


    def get_ozon_orders_by_product(self, id, since_time):

        body = {
            "filter": {
                "since": Service.ozon_datetime(since_time),
                "status": "delivered",
            },
            "with": {
                "financial_data": True
            }
        }

        res = ozon.ozon_requests_loop('/v2/posting/fbo/list', method='post', body=body)

        postings = []

        for order in res:
            for product in order['products']:
                if str(product['sku']) == id:
                    postings.append(order['posting_number'])

        return postings


    def get_posting_income(self, posting_number):
        '''
        Функция возвращает стоимость товара в отправлении за вычетом комиссии и расходов на доставку.
        Если в отправлении несколько разных товаров, возвращается None (невозможно распределить расходы по товарам)
        :return: float
        '''

        body = {
          "filter": {
            "posting_number": posting_number,
            "transaction_type": "all"
          },
          "page": 1,
          "page_size": 1000
        }
        res = ozon.connection('/v3/finance/transaction/list', body=body, method='post')['result']['operations'][0]

        if len(res['items']) > 1: # Если в отправлении несколько товаров
            items_set = set([i['sku'] for i in res['items']])

            if len(items_set) == 1: # Если в отправлении одинаковые товары
                log.add(f'[i] В отправлении {posting_number} несколько одинаковых товаров')
                return res['amount'] / len(res['items'])

            log.add(f'[i] В отправлении {posting_number} несколько разных товаров')
            return None # Если в отправлении разные товары

        return res['amount'] # Если в отправлении один товар


    def update_prices_ozon(self, price_data):
        '''
        Функция обновляет цены товаров. На вход функции подается список словарей с полями sku и price.
        Sku - артикул продавца.
        Всем товарам выставляется одинаковая цена. Старая (зачеркнутая цена) ставится таким образом,
        чтобы скидка была 30%.
        '''

        body = {
            "prices": []
        }

        for product in price_data:
            sku = product['sku']
            price = product['price']
            old_price = round(price / 0.7)
            product_dict = {
                "auto_action_enabled": "DISABLED",
                "old_price": str(old_price),
                "price": str(price),
                "min_price": "0",
                "offer_id": sku
            }
            body['prices'].append(product_dict)

        response = ozon.connection('/v1/product/import/prices', body=body, method='post')

        for product in response['result']:
            new_price = list(filter(lambda x: x['sku'] == product['offer_id'], price_data))[0]['price']
            if product['updated']:
                log.add(f"[a] Цена товара {product['offer_id']} обновлена. Новая цена: {new_price}", mode='f')
            else:
                log.add(f"[!] Цена товара {product['offer_id']} не обновлена! {product['errors']}")


def get_api_data(file='D:\Dropbox\Python\API_data.txt'):
    #  Функция возвращает словарь с данными API из текстового файла..

    with open(file, 'r', encoding='utf-8') as api_keys_file:
        api_keys_lines = api_keys_file.readlines()
    api_keys = {api_keys_line.split(':', 1)[0].strip():api_keys_line.split(':', 1)[1].strip() for api_keys_line in api_keys_lines}
    return api_keys


# Создаем объект Озон
api_keys = get_api_data() # получаем ключи
oz_header = {'Client-Id': api_keys['OZON_ID'], 'Api-Key': api_keys['OZON_key']}
ozon = Service(header=oz_header, url='https://api-seller.ozon.ru', max_requests=500)


