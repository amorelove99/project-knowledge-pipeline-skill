# Privacy boundary

Private pipeline data stays outside normal Git status through `.git/info/exclude`. Do not put credentials, tokens, cookies, SSH keys, OAuth data, personal email addresses, device identifiers, or `.env` values into records. Environment variable names are permitted.

Public exports sanitize home paths, email addresses, and private hosts/IPs. Blog and video include only records explicitly marked `public_safe: true`; all others stay private. Suspected credentials block output and report only the category, never the value. Review public drafts for context-specific sensitive details that a mechanical scanner cannot recognize. Obsidian may retain more local context, but no secrets. The helper never publishes or pushes.
