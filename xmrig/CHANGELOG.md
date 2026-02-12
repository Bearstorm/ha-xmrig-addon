# Changelog

## 6.21.5
- Fixed MSR access inside container using proper /dev/cpu device mapping (rwm)
- Replaced legacy user/pass configuration with wallet/worker naming
- Improved container privilege handling for RandomX optimization
- Fixed GHCR image caching by enforcing full rebuild
- Improved Docker publishing workflow

## 6.21.4
- Added SYS_RAWIO and SYS_ADMIN privileges for MSR support
- Optimized run.sh for cleaner pool/port handling
- Enforced Fast RandomX mode for better hashrate

## 6.21.2
- Added CPU thread control (choose how many cores to use)
- Added CPU priority settings
- Added full_access flag for better hardware communication
- Optimized run script for manual parameter parsing

## 6.21.1
- Fixed connection issues by forcing TLS on port 443
- Added port configuration to UI

## 6.21.0
- Initial release for Bearstorm GitHub
- Optimized for x86_64 architecture

