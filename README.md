# 🪙 XMRig Miner Add-on for Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
![Architecture](https://img.shields.io/badge/Arch-amd64-orange.svg)
![HAOS Compatible](https://img.shields.io/badge/HAOS-Compatible-green.svg)
![Supervised](https://img.shields.io/badge/Supervised-Debian%2012-blue.svg)
![MSR Optional](https://img.shields.io/badge/MSR-Optional-yellow.svg)
![RandomX Optimized](https://img.shields.io/badge/RandomX-Optimized-red.svg)

High-performance and fully configurable **Monero (XMR)** mining add-on for the Home Assistant ecosystem.  
Optimized for **x86_64 (amd64)** architecture and tuned for modern Intel (10th–12th Gen) and AMD processors.

> ⚠ **Important:** Versions older than **6.21.6** are not recommended due to unstable MSR handling and privilege inconsistencies.

---

## 📑 Table of Contents

- [System Requirements](#-system-requirements)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [MSR Optimization (Advanced)](#-msr-optimization-advanced)
- [Security Model](#-security-model)
- [Performance Notes](#-performance-notes)
- [Troubleshooting](#-troubleshooting)
- [Risks & Disclaimer](#-risks--disclaimer)
- [License](#-license)

---

## 💻 System Requirements

To ensure stable operation alongside Home Assistant:

- **Architecture:** x86_64 (Intel or AMD)  
  ARM devices (e.g., Raspberry Pi) are **NOT supported**
- **Minimum CPU:** 4 cores
- **Recommended CPU:** Intel i5/i7 (10th Gen+) or AMD Ryzen 5+
- **RAM:** 4GB minimum (8GB+ recommended if running Frigate)
- **Storage:** ~500MB free
- **OS:**  
  - Home Assistant OS (HAOS)  
  - Home Assistant Supervised (Debian 12 recommended)

---

## 📥 Installation

1. Navigate to **Settings → Add-ons → Add-on Store**
2. Click **⋮ → Repositories**
3. Add:

```
https://github.com/Bearstorm/ha-xmrig-addon
```

4. Install **XMRig Miner**
5. Configure wallet and pool
6. Start the add-on

---

## ⚙ Configuration

| Option | Description | Recommended |
|--------|------------|------------|
| `pool` | Mining pool address | pool.supportxmr.com |
| `port` | Pool port (443 enables TLS) | 443 |
| `wallet` | Your Monero wallet address | Required |
| `worker` | Worker name identifier | HA |
| `threads` | CPU threads used | Total threads - 2 |
| `priority` | CPU priority (0–5) | 2 |
| `msr_mod` | Enables MSR optimization | true (if supported) |

---

## ⚡ MSR Optimization (Advanced)

MSR (Model Specific Register) optimization can increase RandomX performance by up to **~20%** on supported Intel CPUs.

### Built-in MSR Toggle

From version **6.21.6+**, MSR can be controlled directly:

| Setting | Behavior |
|----------|----------|
| `msr_mod: true` | Enables MSR optimization |
| `msr_mod: false` | Disables MSR completely |

If disabled, XMRig runs normally (slightly lower hashrate, fully stable).

---

### 🖥 Home Assistant Supervised (Debian Host)

MSR must be enabled on the **host system**, not inside the container:

```bash
sudo apt update
sudo apt install msr-tools -y
echo "msr" | sudo tee -a /etc/modules
sudo modprobe msr
```

Then in Home Assistant:

1. Open the add-on  
2. Go to **Info** tab  
3. Disable **Protection Mode**  
4. Restart the add-on  
5. Enable `msr_mod` in Configuration  

---

### 🧩 Home Assistant OS (HAOS)

1. Open the add-on  
2. Go to **Info** tab  
3. Disable **Protection Mode**  
4. Restart the add-on  
5. Enable `msr_mod` in Configuration  

> ℹ Some HAOS kernel versions may restrict MSR access even with Protection Mode disabled.

---

## 🔐 Security Model

This add-on uses elevated privileges when MSR is enabled.

### Protection Mode

| Mode | Effect |
|------|--------|
| Enabled | Restricted hardware access |
| Disabled | Full hardware access (required for MSR) |

Disabling Protection Mode grants hardware-level CPU register access.

Only disable if you trust the source code.

---

## 📊 Performance Notes

Example performance (i5-12500T):

| Threads | MSR | Hashrate |
|----------|------|-----------|
| 2 | OFF | ~2000 H/s |
| 2 | ON | ~2400 H/s |
| 4 | ON | ~2500 H/s |

Performance depends heavily on:
- L3 cache size
- Memory speed
- Cooling quality

---

## 🛠 Troubleshooting

### Common MSR Issues

| Log Message | Meaning | Solution |
|-------------|----------|----------|
| `msr kernel module is not available` | MSR not loaded on host | Run `modprobe msr` |
| `FAILED TO APPLY MSR MOD` | Protection mode enabled | Disable Protection Mode |
| `cannot read MSR 0x000001a4` | Kernel blocking MSR | Check HAOS kernel restrictions |
| Low hashrate | MSR disabled or few threads | Enable MSR or increase threads |

---

### Verify MSR is Working

When successful, logs should show:

```
register values for "intel" preset have been set successfully
```

If you see:

```
FAILED TO APPLY MSR MOD
```

MSR is not active.

---

## ⚠ Risks & Disclaimer

- Mining increases CPU temperature by 15–25°C
- Ensure proper cooling
- Disabling Protection Mode reduces container isolation
- Use at your own risk

---

## 📄 License

Creative Commons Attribution-NoDerivs 4.0 International (CC BY-ND 4.0)

You may use and share this project.  
Modified distributions are not permitted.


---

## Support me 🔥
- 😄 PayPal one-off donation
<a href="https://www.paypal.com/donate/?hosted_button_id=PVATF8G5NZ392">
  <img src="https://raw.githubusercontent.com/andreostrovsky/donate-with-paypal/925c5a9e397363c6f7a477973fdeed485df5fdd9/blue.svg" alt="Donate with PayPal" height="40"/>
