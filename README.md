XMRig Miner Add-on for Home Assistant

This is a custom Home Assistant add-on for running XMRig, a high-performance Monero (XMR) miner, directly on your Home Assistant Supervised or OS installation.
Features

    Optimized for HP Pro Mini: Configured to run smoothly on amd64 architecture.

    Background Operation: Runs as a native Home Assistant service.

    Resource Management: Set with low process priority (nice -n 15) to ensure Home Assistant core performance is never compromised.

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

pool: "pool.supportxmr.com:443"
user: "44tR4n25mvaYJgcMSuGsSd37fUYA4brgR7WaNskXAcZYF97jucuKTqkCsFsrid6SvY4v8fFfV22xFTmyzW7zN9oDSXXzViS"
pass: "HP_Pro_Mini"

    pool: Your preferred Monero mining pool.

    user: Your XMR wallet address.

    pass: Worker name (identifier for your machine).

Disclaimer

Mining cryptocurrency can increase power consumption and generate heat. Ensure your hardware has adequate cooling. Use this add-on at your own risk.
