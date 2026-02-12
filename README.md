🪙 XMRig Miner Add-on for Home Assistant

A high-performance custom add-on to run XMRig (Monero miner) directly within your Home Assistant ecosystem. Optimized for stability and system longevity.
🚀 Features

    ⚙️ Architecture Optimized: Specifically tuned for x86_64 (amd64) processors.

    🏠 Native Integration: Runs as a standard Home Assistant service.

    ⚖️ Smart Resource Management: Uses low process priority (nice -n 15) to ensure Frigate, Zigbee2MQTT, and the Core always have priority.

    🛠️ Simple Web UI Config: No terminal needed for basic settings.

📥 Installation

    Open your Home Assistant dashboard.

    Go to Settings ➡️ Add-ons ➡️ Add-on Store.

    Click the ⋮ (top right) and select Repositories.

    Add this URL:

    https://github.com/Bearstorm/ha-xmrig-addon

    Click Add, then Close.

    Search for "XMRig Miner" in the store and click Install.

🔧 Configuration

Add your mining details in the Configuration tab:

pool: "Your XMR mining pool address"
user: "Your Monero (XMR) wallet address"
pass: "Worker identifier (name for this machine)"
