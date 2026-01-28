# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in SQLlog, please report it responsibly:

1. **Do NOT** create a public GitHub issue for security vulnerabilities
2. Email the maintainers directly with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes

## Security Best Practices

When deploying SQLlog:

### Credentials

- Store SQL passwords in `.env` file only (never in config.yaml)
- Ensure `.env` is in `.gitignore` (it is by default)
- Use strong, unique passwords for SQL accounts
- Consider using Windows Authentication instead of SQL Authentication where possible

### Network

- Restrict network access between SQLlog host and PLC/SQL Server
- Use firewalls to limit port access (44818 for PLC, 1433 for SQL)
- Consider VLANs to isolate industrial network

### SQL Server

- Use a dedicated SQL account with minimal permissions (INSERT only)
- Avoid using SA account in production
- Enable SQL Server audit logging

### Host System

- Keep Windows and Python updated
- Run service with minimal required permissions
- Enable Windows audit logging
- Regularly review logs for anomalies

### Configuration Files

- Never commit `config.yaml` or `.env` to version control
- Use `.example` files as templates
- Restrict file system permissions on config files
