# Recommended Hooks for Projects Using dial

Projects that use the dial plugin can add these hooks to `.claude/settings.local.json` for automated static verification when dial produces code.

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

## Why Hooks Matter for dial

The dialectic loop (thesis → antithesis → synthesis) is text-based review. Hooks add **automated static analysis** as a fourth layer:

1. ThesisAgent produces code
2. **Hook runs** — catches type errors, syntax issues immediately
3. AntithesisAgent reviews semantics, consistency, domain patterns
4. AntithesisAgent traces boundary values (Lens 4)

The hook catches issues that are trivially detectable by tooling, freeing the agents to focus on design-level concerns that require judgment.
