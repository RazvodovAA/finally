# Review

## Findings

1. High: The new quick-start instructions point to scripts that do not exist in this checkout, so the documented startup path is broken. [README.md](/Users/antonrazvodov/projects/finally/README.md:8) and [README.md](/Users/antonrazvodov/projects/finally/README.md:9) tell users to run `scripts/start_mac.sh` and `scripts/start_windows.ps1`, but there is no `scripts/` directory in the repo. Anyone following the README will fail before they even reach app setup.

2. Medium: The auto-review hook is self-referential and will start reviewing prior review output on subsequent runs. [.claude/settings.json](/Users/antonrazvodov/projects/finally/.claude/settings.json:2) wires every `Edit|Write` stop event to `codex exec "Please review all changes since the last commit and write feedback to planning/REVIEW.md"`. Because `planning/REVIEW.md` is itself an uncommitted change after the first run, the next review will include the previous review text in its own diff. That creates churn and makes later reviews less about the project change and more about the review artifact. Exclude `planning/REVIEW.md` from the review target or write the report outside the tracked tree.

3. Medium: The canonical project spec now contains review scratch notes and informal answers, which makes it an unreliable contract for downstream agents. [planning/PLAN.md](/Users/antonrazvodov/projects/finally/planning/PLAN.md:460) appends unresolved review commentary directly into the spec, including placeholder answers like `whatever in intersection of simple implementation and user appealing` and `ANSWE: empty heat map`. Agents reading `PLAN.md` as source of truth now have to distinguish requirements from reviewer chatter, and some of those notes are not written at implementation quality. This material belongs in a separate review file, not in the main specification.

4. Medium: The renamed `cerebras` skill is currently internally inconsistent and the code samples will not run as written. [.claude/skills/cerebras/SKILL.md](/Users/antonrazvodov/projects/finally/.claude/skills/cerebras/SKILL.md:20) removes the old `EXTRA_BODY` constant, but the example calls still pass `extra_body=EXTRA_BODY` on [line 28](/Users/antonrazvodov/projects/finally/.claude/skills/cerebras/SKILL.md:28) and [line 35](/Users/antonrazvodov/projects/finally/.claude/skills/cerebras/SKILL.md:35). Anyone following the skill will hit `NameError` immediately.

## Residual Risk

I did not find executable app code changes in this diff, so the main risk here is workflow breakage and bad guidance rather than a runtime regression in `backend/`.
