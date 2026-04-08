# Recommended Hooks for Projects Using tas

Projects that use the tas plugin can add these hooks to `.claude/settings.local.json` for automated static verification when tas produces code.

## TypeScript Projects

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "file=\"${TOOL_INPUT_file_path:-}\"; if [ -n \"$file\" ] && [[ \"$file\" == *.ts ]]; then command -v tsc >/dev/null 2>&1 && tsc --noEmit --pretty \"$file\" 2>&1 | head -20 || true; fi"
          }
        ]
      }
    ]
  }
}
```

## Python Projects

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "file=\"${TOOL_INPUT_file_path:-}\"; if [ -n \"$file\" ] && [[ \"$file\" == *.py ]]; then command -v mypy >/dev/null 2>&1 && mypy --no-error-summary \"$file\" 2>&1 | head -20 || true; fi"
          }
        ]
      }
    ]
  }
}
```

## Go Projects

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "file=\"${TOOL_INPUT_file_path:-}\"; if [ -n \"$file\" ] && [[ \"$file\" == *.go ]]; then command -v go >/dev/null 2>&1 && go vet \"$file\" 2>&1 | head -20 || true; fi"
          }
        ]
      }
    ]
  }
}
```

## Context Protection (Optional)

MainOrchestrator must invoke MetaAgent via `Bash(claude -p ...)`, not `Agent()`.
If you observe MainOrchestrator spawning local agents directly (visible as "N local agents"
in the status bar), add this hook to block `Agent()` calls from the main session:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Agent",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'BLOCKED: MainOrchestrator must not use Agent(). Use Bash(claude -p) to invoke MetaAgent.' && exit 1"
          }
        ]
      }
    ]
  }
}
```

**When to use**: Only if the information hiding in SKILL.md is insufficient and
MainOrchestrator still bypasses MetaAgent. This is a hard enforcement fallback.

**Side effect**: This blocks ALL Agent() calls in the session, including legitimate ones.
If you use other skills that need Agent(), apply this hook selectively during `/tas` runs.

## Why Hooks Matter for tas

The dialectic process is text-based review. Hooks add **automated static analysis** as an additional layer, catching issues that are trivially detectable by tooling and freeing the review process to focus on design-level concerns that require judgment.
