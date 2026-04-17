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

## Hook Propagation to Dialectic Agents

The dialectic engine (`dialectic.py`) creates `ClaudeSDKClient` instances with `cwd=project_root`. The spawned CLI subprocess discovers and loads hooks from the project's `.claude/settings.local.json` automatically — no explicit hook-passing code is needed.

**What this means**: If you configure project-level hooks (e.g., PostToolUse lint checks in `.claude/settings.local.json`), those hooks will also fire inside the Thesis and Antithesis agent sessions during the dialectic.

**Plugin-level hooks** (`hooks/hooks.json` in the tas plugin) only fire at the MainOrchestrator level. They do NOT propagate into dialectic agent sessions. This is by design — SessionStart and Stop hooks belong at the orchestrator boundary, not inside the dialectic.

**To apply lint/guard hooks inside the dialectic**: Add them to the project's `.claude/settings.local.json` (not the plugin's hooks.json). The examples above (TypeScript, Python, Go) work for this purpose.

## Plugin Environment Variables

### `${CLAUDE_PLUGIN_ROOT}` (verified)

`CLAUDE_PLUGIN_ROOT` is an **officially documented** Claude Code environment variable
(confirmed via plugin-dev documentation). It resolves to the absolute path of the plugin
directory and is available in:

- **hooks.json `command` fields** — resolved as shell variable interpolation
- **Shell scripts** invoked by hooks — available as a standard environment variable
- **SKILL.md / agent markdown** — referenceable in markdown content

**Best practice**: Always use `${CLAUDE_PLUGIN_ROOT}` in hook commands for portability.
The tas plugin's `hooks.json` already follows this pattern with a safe guard:

```bash
test -n "${CLAUDE_PLUGIN_ROOT:-}" && test -f "${CLAUDE_PLUGIN_ROOT}/hooks/..." && bash "..." || true
```

The `test -n` guard ensures graceful degradation if the variable is ever unset, and
`|| true` prevents hook failures from blocking the session. No additional fallback
pattern (e.g., `$(dirname "${BASH_SOURCE[0]}")/..`) is needed since the variable is
guaranteed by the Claude Code runtime for all plugin hooks.

### `${CLAUDE_SKILL_DIR}` vs `${CLAUDE_PLUGIN_ROOT}`

| Variable | Scope | Resolves To |
|----------|-------|-------------|
| `CLAUDE_SKILL_DIR` | Skill markdown (SKILL.md) | Path to the skill's own directory |
| `CLAUDE_PLUGIN_ROOT` | Hook commands, shell scripts | Path to the plugin root directory |

For multi-skill plugins like tas (with `tas`, `tas-review`, `tas-workspace`, `tas-explain`
under `skills/`), `CLAUDE_SKILL_DIR` points to each skill's specific directory, while
`CLAUDE_PLUGIN_ROOT` always points to the plugin root.

## Why Hooks Matter for tas

The dialectic process is text-based review. Hooks add **automated static analysis** as an additional layer, catching issues that are trivially detectable by tooling and freeing the review process to focus on design-level concerns that require judgment.
