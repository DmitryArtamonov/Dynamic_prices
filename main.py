from my_modules.log.log import log
from products import Product # добавляем класс с товарами


MINIMUM_PERIOD_DAYS = 7     # минимальный период, который должен пройти с последнего изменения
MINIMUM_ORDERS = 10         # минимальное количество заказов товара
MINIMUM_TRANSACTIONS = 5    # минимальное количество транзакций (доставленных товаров, по которым можно
                            #   посчитать прибыльность)
PRICE_CHANGE_KOEF = 0.05    # коэффициент, на который изменяем цену
ACQUIRING = 0.0015          # комиссия за эквайринг
PROFIT_KOEF = 0.9           # коэффициент приведения расчетной прибыли к реальной (часть прибыли тратится на
                            # дополнительные услуги, которые не учитываются в расчетах)
MINIMUM_MARJ = 0.2          # минимально допустимая маржинальность


log.clear()
Product.get_ozon_dinamic_price_data() # загружаем данные о последнем изменении
Product.append_new_products() # добавляем новые продукты

print('Обновляю себестоимость товаров из Мой Склад')
Product.add_new_selfcost()

products_amount = len(Product.product_list)

for count, product in enumerate(sorted(Product.product_list, key=lambda x: x.skus[0]), start=1):

    print()

    if product.days_passed < MINIMUM_PERIOD_DAYS:
        log.add(f'[i] Товар "{product}" пропущен. С последнего изменения прошло меньше {MINIMUM_PERIOD_DAYS} дней')
        product.new_price = product.new_change = None
        continue

#TODO: при экспорте новых товаров их экселя:
    # проверить, что черех xls не добавляется товар, который уже есть
    # артикулы очистить от перевода строк и пробелов
    # автоматически добавлять артикул озона

    log.add(f'[i] Товар {count} из {products_amount}, "{product}". Собираю данные о количестве заказов.')

    # Добавляем к каждому товару количество заказов с последнего изменения
    product.add_oz_ordered()
    if product.pcs_ordered < MINIMUM_ORDERS:
        log.add(f'[i] Товар "{product}" пропущен. Заказов: {product.pcs_ordered}. Минимум: {MINIMUM_ORDERS}')
        product.new_price = product.new_change = None
        continue

    print(f'[i] Товар {count} из {products_amount}, "{product}". Считаю прибыль.')
    # Получаем среднюю прибыль с одного заказа по данным из доставленных заказов
    product.add_profit(MINIMUM_TRANSACTIONS, ACQUIRING, PROFIT_KOEF)
    if product.profit is None:
        log.add(f'[i] Товар "{product}" пропущен. Недостаточно транзакций')
        product.new_price = product.new_change = None
        continue

    # Добавляем прибыль в день
    product.count_profit_per_day()

    # Добавляем новую цену и новое изменение (1 или -1)
    # если прибыль выросла - изменить цену также, как менялась раньше, усли упала - наоборот
    product.count_new_price(PRICE_CHANGE_KOEF, MINIMUM_MARJ)

    print(f'[i] Товар {count} из {products_amount}, "{product}". Обновляю цену на площадке.')
    # Изменяем цену на площадке
    product.change_price_oz()

# TODO: записать данные в файл лога

Product.save_ozon_dinamic_price_data()
Product.save_changes_xls()
Product.clear_new_products_file()

# for prod in Product.product_list:
#     prod.display()


