# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in SENTINEL, please report it responsibly.

**Do not open a public issue for security vulnerabilities.**

Instead, report via:
- GitHub's private vulnerability reporting (Security tab → Report a vulnerability)
- Direct message to project maintainers

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and aim to provide a resolution timeline within 7 days.

## Scope

Security concerns for this project include:

- **API key exposure** — LLM backend credentials in config or logs
- **Prompt injection** — Malicious input that manipulates agent behavior
- **Data leakage** — Campaign state or player data exposed unintentionally
- **Dependency vulnerabilities** — Known CVEs in project dependencies

## Out of Scope

- Game balance or mechanical exploits (these are design issues, not security)
- Vulnerabilities in third-party LLM APIs themselves
- Issues requiring physical access to the machine running the agent

## Supported Versions

Security updates are applied to the latest version on `master`. We do not maintain security patches for older releases.

| Version | Supported |
|---------|-----------|
| Latest (master) | Yes |
| Older releases | No |
