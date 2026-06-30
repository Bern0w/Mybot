import random
import logging
from dataclasses import dataclass, field
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ⚠️ توکن ربات خودتون رو از @BotFather بگیرید و اینجا جایگزین کنید
BOT_TOKEN = "8602338004:AAGcoLuP24X_IyFeh2bXkcBEjIQlnoqD9vg"

SUITS = ["♠", "♥", "♦", "♣"]
SUIT_NAMES = {"♠": "پیک", "♥": "دل", "♦": "خشت", "♣": "گشنیز"}
RANKS = list(range(2, 15))  # 11=J, 12=Q, 13=K, 14=A
RANK_NAMES = {11: "J", 12: "Q", 13: "K", 14: "A"}

POINTS_TO_WIN = 7      # امتیاز لازم برای بردن کل بازی
TRICKS_TO_WIN_ROUND = 7  # تعداد دست لازم برای بردن یک دور


def rank_name(r):
    return RANK_NAMES.get(r, str(r))


def card_str(card):
    r, s = card
    return f"{rank_name(r)}{s}"


def make_deck():
    return [(r, s) for s in SUITS for r in RANKS]


@dataclass
class Player:
    user_id: int
    name: str
    seat: int
    team: int
    hand: list = field(default_factory=list)


@dataclass
class Game:
    chat_id: int
    players: list = field(default_factory=list)  # ترتیب نشستن، seat 0..3
    state: str = "lobby"  # lobby, hokm, playing, finished
    hakem_seat: int = 0
    hokm: Optional[str] = None
    tricks: dict = field(default_factory=lambda: {0: 0, 1: 0})
    scores: dict = field(default_factory=lambda: {0: 0, 1: 0})
    current_trick: list = field(default_factory=list)  # [(seat, card), ...]
    leading_suit: Optional[str] = None
    turn_seat: int = 0
    round_num: int = 1
    rest_deck: list = field(default_factory=list)


games: dict[int, Game] = {}


def get_player_by_user(game: Game, user_id: int) -> Optional[Player]:
    for p in game.players:
        if p.user_id == user_id:
            return p
    return None


def team_names(game: Game, team: int) -> str:
    return " و ".join(p.name for p in game.players if p.team == team)


def find_game_by_hakem(user_id: int, state: str) -> Optional[Game]:
    for g in games.values():
        if g.players and g.state == state and g.players[g.hakem_seat].user_id == user_id:
            return g
    return None


def find_game_by_turn(user_id: int) -> Optional[Game]:
    for g in games.values():
        if g.state == "playing" and g.players[g.turn_seat].user_id == user_id:
            return g
    return None


# ---------------- Commands ----------------

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "سلام! 🃏ربات حکم آماده‌ست.\n"
            "برای بازی برو توی یه گروه و دستور /newgame رو بزن.\n"
            "این چت خصوصی برای فرستادن کارت‌هاته، پس همینجا /start رو زدی، کافیه."
        )
    else:
        await update.message.reply_text("سلام! برای شروع بازی حکم: /newgame")


