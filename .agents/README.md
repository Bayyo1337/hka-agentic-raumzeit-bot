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
