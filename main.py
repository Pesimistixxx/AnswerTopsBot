import telebot
import os
import random
import string
from dotenv import load_dotenv
from telebot import types


load_dotenv()

lobby_data = {}
input_states = {}
top_states = {}
question_states = {}
user_lobby_data = {}
user_username = {}

with open('sponsors.txt', 'r') as file:
    sponsors = [line.strip() for line in file]

BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)


def get_user_name(user_id):
    if user_id.username:
        username = f"@{user_id.username}"
    else:
        username = f"{user_id.first_name}"
    return username


@bot.message_handler(['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton("🎮 Создать лобби", callback_data='/create'),
        types.InlineKeyboardButton("❓ Правила игры", callback_data='/info'),
        types.InlineKeyboardButton("👥 Присоединиться", callback_data='/join')
    )

    bot.send_message(
        message.chat.id,
        "Добро пожаловать в бот для игры 'Топросы'! 🎲\n"
        "Выберите действие:",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data in ['/create', '/info', '/join'])
def handle_callback(call):
    if call.data == '/create':
        create_lobby(call.message)
    elif call.data == '/join':
        join_lobby(call.message)
    elif call.data == '/info':
        info(call.message)

    bot.answer_callback_query(call.id)


@bot.message_handler(['info', 'help'])
def info(message):
    user_id = message.chat.id
    bot.send_message(user_id, """
    Бот для игры «Топросы»
В чем суть игры? Есть 2 игрока и 1 ведущий,
а также список общих знакомых (5 человек) и 1 спонсор шоу(какая-то популярная личность).
Ведущий задает пользователям либо одинаковый вопрос, либо разные, вопрос должен быть построен так,
чтобы можно расставить людей в порядке топа (Например, кто из этих людей самый добрый).
Участники составляют топ людей и меняются ими, задача игры догадаться был ли у 2 участников
одинаковый вопрос или разные, ведущий может делать игру сложнее задавая максимально
близкие, но разные вопросы, так и легче задавая максимально очевидные вопросы.
Непонятно? По ходу игры разберетесь, удачи!!
    """)


@bot.message_handler(['create'])
def create_lobby(message):
    user_id = message.chat.id
    user_username[user_id] = get_user_name(message.chat)
    if user_id in user_lobby_data:
        bot.send_message(user_id, "Вы уже в лобби! Сначала выйдите из текущего (/leave).")
        return

    lobby_id = ''.join(random.choices(string.ascii_uppercase, k=4))
    while lobby_id in lobby_data:
        lobby_id = ''.join(random.choices(string.ascii_uppercase, k=4))

    lobby_data[lobby_id] = {'creator': user_id,
                            'users': [user_id],
                            'active': False}
    user_lobby_data[user_id] = lobby_id

    bot.send_message(user_id, f'Отлично, лобби создано, код лобби {lobby_id}'
                              f' отправь его друзьям, чтобы они смогли войти')


@bot.message_handler(['leave'])
def leave_lobby(message):
    user_id = message.chat.id
    if user_id not in user_lobby_data:
        bot.send_message(user_id, "Вы не находитесь в лобби, войдите в существуещее лобби (/join)"
                                  " или создайте свое (/create).")
        return

    lobby_id = user_lobby_data[user_id]
    lobby = lobby_data[lobby_id]
    lobby['users'].remove(user_id)

    del user_lobby_data[user_id]

    if len(lobby['users']) == 0:
        del lobby_data[lobby_id]
        bot.send_message(user_id, f'Вы вышли из лобби {lobby_id}, лобби удалено')
    else:
        bot.send_message(user_id, "Вы вышли из лобби.")
        lobby["active"] = False

        for user in lobby_data[lobby_id]['users'][:]:
            bot.send_message(user, f'Участник {user_username[user]} вышел, игра завершена')
            lobby['users'].remove(user)
            del user_lobby_data[user]


@bot.message_handler(['join'])
def join_lobby(message):
    user_id = message.chat.id
    user_username[user_id] = get_user_name(message.chat)

    if user_id in user_lobby_data:
        bot.send_message(user_id, "Вы уже в лобби! Сначала выйдите из текущего (/leave)")
        return

    user_code = bot.send_message(user_id, "Введи код лобби (4 буквы)")
    bot.register_next_step_handler(user_code, check_lobby)


def check_lobby(message):
    user_id = message.chat.id

    try:
        if message.text.startswith('/'):
            return
        user_code = message.text.strip().upper()
    except AttributeError:
        msg = bot.send_message(user_id, "Неподходящее слово Пожалуйста, введите слово")
        bot.register_next_step_handler(msg, check_lobby)
        return

    lobby = lobby_data.get(user_code)
    if not lobby:
        msg = bot.send_message(user_id, "Лобби не найдено! Проверьте код.")
        bot.register_next_step_handler(msg, check_lobby)
        return

    if len(lobby['users']) >= 3:
        msg = bot.send_message(user_id, "Лобби уже заполнено! Найдите другое лобби")
        bot.register_next_step_handler(msg, check_lobby)
        return

    lobby['users'].append(user_id)
    user_lobby_data[user_id] = user_code
    bot.send_message(user_id, f'Вы вошли в лобби {user_code}! Количество участников {len(lobby['users'])}/3')
    for other_user in [user for user in lobby['users'] if user != user_id]:
        bot.send_message(other_user, f'{user_username[user_id]} зашел в лобби, {len(lobby['users'])}/3')
    if len(lobby['users']) == 3:
        lobby['active'] = True
        for user in lobby['users']:
            bot.send_message(user, 'Лобби наполнилось, игра начинается')
            bot.send_message(user, 'azber.ru - лучший сайт на планете Сатурн\n'
                                   '@WordleCrackerBot - для абсолютов Wordle')
        start_game(user_code)


def start_game(lobby_id):
    lobby = lobby_data[lobby_id]
    host = lobby['creator']
    players = [user for user in lobby['users'] if user != host]

    for user in lobby['users']:
        bot.send_message(user, f"Ведущий: {user_username[host]}")
        bot.send_message(user, f"Игроки: {[user_username[player] for player in players]}")

    input_states[host] = {
        'lobby_id': lobby_id,
        'step': 0,
        'players': []
    }

    bot.send_message(host, "Введите 5 человек, которых знают игроки(Отдельными сообщениями)")
    bot.send_message(host, "Введите 1 человека:")


@bot.message_handler(func=lambda message: message.from_user.id in input_states and not message.text.startswith('/'))
def handle_host_players_inputs(message):
    user_id = message.chat.id
    state = input_states[user_id]
    try:
        user_input = message.text.strip()
    except AttributeError:
        bot.send_message(user_id, "Неверное сообщение, введите текст!")
        return

    if not user_input:
        bot.send_message(user_id, "Имя не может быть пустым! Попробуйте еще раз:")
        return

    state['players'].append(user_input)
    state['step'] += 1

    if state['step'] >= 5:
        markup = types.InlineKeyboardMarkup(row_width=2)
        yes_btn = types.InlineKeyboardButton('Да, верно', callback_data="players_correct")
        no_btn = types.InlineKeyboardButton('Нет, выбрать заново', callback_data="players_incorrect")
        markup.add(yes_btn, no_btn)

        bot.send_message(user_id, "\n".join([
            "Список персонажей:",
            *[f"{i + 1}. {name}" for i, name in enumerate(state['players'])]
        ]), reply_markup=markup)

    else:
        bot.send_message(user_id, f"Введите {state['step'] + 1} имя:")


@bot.callback_query_handler(func=lambda call: call.data in ['players_correct', 'players_incorrect'])
def confirm_players(call):
    user_id = call.message.chat.id
    state = input_states[user_id]
    lobby_id = state['lobby_id']

    bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=call.message.message_id,
        reply_markup=None
    )

    if call.data == 'players_correct':
        bot.answer_callback_query(call.id, "Отлично! Результаты подтверждены")
        bot.send_message(user_id, "Отлично! Результаты подтверждены")
        lobby_data[lobby_id]['selectable_players'] = state['players']
        del input_states[user_id]

        questions_creating(lobby_id)

    elif call.data == 'players_incorrect':
        bot.answer_callback_query(call.id, "Хорошо, можешь выбрать людей заново")
        input_states[user_id] = {
            'lobby_id': lobby_id,
            'step': 0,
            'players': []
        }
        bot.send_message(user_id, 'Введите 1 человека')
    else:
        bot.answer_callback_query(call.id, "Ошибка состояния. Начните заново командой /start")


