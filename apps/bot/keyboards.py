from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_continent_keyboard(continents: list[dict], prefix: str) -> InlineKeyboardMarkup:
    rows, row = [], []
    for c in continents:
        row.append(InlineKeyboardButton(c["name"], callback_data=f"cn:{prefix}:{c['code']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def build_country_page_keyboard(
    prefix: str, continent_code: str, page_data: dict
) -> InlineKeyboardMarkup:
    rows = []
    for c in page_data["items"]:
        label = f"{c['flag_emoji']} {c['name']}".strip()
        rows.append([InlineKeyboardButton(label, callback_data=f"ctry:{prefix}:{c['iso2']}")])

    nav = []
    page = page_data["page"]
    if page_data["has_prev"]:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"cnp:{prefix}:{continent_code}:{page - 1}"))
    if page_data["has_next"]:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"cnp:{prefix}:{continent_code}:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)


def build_region_keyboard(prefix: str, iso2: str, regions: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton("🌍 Whole country", callback_data=f"act:{prefix}:{iso2}:-")]]
    row = []
    for r in regions:
        row.append(InlineKeyboardButton(r["name"], callback_data=f"act:{prefix}:{iso2}:{r['slug']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def action_keyboard(iso2: str, region_slug: str | None) -> InlineKeyboardMarkup:
    slug = region_slug or "-"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔔 Subscribe", callback_data=f"act:subscribe:{iso2}:{slug}"),
        InlineKeyboardButton("📄 Get Report", callback_data=f"act:report:{iso2}:{slug}"),
    ]])
