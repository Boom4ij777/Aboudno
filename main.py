
import json
import asyncio
import os
import random
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Используйте переменную окружения для токена
API_TOKEN = os.getenv('BOT_TOKEN', '7416251239:AAGwnGJZukdpjBxPsxxW-8Gaqq6BAYTyZJY')
ADMIN_ID = 7817919248
LOG_CHAT_ID = -1002416113206  # ID чата для логов

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_for_product_name = State()
    waiting_for_product_description = State()
    waiting_for_product_price = State()
    waiting_for_product_text = State()
    waiting_for_balance = State()
    waiting_for_balance_amount = State()

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

# Логирование
def log_action(action, user_id, details=""):
    logs = load_data('logs.json')
    if 'logs' not in logs:
        logs['logs'] = []
    
    log_entry = {
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'action': action,
        'user_id': str(user_id),
        'details': details
    }
    logs['logs'].append(log_entry)
    
    # Ограничиваем логи до последних 100 записей
    if len(logs['logs']) > 100:
        logs['logs'] = logs['logs'][-100:]
    
    save_data('logs.json', logs)
    
    # Отправляем лог в чат
    asyncio.create_task(send_log_to_chat(log_entry))

async def send_log_to_chat(log_entry):
    try:
        emoji = ""
        if log_entry['action'] == 'purchase':
            emoji = "🛒"
        elif log_entry['action'] == 'new_user':
            emoji = "👋"
        elif log_entry['action'] == 'start':
            emoji = "▶️"
        elif log_entry['action'] == 'add_product':
            emoji = "📦"
        elif log_entry['action'] == 'add_balance':
            emoji = "💰"
        elif log_entry['action'] == 'buy_failed':
            emoji = "❌"
        elif log_entry['action'] == 'product_sold_out':
            emoji = "📭"
        elif log_entry['action'] == 'admin_access':
            emoji = "⚙️"
        elif log_entry['action'] == 'check_balance':
            emoji = "💳"
        elif log_entry['action'] == 'visit_shop':
            emoji = "🛍️"
        else:
            emoji = "ℹ️"
        
        log_message = f"{emoji} **{log_entry['timestamp']}**\n"
        log_message += f"👤 **User ID:** `{log_entry['user_id']}`\n"
        log_message += f"📝 **Action:** {log_entry['action']}\n"
        log_message += f"📄 **Details:** {log_entry['details']}"
        
        await bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=log_message,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка при отправке лога в чат: {e}")

def main_menu(user_id=None):
    buttons = [
        [InlineKeyboardButton(text="🛍 Товары", callback_data="shop")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")]
    ]
    
    # Показываем кнопку админки только админу
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="⚙ Админка", callback_data="admin")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_product")],
        [InlineKeyboardButton(text="💸 Пополнить баланс", callback_data="add_balance")],
        [InlineKeyboardButton(text="📋 Логи", callback_data="show_logs")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back")]
    ])
    return kb

@dp.message(Command("start"))
async def start(message: types.Message):
    uid = str(message.from_user.id)
    if uid not in users:
        users[uid] = {"balance": 0}
        save_data("users.json", users)
        log_action("new_user", uid, f"Новый пользователь: {message.from_user.full_name}")
    log_action("start", uid, "Пользователь запустил бота")
    await message.answer("👋 Добро пожаловать!", reply_markup=main_menu(message.from_user.id))

@dp.callback_query(F.data == "balance")
async def show_balance(call: types.CallbackQuery):
    uid = str(call.from_user.id)
    bal = users.get(uid, {}).get("balance", 0)
    log_action("check_balance", uid, f"Проверил баланс: {bal}₽")
    await call.message.edit_text(f"💳 Ваш баланс: {bal}₽", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "shop")
async def show_shop(call: types.CallbackQuery):
    uid = str(call.from_user.id)
    log_action("visit_shop", uid, "Посетил магазин")
    
    if not products:
        await call.message.edit_text("📦 Пока нет товаров", reply_markup=main_menu(call.from_user.id))
        return
    
    buttons = []
    total_items = 0
    for name, item in products.items():
        desc = item.get('description', 'Без описания')
        # Подсчитываем количество доступных товаров
        texts = item.get('texts', [item.get('text', '')])
        quantity = len([t for t in texts if t])
        total_items += quantity
        
        if quantity > 0:
            button_text = f"{name}\n{desc} - {item['price']}₽ ({quantity} шт.)"
        else:
            button_text = f"{name}\n{desc} - {item['price']}₽ (Нет ключей)"
        
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"buy_{name}")])
    
    if not buttons:
        await call.message.edit_text("📦 Пока нет товаров", reply_markup=main_menu(call.from_user.id))
        return
        
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.edit_text(f"🛍 Выберите товар:\n📊 Всего доступно: {total_items} шт.", reply_markup=kb)

