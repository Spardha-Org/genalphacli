# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do NOT open a public issue.**

Instead, email **naik.nandishd@gmail.com** with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive a response within 48 hours acknowledging your report. We will work with you to understand and address the issue before any public disclosure.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |

## Security Best Practices for Self-Hosting

- Never commit `.env` files — use `.env.example` as a template
- Rotate all secrets before deploying to production
- Use HTTPS in production
- Keep dependencies updated
- Review the deployment guide in `docs/deployment/` before deploying
