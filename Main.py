import sqlite3
import http.client
import json
import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.types import *
from db import BotDB

# инициализация базы данных
BotDB = BotDB("accounts.db")
conn = sqlite3.connect('accounts.db')
cursor = conn.cursor()

# создание таблицы accounts, если её ещё нет
cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        country TEXT NOT NULL,
        loggin TEXT NOT NULL,
        password TEXT NOT NULL,
        coocies TEXT NOT NULL,
        price REAL NOT NULL
    )
''')
conn.commit()

# создание объектов бота и диспетчера
bot = Bot(token='5569661722:AAHRgLf9iGOHRLgp9djaMBTtdQrPC_1b1yU')
storage = MemoryStorage()
dp = Dispatcher(bot,storage=storage)
# ID администратора
admin_id = 1955770700


# обработчики команд
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if (not BotDB.user_exists(message.from_user.id)):
        BotDB.add_user(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Купить логи")
    item2 = types.KeyboardButton("Купить фарм")
    item3 = types.KeyboardButton("Баланс")
    item4 = types.KeyboardButton("Поддержка")
    markup.add(item1, item2, item3, item4)
    await message.answer(
        "Привет! Я бот для покупки аккаунтов для арбитража трафика. Чтобы посмотреть список доступных аккаунтов, введите команду /accounts",
        reply_markup=markup)


@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.answer(
        "Список доступных команд:\n/accounts - посмотреть список всех доступных аккаунтов")


@dp.message_handler(commands=['accounts'])
async def accounts(message: types.Message):
    # запрос аккаунтов из базы данных
    cursor.execute('SELECT id, name, price, type, country FROM accounts')
    results = cursor.fetchall()

    # формирование сообщения со списком аккаунтов
    message_text = 'Список доступных аккаунтов:\n'
    for result in results:
        message_text += f'{result[0]}. {result[1]}, {result[3]}, {result[4]} - {result[2]} USDT\n'
    await message.answer(message_text)

@dp.message_handler(commands=['add'])
async def add_account(message: types.Message):
    # проверка прав доступа
    if message.from_user.id != admin_id:
        await message.answer("У вас нет прав на добавление аккаунтов")
        return

    # добавление нового аккаунта в базу данных
    name, type, country, loggin, password, coocies, price = message.text.split()[1:]
    cursor.execute(
        'INSERT INTO accounts (name, type, country, loggin, password, coocies, price) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (name, type, country, loggin, password, coocies, price))
    conn.commit()

    await message.answer("Аккаунт успешно добавлен в базу данных")


class PaymentForm(StatesGroup):
    amount = State()
    success = State()

@dp.message_handler(Text(equals='Пополнить баланс (USDT)'))
async def cancel_handler(message: types.Message):
    await PaymentForm.amount.set()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("5")
    item2 = types.KeyboardButton("10")
    item3 = types.KeyboardButton("25")
    item4 = types.KeyboardButton("50")
    item5 = types.KeyboardButton("100")
    item6 = types.KeyboardButton("Отмена")
    markup.add(item1,item2,item3,item4,item5,item6)
    await bot.send_message(message.chat.id, 'Введите количество usdt', reply_markup=markup)


@dp.message_handler(state=PaymentForm.amount)
async def process_name(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        user_id = message.chat.id
        balance = BotDB.get_balance(user_id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Пополнить баланс (USDT)")
        back = types.KeyboardButton("Назад")
        markup.add(item1,back)
        await bot.send_message(message.chat.id, 'Ваш балланс = ' + str(balance) + ' USDT', reply_markup=markup)
        await state.finish()
    elif message.text.isdigit():
        conn = http.client.HTTPSConnection("api.commerce.coinbase.com")
        payload = json.dumps({
        "name": "Оплата",
                "description": "Оплата",
        "pricing_type": "fixed_price",
        "local_price": {
            "amount": message.text,
            "currency": "usdt"
        }
        })
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CC-Version': '2018-03-22',
            'X-CC-Api-Key': '11f189d0-70cd-45b0-b0c2-6db0bc1bb0ca'
        }
        conn.request("POST", "/charges", payload, headers)
        res = conn.getresponse()
        data = res.read()
        data = data.decode("utf-8")
        data = json.loads(data)
        address = data["data"]["addresses"]["tether"]
        id = data["data"]["id"]
        url = data["data"]["hosted_url"]
        async with state.proxy() as data_storage:
            data_storage['amount'] = float(message.text)
            data_storage['address'] = address
            data_storage["id"] = id
        await PaymentForm.success.set()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        approve = types.KeyboardButton("Подтвердить оплату")
        back = types.KeyboardButton("Отмена")
        markup.add(back,approve)
        await bot.send_message(message.chat.id, "Перечислите " + message.text + "usdt на адресс " + address + "\nИли оплатите по ссылке: " + url, reply_markup=markup)
    else:
        await bot.send_message(message.chat.id, 'Введите целое число!')

@dp.message_handler(state=PaymentForm.success)
async def process_name2(message: types.Message,state: FSMContext):
    async with state.proxy() as data_storage:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Отмена")
        item2 = types.KeyboardButton("Проверить оплату")
        markup.add(item1,item2)
        if message.text == "Отмена":
            await state.finish()

        else:
            conn = http.client.HTTPSConnection("api.commerce.coinbase.com")
            payload = ''
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-CC-Api-Key': '11f189d0-70cd-45b0-b0c2-6db0bc1bb0ca'
            }
            conn.request("GET", "/charges/" + data_storage["id"], payload, headers)
            res = conn.getresponse()
            data = res.read()
            print(data.decode("utf-8"))
            data = json.loads(data)
            status = data["data"]["timeline"][-1]["status"]
            if status == "REFOUNDED":
                #оплачено успешно
                #amount - количество usdt на которое успешно пополнили баланс
                amount = data_storage['amount']
                await state.reset_state (with_data = False)
                await bot.send_message(message.chat.id, "Оплачено успешно!")
                # пополняем баланс на amount usdt
                user_id = message.chat.id
                upd_balance = BotDB.get_balance(user_id) + amount
                BotDB.update_balance(user_id, upd_balance)
            else:
                await bot.send_message(message.chat.id, "Оплата пока не найдена. Возвожно она не прошла проверку сетью.Попробуйте позже!")

class BuyLogsForm(StatesGroup):
    id = State()
    confirm = State()

@dp.message_handler(Text(equals='Купить логи'))
async def buy_log(message: types.Message):
    # запрос аккаунтов из базы данных
    cursor.execute('SELECT id, name, price, type, country FROM accounts WHERE type = "лог"')
    results = cursor.fetchall()

    # формирование сообщения со списком аккаунтов
    message_text = 'Список доступных аккаунтов:\n'
    for result in results:
        message_text += f'{result[0]}. {result[1]}, {result[3]}, {result[4]} - {result[2]} USDT\n'

    await message.answer(message_text)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back = types.KeyboardButton("Назад")
    markup.add(back)
    await bot.send_message(message.chat.id, 'Выберите номер аккаунта', reply_markup=markup)
    await BuyLogsForm.id.set()

@dp.message_handler(state=BuyLogsForm.id)
async def buy_log(message: types.Message,state: FSMContext):
    if message.text =="Назад":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Купить логи")
        item2 = types.KeyboardButton("Купить фарм")
        item3 = types.KeyboardButton("Баланс")
        item4 = types.KeyboardButton("Поддержка")
        markup.add(item1, item2, item3, item4)
        await message.answer(
            "Выберите пункт меню",
            reply_markup=markup)
        await state.finish()

    elif message.text.isdigit():
        id = int(message.text)
        account = BotDB.get_user_buy(id)
        if account == None:
            await bot.send_message(message.chat.id,"Такого аккаунта не существует. Введите корректное значение!")
        else:
            async with state.proxy() as data_storage:
                message_text = f'{account[0]}. {account[1]}, {account[3]}, {account[4]} - {account[7]} USDT\n'
                await bot.send_message(message.chat.id,"Подтвердите покупку аккаунта:\n" + message_text)
                await BuyLogsForm.confirm.set()
                data_storage['id'] = id
    else:
        await bot.send_message(message.chat.id,"Введите корректное число")

@dp.message_handler(state=BuyLogsForm.confirm)
async def buy_log_confirm(message: types.Message,state: FSMContext):
    async with state.proxy() as data_storage:
        money = BotDB.get_balance(user_id=message.chat.id)
        account = BotDB.get_user_buy(data_storage['id'])
        cost = int(account[7])
        if money >= cost:
            user_id = int(message.chat.id)
            message_new = f'Имя: {account[1]}\nТип: {account[2]}\nСтрана: {account[3]}\nЛогин: {account[4]}\nПароль: {account[5]}\nСoocies:{account[6]}'
            await bot.send_message(message.chat.id,"Данные аккаунта:\n" + message_new +"\nСпасибо за покупку)")
            upd_balance = BotDB.get_balance(user_id) - cost
            BotDB.update_balance(user_id, upd_balance)
            await  state.finish()
        else:
            user_id = message.chat.id
            balance = BotDB.get_balance(user_id)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Пополнить баланс (USDT)")
            markup.add(item1)
            await bot.send_message(message.chat.id, 'У вас недостаточно средств для покупки данного аккаунта.\nВаш балланс = ' + str(balance) + ' USDT', reply_markup=markup)
            await state.finish()

class BuyFarmForm(StatesGroup):
    id = State()
    confirm = State()

@dp.message_handler(Text(equals='Купить фарм'))
async def buy_farm(message: types.Message):
    # запрос аккаунтов из базы данных
    cursor.execute('SELECT id, name, price, type, country FROM accounts WHERE type = "фарм"')
    results = cursor.fetchall()

    # формирование сообщения со списком аккаунтов
    message_text = 'Список доступных аккаунтов:\n'
    for result in results:
        message_text += f'{result[0]}. {result[1]}, {result[3]}, {result[4]} - {result[2]} USDT\n'

    await message.answer(message_text)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back = types.KeyboardButton("Назад")
    markup.add(back)
    await bot.send_message(message.chat.id, 'Выберите номер аккаунта', reply_markup=markup)
    await BuyFarmForm.id.set()

@dp.message_handler(state=BuyFarmForm.id)
async def buy_farm(message: types.Message,state: FSMContext):
    if message.text =="Назад":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Купить логи")
        item2 = types.KeyboardButton("Купить фарм")
        item3 = types.KeyboardButton("Баланс")
        item4 = types.KeyboardButton("Поддержка")
        markup.add(item1, item2, item3, item4)
        await message.answer(
            "Выберите пункт меню",
            reply_markup=markup)
        await state.finish()
    elif message.text.isdigit():
        id = int(message.text)
        account = BotDB.get_user_buy(id)
        if account == None:
            await bot.send_message(message.chat.id,"ПОШЁЛ НАХУЙ НЕ ЛОМАЙ БОТА")
        else:
            async with state.proxy() as data_storage:
                message_text = f'{account[0]}. {account[1]}, {account[3]}, {account[4]} - {account[7]} USDT\n'
                await bot.send_message(message.chat.id,"Подтвердите покупку аккаунта:\n" + message_text)
                await BuyFarmForm.confirm.set()
                data_storage['id'] = id
    else:
        await bot.send_message(message.chat.id,"Введите корректное число")

@dp.message_handler(state=BuyFarmForm.confirm)
async def buy_farm_confirm(message: types.Message,state: FSMContext):
    async with state.proxy() as data_storage:
        money = BotDB.get_balance(user_id=message.chat.id)
        account = BotDB.get_user_buy(data_storage['id'])
        cost = int(account[7])
        if money >= cost:
            user_id = int(message.chat.id)
            message_new = f'Имя: {account[1]}\nТип: {account[2]}\nСтрана: {account[3]}\nЛогин: {account[4]}\nПароль: {account[5]}\nСoocies:{account[6]}'
            await bot.send_message(message.chat.id,"Данные аккаунта:\n" + message_new +"\nСпасибо за покупку)")
            upd_balance = BotDB.get_balance(user_id) - cost
            BotDB.update_balance(user_id, upd_balance)
            await  state.finish()
        else:
            user_id = message.chat.id
            balance = BotDB.get_balance(user_id)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton("Пополнить баланс (USDT)")
            markup.add(item1)
            await bot.send_message(message.chat.id, 'У вас недостаточно средств для покупки данного аккаунта.\nВаш балланс = ' + str(balance) + ' USDT', reply_markup=markup)
            await state.finish()

@dp.message_handler(content_types=types.ContentType.TEXT)
async def process_text(message: types.Message):
    if message.text == "Купить фарм":
        # запрос аккаунтов из базы данных
        cursor.execute('SELECT id, name, price, type, country FROM accounts WHERE type = "фарм" ')
        results = cursor.fetchall()

        # формирование сообщения со списком аккаунтов
        message_text = 'Список доступных аккаунтов:\n'
        for result in results:
            message_text += f'{result[0]}. {result[1]}, {result[3]}, {result[4]} - {result[2]} USDT\n'

        await message.answer(message_text)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back = types.KeyboardButton("Назад")
        markup.add(back)
        await bot.send_message(message.chat.id, 'Выберите номер аккаунта', reply_markup=markup)

    elif message.text == "Поддержка":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Заменить невалид")
        item2 = types.KeyboardButton("Техподдержка")
        back = types.KeyboardButton("Назад")
        markup.add(back, item1, item2)
        await bot.send_message(message.from_user.id, "*Текст*", reply_markup=markup)

    elif message.text == "Заменить невалид":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        menu = types.KeyboardButton("В главное меню")
        markup.add(menu)
        await bot.send_message(message.from_user.id, '*Текст и ссылка на тех. поддержку*', reply_markup=markup)

    elif message.text == "Техподдержка":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        menu = types.KeyboardButton("В главное меню")
        markup.add(menu)
        await bot.send_message(message.from_user.id, '*Текст и ссылка на тех. поддержку*', reply_markup=markup)

    elif message.text == "В главное меню":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Купить логи")
        item2 = types.KeyboardButton("Купить фарм")
        item3 = types.KeyboardButton("Баланс")
        item4 = types.KeyboardButton("Поддержка")
        markup.add(item1, item2, item3, item4)
        await bot.send_message(message.from_user.id, 'Выюерите пункт меню', reply_markup=markup)

    elif message.text == "Назад":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Купить логи")
        item2 = types.KeyboardButton("Купить фарм")
        item3 = types.KeyboardButton("Баланс")
        item4 = types.KeyboardButton("Поддержка")
        markup.add(item1, item2, item3, item4)
        await bot.send_message(message.from_user.id, 'Выберите пункт меню', reply_markup=markup)

    if message.text == "Баланс":
        user_id = message.chat.id
        balance = BotDB.get_balance(user_id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Пополнить баланс (USDT)")
        back = types.KeyboardButton("Назад")
        markup.add(item1,back)
        await bot.send_message(message.chat.id, 'Ваш балланс = ' + str(balance) + ' USDT', reply_markup=markup)




if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
