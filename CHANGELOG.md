# Changelog

All notable changes to this project will be documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project intends to follow semantic versioning after its first stable release.

## [Unreleased]

### Added

- OpenRouter-compatible chat, analysis, and grounded news configuration
- Root test configuration and continuous-integration checks
- Public health endpoint and container health checks
- Separate administrator API credentials
- Fresh-install creation of the Telegram bot database
- Security policy and expanded deployment documentation
- Third-party data-flow inventory and authentic generated-output example
- Monthly grouped dependency updates for Python, Docker, Compose, and GitHub Actions
- Social-preview artwork and a public-launch checklist with announcement templates

### Changed

- Containers run application processes as non-root users
- Conservative default worker and database/cache memory settings
- Public analysis methods now match the implemented handlers

### Security

- Removed permissive wildcard CORS defaults
- Avoided logging complete request payloads
- Added constant-time comparison for internal API tokens
