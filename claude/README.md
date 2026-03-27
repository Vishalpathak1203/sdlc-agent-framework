# Claude Code Setup Guide

How to configure Claude Code (CLI / VS Code extension) to use the SDLC agent framework.

---

## Prerequisites

1. Weaviate running (`start_weaviate.py`)
2. Codebase indexed (`update_kb.py --repo-root . --project myapp`)
3. MCP servers configured (Jira + GitHub)

---

## Step 1: Copy Commands to Your Project

```bash
cp -r /path/to/sdlc-agent-framework/claude/commands/* /path/to/your/project/.claude/commands/
```

This gives you these slash commands:
- `/configure` — **start here** — auto-detect stack, generate config, run first KB index
- `/solution` — draft solution approach for a ticket
- `/code` — TDD implementation agent
- `/review-code` — code review against standards + patterns
- `/controller` — full SDLC pipeline orchestrator
- `/pr-review` — respond to PR reviewer comments
- `/safe-commit` — pre-commit validation
- `/update-kb` — sync codebase to Weaviate
- `/update-standards` — sync coding rules to Weaviate
- `/update-pr-kb` — sync PR review history to Weaviate
- `/unit-test-review` — audit unit test quality

---

## Step 2: Configure MCP Servers

Add to your project's `.claude/settings.json`:

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

## Step 3: Configure Script Paths

Each command uses these environment variables. Set them in your shell profile or `.claude/settings.json`:

```bash
export AGENTS_ROOT=/path/to/sdlc-agent-framework
export AGENTS_VENV=~/.sdlc-agents-venv/bin/python
export AGENTS_WEAVIATE_URL=http://localhost:8090
export AGENTS_PROJECT=myapp     # your project name
```

Or set them as defaults in `.claude/settings.json`:

```json
{
  "env": {
    "AGENTS_ROOT": "/path/to/sdlc-agent-framework",
    "AGENTS_VENV": "/Users/you/.sdlc-agents-venv/bin/python",
    "AGENTS_WEAVIATE_URL": "http://localhost:8090",
    "AGENTS_PROJECT": "myapp"
  }
}
```

---

## Step 4: Add CLAUDE.md to Your Project

```bash
cp /path/to/sdlc-agent-framework/templates/CLAUDE.md /path/to/your/project/CLAUDE.md
```

Edit it to describe your project's:
- Stack and framework
- Dev commands (run, test, lint, build)
- Architecture overview
- Coding conventions
- Commit message format

---

## Step 5: Test the Setup

```bash
cd /path/to/your/project
claude
```

In the Claude Code session:
```
/update-kb
```

Should index your codebase and report stats.

```
/solution PROJ-1234
```

Should fetch the ticket, query RAG, and produce a solution approach.

---

## Sub-Agent Configuration

Claude Code supports project-level sub-agents in `.claude/agents/`. Copy from the cursor agents and they work identically:

```bash
mkdir -p /path/to/your/project/.claude/agents/scripts
cp /path/to/sdlc-agent-framework/cursor/agents/* /path/to/your/project/.claude/agents/
cp /path/to/sdlc-agent-framework/scripts/*.py /path/to/your/project/.claude/agents/scripts/
```

---

## Settings Template

See [settings-template.json](settings-template.json) for a full example settings.json with:
- All allowed bash commands
- MCP server configs
- Environment variable defaults
- File read permissions
