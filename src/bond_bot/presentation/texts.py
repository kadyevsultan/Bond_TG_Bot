from __future__ import annotations

from bond_bot.domain.entities import Game, Outcome, Player, SpyMode

GREETING = (
    "🕵️ <b>Шпион</b>\n\n"
    "Играем вживую, одним телефоном. Бот раздаёт слова, ведёт голосование "
    "и объявляет итог.\n\n"
    "Все темы открыты, свои темы создаются без ограничений."
)

RULES = (
    "<b>Правила</b>\n\n"
    "Все получают одно слово, кроме шпионов. Задавайте друг другу вопросы про "
    "загаданное слово так, чтобы шпион не догадался, а свои поняли, что вы не шпион.\n\n"
    "<b>Как играем</b>\n"
    "1. Телефон идёт по кругу, каждый смотрит своё слово\n"
    "2. Обсуждаете вживую, бот не торопит\n"
    "3. Хост открывает голосование и отмечает, кто за кого\n"
    "4. Выгнанный выбывает, бот сразу говорит — был ли он шпионом\n\n"
    "<b>Победа мирных</b>\n"
    "• выгнали всех шпионов\n"
    "• шпион назвал слово и ошибся\n\n"
    "<b>Победа шпионов</b>\n"
    "• осталось двое игроков\n"
    "• шпион назвал слово верно\n\n"
    "<b>Режимы</b>\n"
    "🕵️ <b>Классика</b> — шпион не знает слова\n"
    "🎭 <b>Двойной агент</b> — шпион получает похожее слово и сам не знает, что оно другое"
)

CHOOSE_THEME = "📚 <b>Выберите тему</b>\n\nРядом с названием — сколько в ней слов."
CHOOSE_PLAYERS = "👥 <b>Сколько игроков?</b>"
NO_THEMES = "Пока нет ни одной темы со словами."


def choose_spies(players: int, max_spies: int) -> str:
    return (
        f"🕵️ <b>Сколько шпионов?</b>\n\n"
        f"Игроков: {players}. Максимум шпионов: {max_spies} — "
        f"хотя бы один мирный должен знать слово."
    )


def choose_mode(theme: str, players: int, spies: int) -> str:
    return (
        f"🎭 <b>Режим шпиона</b>\n\n"
        f"Тема: <b>{theme}</b>\nИгроков: {players}\nШпионов: {spies}\n\n"
        f"🕵️ <b>Классика</b> — шпион вообще не знает слова\n"
        f"🎭 <b>Двойной агент</b> — шпион получает похожее слово"
    )


def pass_phone(game: Game, player: Player) -> str:
    return (
        f"📱 <b>Передайте телефон: {player.label}</b>\n\n"
        f"Тема: <b>{game.theme_name}</b>\n"
        f"Игрок {player.number} из {len(game.players)}\n\n"
        f"Остальные не подглядывают."
    )


def word_card(game: Game, player: Player) -> str:
    if player.is_spy and (game.spy_mode is SpyMode.CLASSIC or player.word is None):
        body = "🔴 <b>Вы шпион</b>\n\nСлова вы не знаете. Слушайте и притворяйтесь своим."
    else:
        body = f"Ваше слово:\n\n🔵 <b>{player.word}</b>"
    return f"👤 <b>{player.label}</b>\n\n{body}"


def discussion(game: Game) -> str:
    alive = ", ".join(p.label for p in game.alive)
    lines = [
        f"💬 <b>Обсуждение — раунд {game.round_number}</b>",
        "",
        f"Тема: <b>{game.theme_name}</b>",
        f"В игре: {alive}",
    ]
    if game.last_eliminated:
        lines.append("")
        lines.append(eliminated_line(game))
    lines.append("")
    lines.append("Задавайте вопросы. Когда будете готовы — начинайте голосование.")
    return "\n".join(lines)


def eliminated_line(game: Game) -> str:
    parts = []
    for player in game.last_eliminated:
        mark = "🔴 был шпионом" if player.is_spy else "🔵 был мирным"
        parts.append(f"{player.label} — {mark}")
    return "🚪 Выбыл: " + "; ".join(parts) if len(parts) == 1 else "🚪 Выбыли: " + "; ".join(parts)


def ask_vote(game: Game, voter: Player) -> str:
    voted = len(game.votes)
    total = len(game.alive)
    return (
        f"🗳 <b>Голосование — раунд {game.round_number}</b>\n\n"
        f"За кого голосует <b>{voter.label}</b>?\n\n"
        f"Отмечено голосов: {voted} из {total}"
    )


def tie(numbers: list[int]) -> str:
    tied = ", ".join(f"Игрок {n}" for n in numbers)
    return (
        f"⚖️ <b>Ничья</b>\n\n"
        f"Одинаково голосов набрали: <b>{tied}</b>\n\n"
        f"Что делаем?"
    )


