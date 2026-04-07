# AirHydra — The Unified Wi-Fi Security Framework

<div align="center">

```text
  ___    _               _   _               _                
 / _ \  (_)             | | | |             | |               
/ /_\ \  _   _ __       | |_| |  _   _    __| |  _ __    __ _ 
|  _  | | | | '__|      |  _  | | | | |  / _` | | '__|  / _` |
| | | | | | | |         | | | | | |_| | | (_| | | |    | (_| |
\_| |_/ |_| |_|         \_| |_/  \__, |  \__,_| |_|     \__,_|
                                 __/ |                       
                                |___/                        
```

</div>

**AirHydra** is a professional, hardware-aware Wi-Fi security framework built in Python and Bash. Designed for the "New Generation" of Red Teaming, it merges powerful automated reconnaissance with high-speed handshake cracking.

---

## ⚡ Main Features

- **Hardware-Aware Cracking**: 
  - Automatically identifies CPU, NVIDIA (CUDA), and OpenCL GPU availability.
  - Dynamically adjusts the Cracking Menu to offer only supported device modes.
- **Intelligent Reconnaissance**:
  - Automated Monitor Mode toggling with network stack cleanup.
  - Live AP scanning with BSSID and Channel filtering.
- **Advanced Attack Suite**:
  - **Auto-Deauth Handshake**: Runs dual-terminals for simultaneous Deauth and Capture.
  - **Red Team Toolset**: Handshake parsing with `tshark` integration for verification.
- **Universal Linux Support (Distro-Agnostic)**:
  - Built-in requirement engine for **Debian/Ubuntu/Kali**, **Arch/Manjaro**, and **Fedora/RHEL**.
  - Persistent `system.txt` configuration for zero-config launches after setup.

---

## 🚀 Getting Started

AirHydra is designed to be plug-and-play. The launcher script handles all dependencies and environment configuration.

### 1. Clone & Setup
```bash
git clone https://github.com/LORD-HYDRAA/AirHydra.git
cd AirHydra
chmod +x AirHydra.sh
```

### 2. Launch
```bash
./AirHydra.sh
```

> [!NOTE]
> The first run will automatically build `config/system.txt`, detect your terminal environment, and install any missing tools from `requirements.txt`.

---

## 🛠 Project Components

| File | Purpose |
| :--- | :--- |
| `AirHydra.sh` | The main entry point. Handles setup, config, and system-level initialization. |
| `airhydra.py` | The core framework engine. Manages attack logic, UI rendering, and hardware detection. |
| `requirements.txt`| Cross-distro dependency list for one-click installation support. |
| `config/system.txt` | Persistent environment variables (Auto-generated). |

---

## 📶 System Requirements

AirHydra relies on industry-standard wireless tools. The setup script will attempt to install these for you:

| Category | Tools | Package (Debian) |
| :--- | :--- | :--- |
| **Wireless** | `airmon-ng`, `iw`, `iwconfig` | `aircrack-ng`, `iw`, `wireless-tools` |
| **Forensics** | `tshark` | `tshark` |
| **Cracking** | `hashcat`, `hcxpcapngtool` | `hashcat`, `hcxtools` |
| **Runtime** | `python3`, `python3-pip` | `python3`, `python3-pip` |

---

## ⚖️ Legal Disclaimer

> [!CAUTION]
> This tool is developed for **educational and authorized security testing purposes only**. 
> Unauthorized access to networks or devices without explicit permission is illegal and unethical. The developer assumes no liability for misuse or damage caused by this program. Use responsibly.

---

**Developed with ❤️ for the Offensive Security Community.**
