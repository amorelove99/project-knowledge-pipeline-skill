# Decisions

- Keep one opt-in Skill for all four outputs because they share project evidence.
- Store private records in each project rather than in account-specific chat history.
- Use Python standard library and Markdown files; no service, database, network API, or publishing integration is needed for V1.
- Generate drafts from recorded evidence. Codex reviews semantic claims before calling them finished; a script cannot prove deployment or infer undocumented failures.
- Keep the installed package separate from this source repository, then refresh it after validation.
