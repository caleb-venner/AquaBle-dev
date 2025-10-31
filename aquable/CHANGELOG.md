# Changelog

All notable changes to AquaBle will be documented in this file.


## [2.1.2] - 2025-10-31

### Added (2.1.2)

- Created dedicated README for stable repository deployments

### Changed (2.1.2)

- Updated release workflow to ensure correct README is deployed to stable repository

### Fixed (2.1.2)

- Fixed stable repository README being overwritten with empty file during releases


## [2.1.1] - 2025-10-31

### Added (2.1.1)

- Added verbose log option in add-on config
- Added mdi icon for Home Assistant sidebar Ingress

### Changed (2.1.1)

- Reduced log output for status calls
- Adjusted release version deployment workflow

### Fixed (2.1.1)

- (no user-facing bug fixes in this patch)

## [2.1.0] - 2025-10-31

### Added

- Home Assistant Ingress support with middleware for IP restriction and path handling
- Centralized polling service for device status caching
- Device configuration import/export via JSON
- Dark mode support and dashboard UI improvements
- Health check endpoint and improved service logging

### Changed

- Reorganized backend into modular packages: storage, utils, config, device
- Migrated frontend state management to Zustand
- Unified logging configuration and timezone handling
- Improved device connection handling with retry logic and timeouts
- API endpoint paths made Ingress-compatible

### Fixed

- Device command execution protocol and error handling
- Multi-channel brightness and auto program configuration saving
- Base tag injection for Ingress asset resolution
- Address encoding in metadata API calls
- Graceful handling of missing device metadata
