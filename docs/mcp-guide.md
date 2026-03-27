# MCP Guide: Jira and GitHub

Model Context Protocol (MCP) lets AI agents call external tools directly — no copy-pasting ticket descriptions, no manual context gathering.

---

## What MCP Enables

Without MCP:
```
Developer: (copies Jira ticket) pastes into Cursor...
           (opens GitHub PR) copies diff...
           (pastes into Cursor)...
```

With MCP:
```
Agent: mcp__jira__get_issue("PROJ-1234")        → full ticket, acceptance criteria
       mcp__github__get_pull_request(...)        → PR title, description, diff
       mcp__github__get_pull_request_files(...)  → changed files
       mcp__github__get_pull_request_comments()  → existing review comments
```

The agent has full context automatically.

---

## Jira MCP Setup

### Installation

The Jira MCP server (`mcp-atlassian`) connects to your Jira instance via API token.

```bash
# Install via npx (no global install needed)
npx @modelcontextprotocol/server-atlassian --help
```

### Configuration

**Claude Code** — add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "mcp-atlassian": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-atlassian"],
      "env": {
        "JIRA_URL": "https://your-org.atlassian.net",
        "JIRA_EMAIL": "your.email@company.com",
        "JIRA_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

**Cursor** — add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mcp-atlassian": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-atlassian"],
      "env": {
        "JIRA_URL": "https://your-org.atlassian.net",
        "JIRA_EMAIL": "your.email@company.com",
        "JIRA_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

### Getting an API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create token → name it "sdlc-agents"
3. Copy the token value (shown once)

---

## Jira MCP Tools

### Fetch a ticket

```
mcp__mcp-atlassian__jira_get_issue(issue_id: "PROJ-1234")
```

Returns: summary, description, acceptance criteria, status, assignee, labels, priority, linked issues.

Use in **solution-approach** agent:
```markdown
## Step 1 — Gather ticket details

Call:
mcp__mcp-atlassian__jira_get_issue(issue_id: "$TICKET_ID")

Extract:
- Summary (title)
- Description
- Acceptance criteria (usually in description under "## Acceptance Criteria")
- Labels (may indicate area: frontend, backend, performance)
- Linked issues (dependencies, blocks)
```

### Search tickets

```
mcp__mcp-atlassian__jira_search(
  jql: "project = PROJ AND sprint in openSprints() AND status != Done",
  fields: ["summary", "status", "assignee"]
)
```

### Add a comment

```
mcp__mcp-atlassian__jira_add_comment(
  issue_id: "PROJ-1234",
  comment: "Solution approach drafted and stored in Weaviate. Ready for review."
)
```

Use in **controller** agent after Stage 1 completes.

### Transition issue status

```
mcp__mcp-atlassian__jira_transition_issue(
  issue_id: "PROJ-1234",
  transition: "In Progress"
)
```

---

## GitHub MCP Setup

### Installation

```bash
# Install via npx
npx @modelcontextprotocol/server-github --help
```

### Configuration

**Claude Code** — add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

**Cursor** — add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

### Getting a GitHub Token

1. Go to https://github.com/settings/tokens/new (Classic)
2. Scopes needed: `repo`, `read:org`, `read:user`
3. Copy the token value

---

## GitHub MCP Tools

### Fetch PR details

```
mcp__github__get_pull_request(owner: "org", repo: "myrepo", pull_number: 123)
```

Returns: title, description, base branch, head branch, status, mergeable state.

### Fetch PR files changed

```
mcp__github__get_pull_request_files(owner: "org", repo: "myrepo", pull_number: 123)
```

Returns: list of files with additions, deletions, patch content.

Use in **pr-review-agent** to understand what was changed without checking out the branch.

### Fetch PR review comments

```
mcp__github__get_pull_request_comments(owner: "org", repo: "myrepo", pull_number: 123)
```

Returns: all review comments with content, file path, line number, author, resolved status.

Use in **pr-review-agent** to respond to existing comments.

### Post a PR review

```
mcp__github__create_pull_request_review(
  owner: "org",
  repo: "myrepo",
  pull_number: 123,
  event: "COMMENT",
  body: "Overall looks good. See inline comments."
)
```

### List recent PRs (for PR KB)

```
mcp__github__list_pull_requests(
  owner: "org",
  repo: "myrepo",
  state: "closed",
  per_page: 50,
  sort: "updated"
)
```

Use in **update_pr_kb.py** to fetch review history.

---

## Agent Workflow: Solution Approach with MCP

```markdown
## Step 1 — Fetch ticket via Jira MCP

mcp__mcp-atlassian__jira_get_issue(issue_id: "PROJ-1234")

Extract: title, description, acceptance criteria, labels.

## Step 2 — RAG query based on ticket content

Extract 3-5 concepts from the ticket.
For each concept:
  python query_rag.py "<concept>" --project myapp --rerank --top 5

## Step 3 — Generate solution

Using ticket context + RAG results → draft solution approach.

## Step 4 — Store solution

python query_rag.py --store-solution --ticket "PROJ-1234" --title "..." --approach-file solution.md

## Step 5 — Update Jira

mcp__mcp-atlassian__jira_add_comment(
  issue_id: "PROJ-1234",
  comment: "Solution approach drafted. Stored in Weaviate for ticket pipeline."
)
mcp__mcp-atlassian__jira_transition_issue(issue_id: "PROJ-1234", transition: "In Progress")
```

---

## Agent Workflow: PR Review Agent with MCP

```markdown
## Step 1 — Fetch PR context

mcp__github__get_pull_request(owner, repo, pull_number)
mcp__github__get_pull_request_files(owner, repo, pull_number)
mcp__github__get_pull_request_comments(owner, repo, pull_number)

## Step 2 — Retrieve solution context

python query_rag.py --get-solution "$TICKET_ID"

## Step 3 — Query review patterns for changed files

For each changed file path:
  python query_rag.py "<file path>" --collection reviews --project myapp --top 3

## Step 4 — Generate responses to each reviewer comment

For each unresolved comment:
  - Read comment content and file context
  - Acknowledge the feedback
  - Explain the change made (or why not)
  - Reference RAG context if relevant

## Step 5 — Post responses

mcp__github__add_issue_comment(owner, repo, issue_number, body: "...")
```

---

## Security Notes

- Never commit MCP tokens to git
- Use environment variables or secret managers
- For CI/CD: use GitHub Actions secrets, not `.env` files
- Rotate tokens every 90 days
- Use minimum required scopes

```bash
# Check what scopes your token has
gh auth status
curl -H "Authorization: token ghp_..." https://api.github.com/user
```
