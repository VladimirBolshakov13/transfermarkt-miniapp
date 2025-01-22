import os
import random
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from transfermarkt import Transfermarkt

# Инициализация Transfermarkt API
tm = Transfermarkt()

# Глобальная переменная для текущего игрока
current_player = None

# Получение данных об игроке
def get_player_data(player_name):
    try:
        player = tm.search_player(player_name)[0]
        details = tm.get_player(player['id'])
        return {
            "name": details["name"],
            "position": details["main_position"],
            "club": details["current_club"],
            "nation": details["nationality"],
            "value": details["market_value"],
            "age": details["age"],
        }
    except Exception as e:
        return None

# Команда /start
def start(update: Update, context: CallbackContext):
    global current_player
    player_name = random.choice(["Lionel Messi", "Cristiano Ronaldo", "Zinedine Zidane"])  # Пример имен
    current_player = get_player_data(player_name)

    if current_player:
        update.message.reply_text("Я загадал футболиста! Задавайте вопросы, чтобы угадать его.")
    else:
        update.message.reply_text("Ошибка при получении данных. Попробуйте снова!")

# Обработка вопросов пользователя
def handle_question(update: Update, context: CallbackContext):
    global current_player
    if not current_player:
        update.message.reply_text("Игра не начата. Напишите /start, чтобы начать!")
        return

    question = update.message.text.lower()

    # Ответы на вопросы
    if "позиция" in question:
        answer = f"Его позиция: {current_player['position']}."
    elif "клуб" in question:
        answer = f"Его клуб: {current_player['club']}."
    elif "нация" in question or "страна" in question:
        answer = f"Его национальность: {current_player['nation']}."
    elif "возраст" in question:
        answer = f"Ему {current_player['age']} лет."
    elif "стоимость" in question or "ценность" in question:
        answer = f"Его рыночная стоимость: {current_player['value']}."
    elif "это" in question:  # Попытка угадать
        guess = question.replace("это", "").strip()
        if guess.lower() == current_player["name"].lower():
            answer = f"Поздравляю, вы угадали! Это {current_player['name']}!"
            current_player = None
        else:
            answer = "Нет, это не он. Продолжайте спрашивать!"
    else:
        answer = "Я не понял вопрос. Задайте что-то вроде: 'Его позиция?', 'Его клуб?', 'Его национальность?'."

    update.message.reply_text(answer)

# Запуск бота
def main():
    # Укажите токен вашего Telegram-бота
    token = os.getenv('TOKEN')

    # Создание Updater и Dispatcher
    updater = Updater(token)
    dispatcher = updater.dispatcher

    # Обработчики команд и сообщений
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_question))

    # Запуск бота
    updater.start_polling()
    print("Бот запущен. Нажмите Ctrl+C для завершения работы.")
    updater.idle()
    
if __name__ == "__main__":
    main()
