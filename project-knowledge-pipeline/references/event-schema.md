# Records

`events.jsonl` is append-only. Required: `type`, `title`, `observation`, `evidence`, `result`; optional: `hypothesis`, `action`, `files`, `commit`, `content_value` (`low|medium|high`), `public_safe` (boolean). The helper adds `id` and `timestamp`. Public blog/video drafts include only events explicitly marked `public_safe: true`; omitted means private. Suggested types: `failure`, `rejected_hypothesis`, `root_cause`, `technical_decision`, `user_decision`, `architecture_change`, `scope_change`, `deployment_requirement`, `reproducibility_fact`, `security_privacy`, `validation`, `pre_pipeline_summary`.

`decisions.jsonl` requires `decision`, `reason`; optional: `alternatives`, `status`. The helper adds ID and timestamp. Use for significant decisions only.

`update-repro` accepts a JSON object with keys from `reproducibility.json`. Values replace the supplied keys; omitted keys remain. Include names of required environment variables, never values.
