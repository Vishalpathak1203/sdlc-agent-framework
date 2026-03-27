# Cursor Setup Guide

How to configure Cursor IDE to use the SDLC agent framework.

---

## Prerequisites

1. Weaviate running (`start_weaviate.py`)
2. Codebase indexed (`update_kb.py --repo-root . --project myapp`)
3. Coding standards indexed (`update_kb.py --standards --repo-root . --project myapp`)

---

## Step 1: Make Agent Playbooks Visible to Cursor

### Option A: Add agents folder to workspace (recommended)

In Cursor: **File → Add Folder to Workspace** → select `sdlc-agent-framework/cursor/agents/`

Reference in Composer:
```
Use the controller playbook from the sdlc-agent-framework/cursor/agents/controller.md
```

### Option B: Cursor Rules (auto-loaded per project)

Create `.cursor/rules/sdlc-agents.mdc` in your project:

```markdown
---
description: SDLC agent playbooks for this project
globs: ["**/*"]
alwaysApply: true
---

## Agent Playbooks

These agents are available for the SDLC workflow. Reference them by path.

AGENTS_ROOT: ~/projects/sdlc-agent-framework/cursor/agents
SCRIPTS_ROOT: ~/projects/sdlc-agent-framework/scripts
VENV: ~/.sdlc-agents-venv/bin/python
WEAVIATE_URL: http://localhost:8090
PROJECT: myapp

When working on a ticket, follow: $AGENTS_ROOT/controller.md
When drafting a solution: $AGENTS_ROOT/solution-approach.md
When reviewing code: $AGENTS_ROOT/code-review.md
When responding to PR comments: $AGENTS_ROOT/pr-review-agent.md
```

### Option C: Workspace file

Create `myproject.code-workspace`:
```json
{
  "folders": [
    { "path": "." },
    { "path": "/path/to/sdlc-agent-framework/cursor/agents", "name": "SDLC Agents" }
  ]
}
```

---

## Step 2: Configure MCP Servers

Create `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "mcp-atlassian": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-atlassian"],
      "env": {
        "JIRA_URL": "https://your-org.atlassian.net",
        "JIRA_EMAIL": "your.email@company.com",
        "JIRA_API_TOKEN": "YOUR_JIRA_API_TOKEN"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_GITHUB_TOKEN"
      }
    }
  }
}
```

---

## Step 3: Start a Ticket Workflow

Open Cursor Composer (Cmd+I) and paste:

```
I am starting work on ticket: PROJ-1234

Follow the controller playbook at:
~/projects/sdlc-agent-framework/cursor/agents/controller.md

Project: myapp
Scripts: ~/.sdlc-agents-venv/bin/python ~/projects/sdlc-agent-framework/scripts/
Weaviate: http://localhost:8090
```

The controller will sequence through solution approach → review → code → code review → PR.

---

## Model Selection per Agent

| Agent | Recommended Model | Why |
|-------|------------------|-----|
| controller | claude-haiku-3-5 | Orchestration only, low reasoning needed |
| solution-approach | claude-haiku-3-5 | RAG + structured output |
| solution-review | claude-sonnet-4 | Deep reasoning for architectural decisions |
| code-agent | claude-haiku-3-5 | Fast iteration, TDD loops |
| code-review | claude-sonnet-4 | Nuanced quality analysis |
| unit-test-review | claude-sonnet-4 | Test quality assessment |
| pr-review-agent | claude-sonnet-4 | Diplomatic, context-rich responses |
| knowledge-update | claude-haiku-3-5 | Simple shell command execution |

---

## Cursor Rules Templates

Copy the rules from `../templates/cursor-rules/` to your project's `.cursor/rules/`:

```bash
cp -r ~/projects/sdlc-agent-framework/templates/cursor-rules/* /path/to/your/project/.cursor/rules/
```

Edit each `.mdc` file to match your project's stack.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Agent doesn't follow playbook | Give exact path to playbook in the prompt |
| RAG returns no results | Check Weaviate is running: `curl http://localhost:8090/v1/.well-known/ready` |
| MCP tools not available | Restart Cursor after editing `.cursor/mcp.json` |
| Slow first run | Embedding model downloads on first use (~22MB) |
| Wrong project results | Verify `--project myapp` matches what you used during indexing |
