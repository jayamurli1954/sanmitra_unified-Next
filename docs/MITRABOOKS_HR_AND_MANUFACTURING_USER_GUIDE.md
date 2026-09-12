# MitraBooks — HR & Payroll and Manufacturing & Cost Centres (User Guide)

*This is the source for the two enterprise-module sections added to `docs/MitraBooks_User_Manual.docx` (sections 22 and 23).*


## 22. HR & Payroll

HR & Payroll is an **enterprise add-on**. It is off by default and must be provisioned by your platform administrator and then enabled in MitraBooks before the workspace becomes active. It manages employees, salary structures, payroll runs, leave, investment declarations (Form 12BB) and full & final settlements, and posts payroll to the General Ledger.

Open it from **Human Resources → HR & Payroll** in the left navigation.


### 22.1 Activating HR & Payroll

1. Your platform administrator first **provisions** the add-on for your organization.
1. A business administrator then sees an **Enable HR & Payroll** button in the workspace and clicks it.
1. Once active, the tabs Employees, Payroll, Leave, Form 12BB, Full & Final and Analytics appear.
Access is role-based: an HR Manager or the tenant administrator can manage; a Payroll Auditor has read-only access.


### 22.2 Salary Structures

A salary structure is a reusable template of formula-driven components (Basic, HRA, allowances) used when assigning salaries.

1. On the **Employees** tab, find **Salary Structures**.
1. Enter a name (e.g. **Standard (Non-metro)**), a Basic formula (e.g. **GROSS * 0.5**) and an HRA formula (e.g. **BASIC * 0.4**).
1. Click **Add Structure**.

### 22.3 Adding an Employee

Employees follow an onboarding lifecycle: **Offered** → **Joined** or **Declined**. An employee code is minted only when the candidate joins, so declined candidates never consume a code.

1. Click **+ Add Employee** and fill in name, designation, dates and contact details. The new employee starts in the Offered state.
1. Use **Assign Salary** to attach a salary structure and the CTC figures.
1. When the candidate joins, click **Mark Joined** — the employee code is generated at this point.

### 22.4 Appointment & Joining Letters

1. Open **Letter Settings** to configure the clauses and branding that appear on letters.
1. From an employee row, generate the **Appointment Letter** (offer stage) or the **Joining Letter** (after joining) as a PDF.

### 22.5 Running Payroll

1. Go to the **Payroll** tab and click **Run Payroll** for the pay period.
1. The engine computes each slip with EPF, ESI, Professional Tax (state slabs), TDS (new and old regime, with rebate and cess) and gratuity, all in fixed-precision money.
1. Loss-of-pay is derived from approved leave — it is never typed in.
1. The run produces salary slips and one consolidated journal entry to the GL. Download any slip as a PDF from the run.

### 22.6 Leave Management

1. Create leave types on the **Leave** tab (mark a type as loss-of-pay if applicable).
1. Allocate leave balances to employees.
1. Employees apply for leave; an approver approves or rejects. Approved leave feeds the loss-of-pay calculation in payroll.

### 22.7 Form 12BB (Investment Declarations)

Form 12BB lets employees declare investments and submit proofs so old-regime TDS is computed correctly.

1. On the **Form 12BB** tab the employee declares investments and uploads proof.
1. HR verifies the declaration; verified amounts flow into the old-regime TDS calculation at payroll time.

### 22.8 Full & Final Settlement

1. On the **Full & Final** tab, create an F&F for a leaving employee. Gratuity is computed from tenure.
1. Move it through **Draft → Approved → Paid**. Download the F&F statement as a PDF.

### 22.9 Analytics

The **Analytics** tab shows a trailing-month payroll dashboard (headcount, payroll cost and statutory totals) computed from the posted runs.


## 23. Manufacturing & Cost Centres

This is an **enterprise add-on** with two independent layers: **Cost-Centre Accounting** (departmental/branch budgets and P&L) and **Manufacturing** (bills of materials and work orders). Manufacturing depends on cost centres. Both are off by default and provisioned per organization.

Open it from **Manufacturing → Manufacturing** in the left navigation. It has five tabs: Cost Centres, Budgets, Cost-Centre P&L, BOMs and Work Orders.

**Important — how it affects your books: **the module is built for periodic inventory. Work orders do not post their own inventory journals (that would double-count against the period-end closing-stock entry). Instead they record production and a standard-vs-actual variance for reporting, and feed finished goods and raw-material consumption into the stock register so closing-stock valuation stays correct.


### 23.1 Activating the Add-on

1. The platform administrator provisions Cost-Centre Accounting (and, if needed, Manufacturing) for the organization.
1. A business administrator clicks **Enable Cost Centres**; enabling **Manufacturing** automatically requires cost centres to be on.

### 23.2 Cost Centres

A cost centre is a department, branch or activity you want to measure separately. Cost centres can be nested (e.g. Assembly Line rolls up into Factory, which rolls up into Operations).

1. On the **Cost Centres** tab, enter a Code (e.g. MFG-ASY-01), a Name (e.g. Assembly Line 1) and an optional Parent code.
1. Click **+ Add Cost Centre**. The hierarchy is shown beneath the list.

### 23.3 Tagging Postings to a Cost Centre

Cost centres become useful when transactions carry them. A journal line may be tagged with a cost centre; the system rejects any cost centre that does not belong to your entity, so figures never mix across tenants or entities.


### 23.4 Cost-Centre Budgets

1. On the **Budgets** tab, pick a cost centre, a fiscal year (and optional month), an account and an allocated amount, then **+ Add Budget**.
1. Move a budget **Draft → Approved → Locked**. Only approved/locked budgets drive the variance report.
1. Click **Vs Actual** on a budget to see allocated vs actual spend, variance and burn-rate per account, with unbudgeted spend surfaced separately.

### 23.5 Cost-Centre P&L

1. On the **Cost-Centre P&L** tab, choose a date range and click **Run**.
1. The report shows income, expense and net per cost centre, plus an Untagged bucket, with totals that tie back to the period P&L.
1. Export to **CSV** or **Excel** with the buttons provided.

### 23.6 Bills of Materials (BOM)

A BOM is the recipe for a finished good: the component items it consumes (with a standard rate and scrap allowance) and the operations performed (with an overhead rate). From these the system computes a deterministic standard cost. BOMs reference items from the inventory item master, so create your items first.

1. On the **BOMs** tab, open **+ New BOM**, choose the finished good and an output quantity.
1. Add each component (item, quantity, rate, scrap %) with **Add line**.
1. Click **Save BOM**. The standard cost (total and per unit) is shown in the BOM list.

### 23.7 Work Orders

A work order plans production of a finished good against a BOM and tracks it through its lifecycle: **Draft → Released → In Progress → Completed** (or Cancelled).

1. On the **Work Orders** tab, pick a BOM, a planned quantity and (optionally) the production cost centre, then **+ Create Work Order**. The standard cost is snapshotted.
1. Use **Release** and **Start** to advance the work order.
1. Click **Complete**, enter the produced quantity, actual overhead and actual material consumed (item, quantity, rate), then **Confirm Completion**.
1. The work order shows the **variance** (actual vs standard); a favourable variance is marked. The finished goods and consumed materials flow into the stock register.

### 23.8 How It Affects Stock and the Ledger

- Finished goods produced are added to stock at their production cost.
- Raw materials consumed reduce stock at weighted-average cost.
- No separate work-order inventory journal is posted; financial recognition flows through the existing closing-stock entry, keeping the books consistent under periodic inventory.
- Variance is management information for cost control, tagged to the production cost centre.
