Changelog
6.21.5

Fixed MSR access inside container (proper /dev/cpu device mapping with rwm)

Improved kernel module handling for modern Intel CPUs (12th Gen+)

Removed legacy user/pass naming and replaced with wallet/worker

Added backward-compatible configuration validation

Improved container privilege handling for RandomX optimization

Forced full image rebuild via version bump (cache fix)

Improved Docker image publishing pipeline to GHCR

6.21.4

Added SYS_RAWIO and SYS_NICE privileges for MSR support

Optimized run.sh for cleaner pool/port handling

Enforced Fast RandomX mode for better hashrate

Added /dev/cpu device exposure to container

6.21.2

Added CPU thread control (choose how many cores to use)

Added CPU priority settings

Improved container capability configuration

Optimized run script parameter handling

6.21.1

Fixed connection issues by forcing TLS on port 443

Added manual port configuration to UI

6.21.0

Initial public release

Optimized for x86_64 (amd64) architecture

Integrated native Home Assistant add-on support
