import random
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

# Токен бота
TOKEN = '5575324982:AAFexhykehZBnGFk80ckxJcLOSxcLYq_wNI'

# Размеры поля
SIZE = 10

# Символы для поля
SHIP = '■'
EMPTY = '□'
MISS = '·'
HIT = 'X'

# Определение кораблей (длина корабля)
SHIP_SIZES = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]

class Field:
    def __init__(self):
        self.field = [[EMPTY for _ in range(SIZE)] for _ in range(SIZE)]
        self.ships = []
        self.shots = []

    def render(self):
        field_str = ""
        for row in self.field:
            field_str += " ".join(row) + "\n"
        return field_str

    def can_place_ship(self, row, col, ship_size, orientation):
        # Проверяем, можно ли разместить корабль с учетом расстояния
        for i in range(ship_size):
            if orientation == 'horizontal':
                if self.field[row][col + i] != EMPTY:
                    return False
                # Проверка соседних клеток
                if row > 0 and self.field[row - 1][col + i] != EMPTY:  # верх
                    return False
                if row < SIZE - 1 and self.field[row + 1][col + i] != EMPTY:  # низ
                    return False
                if col > 0 and self.field[row][col + i - 1] != EMPTY:  # слева
                    return False
                if col + i < SIZE - 1 and self.field[row][col + i + 1] != EMPTY:  # справа
                    return False
            else:  # vertical
                if self.field[row + i][col] != EMPTY:
                    return False
                # Проверка соседних клеток
                if row > 0 and self.field[row - 1][col] != EMPTY:  # верх
                    return False
                if row + i < SIZE - 1 and self.field[row + i + 1][col] != EMPTY:  # низ
                    return False
                if col > 0 and self.field[row + i][col - 1] != EMPTY:  # слева
                    return False
                if col < SIZE - 1 and self.field[row + i][col + 1] != EMPTY:  # справа
                    return False
        return True

    def place_ship(self, ship_size):
        placed = False
        while not placed:
            orientation = random.choice(['horizontal', 'vertical'])
            if orientation == 'horizontal':
                row = random.randint(0, SIZE - 1)
                col = random.randint(0, SIZE - ship_size)
                if self.can_place_ship(row, col, ship_size, orientation):
                    for i in range(ship_size):
                        self.field[row][col + i] = SHIP
                    self.ships.append((row, col, orientation, ship_size))
                    placed = True
            else:  # vertical
                row = random.randint(0, SIZE - ship_size)
                col = random.randint(0, SIZE - 1)
                if self.can_place_ship(row, col, ship_size, orientation):
                    for i in range(ship_size):
                        self.field[row + i][col] = SHIP
                        self.ships.append((row, col, orientation, ship_size))
                    placed = True
    def setup_ships(self):
        self.field = [[EMPTY for _ in range(SIZE)] for _ in range(SIZE)]
        self.ships = []
        for ship_size in SHIP_SIZES:
            self.place_ship(ship_size)


class Player:
    def __init__(self, name):
        self.name = name
        self.field = Field()
        self.opponent_field = Field()
        self.field.setup_ships()  # Автоматическая расстановка кораблей


class Game:
    def __init__(self, player1, player2):
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.game_started = False
    def start_game(self):
        self.game_started = True


# Состояния игры
class GameStates(StatesGroup):
    waiting_for_opponent = State()
    waiting_for_start = State()
    playing = State()


# Создание бота
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Словарь для хранения игр
games = {}


@dp.message_handler(commands=['start'], state='*')
async def start_command(message: types.Message, state: FSMContext):
    await message.reply("Привет! Это телеграмм-бот для игры в морской бой с другим человеком.")
    await message.reply("Чтобы начать игру, пригласите второго игрока и введите команду /start_game в ответ на его сообщение.")
    await GameStates.waiting_for_opponent.set()


@dp.message_handler(commands=['start_game'], state=GameStates.waiting_for_opponent)
async def add_opponent(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in games:
        games[user_id] = {'opponent': None, 'game': None}

    # Проверка, что команда вызвана в ответ на сообщение другого пользователя
    if message.reply_to_message is None:
        await message.reply("Пожалуйста, ответьте на сообщение другого игрока, чтобы добавить его в игру.")
        return
    opponent_id = message.reply_to_message.from_user.id
    if opponent_id != user_id:
        games[user_id]['opponent'] = opponent_id
        games[opponent_id] = {'opponent': user_id, 'game': None}
        player1_name = message.from_user.username
        player2_name = message.reply_to_message.from_user.username

        # Создаем игроков
        player1 = Player(player1_name)
        player2 = Player(player2_name)

        # Создаем игру
        game = Game(player1, player2)

        # Сохраняем игру в словаре
        games[user_id]['game'] = game
        games[opponent_id]['game'] = game
        # Начинаем игру
        game.start_game()

        await message.reply(f"Игра начата между {player1_name} и {player2_name}!\n\n"
                            f"Первый ход делает {player1_name}. Используйте команду /make_shot для хода.\n\n"
                            f"Kорабли были расставлены в случайном порядке, для перестановки используйте команду /randomize_ships \n\n"
                            f"Ваше поле:\n{player1.field.render()}")
    else:
        await message.reply("Вы не можете добавить сами себя!")


@dp.message_handler(commands=['randomize_ships'], state=GameStates.waiting_for_opponent)
async def randomize_ships(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    game = games[user_id]['game']
    if game:
        # Случайная расстановка кораблей для текущего игрока
        game.current_player.field.setup_ships()
        await message.reply(f"{game.current_player.name}, ваши корабли были случайно расставлены!\n\n"
                            f"Используйте команду /make_shot для хода или команду /randomize_ships для смены положений кораблей. \n\n"
                            f"Ваше поле:\n{game.current_player.field.render()}")
    else:
        await message.reply("Игра еще не началась!")


@dp.message_handler(commands=['make_shot'], state=GameStates.waiting_for_opponent)
async def make_shot(message: types.Message, state: FSMContext):
    await message.reply("Дальнейшие действия в разработке")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