def questions_creating(lobby_id):
    lobby = lobby_data[lobby_id]
    host = lobby['creator']
    players = [user for user in lobby['users'] if user != host]
    sponsor = random.choice(sponsors)

    for user in lobby['users']:
        bot.send_message(user, "\n".join([
            "Список персонажей:",
            *[f"{i + 1}. {name}" for i, name in enumerate(lobby['selectable_players'])]
        ]))
        bot.send_message(user, 'А также спонсор шоу...')
        bot.send_message(user, sponsor)
    lobby['selectable_players'].append(sponsor)

    question_states[host] = {
        'lobby_id': lobby_id,
        'step': 0,
        'players': players
    }

    bot.send_message(host, f'Введи вопрос для игрока {user_username[players[0]]}')


@bot.message_handler(func=lambda message: message.from_user.id in question_states and not message.text.startswith('/'))
def handle_question_input(message):
    host = message.from_user.id
    state = question_states[host]
    lobby_id = state['lobby_id']
    players = state['players']
    step = state['step']

    if not message.text:
        bot.send_message(host, 'Ошибка, введи текст')

    if step == 0:
        lobby = lobby_data[lobby_id]
        state['step'] += 1
        lobby['questions'] = [message.text]
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        btn_same = types.KeyboardButton('Установить одинаковые вопросы')
        markup.add(btn_same)

        bot.send_message(
            host,
            f'Введи вопрос для игрока {user_username[players[1]]} или оставь предыдущий вопрос',
            reply_markup=markup
        )

    elif step == 1:
        lobby = lobby_data[lobby_id]
        if message.text == 'Установить одинаковые вопросы':
            lobby['questions'].append(lobby['questions'][0])
        else:
            lobby['questions'].append(message.text)
        bot.send_message(host, "Вопросы сохранены! Игроки начали составлять свой топ", reply_markup=types.ReplyKeyboardRemove())

        for i, user in enumerate(players):
            top_states[user] = {
                'lobby_id': lobby_id,
                'step': 0,
                'top_people': []
            }
            bot.send_message(user, f'Можешь начинать вводить свой топ на вопрос: {lobby['questions'][i]}')
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(
                types.KeyboardButton(lobby['selectable_players'][0]),
                types.KeyboardButton(lobby['selectable_players'][1]),
                types.KeyboardButton(lobby['selectable_players'][2])
            )
            markup.add(
                types.KeyboardButton(lobby['selectable_players'][3]),
                types.KeyboardButton(lobby['selectable_players'][4]),
                types.KeyboardButton(lobby['selectable_players'][5])
            )
            bot.send_message(user, '1 место', reply_markup=markup)
        del question_states[host]


