# Reproducibility and release checks

Prefer current repository metadata and executable behavior over old notes. Record supported platforms, architectures, runtime versions, package and system dependencies, environment variable names, permissions, network needs, service manager, install/start/stop/verification commands, validated environments, and known failures.

For `verify github`, use a disposable clone/worktree or temporary directory without damaging the active tree. Check the actual documented path where practical: fresh checkout, installation, configuration, startup, core function, restart persistence, documentation commands, and secret scan. The helper produces an honest baseline report; update each item to PASS only after a real check. `NOT TESTED` remains `NOT TESTED`.
