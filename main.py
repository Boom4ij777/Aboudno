import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor

API_TOKEN = '7416251239:AAGwnGJZukdpjBxPsxxW-8Gaqq6BAYTyZJY'
ADMIN_ID = 7817919248

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Загрузка и сохранение
def load_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

users = load_data('users.json')
products = load_data('products.json')

def main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🛍 Товары", callback_data="shop"))
    kb.add(InlineKeyboardButton("💰 Баланс", callback_data="balance"))
    if ADMIN_ID:
        kb.add(InlineKeyboardButton("⚙ Админка", callback_data="admin"))
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Добавить товар", callback_data="add_product"))
    kb.add(InlineKeyboardButton("💸 Пополнить баланс", callback_data="add_balance"))
    kb.add(InlineKeyboardButton("⬅ Назад", callback_data="back"))
    return kb

@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    uid = str(msg.from_user.id)
    if uid not in users:
        users[uid] = {"balance": 0}
        save_data("users.json", users)
    await msg.answer("👋 Добро пожаловать!", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: True)
async def handle_callbacks(call: types.CallbackQuery):
    uid = str(call.from_user.id)

    if call.data == "balance":
        bal = users.get(uid, {}).get("balance", 0)
        await call.message.edit_text(f"💳 Ваш баланс: {bal}₽", reply_markup=main_menu())

    elif call.data == "shop":
        if not products:
            await call.message.edit_text("📦 Пока нет товаров", reply_markup=main_menu())
            return
        kb = InlineKeyboardMarkup()
        for name, item in products.items():
            kb.add(InlineKeyboardButton(f"{name} - {item['price']}₽", callback_data=f"buy_{name}"))
        kb.add(InlineKeyboardButton("⬅ Назад", callback_data="back"))
        await call.message.edit_text("🛍 Выберите товар:", reply_markup=kb)

    elif call.data == "back":
        await call.message.edit_text("📲 Главное меню", reply_markup=main_menu())

    elif call.data == "admin" and call.from_user.id == ADMIN_ID:
        await call.message.edit_text("⚙ Админ-панель", reply_markup=admin_menu())

    elif call.data == "add_product" and call.from_user.id == ADMIN_ID:
        await call.message.answer("📝 Введи товар:\n\n`Название | Цена | Текст товара`", parse_mode="Markdown")
        dp.register_message_handler(add_product, lambda m: m.from_user.id == ADMIN_ID, content_types=types.ContentTypes.TEXT, state="*")

    elif call.data == "add_balance" and call.from_user.id == ADMIN_ID:
        await call.message.answer("💸 Введи:\n`user_id | сумма`", parse_mode="Markdown")
        dp.register_message_handler(add_balance, lambda m: m.from_user.id == ADMIN_ID, content_types=types.ContentTypes.TEXT, state="*")

    elif call.data.startswith("buy_"):
        name = call.data[4:]
        item = products.get(name)
        if not item:
            await call.message.answer("❌ Товар не найден.")
            return

        price = item['price']
        balance = users.get(uid, {}).get("balance", 0)

        if balance < price:
            await call.message.answer("❌ Недостаточно средств.")
            return

        users[uid]["balance"] -= price
        save_data("users.json", users)
        await call.message.answer(f"✅ Вы купили *{name}*.\n\n📃 Ваш товар:\n`{item['text']}`", parse_mode="Markdown")

async def add_product(msg: types.Message):
    try:
        name, price, text = map(str.strip, msg.text.split("|"))
        products[name] = {"price": int(price), "text": text}
        save_data("products.json", products)
        await msg.answer(f"✅ Товар '{name}' добавлен.")
    except:
        await msg.answer("❌ Ошибка. Формат: `Название | Цена | Текст товара`")
    dp.unregister_message_handler(add_product)

async def add_balance(msg: types.Message):
    try:
        uid, amount = map(str.strip, msg.text.split("|"))
        amount = int(amount)
        if uid not in users:
            users[uid] = {"balance": 0}
        users[uid]["balance"] += amount
        save_data("users.json", users)
        await msg.answer(f"✅ Пользователю {uid} добавлено {amount}₽.")
    except:
        await msg.answer("❌ Неверный формат. Пример: `123456789 | 50`")
    dp.unregister_message_handler(add_balance)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)