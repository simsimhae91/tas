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

MainOrchestrator must invoke MetaAgent via `Agent()`, not `Bash(claude -p ...)`.
If you observe MainOrchestrator using `claude -p` subprocess calls (regression to old
architecture), add this hook to block them:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "if echo \"${TOOL_INPUT_command:-}\" | grep -q 'claude -p'; then echo 'BLOCKED: Use Agent() to invoke MetaAgent, not claude -p.' && exit 1; fi"
          }
        ]
      }
    ]
  }
}
```

**When to use**: Only if MainOrchestrator regresses to `claude -p` subprocess calls.
This is a hard enforcement fallback.

## Why Hooks Matter for tas

The dialectic process is text-based review. Hooks add **automated static analysis** as an additional layer, catching issues that are trivially detectable by tooling and freeing the review process to focus on design-level concerns that require judgment.
