<h1 align="center">AirHydra — The Unified Wi-Fi Security Framework</h1>

<div align="center">
<table>
<tr>
<td>
<pre>
  ___    _               _   _               _                
 / _ \  (_)             | | | |             | |               
/ /_\ \  _   _ __       | |_| |  _   _    __| |  _ __    __ _ 
|  _  | | | | '__|      |  _  | | | | |  / _` | | '__|  / _` |
| | | | | | | |         | | | | | |_| | | (_| | | |    | (_| |
\_| |_/ |_| |_|         \_| |_/  \__, |  \__,_| |_|     \__,_|
                                 __/ |                       
                                |___/                        
</pre>
</td>
</tr>
</table>

**Wireless Security Framework (Red+Blue) │ Lord-Hydra │**
</div>

---

**AirHydra** is a professional, hardware-aware Wi-Fi security framework built in Python and Bash. It bridges the gap between offensive Red Teaming and defensive Blue Teaming by providing a unified environment for wireless audits, live monitoring, and forensic tracking.

> [!IMPORTANT]
> AirHydra is designed for **authorized security auditing and educational purposes only**. Using this tool on networks you do not own or have explicit permission to test is illegal and unethical.

---

## 🔴 Red Team Operations (Offensive)

The Red Team suite focuses on efficient reconnaissance, automated handshake acquisition, and high-performance cracking.

### 1. Intelligent Reconnaissance
- **Live AP Scanning**: Scans across 2.4GHz and 5GHz bands (ABG).
- **Signal Filtering**: Real-time RSSI visualization with distance-based color coding.
- **Auto-Monitor**: Automated monitor mode toggling with a full network stack cleanup to prevent interference.

### 2. Handshake Acquisition
- **Normal Capture**: Standard, manual capture workflow via `airodump-ng`.
- **Advanced Auto-Deauth**: AirHydra orchestrates a multi-terminal attack. It launches a dedicated Capture Terminal and a Deauth Trigger Terminal simultaneously, ensuring the handshake is captured at the precise moment of client disconnection.
- **Fast Handshake Checker**: Integrated `tshark` engine that performs parallel-threaded verification of captured handshakes, ensuring you never waste time on empty `.cap` files.

### 3. Cracking Engine
- **Hardware-Aware Crack**: Automatically detects your system's hardware capabilities (NVIDIA CUDA, OpenCL, or CPU).
- **Multi-Mode Hashcat**: Run Hashcat in CPU, GPU, or Hybrid modes. 
- **Aircrack-ng Fallback**: Automatic fallback to `aircrack-ng` if `hashcat` or specialized hardware is unavailable.
- **Result Management**: Crack results are automatically serialized and saved to `captures/cracked/`.

### 4. Capture Hygiene
- **Empty Cap Cleanup**: Automatically scans your capture library for files without valid handshakes and offers a one-click purge to keep your workspace clean.

---

## 🔵 Blue Team Sentinel (Defensive)

The Blue Team suite provides real-time situational awareness and forensic capabilities to detect and track wireless threats.

### 1. Global Network Monitor
- **Active Traffic Sentinel**: Monitors all nearby Access Points and client stations simultaneously.
- **Anomaly Detection**: 
  - **Duplicate MACs**: Identifies MAC address spoofing in real-time.
  - **MAC Flipping**: Detects stations jumping between BSSIDs suspiciously.
  - **RSSI Instability**: Tracks signal jumps that indicate hardware spoofing or distance anomalies.

### 2. Targeted Network Sentinel
- **AP-Lock Monitoring**: Lock AirHydra onto a specific network (SSID/BSSID) for deep inspection.
- **Client Classification**: Automatically classifies all connected clients as:
  - `LEGITIMATE`: Standard behavior.
  - `SUSPICIOUS`: Minor anomalies detected.
  - `LIKELY SPOOFED`: High-confidence spoofing indicators identified.

### 3. Device Forensic Tracker
- **MAC-Level Tracking**: Focus all defensive resources on a single MAC address.
- **History Trending**: Visualizes RSSI trends and AP-hop history for the selected target.
- **Confidence Scoring**: Dynamic 0–100 confidence score based on behavioral forensic logic.

### 4. Rogue AP (Evil Twin) Hunter
- **SSID Reconciliation**: Scans for duplicate SSIDs.
- **Inconsistency Engine**: Flags Rogue APs by identifying differences in Encryption (e.g., OPN vs WPA2), Channel/Band discrepancies, or Signal Power anomalies within the same SSID group.

---

## ⚡ Hardware-Aware Engine

AirHydra is built for high-performance hardware. 
- **Dynamic Menus**: The framework queries your system for GPU (CUDA/OpenCL) support during boot. If a compatible GPU is found, advanced cracking modes are unlocked automatically.
- **Terminal Orchestration**: Automatically detects your Linux terminal (Gnome, XFCE, Kitty, Alacritty, etc.) to launch multi-window attacks seamlessly.

---

## 🚀 Getting Started

### 1. Clone & Setup
```bash
git clone https://github.com/LORD-HYDRAA/AirHydra.git
cd AirHydra
chmod +x AirHydra.sh
```

### 2. Launch
```bash
sudo ./AirHydra.sh
```

### 3. Configuration
On the first run, AirHydra will auto-generate `config/system.txt`. This file maintains your terminal path, display settings, and detected hardware preferences for zero-config subsequent launches.

---

## 🛠 Required Core Tools

AirHydra abstracts the complexity of several industry-standard tools:

| Category | Primary Tools |
| :--- | :--- |
| **Wireless Stack** | `airmon-ng`, `airodump-ng`, `aireplay-ng`, `iw` |
| **Forensics** | `tshark` |
| **Cracking** | `hashcat`, `hcxpcapngtool`, `aircrack-ng` |
| **Runtime** | `Python 3.x`, `pip3` |

---

## ⚖️ Legal & Security

AirHydra is developed with strict adherence to legal and security standards. 

**The developer is not responsible for any user action or misuse of this tool.**

- **[LICENSE](LICENSE)**: Detailed terms for redistributions and private use.
- **[SECURITY.md](SECURITY.md)**: Our vulnerability disclosure policy.
- **[TERMS OF USE](TERMS_OF_USE.md)**: Comprehensive liability disclaimers.
- **[LIMITATIONS](LIMITATIONS.md)**: Technical boundaries and legal constraints.

---
**Developed By Lord Hydra (Mohemmed Zaid Khan) for the Offensive & Defensive Security Communities.**
