# MitraBooks — OfficeMitra AI (User Guide)

*Source for section 24 added to `docs/MitraBooks_User_Manual.docx`.*


## 24. OfficeMitra AI

**OfficeMitra AI** is SanMitra's thin AI productivity layer inside MitraBooks ERP. It helps you capture tasks, summarize pasted email and meeting notes, parse calendar text, view in-app notifications, and generate a **Today Brief**. When enabled for your tenant, it can also run the **CA Analysis Pack (MIS)** workflow: import Excel facts, reconcile with maker/checker, and export PDF/Excel/PPT packs. It does **not** post journals, invoices, or GST entries from MIS flows.

Open it from **Main Workspaces → OfficeMitra AI** in the left navigation, or from the **OfficeMitra AI** chip on the dashboard.

All AI output is **advisory only** — review before acting. It is not final legal or financial advice.


### 24.1 Opening the workspace

1. Sign in to MitraBooks ERP with a user whose tenant has the **office_ai** module enabled.
1. In the sidebar, under **Main Workspaces**, click **OfficeMitra AI**.
1. The workspace opens with tabs across the top: **Tasks**, **Email Summary**, **Calendar**, **Meeting Notes**, **Notifications**, and **Today Brief**. Additional tabs appear when your administrator enables write-back, MIS, or workflows.

### 24.2 Tasks

Use Tasks to track follow-ups manually or with AI assistance. Paste notes or instructions in the text area, then:

1. Click **Save as task** to store the first line as a manual task.
1. Click **Generate with AI** to ask OfficeMitra to suggest tasks (requires AI provider configuration; otherwise the UI soft-fails with a clear message).
1. Click **Done** on an open task when it is complete.
1. Click **Refresh** to reload the task list.

### 24.3 Email Summary

Paste the full text of an email (no mailbox OAuth in this release). Click **Summarize + suggest tasks** to store a summary and optional follow-up tasks.


### 24.4 Calendar (paste-in)

Paste ICS calendar blocks or simple agenda lines (for example **"10:00 Client GST review"**). Click **Parse + save events** to add today's events. Use **Refresh today** to reload the list.


### 24.5 Meeting Notes

Paste meeting notes, then click **Summarize + suggest tasks**. Summaries are stored for later reference; optional tasks may be proposed when write-back is enabled.


### 24.6 Notifications

OfficeMitra maintains an in-app notification inbox (not email push). Click **Mark read** on individual items or **Refresh** to update the unread count badge on the tab.


### 24.7 Today Brief

The Today Brief combines OfficeMitra-native data and any available connector sections (for example open tasks and today's calendar). Click **Generate today's brief** to create or refresh today's digest. Click **Load latest** to fetch the saved brief without regenerating.


### 24.8 Proposals (confirmation and checker)

When **office_ai.writeback** or MIS export/reconcile is enabled, AI-suggested writes and MIS actions appear in the **Proposals** tab instead of executing immediately.

1. Review the summary, action type, confidence, and status.
1. As **maker**, click **Confirm** on pending proposals you prepared.
1. When maker-checker policy applies, a different user (**checker**) clicks **Approve (checker)** — you cannot approve your own proposal.
1. Click **Dismiss** to discard a proposal you do not want to execute.

### 24.9 MIS Packs (CA Analysis Pack)

Available when **office_ai.mis** and related import/export flags are enabled. This is for monthly MIS assembly — not day-to-day bookkeeping.

1. Open the **MIS Packs** tab.
1. Choose a metric pack and period, then click **Create draft pack**.
1. Upload the SanMitra CA MIS Excel template. Use **Persist valid rows after validation** when ready to insert facts.
1. Review the KPI dashboard and fact table derived from imported rows (not AI estimates).
1. As maker, enter an optional data-quality score and click **Submit reconcile**.
1. After checker approval, use **Export Excel**, **Export PDF summary**, or **Export PPT (checker)**. Files download to your browser.
- MIS flows never write to the General Ledger or GST registers.
- PPT export typically requires a quality score of at least 70 and a separate checker.

### 24.10 Advisory and data boundaries

- OfficeMitra reads companion modules through connectors only — it is not the books of record.
- Figures in MIS packs come from imported or connector-sourced facts; narrative AI must cite those facts.
- Without an AI provider key, task generation and briefs still work with deterministic fallbacks where implemented.
- Contact your platform administrator to enable office_ai, MIS, or write-back flags for your tenant.
