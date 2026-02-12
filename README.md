XMRig Miner Add-on for Home Assistant

This is a custom Home Assistant add-on for running XMRig, a high-performance Monero (XMR) miner, directly on your Home Assistant Supervised or OS installation.
Features

    Architecture Optimized: Specifically built and tested for x86_64 (amd64) systems.

    Background Operation: Runs as a native Home Assistant service.

    Resource Management: Set with low process priority (nice -n 15) to ensure Home Assistant core and add-ons (like Frigate) maintain peak performance.

    Easy Configuration: Manage your pool and wallet directly through the Home Assistant UI.

Installation

    Go to your Home Assistant instance.

    Navigate to Settings -> Add-ons -> Add-on Store.

    Click the three dots in the top right corner and select Repositories.

    Add the following URL: https://github.com/Bearstorm/ha-xmrig-addon

    Click Add and then Close.

    Find the XMRig Miner in the store (under the "Bearstorm Addons" section).

    Click Install.

Configuration

Once installed, navigate to the Configuration tab of the add-on and set your mining details:
YAML

pool: "Your preferred Monero mining pool"
user: "Your XMR wallet address."
pass: "Worker name (identifier for your machine)"

    pool: Your preferred Monero mining pool.

    user: Your XMR wallet address.

    pass: Worker name (identifier for your machine).

Disclaimer

Mining cryptocurrency increases power consumption and generates heat. Use this add-on at your own risk.