@dp.callback_query(F.data == "back")
async def back_to_main(call: types.CallbackQuery):
    await call.message.edit_text("📲 Главное меню", reply_markup=main_menu(call.from_user.id))

@dp.callback_query(F.data == "admin")
async def show_admin(call: types.CallbackQuery):
    if call.from_user.id == ADMIN_ID:
        log_action("admin_access", call.from_user.id, "Вошел в админ-панель")
        await call.message.edit_text("⚙ Админ-панель", reply_markup=admin_menu())

@dp.callback_query(F.data == "add_product")
async def request_product_name(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id == ADMIN_ID:
        await call.message.answer("📝 Введите название товара:")
        await state.set_state(AdminStates.waiting_for_product_name)

@dp.callback_query(F.data == "add_balance")
async def show_users_for_balance(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id == ADMIN_ID:
        if not users:
            await call.message.edit_text("❌ Нет зарегистрированных пользователей", reply_markup=admin_menu())
            return
        
        buttons = []
        for uid, user_data in users.items():
            balance = user_data.get('balance', 0)
            buttons.append([InlineKeyboardButton(
                text=f"ID: {uid} (Баланс: {balance}₽)", 
                callback_data=f"select_user_{uid}"
            )])
        buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="admin")])
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await call.message.edit_text("👥 Выберите пользователя для пополнения баланса:", reply_markup=kb)

@dp.callback_query(F.data == "show_logs")
async def show_logs(call: types.CallbackQuery):
    if call.from_user.id == ADMIN_ID:
        logs = load_data('logs.json')
        if 'logs' not in logs or not logs['logs']:
            await call.message.edit_text("📋 Логи пусты", reply_markup=admin_menu())
            return
        
        # Создаем более подробную сводку
        log_text = "📋 ЛОГИ АКТИВНОСТИ ПОЛЬЗОВАТЕЛЕЙ\n"
        log_text += "=" * 35 + "\n\n"
        
        # Статистика пользователей
        user_stats = {}
        for log in logs['logs']:
            uid = log['user_id']
            if uid not in user_stats:
                user_stats[uid] = {
                    'purchases': 0,
                    'total_spent': 0,
                    'last_activity': log['timestamp']
                }
            
            if log['action'] == 'purchase':
                user_stats[uid]['purchases'] += 1
                # Извлекаем сумму из деталей
                try:
                    amount = int(log['details'].split('за ')[1].split('₽')[0])
                    user_stats[uid]['total_spent'] += amount
                except:
                    pass
            
            user_stats[uid]['last_activity'] = log['timestamp']
        
        # Показываем статистику пользователей
        if user_stats:
            log_text += "👥 СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ:\n"
            for uid, stats in user_stats.items():
                log_text += f"📱 ID: {uid}\n"
                log_text += f"🛒 Покупок: {stats['purchases']}\n"
                log_text += f"💸 Потрачено: {stats['total_spent']}₽\n"
                log_text += f"🕐 Последняя активность: {stats['last_activity']}\n\n"
        
        log_text += "📝 ПОСЛЕДНИЕ ДЕЙСТВИЯ:\n"
        log_text += "-" * 25 + "\n"
        
        # Показываем последние 15 записей с эмодзи
        for log in logs['logs'][-15:]:
            emoji = ""
            if log['action'] == 'purchase':
                emoji = "🛒"
            elif log['action'] == 'new_user':
                emoji = "👋"
            elif log['action'] == 'start':
                emoji = "▶️"
            elif log['action'] == 'add_product':
                emoji = "📦"
            elif log['action'] == 'add_balance':
                emoji = "💰"
            elif log['action'] == 'buy_failed':
                emoji = "❌"
            elif log['action'] == 'product_sold_out':
                emoji = "📭"
            else:
                emoji = "ℹ️"
            
            log_text += f"{emoji} {log['timestamp']}\n"
            log_text += f"👤 {log['user_id']}: {log['details']}\n\n"
        
        # Разбиваем на части если слишком длинное
        if len(log_text) > 4000:
            # Отправляем первую часть
            part1 = log_text[:4000]
            last_newline = part1.rfind('\n\n')
            if last_newline > 0:
                part1 = part1[:last_newline]
            
            await call.message.edit_text(part1 + "\n\n📄 Сообщение обрезано...", reply_markup=admin_menu())
        else:
            await call.message.edit_text(log_text, reply_markup=admin_menu())

