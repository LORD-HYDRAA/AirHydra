#!/bin/bash
# ╔══════════════════════════════════════════════╗
# ║         AirHydra — By Lord-Hydra             ║
# ║         AirHydra.sh — Launcher & Setup       ║
# ╚══════════════════════════════════════════════╝

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"
CONFIG_FILE="$CONFIG_DIR/system.txt"
REQ_FILE="$SCRIPT_DIR/requirements.txt"

# ── Colors ──────────────────────────────────────
R="\033[1;31m"
G="\033[1;32m"
Y="\033[1;33m"
C="\033[1;36m"
W="\033[1;37m"
M="\033[1;35m"
DIM="\033[2m"
RST="\033[0m"

info()  { echo -e "  ${G}[+]${RST} $1"; }
warn()  { echo -e "  ${Y}[!]${RST} $1"; }
err()   { echo -e "  ${R}[✗]${RST} $1"; }
step()  { echo -e "  ${C}[»]${RST} $1"; }

# ── Banner ───────────────────────────────────────
banner() {
    clear
    echo -e "${R}"
    echo '   ___    _               _   _               _                '
    echo '  / _ \  (_)             | | | |             | |               '
    echo ' / /_\ \  _   _ __       | |_| |  _   _    __| |  _ __    __ _ '
    echo "|  _  | | | | '__|      |  _  | | | | |  / _\` | | '__|  / _\` |"
    echo '| | | | | | | |         | | | | | |_| | | (_| | | |    | (_| |'
    echo '\_| |_/ |_| |_|         \_| |_/  \__, |  \__,_| |_|     \__,_|'
    echo '                                  __/ |                       '
    echo '                                 |___/                        '
    echo -e "${RST}${DIM}  ╔══════════════════════════════════════════╗"
    echo    "  ║   WiFi Auditing Tool v1.0  │ Lord-Hydra  ║"
    echo -e "  ╚══════════════════════════════════════════╝${RST}"
    echo ""
}

# ── Detect distro family ─────────────────────────
detect_distro_family() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        ID_LOWER=$(echo "${ID_LIKE:-$ID}" | tr '[:upper:]' '[:lower:]')
        if echo "$ID_LOWER" | grep -qE "debian|ubuntu|kali|parrot|mint|pop"; then
            echo "debian"
        elif echo "$ID_LOWER" | grep -qE "arch|manjaro|blackarch|endeavour|artix"; then
            echo "arch"
        elif echo "$ID_LOWER" | grep -qE "fedora|rhel|centos|rocky|alma"; then
            echo "fedora"
        else
            echo "unknown"
        fi
    else
        echo "unknown"
    fi
}

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "${NAME} ${VERSION_ID}"
    elif [ -f /etc/issue ]; then
        head -1 /etc/issue | tr -d '\n'
    else
        echo "Unknown"
    fi
}

# ── Package manager installer ────────────────────
install_pkg() {
    local pkg="$1"
    local family="$2"
    case "$family" in
        debian)
            apt-get install -y "$pkg" -qq > /dev/null 2>&1
            ;;
        arch)
            pacman -S --noconfirm "$pkg" > /dev/null 2>&1
            ;;
        fedora)
            dnf install -y "$pkg" > /dev/null 2>&1
            ;;
        *)
            return 1
            ;;
    esac
}

# ── Get package name for distro ──────────────────
get_pkg_name() {
    local tool="$1"
    local family="$2"
    # Read from requirements.txt
    local line
    line=$(grep "^$tool|" "$REQ_FILE" 2>/dev/null)
    [ -z "$line" ] && echo "$tool" && return
    case "$family" in
        debian) echo "$line" | cut -d'|' -f2 ;;
        arch)   echo "$line" | cut -d'|' -f3 ;;
        fedora) echo "$line" | cut -d'|' -f4 ;;
        *)      echo "$tool" ;;
    esac
}

