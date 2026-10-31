# CCB website: 20-point implementation and owner review

Reviewed against repository behavior on **31 October 2026**. This is a tailored
review, not an alleged universal list of 20 files. The influencer's exact checklist
was not supplied. Several protections already existed; adding 18 arbitrary files
would not make the site secure, copyright-free, or immune from claims.

"Configured" means present in code, not independently verified on production.
"Added" means implemented locally, not deployed. Outstanding actions remain real
work; do not describe them as completed compliance.

| # | Area | Evidence/status and remaining action |
| --- | --- | --- |
| 1 | robots.txt | Existing public crawler instructions. It is not authentication, a confidentiality boundary, or an anti-scraping guarantee. |
| 2 | sitemap.xml | Existing public URL discovery. Approved policy pages are added dynamically; policy drafts are excluded. This is SEO, not security. |
| 3 | Terms of Use | Added `/terms/`, editable through Admin. Seeded as a clearly marked, non-indexed draft. Institutional review is still required. |
| 4 | Privacy notice | Added `/privacy/`, editable through Admin. The college must confirm its privacy contact, lawful bases, retention periods, recipients, and transfer arrangements before approval. |
| 5 | Cookies, storage, and third parties | Draft notice inventories session/CSRF cookies, theme localStorage, offline caches, reCAPTCHA, maps, and providers. No blanket "cookie-free" claim or unnecessary generic consent banner was added. Determine any required consent/embedding changes from the actual deployed services and applicable obligations. |
| 6 | Copyright and licenses | Added `THIRD_PARTY_NOTICES.md` and retained official Bootstrap/Font Awesome notices, linked from Terms. Actual ownership and permissions for logos, photos, news, and documents remain unverified. No whole-project license was invented. |
| 7 | Security reporting | Added `/.well-known/security.txt` and `SECURITY.md`, using the existing Contact page. The college must assign monitoring and escalation ownership; no bounty, response SLA, or testing authorization is promised. |
| 8 | HTTPS and HSTS | Existing production settings enforce secure transport and HSTS. Confirm actual Render/custom-domain TLS and trusted proxy behavior. HSTS preload remains an explicit operator decision. |
| 9 | Secrets and debug | Existing production startup rejects the default development secret; `.env` is ignored. Verify `DEBUG=False`, strong stable deployment secrets, allowed hosts, and provider permissions. This audit did not read or disclose secret values. |
| 10 | Secure cookies | Existing production Secure, HttpOnly session cookie, SameSite and CSRF cookie settings. Confirm effective Set-Cookie headers on the deployed domain. |
| 11 | CSRF | Existing middleware and tokens protect state-changing forms; custom admin uploads retain CSRF protection. Regression tests cover missing-token rejection. |
| 12 | Output escaping and XSS | Existing Django escaping and plain-text content rendering; policy sections are escaped too. Added a public CSP compatibility baseline. Inline scripts/styles remain allowed, so this is not a strict nonce-based XSS defense. A nonce migration needs separate compatibility testing. |
| 13 | Administrator authentication | Existing password plus PIN gate and throttling remain. A static PIN is another knowledge secret, not equivalent to authenticator/passkey MFA. Genuine MFA and account recovery review remain operator work. |
| 14 | Authorization | Existing staff/model permissions and protected custom upload views; new policy editor uses Django permissions. Review real staff memberships and least privilege; no production permissions were expanded automatically. |
| 15 | Abuse prevention | Existing contact/admin limits, honeypot, email validation and conditional reCAPTCHA. Verify reCAPTCHA keys and use shared Redis for limits across workers; the in-memory fallback is per process. Trusted proxy/client-IP handling needs production verification. |
| 16 | Upload and download safety | Existing multiple-image validation, size/count limits, extension checks on several documents, and signed download URLs. Not every upload path has a uniform limit, and malware scanning is not installed. Review remaining upload limits, content scanning, and media hosting before calling this complete. |
| 17 | Browser security headers | Existing frame blocking, nosniff, and referrer policy plus newly effective Permissions-Policy. Added public CSP with explicit existing CDN/reCAPTCHA/map sources; admin inline-script behavior is intentionally unchanged. The previous Permissions-Policy setting alone did not emit a header. Test CAPTCHA/maps and external integrations in real browsers before deployment. |
| 18 | Dependency monitoring | Added weekly/push/PR pip-audit and regression CI plus Dependabot configuration. No vulnerabilities were suppressed. A local PyPI advisory check identified affected installed packages; their compatible minimum versions were raised and the local environment updated. CI pip-audit and the actual production environment still need verification; adding workflow files alone is not a clean audit result. |
| 19 | Backups and restore | Existing monthly backup workflow was found. A successful restore, backup confidentiality and access limits were not verified. The workflow now checks pg_dump failure directly, passes credentials through environment variables rather than constructing a credential-bearing shell command, and verifies a nonempty custom-format dump. Storage access, encryption requirements, restore testing, and recovery objectives still need verification. |
| 20 | Incident response and operations | Added reporting/escalation guidance. Assign real owners, monitor errors and uptime, review logs for personal data, set retention, and establish breach assessment/notification procedures with the college's privacy/security officers. These institutional processes were not fabricated in code. |

