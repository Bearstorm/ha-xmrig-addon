# 🪙 XMRig Miner Add-on for Home Assistant

[![Home Assistant Badge](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
![Architecture x86_64](https://img.shields.io/badge/Arch-x86__64%20(amd64)-orange.svg)

High-performance and fully configurable Monero (XMR) mining add-on for the Home Assistant ecosystem. Optimized for **x86_64 (amd64)** architecture, specifically tuned for Intel 12th Gen processors.
---

## 💻 System Requirements

To run this miner efficiently without crashing your Home Assistant, we recommend:

* **Minimum CPU:** 4-core x86_64 processor (e.g., Intel Celeron J4125 or newer).
* **Recommended CPU:** Intel Core i5/i7 (10th Gen+) or AMD Ryzen 5+. Higher L3 cache significantly improves hashrate.
* **RAM:** 4GB minimum. 8GB+ recommended if running Frigate or other heavy Add-ons.
* **Storage:** 500MB free space for the container.
* **OS:** Home Assistant OS or Home Assistant Supervised on Debian 12.

**Note for Raspberry Pi users:** This add-on is compiled for **amd64** only. It will not work on Raspberry Pi (ARM).
---

### 🚀 Features
* ⚙️ **Architecture Optimized:** Specifically tuned for modern x86_64 CPUs.
* 🏠 **Native Integration:** Runs as a standard Home Assistant service.
* ⚖️ **Resource Management:** Uses low process priority to ensure critical services like **Frigate** or **Zigbee2MQTT** remain unaffected.
* 🛠️ **Full Control:** Configure CPU threads and priority directly via the web interface.

---

### 📥 Installation

1. In Home Assistant, navigate to **Settings** ➡️ **Add-ons** ➡️ **Add-on Store**.
2. Click the **⋮** (top right) and select **Repositories**.
3. Add the following URL: `https://github.com/Bearstorm/ha-xmrig-addon`
4. Click **Add**, then **Close**.
5. Search for **"XMRig Miner"** and click **Install**.

---

### ⚙️ Configuration Explained

Each option in the configuration tab affects miner behavior and system resource allocation:

| Option | Description | System Impact |
| :--- | :--- | :--- |
| **`pool`** | Pool address (e.g., `pool.supportxmr.com`). | Determines where your hashing power is directed. |
| **`port`** | Connection port (Standard `5555`, or `443` for TLS). | Port 443 with TLS enabled masks mining as standard HTTPS traffic. |
| **`user`** | Your Monero (XMR) wallet address. | **Critical:** If the address is incorrect, you will not receive rewards. |
| **`pass`** | Worker name (e.g., `HP_Pro_Mini`). | Used to identify your machine in pool statistics. |
| **`threads`** | Number of allocated CPU threads. | **Performance:** Higher value = higher hashrate/temp. Keep at least 2 threads free for the OS. |
| **`priority`** | CPU scheduling priority (0 to 5). | **2 (Recommended):** Ensures Home Assistant stability while maintaining mining performance. |

---

### ⚡ Performance Optimization (MSR Mod)
To resolve the `FAILED TO APPLY MSR MOD` error and increase performance by ~20%, you must allow access to CPU registers:

1. **On your Debian Host (Terminal):**
   Run these commands to enable MSR support:
   ```bash
   sudo apt update && sudo apt install msr-tools -y
   sudo modprobe msr
In Home Assistant:

        Go to Settings -> Add-ons -> XMRig Miner.

        Open the Info tab.

        Turn OFF "Protection mode".

        Restart the add-on.

⚠️ Disclaimer & Risks

    Security: Disabling "Protection mode" grants the add-on direct access to hardware (CPU registers). Only do this if you trust the source code.

    Temperature: Mining significantly increases CPU temperature. Ensure your hardware has adequate cooling.

    Stability: Allocating too many threads may cause lag in Frigate video processing or automation delays.

Use this add-on at your own risk.
---

## 📄 License
This project is licensed under the **Creative Commons Attribution-NoDerivs 4.0 International (CC BY-ND 4.0)**.
- You are free to share and use this add-on.
- You **cannot** distribute modified versions of this code.
