def ozon_dynamic_prices():
    from my_modules.log.log import log
    from products import Product # добавляем класс с товарами


    MINIMUM_PERIOD_DAYS = 8     # минимальный период, который должен пройти с последнего изменения
    MINIMUM_ORDERS = 9         # минимальное количество заказов товара
    MINIMUM_TRANSACTIONS = 5    # минимальное количество транзакций (доставленных товаров, по которым можно
                                #   посчитать прибыльность)
    PRICE_CHANGE_KOEF = 0.05    # коэффициент, на который изменяем цену
    ACQUIRING = 0.0015          # комиссия за эквайринг
    PROFIT_KOEF = 0.9           # коэффициент приведения расчетной прибыли к реальной (часть прибыли тратится на
                                # дополнительные услуги, которые не учитываются в расчетах)
    MARJ_MINIMUM = 0.3          # минимально допустимая маржинальность
    PROFIT_MINIMUM = 30         # минимальный доход с единицы товара

    # Для товаров с низкой оборачиваемостью
    # Период за который проверяются продажи
    BADSELLERS_PERIOD = 30
    # Маржа, выше которой цена товара снижается
    BADSELLERS_MARJ_LIMIT = 0.5
    # Количество проданных товаров за период, при котором цена снижается
    BADSELLERS_AMOUNT_LIMIT = 5

    log.clear()
    Product.get_ozon_dinamic_price_data() # загружаем данные о последнем изменении
    Product.append_new_products() # добавляем новые продукты

    print('Загружаю остатки на складах')
    Product.add_stock()

    print('Обновляю себестоимость товаров из Мой Склад')
    Product.add_new_selfcost()

    products_amount = len(Product.product_list)

    for count, product in enumerate(sorted(Product.product_list, key=lambda x: x.skus[0]), start=1):

        print()

        if product.days_passed < MINIMUM_PERIOD_DAYS:
            log.add(f'[i] Товар "{product}" пропущен. С последнего изменения прошло меньше {MINIMUM_PERIOD_DAYS} дней')
            product.new_price = product.new_change = None
            continue

        log.add(f'[i] Товар {count} из {products_amount}, "{product}". Собираю данные о количестве заказов.')

        # Добавляем к каждому товару количество заказанных товаров с последнего изменения
        product.add_oz_ordered()

        # Уменьшаем цену товаров с низкими продажами и высокой маржой
        forced_price_down = product.if_badsellers_himarj(
            period=BADSELLERS_PERIOD,
            marj_limit=BADSELLERS_MARJ_LIMIT,
            sale_limit=BADSELLERS_AMOUNT_LIMIT
        )

        # Если цена не меняется принудительно
        if not forced_price_down:

            if product.pcs_ordered < MINIMUM_ORDERS and not forced_price_down:
                log.add(f'[i] Товар "{product}" пропущен. Заказано: {product.pcs_ordered}. Минимум: {MINIMUM_ORDERS}')
                product.new_price = product.new_change = None
                continue

            # Добавляем количество заказов каждого товара
            product.add_orders_amount()
            print('Orders amount', product.orders)
            print('Pcs amount', product.pcs_ordered)

            # Получаем среднюю прибыль с одного заказа по данным из доставленных заказов
            print(f'[i] Товар {count} из {products_amount}, "{product}". Считаю прибыль.')
            product.add_profit(MINIMUM_TRANSACTIONS, ACQUIRING, PROFIT_KOEF)

            if product.profit is None and not forced_price_down:
                log.add(f'[i] Товар "{product}" пропущен. Недостаточно транзакций')
                product.new_price = product.new_change = None
                continue

            # Добавляем прибыль в день
            product.count_profit_per_day()

        # Если цена меняется принудительно
        else:
            marj = product.marj
            if marj: marj = round(product.marj, 2)
            print('--------')
            print(f'[!] У товара "{product}" низкая оборачиваемость, высокая маржа {marj} и остаток {product.on_stock}.'
                  f' Цена принудительно снижена.')
            print('--------')

        # Добавляем новую цену и новое изменение (1 или -1)
        # если прибыль выросла - изменить цену также, как менялась раньше, если упала - наоборот
        product.count_new_price(PRICE_CHANGE_KOEF, MARJ_MINIMUM, PROFIT_MINIMUM, forced_down=forced_price_down)

        # Добавляем кол-во заказов и штук к общему кол-ву
        product.count_total()

        print(f'[i] Товар {count} из {products_amount}, "{product}". Обновляю цену на площадке.')
        # Изменяем цену на площадке
        product.change_price_oz()

    # TODO: записать данные в файл лога

    Product.save_ozon_dinamic_price_data()
    Product.save_changes_xls()
    Product.clear_new_products_file()

    # for prod in Product.product_list:
    #     prod.display()


