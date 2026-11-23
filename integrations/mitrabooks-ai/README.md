# MitraBooks for AI assistants (MCP)

MitraBooks runs a **Model Context Protocol (MCP) server**. Any MCP-capable AI assistant can
read a company's books through it: Claude, Cursor, VS Code Copilot, Gemini CLI, Antigravity,
and others.

| | |
|---|---|
| Server URL | `https://www.mitrabooks.sanmitratech.in/api/v1/mcp` |
| Transport | Streamable HTTP (JSON replies, stateless) |
| Auth | `Authorization: Bearer <token>`. The token is a personal access token starting `mbk_` |
| Access | **Read-only.** 25 report tools; nothing can be posted, edited or deleted |

## 1. Get a token

In MitraBooks: **Settings → Platform Settings → AI Assistant Connections → Create token**.
Copy the token when it appears, because it is shown only once. Tokens expire after 30, 90,
180 or 365 days and can be revoked on the same screen.

What a token can do:
- It acts as **you**: it sees only the tenant and books your login sees, and role checks still
  apply (e.g. the approval queue needs a tenant admin).
- Only its SHA-256 hash is stored. Deactivating your user, your tenant, or the token cuts
  access on the next call.
- It cannot be used to create or manage other tokens.

## 2. Connect your assistant

Replace `mbk_...` with your token. Avoid committing tokens to git: use environment variables
where the client supports them.

### Claude Code: plugin (tools + workflow skills)
```bash
export MITRABOOKS_MCP_TOKEN=mbk_...
```
```
/plugin marketplace add <path or git URL of this integrations/mitrabooks-ai folder>
/plugin install mitrabooks@mitrabooks
```
The plugin adds the MCP server plus two skills: **month-end-review** and **gst-return-prep**.

### Claude Code: server only
```bash
claude mcp add --transport http mitrabooks https://www.mitrabooks.sanmitratech.in/api/v1/mcp --header "Authorization: Bearer mbk_..."
```

### Cursor (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "mitrabooks": {
      "url": "https://www.mitrabooks.sanmitratech.in/api/v1/mcp",
      "headers": { "Authorization": "Bearer mbk_..." }
    }
  }
}
```

### VS Code / GitHub Copilot (`.vscode/mcp.json`)
```json
{
  "servers": {
    "mitrabooks": {
      "type": "http",
      "url": "https://www.mitrabooks.sanmitratech.in/api/v1/mcp",
      "headers": { "Authorization": "Bearer mbk_..." }
    }
  }
}
```

### Gemini CLI (`~/.gemini/settings.json`)
```json
{
  "mcpServers": {
    "mitrabooks": {
      "httpUrl": "https://www.mitrabooks.sanmitratech.in/api/v1/mcp",
      "headers": { "Authorization": "Bearer mbk_..." }
    }
  }
}
```

### Google Antigravity and other MCP clients
Add a remote (HTTP) MCP server with the URL above and the `Authorization` header. The JSON
key names differ between clients, so check the client's MCP docs.

### Claude Desktop
Desktop "custom connectors" sign in with OAuth, which MitraBooks does not offer yet (see
Roadmap). Until then, bridge through `mcp-remote` in `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "mitrabooks": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://www.mitrabooks.sanmitratech.in/api/v1/mcp",
               "--header", "Authorization:${MITRABOOKS_AUTH}"],
      "env": { "MITRABOOKS_AUTH": "Bearer mbk_..." }
    }
  }
}
```

### claude.ai web and ChatGPT
Both add remote servers as connectors that sign in with **OAuth**, which is not available
yet. See Roadmap.

## Tools

| Area | Tools |
|---|---|
| Ledger | `list_accounts`, `get_trial_balance`, `get_profit_and_loss`, `get_balance_sheet`, `get_account_ledger`, `list_journal_entries`, `get_journal_entry` |
| Parties / AR-AP | `list_parties`, `get_party_statement`, `get_aging_report`, `list_open_items`, `list_unallocated_payments` |
| GST / TDS | `get_gstr3b`, `get_gstr1`, `get_cmp08`, `get_gstr4`, `get_tds_register` |
| Banking | `get_bank_reconciliation`, `get_cash_bank_book` |
| Health | `get_dashboard`, `get_mis_kpis`, `get_financial_health`, `get_cash_flow_forecast`, `get_data_health`, `list_pending_approvals` |

Every tool accepts an optional `accounting_entity_id` for companies with more than one set of books.

## How it works (for developers)

- Code: `app/modules/mcp/` (`tokens.py`, `tools.py`, `server.py`, `router.py`); tests in
  `tests/test_mcp_server.py`.
- Each tool maps to an **existing GET route**. The server swaps the personal token for a
  short-lived access token for that user and calls the route in-process. Every auth, role,
  module-gate and tenant check is the web app's own code, so nothing is duplicated.
- Path arguments are type- and pattern-checked before a path is built, and unknown arguments
  are rejected. Only allow-listed GET routes are reachable.
- Token create and revoke actions are written to the audit log. The endpoint is rate-limited
  to 120 requests a minute.

## Roadmap
1. **OAuth 2.1** (authorization server, PKCE, dynamic client registration) so claude.ai,
   Claude Desktop connectors and ChatGPT can connect with a sign-in button.
2. **Write tools** behind a separate scope: draft journal or invoice, match a bank line,
   record a payment. Each is created as a draft for a human to approve, and the audit trail
   marks it as AI-initiated.
3. More skills: bank-feed coding, TDS quarter prep, CA review pack, year-end close.
4. Publish the marketplace from its own public repo and submit to the Claude plugin directory.
