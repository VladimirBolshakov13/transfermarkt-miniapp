import os
import random
import aiohttp
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

# Загружаем токен из .env
TOKEN = os.getenv("TOKEN")
API_URL = "http://127.0.0.1:8000"

# Создаем экземпляры бота, диспетчера и маршрутизатора
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# Хранение данных о текущей игре
games = {}

# Список характеристик игроков, можно добавить больше
player_traits = {
    "Messi": {
        "is_alive": True,
        "is_playing_now": True,
        "team": "PSG",
        "is_playing_in_top5_leagues": True,
        "position": "forward",
        "clubs": ["Barcelona", "PSG"],
        "goals_scored": 700,
        "matches_played": 800,
        "trophies": ["Ballon d'Or", "Champions League", "La Liga"],
        "health_status": "Excellent",
        "on_transfer": False,
        "birthdate": "1987-06-24",
        "national_team": "Argentina",
        "national_team_matches": 150,
        "national_team_goals": 80,
        "market_value": 100000000,
        "highest_valuation_club": "Barcelona"
    },
    # Добавьте другие игроки
}

# Функция для старта игры
@router.message(Command("startgame"))
async def start_game(message: Message):
    user_id = message.from_user.id

    # Выбираем случайного игрока
    random_player_name = random.choice(list(player_traits.keys()))

    # Запоминаем выбранного игрока для текущего пользователя
    games[user_id] = {
        "player_name": random_player_name,
        "questions_asked": 0,
        "max_questions": 5,  # Количество вопросов, после которых игрок должен угадать
        "traits": player_traits[random_player_name],
    }

    # Сообщаем игроку, что игра началась
    await message.answer(f"Игра началась! Задавайте вопросы, на которые я буду отвечать 'да' или 'нет'. Попробуйте угадать, кто это!\nУ вас {games[user_id]['max_questions']} попыток!")

# Функция для ответа на вопросы
@router.message()
async def ask_question(message: Message):
    user_id = message.from_user.id

    # Проверяем, есть ли активная игра
    if user_id not in games:
        await message.answer("Сначала начните игру, используя команду /startgame.")
        return

    game_data = games[user_id]
    player_name = game_data["player_name"]
    traits = game_data["traits"]

    # Проверяем, не исчерпал ли игрок количество попыток
    if game_data["questions_asked"] >= game_data["max_questions"]:
        await message.answer(f"Вы исчерпали количество попыток. Игрок был {player_name}. Для начала новой игры используйте команду /startgame.")
        del games[user_id]  # Завершаем игру
        return

    # Приводим текст вопроса к нижнему регистру и убираем лишние пробелы
    question = message.text.strip().lower()

    # Задаем вопросы на основе характеристик игрока
    if "живой" in question or "играет до сих пор" in question:
        answer = "да" if traits["is_alive"] else "нет"
    elif "играет" in question and "команде" in question:
        answer = f"Он играет в {traits['team']}." if traits["is_playing_now"] else "Он больше не играет."
    elif "топ 5 лигах" in question:
        answer = "да" if traits["is_playing_in_top5_leagues"] else "нет"
    elif "нападающий" in question:
        answer = "да" if traits["position"] == "forward" else "нет"
    elif "защитник" in question:
        answer = "да" if traits["position"] == "defender" else "нет"
    elif "полузащитник" in question:
        answer = "да" if traits["position"] == "midfielder" else "нет"
    elif "вратарь" in question:
        answer = "да" if traits["position"] == "goalkeeper" else "нет"
    elif "клубах" in question:
        answer = f"Он играл в {', '.join(traits['clubs'])}."
    elif "голов" in question:
        answer = f"Он забил {traits['goals_scored']} голов за карьеру."
    elif "матчей" in question:
        answer = f"Он сыграл {traits['matches_played']} матчей."
    elif "титулы" in question:
        answer = f"Он выиграл титулы: {', '.join(traits['trophies'])}."
    elif "состояние здоровья" in question:
        answer = f"Его состояние здоровья: {traits['health_status']}."
    elif "на трансфере" in question:
        answer = "да" if traits["on_transfer"] else "нет"
    elif "возраст" in question:
        age = 2025 - int(traits["birthdate"].split("-")[0])  # Предполагаем, что текущий год 2025
        answer = f"Ему {age} лет."
    elif "родился" in question:
        answer = f"Он родился {traits['birthdate']}."
    elif "карьеры" in question:
        career_start = 2000  # Пример, можно подставить реальную дату начала карьеры
        answer = f"Он начал свою карьеру в футболе в {career_start} году."
    elif "национальной сборной" in question:
        answer = f"Он играет за {traits['national_team']}."
    elif "матчей за страну" in question:
        answer = f"Он сыграл {traits['national_team_matches']} матчей за свою страну."
    elif "голы за сборную" in question:
        answer = f"Он забил {traits['national_team_goals']} голов за сборную."
    elif "рыночная стоимость" in question:
        answer = f"Его рыночная стоимость: €{traits['market_value']}."
    elif "клубе выше всего" in question:
        answer = f"Его высшая оценка была в клубе {traits['highest_valuation_club']}."
    else:
        answer = "Я не понял вопрос, задайте что-то другое."

    # Увеличиваем счетчик заданных вопросов
    game_data["questions_asked"] += 1

    await message.answer(f"Ответ: {answer}")

# Функция для угадывания игрока
@router.message(Command("guess"))
async def guess_player(message: Message):
    user_id = message.from_user.id

    # Проверяем, есть ли активная игра
    if user_id not in games:
        await message.answer("Сначала начните игру, используя команду /startgame.")
        return

    game_data = games[user_id]
    player_name = game_data["player_name"]

    # Если игрок думает, что угадал
    if message.text.lower() == player_name.lower():
        await message.answer(f"🎉 Поздравляю! Вы угадали: {player_name}.")
        del games[user_id]  # Завершаем игру
    else:
        await message.answer("Неверно, попробуйте ещё раз!")

async def main():
    # Регистрируем маршруты
    dp.include_router(router)

    # Удаляем старые вебхуки, чтобы избежать конфликтов
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
