# Changelog

## 6.21.7
- Switched base image to Debian (bookworm) to reliably install msr-tools via apt
- Added kmod (modprobe) inside container to avoid MSR module detection issues
- Added msr_mod toggle to let user enable/disable MSR mod from UI (variant B)
- Kept MSR self-test (rdmsr 0x1a4) for real validation inside container

## 6.21.6
- Added optional MSR mod toggle (msr_mod) so user can enable/disable MSR optimization
- Added MSR self-test inside container (rdmsr + wrmsr restore) to verify real MSR access
- Disabled AppArmor profile for the add-on to prevent MSR write blocking (apparmor: false)

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

## 6.21.3
- Fixed other workflow

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


