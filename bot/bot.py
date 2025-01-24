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
incorrect_attempts = 0
player_name = ""

# Функция для получения случайного игрока из API Transfermarkt
async def fetch_random_player():
    try:
        # Загружаем список игроков
        with open('ballon_dor_winners.json', 'r', encoding='utf-8') as file:
            players = json.load(file)
    except Exception as e:
        print(f"Ошибка при загрузке файла: {e}")
        return "Ошибка при загрузке списка игроков."

    random_player_name = random.choice(players)['name']
    print(f"Выбранный игрок: {random_player_name}")

    async with aiohttp.ClientSession() as session:
        try:
            # Поиск игрока по имени
            async with session.get(f"{API_URL}/players/search/{random_player_name}") as response:
                if response.status == 200:
                    search_results = await response.json()
                    if search_results['results']:
                        player_data = search_results['results'][0]
                        player_id = player_data['id']
                        
                        # Запрос профиля игрока
                        async with session.get(f"{API_URL}/players/{player_id}/profile") as profile_response:
                            if profile_response.status == 200:
                                profile_data = await profile_response.json()
                                
                                # Проверяем параметры игрока
                                club_info = profile_data.get('club')
                                is_retired = profile_data.get('isRetired', False)
                                position = profile_data.get('position')
                                citizenship = profile_data.get('citizenship')
                                age = profile_data.get('age')

                                print(f"Игрок {random_player_name} (ID: {player_id}):")
                                print(f"  Завершил карьеру: {is_retired}")
                                print(f"  Позиция: {position}")
                                print(f"  Гражданство: {citizenship}")
                                print(f"  Возраст: {age}")

                                if club_info:
                                    club_name = club_info.get('name')
                                    club_id = club_info.get('id')
                                    print(f"  Клуб: {club_name} (ID: {club_id})")
                                else:
                                    print("  Игрок не имеет клуба.")

                                # Получаем достижения игрока
                                achievements = await get_player_achievements(player_id)
                                achievement_titles = ["World Cup winner", "Champions League winner", "Golden Boot winner (Europe)", "Winner Ballon d'Or"]
                                
                                for title in achievement_titles:
                                    if any(ach["title"] == title for ach in achievements):
                                        print(f"  Игрок выиграл: {title}")

                                # Запрос информации о клубе
                                if club_info:
                                    club_id = club_info.get('id')
                                    country_name = await get_player_club_country(club_id)
                                    if country_name:
                                        print(f"  Клуб находится в стране: {country_name}")
                                else:
                                    print("  Игрок не имеет клуба, поэтому информация о стране недоступна.")

                                return profile_data  # Возвращаем данные профиля игрока
                            else:
                                print(f"Ошибка профиля: статус {profile_response.status}")
                                return "Не удалось загрузить профиль игрока."
                    else:
                        print(f"Игрок {random_player_name} не найден.")
                        return "Игрок не найден."
                else:
                    print(f"Ошибка поиска игрока: статус {response.status}")
                    return "Не удалось загрузить игрока."
        except Exception as e:
            print(f"Ошибка API: {e}")
            return "Произошла ошибка при обращении к API."

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

    # Приводим вопрос к нижнему регистру для удобства обработки
    question = question.lower()

    # Проверка на "Лигу чемпионов"
    if "лигу чемпионов" in question or "лч" in question or "выиграл лч" in question:
        for achievement in achievements:
            if achievement["title"] == "Champions League winner":
                count = achievement["count"]
                seasons = ", ".join([detail["season"]["name"] for detail in achievement["details"]])
                return f"Да, он выиграл Лигу чемпионов {count} раз(а): {seasons}."
        return "Нет, он никогда не выигрывал Лигу чемпионов."

    # Проверка на "золотой мяч"
    if "золотой мяч" in question or "зм" in question or "выиграл золотой мяч" in question:
        for achievement in achievements:
            if achievement["title"] == "Winner Ballon d'Or":
                count = achievement["count"]
                seasons = ", ".join([detail["season"]["name"] for detail in achievement["details"]])
                return f"Да, он выиграл Золотой мяч {count} раз(а): {seasons}."
        return "Нет, он никогда не выигрывал Золотой мяч."

    # Проверка на "Чемпионат мира"
    if "чемпионат мира" in question or "чм" in question or "выиграл чм" in question:
        for achievement in achievements:
            if achievement["title"] == "World Cup winner":
                count = achievement["count"]
                seasons = ", ".join([detail["season"]["name"] for detail in achievement["details"]])
                return f"Да, он выиграл Чемпионат мира {count} раз(а): {seasons}."
        return "Нет, он никогда не выигрывал Чемпионат мира."

    # Проверка на "золотую бутсу"
    if "золотую бутсу" in question or "выиграл золотую бутсу" in question:
        for achievement in achievements:
            if achievement["title"] == "Golden Boot winner (Europe)":
                count = achievement["count"]
                seasons = ", ".join([detail["season"]["name"] for detail in achievement["details"]])
                return f"Да, он выиграл Золотую бутсу {count} раз(а): {seasons}."
        return "Нет, он никогда не выигрывал Золотую бутсу."

    # Ответ на запрос о подсказке
    if "подсказка" in question:
        player_achievements = []
        for achievement in achievements:
            player_achievements.append(achievement["title"])
        return f"Игрок имеет следующие достижения: {', '.join(player_achievements)}."

    return "Я не уверен, о каком достижении идет речь."

