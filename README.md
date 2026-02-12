# 🪙 XMRig Miner Add-on for Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
![Architecture](https://img.shields.io/badge/Arch-amd64-orange.svg)
![HAOS Compatible](https://img.shields.io/badge/HAOS-Compatible-green.svg)
![Supervised](https://img.shields.io/badge/Supervised-Debian%2012-blue.svg)
![MSR Optional](https://img.shields.io/badge/MSR-Optional-yellow.svg)
![RandomX Optimized](https://img.shields.io/badge/RandomX-Optimized-red.svg)

![Build](https://github.com/Bearstorm/ha-xmrig-addon/actions/workflows/publish.yml/badge.svg)
![GHCR](https://img.shields.io/badge/GHCR-Published-blue)

![Release](https://img.shields.io/github/v/release/Bearstorm/ha-xmrig-addon?display_name=tag&style=flat-square)
![License](https://img.shields.io/github/license/Bearstorm/ha-xmrig-addon?style=flat-square)
![Visitors](https://komarev.com/ghpvc/?username=Bearstorm&repo=ha-xmrig-addon&style=flat-square)



High-performance and fully configurable **Monero (XMR)** mining add-on for Home Assistant.  
Optimized for **x86_64 (amd64)** architecture and tuned for modern Intel (10th–12th Gen) and AMD processors.

> ⚠ **Important:** Versions older than **6.21.6** are not recommended due to unstable MSR handling and privilege inconsistencies.

---

## 📑 Table of Contents

- [System Requirements](#-system-requirements)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [MSR Optimization](#-msr-optimization-advanced)
- [Security Model](#-security-model)
- [Performance Notes](#-performance-notes)
- [Kernel Compatibility Matrix](#-kernel-compatibility-matrix)
- [Troubleshooting](#-troubleshooting)
- [Known Limitations](#-known-limitations)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [Risks & Disclaimer](#-risks--disclaimer)
- [License](#-license)

---

## 💻 System Requirements

- **Architecture:** x86_64 (Intel or AMD)  
- ARM devices (Raspberry Pi) are **NOT supported**
- **Minimum CPU:** 4 cores
- **Recommended CPU:** Intel i5/i7 (10th Gen+) or AMD Ryzen 5+
- **RAM:** 4GB minimum (8GB+ recommended if running Frigate)
- **Storage:** ~500MB free
- **OS:** HAOS or Supervised (Debian 12 recommended)

---

## 📥 Installation

1. Go to **Settings → Add-ons → Add-on Store**
2. Click **⋮ → Repositories**
3. Add:

```
https://github.com/Bearstorm/ha-xmrig-addon
```

4. Install **XMRig Miner**
5. Configure wallet and pool
6. Start

---

## ⚙ Configuration

| Option | Description | Recommended |
|--------|------------|------------|
| `pool` | Mining pool address | pool.supportxmr.com |
| `port` | Pool port | 443 |
| `wallet` | Monero wallet address | Required |
| `worker` | Worker name | HA |
| `threads` | CPU threads used | Total - 2 |
| `priority` | CPU priority (0–5) | 2 |
| `msr_mod` | Enables MSR optimization | true |

---

## ⚡ MSR Optimization (Advanced)

MSR optimization may improve performance by **~20%** on supported Intel CPUs.

### Toggle MSR

| Setting | Behavior |
|----------|----------|
| `msr_mod: true` | Enables MSR |
| `msr_mod: false` | Fully disables MSR |

---

### Home Assistant Supervised (Debian Host)

```bash
sudo apt update
sudo apt install msr-tools -y
echo "msr" | sudo tee -a /etc/modules
sudo modprobe msr
```

Then:
- Disable **Protection Mode**
- Restart add-on
- Enable `msr_mod`

---

### Home Assistant OS (HAOS)

- Disable **Protection Mode**
- Restart add-on
- Enable `msr_mod`

> Some HAOS kernel versions restrict MSR access.

---

## 🔐 Security Model

| Feature | Required For |
|----------|--------------|
| Protection Mode OFF | MSR access |
| Full hardware access | MSR tuning |
| Host PID | Low-level CPU operations |

Disable Protection Mode only if trusted.

---

## 📊 Performance Notes

| CPU | Threads | MSR | Hashrate |
|------|----------|------|-----------|
| i5-12500T | 2 | OFF | ~2000 H/s |
| i5-12500T | 2 | ON | ~2400 H/s |
| i5-12500T | 4 | ON | ~2500 H/s |

Performance depends on L3 cache and memory speed.

---

## 🧩 Kernel Compatibility Matrix

| Platform | Kernel | MSR Support | Notes |
|-----------|--------|------------|--------|
| Debian 12 | 6.x | ✅ Full | Recommended |
| HAOS 11 | 6.x | ⚠ Partial | Depends on security policy |
| HAOS 10 | 5.x | ⚠ Limited | MSR may be blocked |
| Generic Docker | varies | ❌ Not supported | Host module required |

---

## 🛠 Troubleshooting

| Log Message | Meaning | Fix |
|-------------|----------|------|
| `msr kernel module is not available` | MSR not loaded | `modprobe msr` |
| `FAILED TO APPLY MSR MOD` | Protection mode ON | Disable Protection Mode |
| `cannot read MSR 0x000001a4` | Kernel blocking MSR | Check kernel policy |
| Low hashrate | MSR disabled | Enable `msr_mod` |

---

## ⚠ Known Limitations

- ARM architecture not supported
- MSR only benefits Intel CPUs
- HAOS kernel security policies may block MSR
- Cannot bypass kernel-level MSR restrictions
- MSR optimization not available in protected container mode

---

## 🗺 Roadmap

- [ ] Auto-detect MSR availability
- [ ] Add dynamic thread auto-scaling
- [ ] Add performance dashboard sensor entities
- [ ] Add optional power usage estimation
- [ ] Improve kernel compatibility detection
- [ ] Add multi-arch build (future evaluation)

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Open Pull Request

Please ensure:
- Code follows existing structure
- Docker builds pass
- Changelog is updated

---

## ⚠ Risks & Disclaimer

- Mining increases CPU temperature (15–25°C)
- Ensure proper cooling
- Disabling Protection Mode reduces isolation
- Use at your own risk

---

## 📄 License

This project is licensed under the MIT License.  
See the [LICENSE](LICENSE) file for details.



---

## Support me 🔥
- 😄 PayPal one-off donation
<a href="https://www.paypal.com/donate/?hosted_button_id=PVATF8G5NZ392">
  <img src="https://raw.githubusercontent.com/andreostrovsky/donate-with-paypal/925c5a9e397363c6f7a477973fdeed485df5fdd9/blue.svg" alt="Donate with PayPal" height="40"/>