@bot.message_handler(func=lambda message: message.from_user.id in top_states and not message.text.startswith('/'))
def handle_user_top(message):
    user_id = message.from_user.id
    state = top_states[user_id]
    lobby_id = state['lobby_id']
    lobby = lobby_data[lobby_id]
    selectable_players = lobby['selectable_players']

    if message.text not in selectable_players:
        bot.send_message(message.from_user.id, 'Неправильно выбран человек, попробуй ещё раз')
        active_players = [player for player in selectable_players if player not in top_states[user_id]['top_people']]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i in range(0, len(active_players), 3):
            row_buttons = active_players[i:i + 3]
            markup.add(*[types.KeyboardButton(btn) for btn in row_buttons])
        bot.send_message(user_id, f"Выбери {state['step'] + 1} место", reply_markup=markup)
        return

    top_states[user_id]['top_people'].append(message.text)

    if state['step'] >= 5:
        bot.send_message(user_id, f"Все места выбраны", reply_markup=types.ReplyKeyboardRemove())
        markup = types.InlineKeyboardMarkup(row_width=2)
        yes_btn = types.InlineKeyboardButton('Да, верно', callback_data="top_correct")
        no_btn = types.InlineKeyboardButton('Нет, выбрать заново', callback_data="top_incorrect")
        markup.add(yes_btn, no_btn)

        bot.send_message(user_id, "\n".join([
            "Топ персонажей:",
            *[f"{i + 1}. {name}" for i, name in enumerate(top_states[user_id]['top_people'])]
        ]))
        bot.send_message(user_id, 'Все верно?', reply_markup=markup)
    else:
        top_states[user_id]['step'] += 1
        active_players = [player for player in selectable_players if player not in top_states[user_id]['top_people']]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i in range(0, len(active_players), 3):
            row_buttons = active_players[i:i + 3]
            markup.add(*[types.KeyboardButton(btn) for btn in row_buttons])
        bot.send_message(user_id, f"{state['step']} место выбрано, теперь выбери {state['step'] + 1} место",
                         reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ['top_correct', 'top_incorrect'])