SPY_GUESS_WARNING = (
    "🎯 <b>Шпион называет слово</b>\n\n"
    "Передайте телефон шпиону. Он выберет слово из списка темы, "
    "и бот сразу объявит результат.\n\n"
    "Решение необратимо."
)

SPY_GUESS_PICK = "🎯 <b>Шпион, выберите слово</b>"


def finished(game: Game) -> str:
    outcome = game.outcome
    if outcome is Outcome.CIVILIANS_BY_VOTE:
        headline = "🔵 <b>Победа мирных!</b>\n\nВсе шпионы раскрыты."
    elif outcome is Outcome.CIVILIANS_BY_WRONG_GUESS:
        headline = "🔵 <b>Победа мирных!</b>\n\nШпион назвал слово и ошибся."
    elif outcome is Outcome.SPIES_BY_GUESS:
        headline = "🔴 <b>Победа шпионов!</b>\n\nШпион угадал слово."
    else:
        headline = "🔴 <b>Победа шпионов!</b>\n\nОсталось двое игроков — шпиона не нашли."

    roles = []
    for player in game.players:
        icon = "🔴" if player.is_spy else "🔵"
        role = "шпион" if player.is_spy else "мирный"
        status = " (выбыл)" if player.eliminated else ""
        roles.append(f"{icon} {player.label} — {role}{status}")

    return (
        f"{headline}\n\n"
        f"Тема: <b>{game.theme_name}</b>\n"
        f"Загаданное слово: <b>{game.civilian_word}</b>\n\n"
        + "\n".join(roles)
    )


THEMES_HUB = (
    "📚 <b>Темы</b>\n\n"
    "Свои темы можно создавать без ограничений, а каталог открыт для всех — "
    "любую чужую тему можно взять и играть."
)

MY_THEMES_EMPTY = "У вас пока нет своих тем. Создайте первую — это бесплатно и без лимитов."
CATALOG_EMPTY = "Каталог пока пуст. Создайте тему — она появится здесь для всех."
ASK_THEME_NAME = "➕ <b>Новая тема</b>\n\nПришлите название темы."
THEME_NAME_TOO_LONG = "Название слишком длинное, максимум 64 символа."
WORD_TOO_LONG = "Слово слишком длинное, максимум 64 символа."
NOT_YOUR_THEME = "Эту тему может редактировать только её автор."
THEME_DELETED = "🗑 Тема удалена."
NO_SIMILAR_HINT = (
    "Похожих слов нет. В режиме «Двойной агент» шпиону достанется "
    "случайное другое слово темы."
)


def my_themes(count: int) -> str:
    return f"📁 <b>Мои темы</b>\n\nВсего: {count}"


def catalog(count: int) -> str:
    return f"🌍 <b>Каталог тем</b>\n\nДоступно тем: {count}"


def theme_card(name: str, words: int, author: str) -> str:
    return f"📗 <b>{name}</b>\n\nСлов: {words}\nАвтор: {author}"


def word_list(theme_name: str, count: int) -> str:
    return (
        f"✏️ <b>{theme_name}</b>\n\n"
        f"Слов: {count}. Рядом с каждым — сколько у него похожих слов.\n\n"
        f"Нажмите на слово, чтобы открыть его."
    )


def editor_word_card(word: str, similar: list[str]) -> str:
    listed = "\n".join(f"• {s}" for s in similar)
    body = f"Похожие слова:\n{listed}" if similar else NO_SIMILAR_HINT
    return f"🔤 <b>{word}</b>\n\n{body}"


def ask_word(theme_name: str) -> str:
    return (
        f"➕ <b>Новое слово в тему «{theme_name}»</b>\n\n"
        f"Пришлите слово. Можно несколько сразу — каждое с новой строки."
    )


def ask_similar(word: str) -> str:
    return (
        f"➕ <b>Похожее слово к «{word}»</b>\n\n"
        f"Пришлите слово, которое может достаться шпиону вместо «{word}». "
        f"Можно несколько сразу — каждое с новой строки."
    )


def confirm_delete(name: str) -> str:
    return f"🗑 Удалить тему <b>{name}</b> вместе со всеми словами?"


def added_words(added: list[str], skipped: list[str]) -> str:
    lines = []
    if added:
        lines.append("✅ Добавлено: " + ", ".join(added))
    if skipped:
        lines.append("⚠️ Уже было: " + ", ".join(skipped))
    return "\n".join(lines) if lines else "Ничего не добавлено."


GAME_CANCELLED = "🛑 Игра отменена."
NO_ACTIVE_GAME = "Игра не найдена — начните новую."
