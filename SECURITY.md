# Security Policy

## Reporting a Vulnerability

We take the security of **Social Network Analyzer** seriously. If you discover any potential security vulnerabilities or issues, please follow the steps below:

### How to Report

1. **Do Not Open a Public Issue**  
   To protect users, please avoid reporting security vulnerabilities in public GitHub issues.

2. **Contact the Maintainers**  
   - Email us at **[victoku1.info@gmail.com]** with the subject line: `Security Vulnerability in Social Network Analyzer`.
   - Include:
     - A detailed description of the issue.
     - Steps to reproduce or exploit the vulnerability.
     - Any relevant logs, screenshots, or additional context.

3. **Wait for Confirmation**  
   We will acknowledge receipt of your report and provide a status update as soon as possible.

4. **Follow Responsible Disclosure**  
   Please allow us adequate time to address and mitigate the vulnerability before publicly discussing or disclosing it.

---

## Security Best Practices

While using this project, please keep the following in mind:

- **Environment Variables**: Always store sensitive information like your OpenAI API key in a `.env` file or environment variables and never commit them to version control.
- **Dependency Updates**: Regularly update dependencies listed in `requirements.txt` to avoid using outdated or vulnerable packages.
- **HTTPS**: Ensure your deployment uses HTTPS to protect sensitive user data.
- **Data Privacy**: Do not use this project to collect or analyze sensitive personal information without explicit consent from users.

---

## Scope

This document applies only to **Social Network Analyzer** and not to dependencies or external APIs (e.g., OpenAI). If you discover issues in third-party tools or services, please report them directly to the respective maintainers.

---

## Why Not Open a Public Issue?

Opening a public issue for security vulnerabilities is discouraged because it might:
- **Expose the Vulnerability to Attackers**: Sharing a vulnerability publicly before it's fixed could allow malicious actors to exploit it.
- **Risk User Data or System Integrity**: For projects dealing with user-provided data or APIs, publicizing vulnerabilities can compromise privacy and security.
- **Delay the Fix**: Public discussions about vulnerabilities may distract from the resolution process, leaving the issue exploitable for longer.

---

## Thank You

We appreciate your help in keeping **Social Network Analyzer** secure for everyone. Thank you for following responsible disclosure practices!