# ── Detect terminal ──────────────────────────────
detect_terminal() {
    export DISPLAY="${DISPLAY:-:0}"
    if command -v x-terminal-emulator >/dev/null 2>&1; then
        echo "x-terminal-emulator|$(which x-terminal-emulator)"
        return
    fi
    if command -v exo-open >/dev/null 2>&1; then
        echo "exo-open|$(which exo-open)"
        return
    fi
    local terms=("gnome-terminal" "xfce4-terminal" "konsole" "kitty"
                  "alacritty" "lxterminal" "mate-terminal" "terminator"
                  "tilix" "xterm")
    for t in "${terms[@]}"; do
        local p
        p=$(which "$t" 2>/dev/null)
        if [ -n "$p" ]; then
            echo "$t|$p"
            return
        fi
        for dir in /usr/bin /usr/local/bin /bin; do
            if [ -x "$dir/$t" ]; then
                echo "$t|$dir/$t"
                return
            fi
        done
    done
    echo "none|none"
}

# ── Check & install requirements ─────────────────
check_requirements() {
    local family="$1"
    echo ""
    echo -e "  ${M}─────────────────────────────────────────────"
    echo    "  CHECKING REQUIREMENTS"
    echo -e "  ─────────────────────────────────────────────${RST}"
    echo ""

    local missing=()
    local installed=()

    # Read requirements.txt — skip comments and empty lines
    while IFS='|' read -r tool apt_pkg pacman_pkg dnf_pkg desc; do
        [[ "$tool" =~ ^#.*$ || -z "$tool" ]] && continue
        tool=$(echo "$tool" | tr -d ' ')
        if command -v "$tool" >/dev/null 2>&1; then
            info "$tool — ${G}OK${RST}"
            installed+=("$tool")
        else
            warn "$tool — ${R}MISSING${RST} ($desc)"
            missing+=("$tool")
        fi
    done < "$REQ_FILE"

    if [ ${#missing[@]} -eq 0 ]; then
        echo ""
        info "All requirements satisfied!"
        return 0
    fi

    echo ""
    warn "${#missing[@]} tool(s) missing. Installing..."
    echo ""

    if [ "$family" = "unknown" ]; then
        err "Unknown distro — cannot auto-install."
        err "Please install manually: ${missing[*]}"
        return 1
    fi

    # Check if running as root for install
    if [ "$EUID" -ne 0 ]; then
        warn "Need root to install packages. Re-running with sudo..."
        exec sudo -E bash "$0" "$@"
    fi

    # Update package list first
    step "Updating package lists..."
    case "$family" in
        debian) apt-get update -qq > /dev/null 2>&1 ;;
        arch)   pacman -Sy > /dev/null 2>&1 ;;
        fedora) dnf check-update > /dev/null 2>&1 ;;
    esac

    # Install missing tools
    local failed=()
    for tool in "${missing[@]}"; do
        pkg=$(get_pkg_name "$tool" "$family")
        step "Installing $tool ($pkg)..."
        if install_pkg "$pkg" "$family"; then
            info "$tool installed!"
        else
            err "$tool — install failed! Install manually: $pkg"
            failed+=("$tool")
        fi
    done

    if [ ${#failed[@]} -gt 0 ]; then
        warn "Failed to install: ${failed[*]}"
        warn "Please install them manually and re-run AirHydra."
    fi

    echo ""
}



# ── Build config ─────────────────────────────────
build_config() {
    echo ""
    echo -e "  ${M}─────────────────────────────────────────────"
    echo    "  FIRST RUN — Building System Config"
    echo -e "  ─────────────────────────────────────────────${RST}"
    echo ""

    mkdir -p "$CONFIG_DIR"

    REAL_USER="${SUDO_USER:-$USER}"
    REAL_HOME=$(eval echo "~$REAL_USER")

    step "Detecting distro..."
    DISTRO=$(detect_distro)
    DISTRO_FAMILY=$(detect_distro_family)
    info "Distro       : $DISTRO"
    info "Distro family: $DISTRO_FAMILY"

    step "Detecting display..."
    if [ -n "$DISPLAY" ]; then
        DISP="$DISPLAY"
    elif [ -n "$WAYLAND_DISPLAY" ]; then
        DISP="$WAYLAND_DISPLAY"
    else
        DISP=$(su - "$REAL_USER" -c 'echo $DISPLAY' 2>/dev/null)
        [ -z "$DISP" ] && DISP=":0"
    fi
    info "Display: $DISP"

    step "Detecting terminal..."
    TERM_INFO=$(detect_terminal)
    TERM_NAME=$(echo "$TERM_INFO" | cut -d'|' -f1)
    TERM_PATH=$(echo "$TERM_INFO" | cut -d'|' -f2)
    if [ "$TERM_NAME" = "none" ]; then
        warn "No terminal found — new windows will run in background."
    else
        info "Terminal: $TERM_NAME ($TERM_PATH)"
    fi

    step "Detecting Python3..."
    PY=$(which python3 2>/dev/null || which python 2>/dev/null)
    if [ -z "$PY" ]; then
        err "Python3 not found! Install python3 first."
        exit 1
    fi
    info "Python: $PY"

    # Install requirements first (ensure hashcat is available for detection)
    check_requirements "$DISTRO_FAMILY"

    step "Detecting GPU support (Hashcat)..."
    if hashcat -I 2>/dev/null | grep -iE "CUDA|OpenCL|GPU" >/dev/null 2>&1; then
        GPU_AVAILABLE="yes"
        info "GPU detected! Enabling advanced modes."
    else
        GPU_AVAILABLE="no"
        warn "No compatible GPU found. Using CPU mode only."
    fi

    # Write config
    cat > "$CONFIG_FILE" << CFGEOF
# AirHydra System Config
# Generated: $(date)
# Delete this file to regenerate

DISTRO=$DISTRO
DISTRO_FAMILY=$DISTRO_FAMILY
REAL_USER=$REAL_USER
REAL_HOME=$REAL_HOME
DISPLAY=$DISP
TERMINAL_NAME=$TERM_NAME
TERMINAL_PATH=$TERM_PATH
PYTHON=$PY
SCRIPT_DIR=$SCRIPT_DIR
GPU_AVAILABLE=$GPU_AVAILABLE
CFGEOF

    info "Config saved → $CONFIG_FILE"
    echo ""

    # Install requirements
    # check_requirements "$DISTRO_FAMILY" (moved earlier)

    echo ""
    echo -e "  ${M}─────────────────────────────────────────────${RST}"
    echo ""
    sleep 1
}

# ── Launch AirHydra ──────────────────────────────
launch() {
    PY=$(grep "^PYTHON=" "$CONFIG_FILE" | cut -d= -f2)
    [ -z "$PY" ] && PY="python3"

    if [ "$EUID" -ne 0 ]; then
        warn "AirHydra needs root. Re-launching with sudo..."
        echo ""
        exec sudo -E bash "$0" "$@"
    fi

    exec "$PY" "$SCRIPT_DIR/airhydra.py"
}

# ── Main ─────────────────────────────────────────
banner

if [ ! -f "$CONFIG_FILE" ]; then
    warn "No config found — running first-time setup..."
    build_config
else
    # Config exists — just verify requirements quickly
    FAMILY=$(grep "^DISTRO_FAMILY=" "$CONFIG_FILE" | cut -d= -f2)
    info "Config found → $CONFIG_FILE"

    # Quick check — any tools missing?
    MISSING_COUNT=0
    while IFS='|' read -r tool rest; do
        [[ "$tool" =~ ^#.*$ || -z "$tool" ]] && continue
        tool=$(echo "$tool" | tr -d ' ')
        command -v "$tool" >/dev/null 2>&1 || MISSING_COUNT=$((MISSING_COUNT + 1))
    done < "$REQ_FILE"

    if [ "$MISSING_COUNT" -gt 0 ]; then
        warn "$MISSING_COUNT tool(s) missing — running requirement check..."
        check_requirements "$FAMILY"
    fi

    # Ensure GPU_AVAILABLE is in the config
    if ! grep -q "^GPU_AVAILABLE=" "$CONFIG_FILE"; then
        step "Detecting GPU support (Hashcat)..."
        if hashcat -I 2>/dev/null | grep -iE "CUDA|OpenCL|GPU" >/dev/null 2>&1; then
            GPU_AVAIL="yes"
            info "GPU detected! Enabling advanced modes."
        else
            GPU_AVAIL="no"
            warn "No compatible GPU found. Using CPU mode only."
        fi
        echo "GPU_AVAILABLE=$GPU_AVAIL" >> "$CONFIG_FILE"
    fi
    echo ""
fi

launch "$@"
