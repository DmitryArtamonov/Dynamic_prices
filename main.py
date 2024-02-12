from ozon_dynamic_prices import ozon_dynamic_prices
from wb_set_price import wb_set_prices
from time import sleep

# print("\n---- Устанавливаю динамические цены на Озон -----\n")
ozon_dynamic_prices()

print("Пауза 30 сек, ждем обновления данных")
sleep(30)

print("\n---- Переношу цены с Озона на Вайлдберрис -----\n")
wb_set_prices(koef=2)
