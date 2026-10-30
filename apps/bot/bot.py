from __future__ import annotations
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .keyboards import (
    action_keyboard,
    build_continent_keyboard,
    build_country_page_keyboard,
    build_region_keyboard,
)
from .utils import (
    ensure_profile,
    get_continents,
    get_country_and_regions,
    get_countries_page,
    get_latest_prices,
    list_subscriptions,
    nearest_location,
    request_report,
    search_countries,
    toggle_subscription,
)

logger = logging.getLogger(__name__)

_WELCOME = (
    "\U0001f44b <b>Welcome to Zetrix</b>\n\n"
    "I track rental prices worldwide and alert you when they move.\n\n"
    "<b>Commands:</b>\n"
    "/prices [country] — current prices\n"
    "/subscribe [country] — price-change alerts\n"
    "/unsubscribe [country] — remove alert\n"
    "/mysubscriptions — active alerts\n"
    "/report [country] — receive a PDF report\n\n"
    "Run a command with no argument to browse by continent, or pass a "
    "country name/code directly (e.g. <code>/prices Indonesia</code>).\n"
    "Or <b>share your location</b> \U0001f4cd to find the nearest area automatically."
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username or ""
    await ensure_profile(chat_id, username)
    await update.message.reply_text(
        _WELCOME
        + f"\n\nYour Telegram Chat ID is <code>{chat_id}</code> — "
        + "paste it into your profile on the Zetrix site to link notifications to your account.",
        parse_mode="HTML",
    )


async def _start_picker_or_search(update: Update, context: ContextTypes.DEFAULT_TYPE, prefix: str) -> None:
    if context.args:
        query = " ".join(context.args)
        matches = await search_countries(query)
        if not matches:
            await update.message.reply_text(f"No country found matching “{query}”.")
            return
        if len(matches) == 1:
            await _select_country(update, prefix, matches[0]["iso2"], via_callback=False)
            return
        rows_text = "\n".join(f"• {m['flag_emoji']} {m['name']} ({m['iso2']})" for m in matches)
        await update.message.reply_text(
            f"Multiple matches for “{query}”, try the exact ISO code:\n{rows_text}"
        )
        return

    continents = await get_continents()
    await update.message.reply_text(
        "Choose a continent:", reply_markup=build_continent_keyboard(continents, prefix)
    )


async def cmd_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _start_picker_or_search(update, context, "prices")


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _start_picker_or_search(update, context, "subscribe")


async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _start_picker_or_search(update, context, "unsubscribe")


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _start_picker_or_search(update, context, "report")


async def cmd_my_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    subs = await list_subscriptions(chat_id)
    if not subs:
        await update.message.reply_text(
            "You have no active subscriptions.\nUse /subscribe to add one."
        )
        return
    lines = ["<b>Your active subscriptions:</b>"]
    for s in subs:
        lines.append(
            f"• {s['label']} ({s['market_type']}) — ≥{s['threshold_pct']}% {s['direction']}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    loc = update.message.location
    nearest = await nearest_location(loc.latitude, loc.longitude)
    if not nearest:
        await update.message.reply_text("No location data available yet.")
        return
    await update.message.reply_text(
        f"\U0001f4cd Nearest area: <b>{nearest['label']}</b>", parse_mode="HTML"
    )
    await _send_prices(update, nearest["country_iso2"], nearest["region_slug"])


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    kind = parts[0]

    if kind == "cn":
        _, prefix, code = parts
        page_data = await get_countries_page(code, 0)
        await query.edit_message_text(
            "Choose a country:",
            reply_markup=build_country_page_keyboard(prefix, code, page_data),
        )
    elif kind == "cnp":
        _, prefix, code, page = parts
        page_data = await get_countries_page(code, int(page))
        await query.edit_message_text(
            "Choose a country:",
            reply_markup=build_country_page_keyboard(prefix, code, page_data),
        )
    elif kind == "ctry":
        _, prefix, iso2 = parts
        await _select_country(update, prefix, iso2, via_callback=True)
    elif kind == "act":
        _, prefix, iso2, slug = parts
        region_slug = None if slug == "-" else slug
        dispatch = {
            "prices": _send_prices,
            "subscribe": _do_subscribe,
            "unsubscribe": _do_unsubscribe,
            "report": _do_report,
        }
        handler = dispatch.get(prefix)
        if handler:
            await handler(update, iso2, region_slug, via_callback=True)


async def _select_country(update: Update, prefix: str, iso2: str, via_callback: bool) -> None:
    info = await get_country_and_regions(iso2)
    if not info:
        return
    if info["regions"]:
        markup = build_region_keyboard(prefix, iso2, info["regions"])
        text = f"{info['flag_emoji']} <b>{info['name']}</b> — choose a region:"
        if via_callback:
            await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)
        return

    dispatch = {
        "prices": _send_prices,
        "subscribe": _do_subscribe,
        "unsubscribe": _do_unsubscribe,
        "report": _do_report,
    }
    await dispatch[prefix](update, iso2, None, via_callback=via_callback)


# --- Shared action helpers ---

async def _send_prices(update: Update, iso2: str, region_slug: str | None, via_callback: bool = False) -> None:
    info = await get_country_and_regions(iso2)
    label = next(
        (r["name"] for r in (info["regions"] if info else []) if r["slug"] == region_slug),
        info["name"] if info else iso2,
    )
    data = await get_latest_prices(iso2, region_slug)

    if not data:
        msg = (
            f"\U0001f4ca <b>{label} — Rental</b>\n\n"
            "No price data available yet.\n"
            "Scrapers have not run for this location."
        )
    else:
        change_line = ""
        if data["change"] is not None:
            arrow = "\U0001f4c8" if data["change"] > 0 else "\U0001f4c9"
            change_line = f"{arrow} Change: <b>{data['change']:+.1f}%</b>\n"
        msg = (
            f"\U0001f4ca <b>{label} — Rental</b>\n"
            f"Date: {data['date']}\n\n"
            f"\U0001f4b5 Average: <b>${data['avg']:.0f}/night</b>\n"
            f"⬇️ Min: ${data['min']:.0f}   "
            f"⬆️ Max: ${data['max']:.0f}\n"
            f"\U0001f3e0 Listings: {data['count']}\n"
            f"{change_line}"
        )

    keyboard = action_keyboard(iso2, region_slug)
    if via_callback:
        await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=keyboard)
    else:
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)


