# 🪙 XMRig Miner Add-on for Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
![Architecture](https://img.shields.io/badge/Arch-x86__64%20(amd64)-orange.svg)

High-performance and fully configurable Monero (XMR) mining add-on for the Home Assistant ecosystem.  
Optimized for **x86_64 (amd64)** architecture, specifically tuned for modern Intel (10th–12th Gen) and AMD processors.

> ⚠️ **Important:** Versions older than **6.21.6** are not recommended due to unstable MSR handling and privilege inconsistencies.

---

## 💻 System Requirements

To run this miner efficiently without impacting Home Assistant stability:

- **Architecture:** x86_64 (Intel or AMD)  
  ARM devices (e.g., Raspberry Pi) are **NOT supported**
- **Minimum CPU:** 4-core processor (Intel Celeron J4125 or newer)
- **Recommended CPU:** Intel Core i5/i7 (10th Gen+) or AMD Ryzen 5+  
  Higher L3 cache significantly improves hashrate
- **RAM:** 4GB minimum (8GB+ recommended if running Frigate or heavy add-ons)
- **Storage:** ~500MB free space
- **OS:** Home Assistant OS or Home Assistant Supervised (Debian 12 recommended)

---

## 🚀 Features

- ⚙️ Optimized for modern x86_64 CPUs
- 🏠 Native Home Assistant integration
- 🎛️ Adjustable CPU threads
- ⚖️ Configurable CPU priority
- 🔧 Built-in MSR optimization toggle
- 🔐 Compatible with Protection Mode

---

## 📥 Installation

1. Go to **Settings → Add-ons → Add-on Store**
2. Click the **⋮ menu** (top right) → **Repositories**
3. Add:
   ```
   https://github.com/Bearstorm/ha-xmrig-addon
   ```
4. Install **XMRig Miner**
5. Configure and start

---

## ⚙️ Configuration Options

| Option | Description | Impact |
|--------|------------|--------|
| `pool` | Mining pool address | Where hashing power is directed |
| `port` | Pool port (443 recommended) | Enables TLS |
| `wallet` | Your XMR wallet address | Required for payouts |
| `worker` | Worker name | Visible in pool stats |
| `threads` | CPU threads to use | Higher = higher hashrate |
| `priority` | CPU priority (0–5) | 2 recommended |
| `msr_mod` | Enable MSR optimization | +Performance if supported |

---

# ⚡ MSR Optimization (Advanced)

MSR (Model Specific Register) tuning can increase RandomX performance by up to ~20% on supported Intel CPUs.

## 🔄 Built-in MSR Toggle

From version **6.21.6+**, MSR optimization can be enabled or disabled directly:

| Setting | Behavior |
|----------|----------|
| `msr_mod: true` | Enables MSR optimization |
| `msr_mod: false` | Disables MSR optimization completely |

If disabled, XMRig runs normally without MSR tuning (slightly lower hashrate, maximum stability).

---

## 🖥️ Home Assistant Supervised (Debian Host)

MSR must be enabled on the **host system** (not inside the container):

```bash
sudo apt update
sudo apt install msr-tools -y
echo "msr" | sudo tee -a /etc/modules
sudo modprobe msr
```

Then in Home Assistant:

1. Open the add-on  
2. Go to the **Info** tab  
3. Disable **Protection Mode**  
4. Restart the add-on  
5. Enable `msr_mod` in **Configuration**

---

## 🧩 Home Assistant OS (HAOS)

1. Open the add-on  
2. Go to the **Info** tab  
3. Disable **Protection Mode**  
4. Restart the add-on  
5. Enable `msr_mod` in **Configuration**

> ℹ️ Some HAOS kernel or security configurations may restrict MSR access even with Protection Mode disabled.

---

# 🔒 Protection Mode Explained

- **Enabled:** Maximum security, MSR access blocked  
- **Disabled:** Required for MSR optimization  
- Safe to keep enabled if `msr_mod: false`

---

# ⚠️ Disclaimer & Risks

- Disabling Protection Mode grants hardware-level access  
- Mining increases CPU temperature (+15–25°C typical)  
- Leave at least 2 threads free for system stability  
- Use at your own risk

---

# 📄 License

Creative Commons Attribution-NoDerivs 4.0 International (CC BY-ND 4.0)

You may share and use this add-on.  
Modified versions may not be redistributed.

---

## Support me 🔥
- 😄 PayPal one-off donation
<a href="https://www.paypal.com/donate/?hosted_button_id=PVATF8G5NZ392">
  <img src="https://raw.githubusercontent.com/andreostrovsky/donate-with-paypal/925c5a9e397363c6f7a477973fdeed485df5fdd9/blue.svg" alt="Donate with PayPal" height="40"/>