# Функция для обработки вопросов о позиции игрока
async def handle_position_question(player_traits, question):
    global incorrect_attempts, player_name  # Используем глобальные переменные для подсчета неправильных ответов и имени игрока

    # Проверяем наличие позиции в данных
    if "position" not in player_traits or "main" not in player_traits["position"]:
        return "Информация о позиции отсутствует."  # Обработка случая, когда позиция отсутствует

    position = player_traits["position"]["main"].lower()
    print(f"Полученная позиция игрока: {position}")  # Логируем полученную позицию

    # Если имя игрока еще не было задано, можем его установить здесь
    if not player_name:
        player_name = player_traits["name"]  # Предположим, что имя хранится в player_traits
        print(f"Имя загаданного игрока: {player_name}")  # Логируем имя загаданного игрока

    if "позиция" in question:
        return f"Он играет на позиции: {position.capitalize()}."  # Отправляем конкретную позицию

    # Вратари
    if "вратарь" in question:
        if position == "goalkeeper":
            incorrect_attempts = 0  # Сброс счетчика при правильном ответе
            return "Да"
        else:
            incorrect_attempts += 1

    # Защитники
    if "защитник" in question:
        if position in ["centre-back", "full-back", "wing-back"]:
            incorrect_attempts = 0
            return "Да"
        else:
            incorrect_attempts += 1

    # Полузащитники
    if "полузащитник" in question:
        if position in ["central midfielder", "attacking midfielder", "defensive midfielder", "wide midfielder"]:
            incorrect_attempts = 0
            return "Да"
        else:
            incorrect_attempts += 1

    # Нападающие
    if "нападающий" in question:
        if position in ["striker", "left winger", "right winger", "second striker", "centre-forward"]:
            incorrect_attempts = 0
            return "Да"
        else:
            incorrect_attempts += 1

    # Если неправильные ответы достигли 3, отправляем позицию игрока
    if incorrect_attempts >= 3:
        print(f"Загаданный игрок: {player_name}")  # Выводим имя загаданного игрока в терминал
        incorrect_attempts = 0  # Сбрасываем счетчик
        return f"Увы, вы не угадали. Он играет на позиции: {position.capitalize()}."  # Отправляем позицию игрока

    return "Нет"

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

    # Проверяем, если это предположение
    if question.startswith("это ") and question.endswith("?"):
        guessed_player_name = question[4:-1].strip()
        if guessed_player_name.lower() == player_name.lower():
            await message.answer(f"🎉 Поздравляю! Вы угадали: {player_name}.")
            del games[user_id]
            return
        else:
            await message.answer("Неверно, попробуйте ещё раз!")
            return

    # Обработка вопроса о позиции
    if "позиция" in question:
        position_response = await handle_position_question(player_traits, question)
        await message.answer(f"Ответ: {position_response}")
        game_data["questions_asked"] += 1
        return

    # Если вопрос касается достижений
    if "золотой мяч" in question or "лучший игрок fifa" in question:
        answer = await handle_achievement_question(player_id, question)
        await message.answer(f"Ответ: {answer}")
        game_data["questions_asked"] += 1
        return

    # Если вопрос касается лиги игрока
    league_response = await handle_league_question(player_id, question)
    if league_response:
        await message.answer(f"Ответ: {league_response}")
        game_data["questions_asked"] += 1
        return

    # Общее сообщение при нераспознанном вопросе
    game_data["questions_asked"] += 1
    await message.answer("Я не знаю ответа на этот вопрос, попробуйте задать другой.")

async def handle_age_question(player_traits, question):
    age = player_traits.get("age")
    if not age:
        return "Информация о возрасте игрока отсутствует."
    
    if "больше" in question:
        try:
            target_age = int(question.split("больше")[1].strip().split()[0])
            return "Да" if age > target_age else "Нет"
        except ValueError:
            return "Я не понял возраст в вопросе."
    
    if "меньше" in question:
        try:
            target_age = int(question.split("меньше")[1].strip().split()[0])
            return "Да" if age < target_age else "Нет"
        except ValueError:
            return "Я не понял возраст в вопросе."
    
    return "Я не знаю, что ответить на этот вопрос."

async def handle_nationality_question(player_traits, question):
    nationality = player_traits.get("nationality", {}).get("name", "").lower()
    if not nationality:
        return "Информация о национальности игрока отсутствует."
    
    if nationality in question:
        return "Да"
    return "Нет"

async def handle_club_question(player_traits, question):
    club = player_traits.get("club", {}).get("name", "").lower()
    if not club:
        return "Информация о клубе игрока отсутствует."
    
    if club in question.lower():
        return "Да"
    return "Нет"

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