def confirm_top(call):
    user_id = call.message.chat.id
    state = top_states[user_id]
    lobby_id = state['lobby_id']
    lobby = lobby_data[lobby_id]
    host = lobby['creator']
    players = [user for user in lobby['users'] if user != host]

    bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=call.message.message_id,
        reply_markup=None
    )
    if call.data == 'top_correct':
        if lobby.get('players_top') is None:
            lobby['players_top'] = []

        lobby['players_top'].append(top_states[user_id]['top_people'])
        del top_states[user_id]

        other_user_id = [user for user in players if user != user_id][0]

        if len(lobby['players_top']) == 2:
            for user in lobby['users']:
                bot.send_message(user, 'Топы составлены, приступаем к отгадыванию')
            bot.send_message(host, f'{lobby['players_top']}')

            bot.send_message(host, lobby['questions'][players.index(user_id)])
            bot.send_message(host, "\n".join([f"{i+1}. {name}" for i, name in enumerate(lobby['players_top'][1])]))
            bot.send_message(host, lobby['questions'][players.index(other_user_id)])
            bot.send_message(host, "\n".join([f"{i+1}. {name}" for i, name in enumerate(lobby['players_top'][0])]))

            markup = types.InlineKeyboardMarkup(row_width=2)
            same_btn = types.InlineKeyboardButton('У соперника такой же вопрос', callback_data="same_question")
            other_btn = types.InlineKeyboardButton('У соперника другой же вопрос', callback_data="other_question")
            markup.add(same_btn, other_btn)

            for user in players:
                bot.send_message(user, 'Топ соперника, попытайся определить одинаковые ли у вас вопросы')

            bot.send_message(other_user_id, "\n".join([f"{i + 1}. {name}" for i, name in enumerate(lobby['players_top'][1])]), reply_markup=markup)
            bot.send_message(user_id, "\n".join([f"{i + 1}. {name}" for i, name in enumerate(lobby['players_top'][0])]), reply_markup=markup)

        else:
            bot.send_message(user_id, 'Ожидаем другого игрока')
            bot.send_message(host, f'{user_username[user_id]} ответил')

    elif call.data == 'top_incorrect':
        top_states[user_id]['step'] = 0
        top_states[user_id]['top_people'] = []

        bot.send_message(user_id, f'Можешь начинать вводить свой топ на вопрос: {lobby["questions"][players.index(user_id)]}')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            types.KeyboardButton(lobby['selectable_players'][0]),
            types.KeyboardButton(lobby['selectable_players'][1]),
            types.KeyboardButton(lobby['selectable_players'][2])
        )
        markup.add(
            types.KeyboardButton(lobby['selectable_players'][3]),
            types.KeyboardButton(lobby['selectable_players'][4]),
            types.KeyboardButton(lobby['selectable_players'][5])
        )
        bot.send_message(user_id, '1 место', reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "Ошибка состояния. Начните заново командой /start")


@bot.callback_query_handler(func=lambda call: call.data in ['same_question', 'other_question'])
def reveal_answers(call):
    user_id = call.message.chat.id
    lobby_id = user_lobby_data[user_id]
    lobby = lobby_data[lobby_id]
    host = lobby['creator']
    first_question = lobby['questions'][0]
    second_question = lobby['questions'][1]

    bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=call.message.message_id,
        reply_markup=None
    )

    if call.data == 'same_question' and first_question == second_question:
        bot.send_message(host, f'{user_username[user_id]} ответил правильно')
        bot.send_message(user_id, f'ты ответил правильно')

    elif call.data == 'other_question' and first_question == second_question:
        bot.send_message(host, f'{user_username[user_id]} ответил неправильно')
        bot.send_message(user_id, f'ты ответил неправильно')

    elif call.data == 'same_question' and first_question != second_question:
        bot.send_message(host, f'{user_username[user_id]} ответил неправильно')
        bot.send_message(user_id, f'ты ответил неправильно')

    elif call.data == 'other_question' and first_question != second_question:
        bot.send_message(host, f'{user_username[user_id]} ответил правильно')
        bot.send_message(user_id, f'ты ответил правильно')

    else:
        bot.answer_callback_query(call.id, "Ошибка состояния. Начните заново командой /start")

    lobby['answers_received'] = lobby.get('answers_received', 0) + 1

    if lobby['answers_received'] == 2:
        markup = types.InlineKeyboardMarkup(row_width=1)
        replay_btn = types.InlineKeyboardButton('Сыграть снова', callback_data="replay")
        markup.add(replay_btn)
        bot.send_message(host, 'Игра завершена', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'replay')
def replay(call):
    user_id = call.message.chat.id
    lobby_id = user_lobby_data[user_id]
    lobby = lobby_data.get(lobby_id)
    lobby = {
        'creator': lobby['creator'],
        'users': lobby['users'],
        'active': True,
        'selectable_players': lobby['selectable_players'][:-1]
    }
    lobby_data[lobby_id] = lobby

    for state_dict in [input_states, top_states, question_states]:
        for uid in list(state_dict.keys()):
            del state_dict[uid]

    for user in lobby['users']:
        bot.send_message(user, "Игра перезапускается! Начинаем новый раунд")
    questions_creating(lobby_id)


if __name__ == '__main__':
    bot.infinity_polling()
