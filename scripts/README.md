# scripts/

Developer-only tooling for the tas plugin. Scripts in this directory are **NOT**
runtime dependencies of the plugin. They may import packages that are **NOT**
in `skills/tas/runtime/requirements.txt` (which stays at `claude-agent-sdk>=0.1.50`).

End users of `/tas` do not need to install anything from this directory.

## Tools

### `measure-prompt-tokens.py` — Phase 5 SLIM-01

Measures token counts for prompt files via Anthropic `count_tokens` API.
Used when adjusting `skills/tas/agents/meta.md` and
`skills/tas/references/meta-{classify,execute}.md` to stay below the
5,500-token degradation threshold (target 4,500 per D-06).

```bash
pip install anthropic      # dev machine only — NEVER add to runtime/requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/measure-prompt-tokens.py \
    skills/tas/agents/meta.md \
    skills/tas/references/meta-classify.md \
    skills/tas/references/meta-execute.md
```

Exit codes: 0 = success, 1 = user error, 2 = API error.
