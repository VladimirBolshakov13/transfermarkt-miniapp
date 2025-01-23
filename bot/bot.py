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

# Функция для получения случайного игрока из API Transfermarkt
async def fetch_random_player():
    random_player_id = random.randint(1, 10000)  # Предполагаем, что ID игрока лежит в диапазоне 1-10000
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/players/{random_player_id}/profile") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Ошибка: статус ответа {response.status}")
                    return None
        except Exception as e:
            print(f"Ошибка при обращении к API: {e}")
            return None

# Функция для получения достижений игрока
async def get_player_achievements(player_id):
    """Получить список достижений игрока по его ID."""
    async with aiohttp.ClientSession() as session:
        url = f"{API_URL}/players/{player_id}/achievements"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()  # Получаем данные в формате JSON
                    return data.get("achievements", [])  # Извлекаем достижения
                return []
        except Exception as e:
            print(f"Ошибка при обращении к API для получения достижений: {e}")
            return []

# Функция для обработки вопросов о достижениях игрока
async def handle_achievement_question(player_id, question):
    """Обрабатывает вопросы о достижениях игрока."""
    achievements = await get_player_achievements(player_id)
    
    if "золотой мяч" in question:
        for achievement in achievements:
            if achievement["title"] == "Winner Ballon d'Or":
                count = achievement["count"]
                seasons = ", ".join([detail["season"]["name"] for detail in achievement["details"]])
                return f"Да, он выиграл Золотой мяч {count} раз(а): {seasons}."
        return "Нет, он никогда не выигрывал Золотой мяч."
    
    if "лучший игрок fifa" in question:
        for achievement in achievements:
            if achievement["title"] == "The Best FIFA Men's Player":
                count = achievement["count"]
                seasons = ", ".join([detail["season"]["name"] for detail in achievement["details"]])
                return f"Да, он становился лучшим игроком FIFA {count} раз(а): {seasons}."
        return "Нет, он никогда не становился лучшим игроком FIFA."

    return "Я не уверен, о каком достижении идет речь."

# Функция для обработки вопросов о позиции игрока
async def handle_position_question(player_traits, question):
    """Обрабатывает вопросы о позиции игрока."""
    position = player_traits["position"]["main"].lower()
    
    if "вратарь" in question:
        return "Да" if position == "goalkeeper" else "Нет"
    if "защитник" in question:
        return "Да" if position == "defender" else "Нет"
    if "полузащитник" in question:
        return "Да" if position == "midfielder" else "Нет"
    if "нападающий" in question:
        return "Да" if position == "forward" else "Нет"
    
    return "Я не уверен, о какой позиции идет речь."

# Функция для старта игры
@router.message(Command("startgame"))
async def start_game(message: Message):
    user_id = message.from_user.id

    # Получаем информацию об одном случайном игроке
    player = await fetch_random_player()
    if not player:
        await message.answer("Не удалось загрузить игрока. Попробуйте позже.")
        return

    random_player_name = player["name"]
    
    # Запоминаем выбранного игрока для текущего пользователя
    games[user_id] = {
        "player_name": random_player_name,
        "player_id": player["id"],  # Сохраняем ID игрока
        "questions_asked": 0,
        "max_questions": 10,  # Количество вопросов, после которых игрок должен угадать
        "traits": player,  # Используем данные игрока из API
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
    player_id = game_data["player_id"]
    player_traits = game_data["traits"]  # Получаем данные игрока

    # Проверяем, не исчерпал ли игрок количество попыток
    if game_data["questions_asked"] >= game_data["max_questions"]:
        await message.answer(f"Вы исчерпали количество попыток. Игрок был {player_name}. Для начала новой игры используйте команду /startgame.")
        del games[user_id]  # Завершаем игру
        return

    # Приводим текст вопроса к нижнему регистру и убираем лишние пробелы
    question = message.text.strip().lower()

    # Проверяем, пытается ли пользователь угадать игрока
    if question.startswith("это ") and question.endswith("?"):
        guessed_player_name = question[4:-1]  # Извлекаем имя игрока
        if guessed_player_name.lower() == player_name.lower():
            await message.answer(f"🎉 Поздравляю! Вы угадали: {player_name}.")
            del games[user_id]  # Завершаем игру
            return
        else:
            await message.answer("Неверно, попробуйте ещё раз!")
            return

    # Обработка вопросов о позициях
    position_response = await handle_position_question(player_traits, question)
    if position_response != "Я не уверен, о какой позиции идет речь.":
        await message.answer(f"Ответ: {position_response}")
        game_data["questions_asked"] += 1
        return

    # Обработка вопросов о достижениях
    if "золотой мяч" in question or "лучший игрок fifa" in question:
        answer = await handle_achievement_question(player_id, question)
        await message.answer(f"Ответ: {answer}")
        game_data["questions_asked"] += 1
        return

    # Увеличиваем счетчик заданных вопросов
    game_data["questions_asked"] += 1

    await message.answer("Я не знаю ответа на этот вопрос, попробуйте задать другой.")

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
    guessed_player_name = message.text.split(" ", 1)[1].strip()
    if guessed_player_name.lower() == player_name.lower():
        await message.answer(f"🎉 Поздравляю! Вы угадали: {player_name}.")
        del games[user_id]  # Завершаем игру
    else:
        await message.answer("Неверно, попробуйте ещё раз!")

# Инфо о пользователе
@router.message(Command("info"))
async def info(message: Message):
    await message.answer("Эта игра позволяет вам угадать футбольного игрока, задавая вопросы.")

# Подключаем маршрутизатор
dp.include_router(router)

# Запуск бота без executor
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
