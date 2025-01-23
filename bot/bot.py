import os
import json
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
    # Загружаем список футболистов из файла
    try:
        with open('ballon_dor_winners.json', 'r', encoding='utf-8') as file:
            players = json.load(file)
    except Exception as e:
        print(f"Ошибка при загрузке файла: {e}")
        return None

    # Случайным образом выбираем игрока из списка
    random_player_name = random.choice(players)['name']

    async with aiohttp.ClientSession() as session:
        try:
            # Поиск игрока по имени
            async with session.get(f"{API_URL}/players/search/{random_player_name}") as response:
                if response.status == 200:
                    search_results = await response.json()

                    if search_results['results']:
                        # Выбираем первого найденного игрока
                        player_data = search_results['results'][0]
                        player_id = player_data['id']
                        
                        # Запрашиваем профиль игрока по ID
                        async with session.get(f"{API_URL}/players/{player_id}/profile") as profile_response:
                            if profile_response.status == 200:
                                return await profile_response.json()
                            else:
                                print(f"Ошибка при получении профиля: статус ответа {profile_response.status}")
                                profile_content = await profile_response.text()
                                print(f"Содержание ошибки: {profile_content}")
                    else:
                        print(f"Игрок {random_player_name} не найден в результате поиска.")
                else:
                    print(f"Ошибка поиска игрока: статус ответа {response.status}")
                    search_content = await response.text()
                    print(f"Содержание ошибки: {search_content}")
        except Exception as e:
            print(f"Ошибка при обращении к API: {e}")

    return None

# Функция для получения достижений игрока
async def get_player_achievements(player_id):
    async with aiohttp.ClientSession() as session:
        url = f"{API_URL}/players/{player_id}/achievements"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("achievements", [])
                return []
        except Exception as e:
            print(f"Ошибка при обращении к API для получения достижений: {e}")
            return []

# Функция для получения страны клуба игрока
async def get_player_club_country(player_id):
    async with aiohttp.ClientSession() as session:
        # Получаем профиль игрока, чтобы узнать его клуб
        profile_url = f"{API_URL}/players/{player_id}/profile"
        try:
            async with session.get(profile_url) as response:
                if response.status == 200:
                    player_data = await response.json()
                    club_name = player_data.get("club", {}).get("name")  # Получаем имя клуба игрока
                    
                    if club_name:
                        # Теперь ищем клуб по имени
                        club_search_url = f"{API_URL}/clubs/search/{club_name}"
                        async with session.get(club_search_url) as club_response:
                            if club_response.status == 200:
                                club_data = await club_response.json()
                                if club_data["results"]:
                                    return club_data["results"][0]["country"]  # Возвращаем страну клуба
                return None
        except Exception as e:
            print(f"Ошибка при обращении к API для получения страны клуба: {e}")
            return None

# Функция для обработки вопросов о достижениях игрока
async def handle_achievement_question(player_id, question):
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

# Функция для обработки вопросов о лиге игрока
async def handle_league_question(player_id, question):
    country = await get_player_club_country(player_id)
    
    if country:
        if "в лиге" in question:
            return f"Игрок выступает в лиге страны: {country}."
        return f"Игрок играет в {country}."
    
    return "Я не знаю, в какой лиге играет этот игрок."

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
        "player_id": player["id"],
        "questions_asked": 0,
        "max_questions": 10,
        "traits": player,
    }

    await message.answer(f"Игра началась! Задавайте вопросы, на которые я буду отвечать 'да' или 'нет'. Попробуйте угадать, кто это!\nУ вас {games[user_id]['max_questions']} попыток!")

# Функция для ответа на вопросы
@router.message()
async def ask_question(message: Message):
    user_id = message.from_user.id

    if user_id not in games:
        await message.answer("Сначала начните игру, используя команду /startgame.")
        return

    game_data = games[user_id]
    player_name = game_data["player_name"]
    player_id = game_data["player_id"]
    player_traits = game_data["traits"]

    if game_data["questions_asked"] >= game_data["max_questions"]:
        await message.answer(f"Вы исчерпали количество попыток. Игрок был {player_name}. Для начала новой игры используйте команду /startgame.")
        del games[user_id]
        return

    question = message.text.strip().lower()

    if question.startswith("это ") and question.endswith("?"):
        guessed_player_name = question[4:-1]
        if guessed_player_name.lower() == player_name.lower():
            await message.answer(f"🎉 Поздравляю! Вы угадали: {player_name}.")
            del games[user_id]
            return
        else:
            await message.answer("Неверно, попробуйте ещё раз!")
            return

    position_response = await handle_position_question(player_traits, question)
    if position_response != "Я не уверен, о какой позиции идет речь.":
        await message.answer(f"Ответ: {position_response}")
        game_data["questions_asked"] += 1
        return

    if "золотой мяч" in question or "лучший игрок fifa" in question:
        answer = await handle_achievement_question(player_id, question)
        await message.answer(f"Ответ: {answer}")
        game_data["questions_asked"] += 1
        return

    league_response = await handle_league_question(player_id, question)
    if league_response:
        await message.answer(f"Ответ: {league_response}")
        game_data["questions_asked"] += 1
        return

    game_data["questions_asked"] += 1

    await message.answer("Я не знаю ответа на этот вопрос, попробуйте задать другой.")

# Функция для угадывания игрока
@router.message(Command("guess"))
async def guess_player(message: Message):
    user_id = message.from_user.id

    if user_id not in games:
        await message.answer("Сначала начните игру, используя команду /startgame.")
        return

    game_data = games[user_id]
    player_name = game_data["player_name"]

    guessed_player_name = message.text.split(" ", 1)[1].strip()
    if guessed_player_name.lower() == player_name.lower():
        await message.answer(f"🎉 Поздравляю! Вы угадали: {player_name}.")
        del games[user_id]
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
