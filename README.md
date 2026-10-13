# 🪙 XMRig Miner Add-on for Home Assistant


[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
![Architecture](https://img.shields.io/badge/Arch-amd64-orange.svg)
![HAOS Compatible](https://img.shields.io/badge/HAOS-Compatible-green.svg)
![Legacy Supervised](https://img.shields.io/badge/Supervised-Legacy-lightgrey.svg)
![MSR Legacy](https://img.shields.io/badge/MSR-Legacy%20Only-yellow.svg)
![RandomX Optimized](https://img.shields.io/badge/RandomX-Optimized-red.svg)

![Build](https://github.com/Bearstorm/ha-xmrig-addon/actions/workflows/publish.yml/badge.svg)
![GHCR](https://img.shields.io/badge/GHCR-Published-blue)

![Release](https://img.shields.io/github/v/release/Bearstorm/ha-xmrig-addon?display_name=tag&style=flat-square)
![License](https://img.shields.io/github/license/Bearstorm/ha-xmrig-addon)
![Visitors](https://komarev.com/ghpvc/?username=Bearstorm&repo=ha-xmrig-addon&style=flat-square)



Configurable **Monero (XMR)** mining add-on for Home Assistant OS on **x86_64 (amd64)**. The repository also preserves a separate legacy Supervised/MSR variant for existing installations.

> ⚠ **Important:** Home Assistant Supervised is no longer an officially supported Home Assistant installation method. The Supervised/MSR add-on is retained for existing legacy systems, not recommended for new installations.
>
> **Current stable HAOS Safe runs XMRig 6.26.0 through `run.sh`.** The Python Controller, MQTT entities and Mining switch are **experimental beta-only features**, not features of the published stable HAOS Safe add-on.

---

## 🔀 Which Version Should I Install?

| Your System | Install This Add-on |
|-------------|---------------------|
| Home Assistant OS (HAOS), amd64 | **XMRig Miner (HAOS Safe)** |
| Existing legacy Home Assistant Supervised deployment | **XMRig Miner (Supervised / MSR)** (unsupported Home Assistant installation method) |
| Disposable HAOS test environment | **XMRig Miner 2.0 (Beta Test)** (development branch only; not released) |

### How to check your system:
Go to:
Settings → System → About

- If you see **Home Assistant OS** → use **HAOS Safe**.
- If you maintain an existing **Home Assistant Supervised** installation → the **Supervised / MSR** variant remains for legacy compatibility only.
- The experimental beta is **not** a stable update or an installation recommendation for your production Home Assistant.

---

## 📑 Table of Contents

- [System Requirements](#-system-requirements)
- [Variant Comparison](#-variant-comparison)
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

## 🔎 Variant Comparison

**Quick pick:** Home Assistant OS → **HAOS Safe** | Existing unsupported Supervised → **legacy Supervised / MSR**

| Feature | HAOS Safe | Supervised / MSR (Legacy) |
|---------|-----------|----------------------------|
| Architecture | amd64 | amd64 |
| XMRig 6.26.0 | ✅ | Check the legacy add-on version |
| MSR Optimization | ❌ | Configurable, hardware/host dependent |
| Host privileges required | ❌ | ✅ |
| Host network/PID access | ❌ | ✅ |
| Recommended for new Home Assistant installs | ✅ (HAOS) | ❌ |
| Python MQTT Discovery / Mining switch in stable image | ❌ | ❌ |

The separate **Beta Test** add-on includes Python Controller and MQTT features in development, but has not passed validation on a real HAOS Supervisor.

---

## ⚠ Platform Support Clarification

This repository contains **two maintained installation paths and an experimental beta directory**:

### 🛡 XMRig Miner (HAOS Safe)
- Designed for Home Assistant OS on amd64.
- Does not use MSR, kernel modules, host network or privileged host access.
- Configured for Home Assistant Protection Mode ON.
- The stable Docker image starts the existing Bash `run.sh`, without MQTT monitoring/switch support.

### ⚙ XMRig Miner (Supervised / MSR) — Legacy
- Kept for existing Home Assistant Supervised setups only; upstream Home Assistant support for this installation method has ended.
- Uses elevated container permissions and may perform MSR operations on compatible hosts.
- Not suitable for Protection Mode ON; **not recommended for new installations**.
- Mentioning Debian 12 in an existing legacy configuration does **not** mean Home Assistant Supervised on Debian 12 is officially supported.

### 🧪 XMRig Miner 2.0 (Beta Test) — Development Only
- An independently packaged add-on in `xmrig_haos_beta/`, with its own slug and MQTT topic namespace.
- Includes test-candidate Python Controller, telemetry, MQTT Discovery, ON/OFF and persisted requested state.
- Builds and passes isolated CI tests; **not yet validated on a real HAOS Supervisor or published as a stable add-on**.

---

## 💻 System Requirements

- **Architecture:** x86_64 (amd64), Intel or AMD. ARM builds are not provided.
- **Platform for new installations:** Home Assistant OS.
- **Memory, storage, temperature and CPU limits:** depend on workload, number of threads, RandomX mode and other HA services; no universal minimum or hashrate guarantee is claimed here.
- **HAOS Safe:** no MSR kernel module or host permissions required.
- **Legacy Supervised/MSR:** requires a compatible existing host and privileged configuration; unsupported Home Assistant installation method.
- **Docker base:** the HAOS Dockerfile currently uses Debian Bookworm (12) as its container base. This is separate from support for Home Assistant Supervised.

---

## 📥 Installation

1. In **Home Assistant OS**, open the add-on store.
2. Open **Repositories** and add:

```text
https://github.com/Bearstorm/ha-xmrig-addon
```

3. Choose **XMRig Miner (HAOS Safe)**.
4. Set the required wallet and review pool, threads, priority and TLS settings.
5. Start the add-on and review its logs and CPU temperature.

The **Supervised / MSR** add-on is preserved for existing legacy users only. The **Beta Test** add-on is a development artifact, not distributed as a stable add-on through the normal repository branch. Do not install it on production HAOS.

---

## ⚙ Configuration

| Option | HAOS Safe | Supervised / MSR (Legacy) | Description |
|--------|-----------|----------------------------|-------------|
| `pool` | ✅ | ✅ | Mining pool host |
| `port` | ✅ | ✅ | Mining pool port |
| `wallet` | ✅ | ✅ | Required wallet identifier |
| `worker` | ✅ | ✅ | Worker name |
| `threads` | ✅ | ✅ | CPU mining threads |
| `priority` | ✅ | ✅ | CPU priority |
| `tls_mode` | ✅ | ❌ | `auto`, `enabled`, `disabled`; auto enables TLS on port 443 |
| `msr_mod` | ❌ | ✅ | Host-dependent MSR optimization; legacy variant only |

The HAOS Safe defaults are pool `pool.supportxmr.com`, port `443`, worker `HA`, threads `2` and priority `2`. A wallet must be provided before mining. **MQTT settings and persistent ON/OFF are not available in the current stable HAOS image.**

---

## ⚡ MSR Optimization (Advanced)

MSR tuning is a **legacy Supervised/MSR-only** feature. Benefits vary by CPU, kernel and host configuration; no fixed performance gain is guaranteed.

### Toggle MSR

| Setting | Behavior |
|---------|----------|
| `msr_mod: true` | Requests MSR optimization on a compatible legacy host |
| `msr_mod: false` | Disables the add-on MSR setting |

### Home Assistant Supervised (Legacy Host)

This installation method is no longer officially supported by Home Assistant. Host MSR setup and low-level permissions must be handled only by an experienced administrator of an existing legacy deployment. **Do not disable Protection Mode or grant host privileges on HAOS to enable MSR.**

### MSR Availability

- **HAOS Safe:** no MSR access or host/kernel modification.
- **Legacy Supervised/MSR:** may require access to `/dev/cpu`, kernel support and privileged capabilities.

---

## 🔐 Security Model

### HAOS Safe Variant
- No host PID or host network access; no full host permissions.
- Configured for Protection Mode ON and no MSR access.
- Uses the existing stable `run.sh` entrypoint.

### Supervised / MSR Variant (Legacy)
- Requests privileged host capabilities and access to `/dev/cpu`.
- Intended solely for legacy installs; do not treat it as an officially supported Home Assistant installation path.

### Experimental Beta
- Separate add-on slug, manual boot and limited host permissions.
- MQTT uses the Supervisor-provided optional broker service and a separate `xmrig_haos_beta` namespace.
- Security assertions are based on source and isolated CI checks; **real HAOS Protection Mode compatibility is not yet verified**.

---

## 📊 Performance Notes

Hashrate varies with CPU model, number of threads, CPU cache, memory, RandomX mode, thermal limits and competing Home Assistant workloads. This project does not claim universal hashrate figures or guaranteed MSR speedups.

Tune thread count gradually and monitor Home Assistant responsiveness and processor temperature. XMRig CPU usage can affect other HA workloads.

---

## 🧩 Kernel Compatibility Matrix

| Platform | MSR Access | Project Status |
|----------|------------|----------------|
| Home Assistant OS (amd64) | Disabled in HAOS Safe | Primary add-on platform |
| Home Assistant Supervised | Host-dependent, privileged | Legacy; upstream installation method unsupported |
| Debian Bookworm container base | Not a host compatibility guarantee | Currently used for the HAOS image |
| ARM / Raspberry Pi | No supported build | Not available |

Compatibility depends on the actual host/kernel and add-on security configuration, **not merely on a Debian or HAOS version number**.

---

## 🛠 Troubleshooting

| Symptom | Scope | What to check |
|---------|-------|---------------|
| Add-on does not start | HAOS Safe | A wallet is configured; pool, port and thread settings are valid; check add-on logs |
| No pool connection | HAOS Safe | Pool reachability, port and `tls_mode` |
| High CPU temperature or HA slowdown | Both variants | Reduce `threads`; inspect cooling and competing workloads |
| MSR module/permission error | Legacy only | Host/kernel compatibility and legacy privileges; do **not** enable host access on HAOS |
| No MQTT entities in stable HAOS Safe | Expected | MQTT features are beta-only; the stable image still starts `run.sh` |
| Experimental beta fails on HAOS | Development only | See `docs/HAOS_BETA_ACCEPTANCE.md`; do not deploy to production |

---

## ⚠ Known Limitations

- AMD64 only; no ARM image is supplied.
- Stable HAOS Safe has **no MQTT Discovery, MQTT Mining switch or persisted Mining ON/OFF control**.
- MSR is not available in HAOS Safe; the Supervised/MSR variant is legacy.
- Experimental beta features are tested in Docker/CI but have not completed real HAOS Supervisor and Protection Mode acceptance tests.
- Actual mining consumes CPU resources and electricity and can raise temperatures.

---

## 🗺 Roadmap

- [x] Develop Python Controller, MQTT Discovery and Mining switch in an isolated beta candidate
- [x] Test ON/OFF state persistence, crash guard and MQTT handling in isolated CI
- [ ] Validate the separate beta add-on on disposable HAOS with real Supervisor MQTT service
- [ ] Verify rollback, host isolation and broker permissions on real HAOS
- [ ] Review and approve stable release documentation before promoting any beta functionality
- [ ] Explore dynamic thread scaling, power reporting and additional architectures only after verification

**Roadmap checkmarks refer to development/CI work, not production feature availability.**

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

- Mining increases CPU load, heat and electricity consumption; the temperature increase is hardware-dependent
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
