import openpyxl as op
import json
from time import sleep
from tqdm import tqdm
from datetime import datetime, timedelta
from apiconnect import ozon
from log import log


class Product:
    product_list = []


    def __init__(self, title, changed, skus, skus_oz, price, prev_change, prev_profit_day, selfcost):
        self.title = title
        self.changed = changed
        self.skus = skus
        self.skus_oz = skus_oz
        self.price = price
        self.prev_change = prev_change
        self.prev_profit_day = prev_profit_day
        self.selfcost = selfcost
        timepassed = datetime.now() - changed
        self.days_passed = timepassed.days + timepassed.seconds / (24 * 3600)
        self.new_change = None
        self.profit_day = None
        self.marj = None
        self.profit = None
        self.new_price = None
        self.pcs_ordered = None






    def __str__(self):
        return self.title

    def display(self):
        print(self.__dict__)


    @classmethod
    def get_ozon_dinamic_price_data(cls):
        """ Создаем лист товаров на основе записи в last_change.json"""
        with open ('data/last_change.json', encoding='utf-8') as last_change_json:
            last_change_data = json.load(last_change_json)

        for prod in last_change_data:  # создаем новый Product и добавляем его в список
            new_product_gr = Product(
                title = prod['title'],
                changed = datetime.fromisoformat(prod['changed']), # время последнего изменения
                skus = prod['skus'],                               # список наших sku
                skus_oz = prod['skus_oz'],                         # список sku озона
                price = prod['price'],                             # текущая цена
                prev_change = prod['prev_change'],                 # предыдущее изменение цены (1 или -1)
                prev_profit_day = prod['prev_profit_day'],         # прибыль в день за прошлый период
                selfcost = prod['selfcost']                       # себестоимость средняя по всем товарам
            )

            cls.product_list.append(new_product_gr)

        return cls.product_list

    @classmethod
    def append_new_products(cls):
        """
        Функция дополняет список товаров товарами из файла new_products.xls и очищает файл
        """

        workbook = op.load_workbook('data/new_products.xlsx')
        sheet = workbook.active
        date_from = datetime.now() - timedelta(days=14)

        added_skus = []                     # создаем список уже занесенных артикулов для последующей проверки новых
        for product in Product.product_list:
            added_skus.extend(product.skus)

        # создаем новый товар с полями из Excel
        row = 2
        while sheet.cell(row, 1).value:     # перебор строк, пока значение в поле артикул заполнено
            new_product = cls(
                title=sheet.cell(row, 2).value,
                skus=sheet.cell(row, 1).value.strip().split(', '),
                skus_oz=[],
                price=int(sheet.cell(row, 3).value),
                prev_change=int(sheet.cell(row, 4).value),
                selfcost=int(sheet.cell(row, 5).value),
                changed=date_from,
                prev_profit_day=0
                )

            # проверяем, что новых ску нет в базе
            pass_sku = False
            for sku in new_product.skus:
                if sku in added_skus:
                    log.add(f'[!] Артикул {sku} {new_product} уже есть в базе. Товар пропущен.')
                    pass_sku = True
            if pass_sku:
                row += 1
                continue

            # добавляем sku Озона
            skus_oz = ozon.get_ozon_skus(new_product.skus)
            if skus_oz is None:
                log.add(f'[!] Ошибка при поиске артикулов нового товара {new_product}: {new_product.skus}'
                        f'Товар пропущен.')
                row += 1
                continue
            new_product.skus_oz = skus_oz

            # добавляем новый продукт в базу
            cls.product_list.append(new_product)
            log.add(f'[a] Товар {new_product} добавлен')
            sheet.delete_rows(row)

        while True:
            try:
                workbook.save('data/new_products.xlsx')
                break
            except Exception as e:
                log.add(f'[!] Ошибка сохранения файла new_products.xlsx. Закройте файл, если он открыт. {e}')
                sleep(3)

    @classmethod
    def save_ozon_dinamic_price_data(cls):
        """
        Сохраняем измененные данные в файл .json
        """
        new_json = []
        for product in cls.product_list:
            if product.new_price is None:
                data = {
                    "title": product.title,
                    "changed": product.changed.isoformat(),
                    "skus": product.skus,
                    "skus_oz": product.skus_oz,
                    "price": product.price,
                    "prev_change": product.prev_change,
                    "prev_profit_day": product.prev_profit_day,
                    "selfcost": product.selfcost
                }
            else:
                data = {
                    "title": product.title,
                    "changed": datetime.now().isoformat(),
                    "skus": product.skus,
                    "skus_oz": product.skus_oz,
                    "price": product.new_price,
                    "prev_change": product.new_change,
                    "prev_profit_day": product.profit_day,
                    "selfcost": product.selfcost
                }
            new_json.append(data)

        while True:
            try:
                with open ('data/last_change.json', mode='w', encoding='utf-8') as last_change_json:
                    json.dump(new_json, last_change_json, ensure_ascii=False)
                break
            except Exception as e:
                log.add(f'[!] Ошибка сохранения json файла. Закройте файл, если он открыт. {e}')
                sleep(3)


    @classmethod
    def save_changes_xls(cls):
        """
        Сохраняем изменения в журнал xls
        """

        workbook = op.load_workbook('data/changes.xlsx')
        sheet = workbook.active

        for product in cls.product_list:
            if product.new_price is None: continue
            new_row = [
                product.changed.strftime("%d.%m.%Y"),
                round(product.days_passed, 1),
                ' '.join(product.skus),
                product.title,
                product.price,
                product.new_price,
                product.new_change,
                product.pcs_ordered,
                round(product.pcs_ordered / product.days_passed, 1),
                round(product.profit_day),
                round(product.profit),
                product.marj,
                product.selfcost
            ]
            sheet.append(new_row)

        while True:
            try:
                workbook.save('data/changes.xlsx')
                break
            except Exception as e:
                log.add(f'[!] Ошибка сохранения xls файла. Закройте файл, если он открыт. {e}')
                sleep(3)


    def add_oz_ordered(self):
        """Дополняем товар данными о количестве заказов на озон за период"""
        all_data = ozon.get_ozon_orders_statistic(self.changed, datetime.now())
        pcs_ordered = 0
        for product_oz_sku in self.skus_oz:
            for prod_stat in all_data:
                if product_oz_sku == prod_stat['sku_oz']:
                    pcs_ordered += prod_stat['pcs_ordered']
        self.pcs_ordered = pcs_ordered

    def add_profit(self, minimum_transactions, aquiring):
        """Дополняем товар средним доходом"""

        #1. Собираем номера отправлений доставленных заказов
        #TODO: добавить цикл для подсчета всех товаров в списке, а не только первого
        postings = []
        for sku_oz in self.skus_oz:
            postings.extend(ozon.get_ozon_orders_by_product(sku_oz, self.changed))

        #2. Считаем средний доход от доставленных товаров
        postings_total = 0  # кол-во отправлений
        income_total = 0    # сумма перечисленная озоном
        for posting in tqdm(postings):
            income = ozon.get_posting_income(posting)
            if income is None: continue # если в отправлении были разные товары, его не учитываем

            income_total += income
            postings_total += 1

        if postings_total < minimum_transactions: # пропускаем товары, у которых мало доставленных заказов
            self.profit = None
        else:
            self.profit = round(
                income_total / postings_total - self.selfcost - aquiring * self.price,
                ndigits=2)
            self.marj = round(self.profit / self.selfcost, 2)  # маржинальность


    def count_profit_per_day(self):
        """
        Считаем среднюю прибыль в день. Экстраполируем данные из транзакций на все товары и делим на прошедшие дни
        """
        profit = self.profit * self.pcs_ordered
        self.profit_day = profit / self.days_passed

    def count_new_price(self, koef):
        if self.profit_day > self.prev_profit_day:
            self.new_change = self.prev_change
        else:
            self.new_change = -self.prev_change

        self.new_price = round(self.price + self.price * koef * self.new_change)


    def change_price_oz(self):
        data_list = []
        for sku in self.skus:
            data = {'sku': sku, 'price':self.new_price}
            data_list.append(data)
        ozon.update_prices_ozon(data_list)


