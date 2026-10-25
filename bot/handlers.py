"""
Обработчики команд и сообщений Telegram-бота «Горизонт» на базе aiogram 3.
Реализует команды /start, /login, /status, /goals, /newgoal, /help, /logout
и машины состояний (FSM) для интерактивного ввода.
"""

from typing import Optional
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from api_client import api_client, BackendConnectionError, AuthenticationError
from config import DEMO_CREDENTIALS

router = Router(name="horizont_handlers")


# ============================================================================
# FSM СОСТОЯНИЯ
# ============================================================================

class LoginFSM(StatesGroup):
    waiting_for_credentials = State()


class NewGoalFSM(StatesGroup):
    waiting_for_title = State()
    waiting_for_sphere = State()
    waiting_for_cost = State()


# ============================================================================
# КЛАВИАТУРЫ
# ============================================================================

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная постоянная клавиатура авторизованного пользователя."""
    kb = [
        [
            KeyboardButton(text="📊 Мой баланс (/status)"),
            KeyboardButton(text="🎯 Список целей (/goals)")
        ],
        [
            KeyboardButton(text="➕ Новая цель (/newgoal)"),
            KeyboardButton(text="ℹ️ Справка (/help)")
        ],
        [
            KeyboardButton(text="🚪 Выйти из системы (/logout)")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_demo_login_inline_kb() -> InlineKeyboardMarkup:
    """Инлайн-кнопки быстрого 1-click входа для демо-резидентов."""
    buttons = [
        [
            InlineKeyboardButton(text="⚡ Войти как Admin (Полный доступ)", callback_data="demo_login:admin"),
        ],
        [
            InlineKeyboardButton(text="⚡ Войти как User (Пользователь)", callback_data="demo_login:user"),
        ],
        [
            InlineKeyboardButton(text="✏️ Ввести свой логин и пароль", callback_data="manual_login"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_progress_bar(percent: int, length: int = 10) -> str:
    """Генерация визуального прогресс-бара [████████░░]."""
    clamped = max(0, min(100, percent))
    filled = int(round((clamped / 100) * length))
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"


# ============================================================================
# КОМАНДА /START
# ============================================================================

@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()
    user_id = message.from_user.id

    if api_client.is_authenticated(user_id):
        sess = api_client.get_session(user_id)
        user_info = sess.get("user", {})
        name = user_info.get("name") or user_info.get("login", "Резидент")
        role = "Администратор" if user_info.get("role") == "admin" else "Пользователь"

        await message.answer(
            f"🌟 **С возвращением в «Горизонт», {name}!**\n\n"
            f"👤 Активный профиль: **{name}** ({role})\n"
            f"Используйте кнопки меню внизу экрана или команды:\n"
            f"📊 /status — Сводка баланса и финансовый срез\n"
            f"🎯 /goals — Просмотр целей и прогресса\n"
            f"➕ /newgoal — Создать новую цель\n"
            f"ℹ️ /help — Справка по функциям",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return

    # Приветствие для неавторизованного пользователя
    welcome_text = (
        "✨ **Добро пожаловать в систему «ГОРИЗОНТ»!**\n"
        "Карта желаний, колесо жизненного баланса & декомпозиция целей.\n\n"
        "🔒 **Закрытый контур:** Для взаимодействия с вашими целями и колесом баланса "
        "необходимо привязать аккаунт к бэкенду FastAPI.\n\n"
        "💡 **Как авторизоваться?**\n"
        "1. Нажмите одну из кнопок быстрого демо-доступа ниже.\n"
        "2. Либо отправьте команду:\n"
        "`/login <логин> <пароль>`\n"
        "_(например: `/login admin admin` или `/login user user`)_."
    )
    await message.answer(
        welcome_text,
        reply_markup=get_demo_login_inline_kb(),
        parse_mode="Markdown"
    )


# ============================================================================
# АВТОРИЗАЦИЯ (/LOGIN И FSM)
# ============================================================================

@router.message(Command("login"))
async def handle_login_command(message: Message, command: CommandObject, state: FSMContext):
    """Обработка команды /login [логин] [пароль]."""
    await state.clear()
    user_id = message.from_user.id
    args = (command.args or "").strip().split()

    if len(args) == 2:
        login_val, password_val = args[0], args[1]
        await execute_login(message, user_id, login_val, password_val)
        return

    # Если аргументы не переданы, запрашиваем через FSM
    await state.set_state(LoginFSM.waiting_for_credentials)
    await message.answer(
        "🔑 **Ввод учетных данных «Горизонт»**\n\n"
        "Введите ваш логин и пароль через пробел:\n"
        "`<логин> <пароль>`\n\n"
        "Либо используйте демо-доступ: `admin admin` или `user user`.\n"
        "Для отмены отправьте /cancel.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )


@router.message(LoginFSM.waiting_for_credentials)
async def process_manual_login(message: Message, state: FSMContext):
    """Обработка ввода логина и пароля в состоянии FSM."""
    text = (message.text or "").strip()
    if text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Авторизация отменена.", reply_markup=ReplyKeyboardRemove())
        return

    parts = text.split()
    if len(parts) < 2:
        await message.answer(
            "⚠️ Пожалуйста, укажите логин и пароль через пробел, например: `admin admin`",
            parse_mode="Markdown"
        )
        return

    login_val, password_val = parts[0], parts[1]
    await state.clear()
    await execute_login(message, message.from_user.id, login_val, password_val)


@router.callback_query(F.data.startswith("demo_login:"))
async def handle_demo_login_callback(query: CallbackQuery, state: FSMContext):
    """Обработка нажатия инлайн-кнопок 1-click демо-входа."""
    await state.clear()
    await query.answer()
    role = query.data.split(":")[1]
    creds = DEMO_CREDENTIALS.get(role, DEMO_CREDENTIALS["user"])

    msg = query.message
    user_id = query.from_user.id
    await execute_login(msg, user_id, creds["username"], creds["password"])


@router.callback_query(F.data == "manual_login")
async def handle_manual_login_callback(query: CallbackQuery, state: FSMContext):
    """Переход в режим ручного ввода логина."""
    await query.answer()
    await state.set_state(LoginFSM.waiting_for_credentials)
    await query.message.answer(
        "✏️ Отправьте логин и пароль через пробел:\n`admin admin` или `user user`",
        parse_mode="Markdown"
    )


async def execute_login(message: Message, user_id: int, login_val: str, password_val: str):
    """Выполнение запроса на авторизацию к FastAPI бэкенду."""
    wait_msg = await message.answer("⏳ Проверяем учетные данные на сервере «Горизонт»...")
    try:
        user_info = await api_client.login(user_id, login_val, password_val)
        name = user_info.get("name") or user_info.get("login")
        role = "Администратор (Admin)" if user_info.get("role") == "admin" else "Пользователь (User)"

        await wait_msg.delete()
        await message.answer(
            f"✅ **Авторизация успешна!**\n\n"
            f"👤 Резидент: **{name}**\n"
            f"🛡 Роль: **{role}**\n\n"
            f"Теперь ваш Telegram привязан к системе «Горизонт». "
            f"Вы можете в любой момент запросить актуальный баланс или добавить цель.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    except AuthenticationError as e:
        await wait_msg.delete()
        await message.answer(
            f"❌ **Ошибка авторизации:** {str(e)}\n\n"
            f"Попробуйте снова: `/login <логин> <пароль>`\n"
            f"Или выберите демо-доступ:",
            reply_markup=get_demo_login_inline_kb(),
            parse_mode="Markdown"
        )
    except BackendConnectionError as e:
        await wait_msg.delete()
        await message.answer(
            f"⚠️ **Сервер «Горизонт» (FastAPI) недоступен.**\n\n"
            f"{str(e)}\n\n"
            f"Убедитесь, что сервер запущен локально командой:\n"
            f"`uvicorn main:app --reload` в папке `backend/`.",
            parse_mode="Markdown"
        )


# ============================================================================
# КОМАНДА /STATUS (БАЛАНС, ГАРМОНИЯ И ФИНАНСОВЫЙ СРЕЗ)
# ============================================================================

@router.message(Command("status"))
@router.message(F.text == "📊 Мой баланс (/status)")
async def handle_status(message: Message):
    """
    Главная сводная команда:
    - Индекс гармонии колеса баланса (%)
    - Средний балл сфер жизни (0-10)
    - Список сфер и статусы
    - Количество целей
    - Суммарный бюджет в BYN и эквивалент в USD (НБРБ)
    """
    user_id = message.from_user.id
    if not api_client.is_authenticated(user_id):
        await message.answer(
            "🔒 Вы не авторизованы. Сначала войдите в систему с помощью команды /start или `/login`.",
            reply_markup=get_demo_login_inline_kb(),
            parse_mode="Markdown"
        )
        return

    wait_msg = await message.answer("🔄 Запрашиваем актуальный баланс и цели с сервера...")

    try:
        data = await api_client.get_status_overview(user_id)
    except AuthenticationError as e:
        await wait_msg.delete()
        await message.answer(f"🔒 {str(e)}", reply_markup=get_demo_login_inline_kb())
        return
    except BackendConnectionError as e:
        await wait_msg.delete()
        await message.answer(
            f"⚠️ **Ошибка связи с бэкендом:**\n{str(e)}",
            parse_mode="Markdown"
        )
        return

    await wait_msg.delete()

    user = data["user"]
    user_name = user.get("name") or user.get("login", "Резидент")
    role_str = "Admin" if user.get("role") == "admin" else "User"

    harmony = data["harmony_percent"]
    progress_bar = format_progress_bar(harmony, length=10)

    if harmony >= 80:
        verdict = "🟢 Высокая гармония (сферы жизни сбалансированы)"
    elif harmony >= 60:
        verdict = "🟡 Умеренный баланс (есть сферы, требующие внимания)"
    else:
        verdict = "🔴 Обнаружен перекос (часть сфер проседает)"

    # Формирование списка сфер
    spheres_lines = []
    for s in data["spheres"]:
        title = s.get("title", "Сфера")
        score = float(s.get("current_score", 0.0))
        target = float(s.get("target_score", 10.0))
        pct = int(round((score / target) * 100)) if target > 0 else 0
        icon = "🟢" if pct >= 80 else ("🟡" if pct >= 50 else "🟠")
        spheres_lines.append(f"• {icon} *{title}:* `{score:.1f}` / `{target:.1f}` ({pct}%)")

    spheres_text = "\n".join(spheres_lines) if spheres_lines else "_Сферы жизни еще не настроены_"

    # Форматирование сумм бюджетов
    total_byn_str = f"{int(round(data['total_byn'])):,} Br".replace(",", " ")
    total_usd_str = f"${int(round(data['total_usd'])):,} USD".replace(",", " ")

    status_message = (
        f"📊 **СВОДКА БАЛАНСА И ЦЕЛЕЙ «ГОРИЗОНТ»**\n"
        f"👤 Резидент: *{user_name}* ({role_str})\n"
        f"────────────────────────\n\n"
        f"🌟 **Индекс гармонии:** *{harmony}%* {progress_bar}\n"
        f"Статус: {verdict}\n\n"
        f"🔮 **Сферы жизни** (средний балл: *{data['avg_score']} / 10*):\n"
        f"{spheres_text}\n\n"
        f"🎯 **Реестр целей:**\n"
        f"• Всего целей: *{data['total_goals']}*\n"
        f"• В работе: *{data['in_progress_goals']}* | Достигнуто: *{data['achieved_goals']}*\n\n"
        f"💰 **Финансовый срез:**\n"
        f"• Суммарный бюджет: *{total_byn_str}*\n"
        f"• Эквивалент: *{total_usd_str}*\n"
        f"• Официальный курс: `1 USD = {data['fx_rate']:.4f} BYN` (НБРБ)\n"
        f"────────────────────────"
    )

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Посмотреть цели", callback_data="view_goals"),
            InlineKeyboardButton(text="➕ Новая цель", callback_data="start_new_goal")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить статус", callback_data="refresh_status")
        ]
    ])

    await message.answer(status_message, reply_markup=inline_kb, parse_mode="Markdown")


@router.callback_query(F.data == "refresh_status")
async def handle_refresh_status_callback(query: CallbackQuery):
    """Быстрое обновление статуса по инлайн-кнопке."""
    await query.answer("Обновление данных...")
    await handle_status(query.message)


# ============================================================================
# КОМАНДА /GOALS (РЕЕСТР ЦЕЛЕЙ)
# ============================================================================

@router.message(Command("goals"))
@router.message(F.text == "🎯 Список целей (/goals)")
async def handle_goals(message: Message):
    """Вывод списка активных целей пользователя."""
    user_id = message.from_user.id
    if not api_client.is_authenticated(user_id):
        await message.answer("🔒 Сначала авторизуйтесь через /start или `/login`.")
        return

    try:
        goals = await api_client.get_goals(user_id)
        spheres = await api_client.get_spheres(user_id)
    except Exception as e:
        await message.answer(f"⚠️ Ошибка получения целей: {str(e)}")
        return

    if not goals:
        await message.answer(
            "🎯 **В вашем реестре пока нет целей.**\n"
            "Добавьте первую цель с помощью команды /newgoal!",
            parse_mode="Markdown"
        )
        return

    spheres_map = {str(s.get("id")): s.get("title") for s in spheres}

    lines = ["🎯 **ВАШИ ЦЕЛИ И ЖЕЛАНИЯ:**\n"]
    for idx, g in enumerate(goals, start=1):
        title = g.get("title", "Без названия")
        sphere_name = spheres_map.get(str(g.get("sphere_id")), "Сфера")
        progress = g.get("progress_percent", 0)
        status = g.get("status", "in_progress")
        cost = float(g.get("cost_amount") or 0.0)
        currency = g.get("currency", "BYN")
        deadline = g.get("deadline") or "без дедлайна"

        status_emoji = "✅" if status == "achieved" else ("⏳" if status == "in_progress" else "📝")
        p_bar = format_progress_bar(progress, length=6)

        cost_str = f"{int(round(cost)):,} {currency}".replace(",", " ") if cost > 0 else "0 BYN"

        lines.append(
            f"*{idx}. {title}* {status_emoji}\n"
            f"   🔮 Сфера: _{sphere_name}_ | Дедлайн: _{deadline}_\n"
            f"   📈 Прогресс: `{progress}%` {p_bar}\n"
            f"   💰 Бюджет: *{cost_str}*\n"
        )

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.callback_query(F.data == "view_goals")
async def handle_view_goals_callback(query: CallbackQuery):
    """Коллбэк перехода к списку целей."""
    await query.answer()
    await handle_goals(query.message)


# ============================================================================
# КОМАНДА /NEWGOAL (СОЗДАНИЕ ЦЕЛИ ЧЕРЕЗ FSM)
# ============================================================================

@router.message(Command("newgoal"))
@router.message(F.text == "➕ Новая цель (/newgoal)")
async def handle_new_goal_start(message: Message, state: FSMContext):
    """Старт диалога добавления цели."""
    user_id = message.from_user.id
    if not api_client.is_authenticated(user_id):
        await message.answer("🔒 Сначала авторизуйтесь через /start или `/login`.")
        return

    await state.set_state(NewGoalFSM.waiting_for_title)
    await message.answer(
        "➕ **Создание новой цели в системе «Горизонт»**\n\n"
        "Шаг 1 из 3: Введите **название цели**:\n"
        "_(например: «Выучить разговорный английский B2» или «Купить новый макбук»)_\n\n"
        "Для отмены отправьте /cancel.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "start_new_goal")
async def handle_start_new_goal_callback(query: CallbackQuery, state: FSMContext):
    """Старт добавления цели из инлайн-кнопки."""
    await query.answer()
    await handle_new_goal_start(query.message, state)


@router.message(NewGoalFSM.waiting_for_title)
async def process_goal_title(message: Message, state: FSMContext):
    """Обработка названия цели и вывод выбора сферы."""
    title = (message.text or "").strip()
    if title.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Создание цели отменено.", reply_markup=get_main_keyboard())
        return

    if len(title) < 3:
        await message.answer("⚠️ Название слишком короткое. Введите понятное название цели:")
        return

    await state.update_data(goal_title=title)

    # Получаем сферы пользователя
    try:
        spheres = await api_client.get_spheres(message.from_user.id)
    except Exception as e:
        await state.clear()
        await message.answer(f"⚠️ Ошибка загрузки сфер: {str(e)}", reply_markup=get_main_keyboard())
        return

    if not spheres:
        await state.clear()
        await message.answer("⚠️ У вас нет настроенных сфер жизни.", reply_markup=get_main_keyboard())
        return

    # Клавиатура выбора сферы
    buttons = []
    for s in spheres:
        buttons.append([InlineKeyboardButton(text=f"🔮 {s['title']}", callback_data=f"set_sphere:{s['id']}")])

    inline_kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await state.set_state(NewGoalFSM.waiting_for_sphere)
    await message.answer(
        f"🎯 Цель: *{title}*\n\n"
        f"Шаг 2 из 3: Выберите **сферу жизни**, к которой относится эта цель:",
        reply_markup=inline_kb,
        parse_mode="Markdown"
    )


@router.callback_query(NewGoalFSM.waiting_for_sphere, F.data.startswith("set_sphere:"))
async def process_goal_sphere(query: CallbackQuery, state: FSMContext):
    """Обработка выбранной сферы жизни."""
    await query.answer()
    sphere_id = query.data.split(":")[1]
    await state.update_data(sphere_id=sphere_id)

    await state.set_state(NewGoalFSM.waiting_for_cost)
    await query.message.answer(
        "💰 Шаг 3 из 3: Введите **бюджет цели** в BYN (или `0`, если цель нематериальная):\n"
        "_(например: `2500` или `0`)_\n\n"
        "Для отмены отправьте /cancel.",
        parse_mode="Markdown"
    )


@router.message(NewGoalFSM.waiting_for_cost)
async def process_goal_cost(message: Message, state: FSMContext):
    """Завершение создания цели и отправка на бэкенд."""
    text = (message.text or "").strip().replace(" ", "").replace(",", ".")
    if text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Создание цели отменено.", reply_markup=get_main_keyboard())
        return

    try:
        cost_val = float(text)
        if cost_val < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите корректное положительное число или 0:")
        return

    data = await state.get_data()
    title = data["goal_title"]
    sphere_id = data["sphere_id"]
    await state.clear()

    wait_msg = await message.answer("⏳ Сохраняем цель в базе данных «Горизонт»...")
    try:
        created = await api_client.create_goal(
            telegram_id=message.from_user.id,
            title=title,
            sphere_id=sphere_id,
            cost_amount=cost_val,
            currency="BYN"
        )
        await wait_msg.delete()
        await message.answer(
            f"🎉 **Цель успешно создана!**\n\n"
            f"🎯 *{created.get('title')}*\n"
            f"💰 Бюджет: *{cost_val:,.0f} BYN*\n"
            f"📈 Прогресс: *0%*\n\n"
            f"Карточка добавлена в вашу витрину желаний на сайте и в Telegram-боте.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        await wait_msg.delete()
        await message.answer(
            f"❌ **Ошибка создания цели:** {str(e)}",
            reply_markup=get_main_keyboard()
        )


# ============================================================================
# КОМАНДЫ /HELP И /LOGOUT
# ============================================================================

@router.message(Command("help"))
@router.message(F.text == "ℹ️ Справка (/help)")
async def handle_help(message: Message):
    """Справка по доступным командам."""
    help_text = (
        "📖 **СПРАВКА ПО БОТУ «ГОРИЗОНТ»**\n\n"
        "Бот синхронизирован с сервером планирования и колеса баланса жизни.\n\n"
        "⚡ **Основные команды:**\n"
        "• /status — Текущий индекс гармонии, средний балл сфер и бюджет целей (Br / USD)\n"
        "• /goals — Просмотр ваших активных целей и прогресса\n"
        "• /newgoal — Быстрое добавление новой цели прямо из Telegram\n"
        "• /login `<логин>` `<пароль>` — Авторизация под учетной записью\n"
        "• /logout — Завершение сессии в Telegram-боте\n"
        "• /start — Стартовое меню и проверка привязки аккаунта\n\n"
        "🌐 **Веб-версия системы:**\n"
        "https://chembrovich-sa-case.github.io/dream-map-planner/\n\n"
        "💡 *Совет:* Вы можете проверять динамику баланса каждый день с помощью /status!"
    )
    await message.answer(help_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")


@router.message(Command("logout"))
@router.message(F.text == "🚪 Выйти из системы (/logout)")
async def handle_logout(message: Message, state: FSMContext):
    """Выход из профиля."""
    await state.clear()
    api_client.logout(message.from_user.id)
    await message.answer(
        "👋 Вы вышли из учетной записи. Токен сессии удален.\n"
        "Для повторного входа отправьте команду /start или /login.",
        reply_markup=ReplyKeyboardRemove()
    )


# ============================================================================
# ОТМЕНА ДЕЙСТВИЙ (/CANCEL)
# ============================================================================

@router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext):
    """Универсальная отмена текущего состояния."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активных действий для отмены.", reply_markup=get_main_keyboard())
        return

    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=get_main_keyboard())