@dp.callback_query(F.data.startswith("select_user_"))
async def select_user_for_balance(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id == ADMIN_ID:
        uid = call.data[12:]  # Remove "select_user_" prefix
        await state.update_data(selected_user_id=uid)
        await call.message.answer(f"💰 Введите сумму для пополнения баланса пользователя {uid}:")
        await state.set_state(AdminStates.waiting_for_balance_amount)

@dp.callback_query(F.data.startswith("buy_"))
async def buy_product(call: types.CallbackQuery):
    uid = str(call.from_user.id)
    name = call.data[4:]
    item = products.get(name)
    
    if not item:
        log_action("buy_failed", uid, f"Товар не найден: {name}")
        await call.message.answer("❌ Товар не найден.")
        return

    # Проверяем, есть ли доступные тексты для товара
    texts = item.get('texts', [item.get('text', '')])
    available_texts = [t for t in texts if t]
    
    if not available_texts:
        log_action("buy_failed", uid, f"Нет ключей для товара: {name}")
        await call.message.answer("❌ Нет ключей, ожидайте пополнение")
        return

    price = item['price']
    balance = users.get(uid, {}).get("balance", 0)

    if balance < price:
        log_action("buy_failed", uid, f"Недостаточно средств для {name} (нужно: {price}, есть: {balance})")
        await call.message.answer("❌ Недостаточно средств.")
        return
    
    # Выбираем случайный текст и удаляем его из списка
    selected_text = random.choice(available_texts)
    texts.remove(selected_text)
    
    # Обновляем товар (оставляем позицию, но без текстов)
    item['texts'] = texts
    
    if 'text' in item:
        del item['text']  # Удаляем старое поле text
    
    users[uid]["balance"] -= price
    save_data("users.json", users)
    save_data("products.json", products)
    
    log_action("purchase", uid, f"Купил {name} за {price}₽")
    await call.message.answer(f"✅ Вы купили *{name}*.\n\n📃 Ваш товар:\n`{selected_text}`", parse_mode="Markdown")

@dp.message(AdminStates.waiting_for_product_name)
async def get_product_name(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await state.update_data(name=message.text.strip())
        await message.answer("📝 Введите описание товара:")
        await state.set_state(AdminStates.waiting_for_product_description)

@dp.message(AdminStates.waiting_for_product_description)
async def get_product_description(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await state.update_data(description=message.text.strip())
        await message.answer("💰 Введите цену товара (только число):")
        await state.set_state(AdminStates.waiting_for_product_price)

@dp.message(AdminStates.waiting_for_product_price)
async def get_product_price(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        try:
            price = int(message.text.strip())
            await state.update_data(price=price)
            await message.answer("📄 Введите тексты товаров (каждый текст с новой строки):\n\n"
                               "Пример:\n"
                               "Ключ1: ABC123\n"
                               "Ключ2: DEF456\n"
                               "Ключ3: GHI789")
            await state.set_state(AdminStates.waiting_for_product_text)
        except ValueError:
            await message.answer("❌ Неверная цена. Введите только число:")

@dp.message(AdminStates.waiting_for_product_text)
async def add_product_final(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        data = await state.get_data()
        name = data['name']
        description = data['description']
        price = data['price']
        texts_input = message.text.strip()
        
        # Разделяем тексты по строкам (каждая строка = отдельный товар)
        texts = [text.strip() for text in texts_input.split('\n') if text.strip()]
        
        products[name] = {
            "description": description,
            "price": price,
            "texts": texts
        }
        save_data("products.json", products)
        
        log_action("add_product", message.from_user.id, f"Добавлен товар: {name} ({len(texts)} шт.)")
        
        await message.answer(f"✅ Товар '{name}' успешно добавлен!\n\n"
                           f"📦 Название: {name}\n"
                           f"📝 Описание: {description}\n"
                           f"💰 Цена: {price}₽\n"
                           f"📊 Количество: {len(texts)} шт.")
        await state.clear()

@dp.message(AdminStates.waiting_for_balance_amount)
async def add_balance_amount(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        try:
            amount = int(message.text.strip())
            data = await state.get_data()
            uid = data['selected_user_id']
            
            if uid not in users:
                users[uid] = {"balance": 0}
            
            old_balance = users[uid]["balance"]
            users[uid]["balance"] += amount
            new_balance = users[uid]["balance"]
            
            save_data("users.json", users)
            log_action("add_balance", message.from_user.id, f"Пополнил баланс {uid}: +{amount}₽ ({old_balance}₽ → {new_balance}₽)")
            
            # Уведомляем пользователя о пополнении баланса
            try:
                await bot.send_message(
                    chat_id=int(uid),
                    text=f"💰 Ваш баланс пополнен на {amount}₽!\n"
                         f"💳 Текущий баланс: {new_balance}₽"
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление пользователю {uid}: {e}")
            
            await message.answer(f"✅ Пользователю {uid} добавлено {amount}₽\n"
                               f"💳 Баланс: {old_balance}₽ → {new_balance}₽\n"
                               f"📨 Уведомление отправлено пользователю")
        except ValueError:
            await message.answer("❌ Неверная сумма. Введите только число:")
            return
        except Exception as e:
            await message.answer("❌ Произошла ошибка при пополнении баланса")
        await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