## Policy approval workflow

1. Open **Admin → Terms and privacy pages**. Review both drafts and every section.
2. Replace editorial passages requiring confirmation with the college's actual,
   approved processing details. In particular, identify the responsible privacy
   contact, lawful bases, actual retention/deletion rules, and provider recipients.
3. Confirm asset permissions and service/license obligations separately. Approving a
   page does not perform a rights audit or grant rights.
4. Mark **Approved for publication** only after institutional/privacy/legal review.
   Approved pages lose their draft marker and noindex instruction and enter the
   dynamic sitemap. Review future edits under the same process.
5. Before deployment, back up the database, run migration 0014 and collectstatic,
   then verify legal pages, login, uploads, CAPTCHA, maps, and sticky search.

Draft policies are not cached by the service worker. Existing unrelated public
pages may still be available offline. Contact submissions and admin routes remain
excluded. Draft legal pages have a noindex header and are not in the sitemap.

## References

- [Philippine Data Privacy Act, particularly Sections 11, 12, 16 and 20](https://privacy.gov.ph/data-privacy-act/)
- [IPOPHL copyright guidance](https://www.ipophil.gov.ph/copyright/)
- [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [OWASP Django security guidance](https://cheatsheetseries.owasp.org/cheatsheets/Django_Security_Cheat_Sheet.html)
- [RFC 9116 security.txt format](https://www.rfc-editor.org/rfc/rfc9116.html)
- [Google reCAPTCHA CSP guidance](https://developers.google.com/recaptcha/docs/faq#im-using-content-security-policy-csp-on-my-website-how-can-i-configure-it-to-work-with-recaptcha)

No file or disclaimer can guarantee that a site cannot be sued. This implementation
does not certify legal compliance or retroactively clear third-party copyright.

## Dependency remediation snapshot

The local environment's installed package/version metadata was checked against
PyPI's version-specific advisory data. Affected packages included Django 5.2.14,
Pillow 12.2.0, certifi 2026.4.22, pip 26.0.1, sqlparse 0.5.5, and urllib3 2.7.0.
The compatible candidates selected were Django 5.2.18, Pillow 13.0.0,
certifi 2026.10.23, pip 26.2.2, sqlparse 0.6.0, and urllib3 2.8.0. Those candidates
reported no advisories in PyPI at the time of the check. Requirements now enforce
these minimums; Render/CI bootstrap pip is updated too. Pillow 13 requires Python
3.11 or newer, which matches the tracked Render runtime configuration.

This is a point-in-time known-advisory check, not proof of no vulnerabilities.
The actual Render environment, transitive dependencies resolved during deployment,
and scheduled pip-audit results must be checked separately. Existing manually
configured Render build commands must also be updated to match `render.yaml`.

Backup artifacts now use PostgreSQL custom format (`.dump`), not gzipped SQL.
Restore testing should use a separate test database and `pg_restore`; never point a
restore command at production as an informal test. Confidentiality/encryption and
artifact access review remain required before storing personal data in CI artifacts.

## Local verification results and production caveats

- After the dependency updates, the local environment's 22 installed package
  versions returned no advisories from PyPI's version-specific advisory data and
  every package lookup completed. This does not establish the state of Render.
- `pip check`, Django checks, migration consistency, the 58 Django tests, and the
  seven JavaScript lifecycle tests are used to verify this change.
- `check --deploy --fail-level WARNING` using local settings reported W009 for the
  local SECRET_KEY and W021 for intentionally disabled HSTS preload. The local key
  was not rotated: doing so would invalidate sessions and signed links. Confirm a
  strong production key on Render before deployment; the code's absence of a
  default development key alone is not enough. HSTS preload requires a separate
  domain/readiness decision and was not enabled to hide the warning.
- The application has not been deployed or penetration-tested. CAPTCHA/maps and
  sticky positioning still need real-browser verification; no browser-control
  surface is available in this session.
