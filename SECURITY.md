# Security Policy

## Supported Versions

Only the latest release of Tikara receives security updates. If you are on an older version, please upgrade before reporting.

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |
| Older   | :x:                |

## Scope

The following are considered in scope for security reports:

- Vulnerabilities in Tikara's own Python code
- Vulnerabilities in Tikara's direct dependencies (e.g. JPype1, Pydantic)
- Vulnerabilities in the bundled Apache Tika JAR — please report these here so the JAR can be updated in a release

If a vulnerability originates in Apache Tika itself (not just the bundled version), please also report it upstream to the [Apache Security Team](https://www.apache.org/security/) so the broader ecosystem benefits.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

### Preferred: GitHub Private Security Advisory

Use GitHub's built-in private disclosure flow:

1. Go to the [Security Advisories page](https://github.com/baughmann/tikara/security/advisories)
2. Click **"Report a vulnerability"**
3. Fill in the details (affected version, description, steps to reproduce, and potential impact)

### Alternative: Email

If you prefer, you can email **baughmann1@gmail.com** directly. Please include:

- A description of the vulnerability
- Steps to reproduce or a minimal proof-of-concept
- The version of Tikara affected
- Any suggested fix, if you have one

## What to Expect

- **Acknowledgement**: within 1 week of your report
- **Assessment**: once triaged, you will receive a summary of the finding and an estimated timeline for a fix or mitigation
- **Fix & Disclosure**: once a fix is released, a GitHub Security Advisory will be published crediting the reporter (unless you prefer to remain anonymous)

If a report is accepted, a patched release will be made as soon as practical. If a report is declined (e.g. it is a known limitation, out of scope, or not reproducible), you will be notified with an explanation.

Thank you for helping keep Tikara and its users safe.