async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("این بازی باید توی یه گروه شروع بشه.")
        return
    games[chat_id] = Game(chat_id=chat_id)
    await update.message.reply_text(
        "🃏 بازی حکم ساخته شد!\n"
        "برای پیوستن /join رو بزنید (دقیقاً ۴ نفر لازمه).\n"
        "⚠️ حتماً قبلش یه بار توی پیوی ربات /start بزنید تا بتونه کارت‌هاتون رو خصوصی بفرسته."
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = games.get(chat_id)
    if not game or game.state != "lobby":
        await update.message.reply_text("بازی فعالی برای پیوستن نیست. اول /newgame بزن.")
        return
    user = update.effective_user
    if get_player_by_user(game, user.id):
        await update.message.reply_text("شما قبلاً عضو شدید.")
        return
    if len(game.players) >= 4:
        await update.message.reply_text("بازی پره (۴ نفر).")
        return
    seat = len(game.players)
    game.players.append(Player(user_id=user.id, name=user.first_name, seat=seat, team=seat % 2))
    await update.message.reply_text(f"✅ {user.first_name} پیوست. ({len(game.players)}/4)")
    if len(game.players) == 4:
        t0 = team_names(game, 0)
        t1 = team_names(game, 1)
        await update.message.reply_text(f"تیم‌ها مشخص شد:\nتیم ۱: {t0}\nتیم ۲: {t1}")
        await start_round(context, game)


async def cancelgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in games:
        del games[chat_id]
        await update.message.reply_text("بازی لغو شد.")
    else:
        await update.message.reply_text("بازی فعالی نیست.")


async def score_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = games.get(chat_id)
    if not game:
        await update.message.reply_text("بازی فعالی نیست.")
        return
    t0 = team_names(game, 0)
    t1 = team_names(game, 1)
    await update.message.reply_text(
        f"📊 امتیازات (دور {game.round_num}):\n"
        f"تیم ۱ ({t0}): {game.scores[0]}\n"
        f"تیم ۲ ({t1}): {game.scores[1]}"
    )


async def myhand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    for game in games.values():
        p = get_player_by_user(game, user.id)
        if p and p.hand:
            await send_hand_private(context, game, p)
            return
    await update.message.reply_text("کارتی برای شما وجود نداره.")


# ---------------- Game flow ----------------

async def start_round(context, game: Game):
    game.state = "hokm"
    game.tricks = {0: 0, 1: 0}
    game.hokm = None
    game.current_trick = []
    game.leading_suit = None
    for p in game.players:
        p.hand = []

    deck = make_deck()
    random.shuffle(deck)

    hakem = game.players[game.hakem_seat]
    hakem.hand = sorted(deck[:5], key=lambda c: (c[1], c[0]))
    game.rest_deck = deck[5:]

    await context.bot.send_message(
        game.chat_id,
        f"🎴 دور {game.round_num} شروع شد!\nحاکم این دور: {hakem.name}\nمنتظر انتخاب خال حکم..."
    )

    kb = [[InlineKeyboardButton(f"{s} {SUIT_NAMES[s]}", callback_data=f"hokm:{s}") for s in SUITS]]
    hand_text = "  ".join(card_str(c) for c in hakem.hand)
    try:
        await context.bot.send_message(
            hakem.user_id,
            f"شما حاکم دور {game.round_num} هستید. کارت‌های شما:\n{hand_text}\n\nخال حکم رو انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(kb),
        )
    except Exception:
        await context.bot.send_message(
            game.chat_id,
            f"⚠️ نتونستم به {hakem.name} پیام خصوصی بدم. باید اول توی پیوی به ربات /start بزنه، بعد /newgame رو دوباره بزنید."
        )


async def on_hokm_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    suit = query.data.split(":")[1]
    user_id = query.from_user.id

    game = find_game_by_hakem(user_id, "hokm")
    if not game:
        return

    game.hokm = suit
    hakem = game.players[game.hakem_seat]
    hakem.hand += game.rest_deck[:8]
    rest = game.rest_deck[8:]

    seat = (game.hakem_seat + 1) % 4
    idx = 0
    while seat != game.hakem_seat:
        p = game.players[seat]
        p.hand = rest[idx:idx + 13]
        idx += 13
        seat = (seat + 1) % 4
    hakem.hand = sorted(hakem.hand, key=lambda c: (c[1], c[0]))

    await query.edit_message_text(f"خال حکم: {suit} {SUIT_NAMES[suit]} ✅")
    await context.bot.send_message(
        game.chat_id,
        f"🃏 {hakem.name} خال حکم رو «{SUIT_NAMES[suit]} {suit}» انتخاب کرد!\nبازی شروع می‌شه."
    )

    game.state = "playing"
    game.turn_seat = game.hakem_seat
    game.current_trick = []
    game.leading_suit = None

    for p in game.players:
        if p.user_id != hakem.user_id:
            await send_hand_private(context, game, p)

    await prompt_turn(context, game)


async def send_hand_private(context, game: Game, p: Player):
    p.hand = sorted(p.hand, key=lambda c: (c[1], c[0]))
    hand_text = "  ".join(card_str(c) for c in p.hand)
    try:
        await context.bot.send_message(p.user_id, f"کارت‌های شما (حکم: {game.hokm}):\n{hand_text}")
    except Exception:
        await context.bot.send_message(
            game.chat_id,
            f"⚠️ نتونستم به {p.name} پیام خصوصی بدم. باید اول توی پیوی به ربات /start بزنه."
        )


def playable_cards(p: Player, leading_suit):
    if leading_suit is None:
        return p.hand
    same_suit = [c for c in p.hand if c[1] == leading_suit]
    return same_suit if same_suit else p.hand


async def prompt_turn(context, game: Game):
    p = game.players[game.turn_seat]
    options = playable_cards(p, game.leading_suit)
    kb = [[InlineKeyboardButton(card_str(c), callback_data=f"play:{c[0]}:{c[1]}")] for c in options]
    try:
        await context.bot.send_message(
            p.user_id, "نوبت شماست، یه کارت بازی کنید:", reply_markup=InlineKeyboardMarkup(kb)
        )
    except Exception:
        await context.bot.send_message(
            game.chat_id, f"⚠️ نمی‌تونم به {p.name} پیام خصوصی بدم. باید قبلش توی پیوی /start بزنه."
        )


async def on_card_played(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, rank, suit = query.data.split(":")
    card = (int(rank), suit)
    user_id = query.from_user.id

    game = find_game_by_turn(user_id)
    if not game:
        await query.edit_message_text("الان نوبت شما نیست یا بازی فعالی پیدا نشد.")
        return

    p = get_player_by_user(game, user_id)
    valid = playable_cards(p, game.leading_suit)
    if card not in p.hand or card not in valid:
        await query.edit_message_text("کارت نامعتبره، دوباره تلاش کنید.")
        return

    p.hand.remove(card)
    game.current_trick.append((p.seat, card))
    if game.leading_suit is None:
        game.leading_suit = card[1]

    await query.edit_message_text(f"شما بازی کردید: {card_str(card)} ✅")
    await context.bot.send_message(game.chat_id, f"🃏 {p.name}: {card_str(card)}")

    if len(game.current_trick) < 4:
        game.turn_seat = (game.turn_seat + 1) % 4
        await prompt_turn(context, game)
    else:
        await resolve_trick(context, game)


def trick_winner(trick, hokm):
    leading_suit = trick[0][1][1]
    trumps = [t for t in trick if t[1][1] == hokm]
    if trumps:
        winner = max(trumps, key=lambda t: t[1][0])
    else:
        same = [t for t in trick if t[1][1] == leading_suit]
        winner = max(same, key=lambda t: t[1][0])
    return winner[0]  # seat


async def resolve_trick(context, game: Game):
    winner_seat = trick_winner(game.current_trick, game.hokm)
    winner = game.players[winner_seat]
    game.tricks[winner.team] += 1

    trick_text = "  ".join(f"{game.players[s].name}:{card_str(c)}" for s, c in game.current_trick)
    await context.bot.send_message(
        game.chat_id,
        f"🏆 این دست رو {winner.name} برد!\n{trick_text}\n"
        f"تعداد دست‌ها: تیم ۱={game.tricks[0]}  تیم ۲={game.tricks[1]}"
    )

    game.current_trick = []
    game.leading_suit = None
    game.turn_seat = winner_seat

    if game.tricks[0] >= TRICKS_TO_WIN_ROUND or game.tricks[1] >= TRICKS_TO_WIN_ROUND:
        await finish_round(context, game)
    else:
        await prompt_turn(context, game)


async def finish_round(context, game: Game):
    winning_team = 0 if game.tricks[0] >= TRICKS_TO_WIN_ROUND else 1
    losing_team = 1 - winning_team
    kot = game.tricks[losing_team] == 0
    points = 2 if kot else 1
    game.scores[winning_team] += points

    names = team_names(game, winning_team)
    msg = f"🎉 تیم {winning_team + 1} ({names}) این دور رو برد! ({game.tricks[winning_team]} دست)\n"
    if kot:
        msg += "💥 کُت! (حریف هیچ دستی نبرد) — ۲ امتیاز\n"
    msg += f"\n📊 امتیازات کل:\nتیم ۱: {game.scores[0]}\nتیم ۲: {game.scores[1]}"
    await context.bot.send_message(game.chat_id, msg)

    if game.scores[winning_team] >= POINTS_TO_WIN:
        await context.bot.send_message(
            game.chat_id, f"🏆🏆 تیم {winning_team + 1} ({names}) برنده نهایی بازی شد! تبریک 🎊"
        )
        game.state = "finished"
        del games[game.chat_id]
        return

    game.round_num += 1
    game.hakem_seat = (game.hakem_seat + 1) % 4
    await start_round(context, game)


# ---------------- Main ----------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("newgame", newgame))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("cancelgame", cancelgame))
    app.add_handler(CommandHandler("score", score_cmd))
    app.add_handler(CommandHandler("myhand", myhand))
    app.add_handler(CallbackQueryHandler(on_hokm_chosen, pattern=r"^hokm:"))
    app.add_handler(CallbackQueryHandler(on_card_played, pattern=r"^play:"))
    app.run_polling()


if __name__ == "__main__":
    main()
