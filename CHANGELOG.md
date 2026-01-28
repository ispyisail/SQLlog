# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-28

### Added

- Initial release of SQLlog PLC-to-SQL bridge
- 4-state handshake protocol for reliable data transfer
- Thread-safe PLC communication via pycomm3
- SQL Server integration with parameterized queries
- SQLite store-and-forward cache for offline resilience
- Automatic fault recovery with exponential backoff
- Windows service support with pywin32
- System tray application with status indicators
- YAML-based configuration with environment variable substitution
- Data validation with configurable limits
- Loguru-based structured logging with rotation
- Comprehensive test suite with pytest
- Connection test utility script

### Security

- SQL password stored in .env file (excluded from git)
- Environment variable substitution in config files
- Parameterized SQL queries prevent injection

## [Unreleased]

### Planned

- Email/SMS alerting on persistent faults
- Web dashboard for monitoring
- Multi-PLC support
- Database schema auto-migration
