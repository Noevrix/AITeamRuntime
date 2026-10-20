# Security and disclosure

Do not put keys, cookies, OAuth codes, private transcripts, SQLite databases or
logs in GitHub issues. No public security contact is configured until the owner
confirms the repository. Contact the owner privately before sharing details.

The desktop console binds only loopback, exposes an allowlist of API operations
and does not start models or OAuth. It is not a multi-user server or a security
boundary against malicious software running as the same OS user.

Never distribute `.env`, `runs`, `.local`, databases, WAL/SHM files, credential
stores or build caches. Review both the candidate tree and reachable Git history
before upload. `scripts/audit_release.py` writes only paths/categories under
ignored `.local`; heuristic scanning is not a complete credential detector.

If a real secret has entered Git history, removing the current file is not
sufficient: revoke/rotate it and agree a history-remediation plan before release.
Do not rewrite remote history automatically.