async def _do_subscribe(update: Update, iso2: str, region_slug: str | None, via_callback: bool = False) -> None:
    chat_id = str(update.effective_chat.id)
    result = await toggle_subscription(chat_id, iso2, region_slug, activate=True)
    if result == "no_profile":
        msg = "Please /start first to register your account."
    else:
        msg = "✅ Subscribed! You will be notified when rental prices change by ≥5%."
    _reply = update.callback_query.edit_message_text if via_callback else update.message.reply_text
    await _reply(msg, parse_mode="HTML")


async def _do_unsubscribe(update: Update, iso2: str, region_slug: str | None, via_callback: bool = False) -> None:
    chat_id = str(update.effective_chat.id)
    await toggle_subscription(chat_id, iso2, region_slug, activate=False)
    msg = "\U0001f515 Unsubscribed."
    _reply = update.callback_query.edit_message_text if via_callback else update.message.reply_text
    await _reply(msg, parse_mode="HTML")


async def _do_report(update: Update, iso2: str, region_slug: str | None, via_callback: bool = False) -> None:
    chat_id = str(update.effective_chat.id)
    await request_report(chat_id, iso2, region_slug)
    msg = "\U0001f4c4 Generating report... You will receive the PDF in a few moments!"
    _reply = update.callback_query.edit_message_text if via_callback else update.message.reply_text
    await _reply(msg, parse_mode="HTML")


def build_app(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("prices", cmd_prices))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("mysubscriptions", cmd_my_subscriptions))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(handle_callback))
    return app
