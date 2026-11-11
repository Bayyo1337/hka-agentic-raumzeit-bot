# AI agent workspace

This directory contains repository-owned guidance for AI coding agents. It is
deliberately tool-agnostic so that GitHub Copilot, Claude, Gemini, and local
automation can follow the same project rules.

## Structure

```text
.agents/
├── README.md
├── roles/
│   ├── implementer.md
│   ├── integrator.md
│   ├── researcher.md
│   ├── reviewer.md
│   └── strategist.md
└── templates/
    └── handoff.md
```

`AGENTS.md` in the repository root is the mandatory entry point. Role files
describe responsibilities, not a specific CLI or model. Agents should leave a
handoff when another agent must continue the task.

The older `.gemini/` directory contains Gemini CLI-specific prompts and skills.
It is complementary to this structure and is not duplicated here.

## Model routing

Role-to-model assignments are stored in `.agents/models.toml`. It contains
model names and workflow policy only; credentials and provider configuration
remain in the local runner environment.

Recommended routing:

| Role | Model profile | Reason |
|---|---|---|
| Strategist | strong reasoning | Scope, sequencing, and acceptance criteria |
| Researcher | fast/cheap | Evidence collection and reproduction |
| Implementer | strong coding | Surgical implementation and tests |
| Reviewer | reasoning-focused | Independent bug and regression detection |
| Integrator | strong general model | Resolve findings and final validation |

Any OpenAI-compatible runner may load the model names and override them through
environment variables or command-line options. Each handoff must record the
effective model and any fallback. API keys and secret-bearing prompts must
never be committed.

## Execution protocol

1. Strategist defines a bounded work package and acceptance criteria.
2. Researcher gathers evidence and reproduces current behavior.
3. Implementer changes only the approved files and adds focused tests.
4. Reviewer independently checks the diff and validation results.
5. Integrator handles only review findings, runs final checks, and writes the
   release handoff.

Agents must not edit the same files concurrently. A failed gate returns the
work package to the responsible role instead of silently advancing it.

For wrappers and CI, resolve the effective model with:

```bash
python scripts/resolve_agent_model.py researcher
AGENT_REVIEWER_MODEL=o3 python scripts/resolve_agent_model.py reviewer
```

The environment override pattern is `AGENT_<ROLE>_MODEL`. This makes model
selection explicit per run while keeping the repository configuration
portable.
