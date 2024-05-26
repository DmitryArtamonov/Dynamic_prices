from my_modules.mp_apiconnect.ozon import ozon
from my_modules.mp_apiconnect.wildberries import wb
from my_modules.log.log import log


def wb_set_prices(koef=0):
    """
    Берет текущие цены на Озоне и устанавливает аналогичные с учетом коэффициента на ВБ
    :param koef: int На сколько процентов надо увеличить цену. По умолчанию 0
    :return: None
    """

    def create_joint_product_list():
        """
        Возвращает единый список товаров:
            'sku' - артикул zeero
            'oz_name'
            'oz_price'
            'wb_name'
            'wb_price'
            'wb_discount'
            'wb_fin_price'
        """

        oz_skus = list(map(lambda x: x['offer_id'], ozon.products))
        wb_skus = list(map(lambda x: x['sku_zr'], wb.products))

        # Проверяем артикулы ВБ, не совпадающие с Озоном
        if set(wb_skus) - set(oz_skus):
            print('На Вайлдберис есть артикулы, отсутствующие на Озоне:', set(wb_skus) - set(oz_skus))

        joint_skus = set(oz_skus + wb_skus)
        joint_products = []
        for sku in joint_skus:
            product_oz = list(filter(lambda x: x['offer_id'] == sku, ozon.products))
            product_wb = list(filter(lambda x: x['sku_zr'] == sku, wb.products))

            product = {'sku': sku}

            if product_oz:
                product_oz = product_oz[0]
                product.update({
                    'oz_name': product_oz['name'],
                    'oz_price': float(product_oz['price'])
                })

            if product_wb:
                product_wb = product_wb[0]
                product.update({
                    'wb_id': product_wb['id'],
                    'wb_name': product_wb['title'],
                    'wb_price': product_wb['price'],
                    'wb_discount': product_wb['discount'],
                    'wb_price_marketing': product_wb['price_marketing']
                })
            joint_products.append(product)
        return joint_products

    def change_price(product_list: list, koef: int):
        """
        Формируем список с измененными ценами и передаем его в метод изменения цен
        :param koef: коэффициент изменения цены
        :param product_list: список товаров из ф-ии create_joint_product_list()
        :return: None
        """

        price_list = []

        # Проходим по всем товарам списка
        for product in product_list:

            # Пропускаем товары, не имеющие цену Озона
            if 'oz_price' not in product or 'wb_price' not in product:
                continue

            new_price = round(product['oz_price'] * (1 + koef / 100))
            cur_price = product['wb_price']

            # Пропускаем товары с разницей в цене ВБ и Озона < 5 руб
            if abs(new_price - cur_price) < 5:
                log.add(f"[i] Цена товара не изменилась: {product['sku']} {product['oz_name']}: {cur_price}руб.", 'f')
                continue

            log.add(f"[i] Меняю цену товара {product['sku']} {product['oz_name']}\n"
                    f"c {cur_price} на {new_price}руб.")
            # Предупреждаем, если изменение более 30%
            if abs(new_price / cur_price - 1) > 0.3:
                log.add(f"[!] Цена товара {product['sku']} {product['oz_name']} изменена более чем на 30%\n"
                        f"c {cur_price} на {new_price}руб.")
            price_list.append({
                'id': product['wb_id'],
                'price': new_price
            })

        wb.set_prices(price_list)

    # Обновляем данные товаров Озона
    ozon.products = ozon.get_products()

    change_price(create_joint_product_list(), koef=koef)

    return create_joint_product_list()
