# GruhaMitra User Guide

Audience: housing society admins, committee members, residents, and prospective demo users.

Demo URL:

```text
https://www.gruhamitra.sanmitratech.in/gruhamitra/login
```

Public product page:

```text
https://www.gruhamitra.sanmitratech.in/gruhamitra/
```

## Current State

GruhaMitra is available as a housing society operations app with:

- Society dashboard
- Flats and blocks setup
- Member onboarding and management
- Maintenance bill generation
- Maintenance receipt posting
- MitraBooks-backed accounting
- Chart of accounts, vouchers, ledgers, trial balance, and reports
- Complaints
- Meetings, notices, attendance, minutes, and resolutions
- Messages and notice-room style communication
- Society settings and billing rules

Payment gateway and automated notifications are configuration-dependent and may not be enabled for every demo or tenant.

## Target State

GruhaMitra should give each housing society or RWA a tenant-scoped workspace where admins manage society operations and residents view their own society activity, dues, notices, meetings, and service requests.

All accounting-impacting workflows should continue to post through MitraBooks accounting rather than maintaining a separate accounting ledger inside GruhaMitra.

## Important Safety Notes

- Do not share Platform Owner credentials with prospects.
- Use only demo tenant credentials for demos.
- Do not enter real resident personal data in the public demo tenant.
- Do not enter real bank, payment gateway, or production financial credentials in a demo.
- Posted accounting entries should be corrected through reversal or adjustment, not direct editing.

## Demo Credentials

Use these only after the demo seed has been run in the backend environment.

```text
Admin demo  # this is for Society Admin to login
Email: demo.admin@gruhamitra.sanmitratech.in
Password: GruhaDemo@2026

Resident demo # this is for Society resident to login
Email: demo.resident@gruhamitra.sanmitratech.in
Password: ResidentDemo@2026
```

The demo tenant is:

```text
gruhamitra-demo-society
```

## Admin Guide

### 1. Login

1. Open the GruhaMitra login page.
2. Enter the admin demo email and password.
3. After login, confirm the dashboard opens for the demo society.

Expected result:

- The dashboard shows society-level cards such as Society Balance, This Month Billing, Dues Pending, and Complaints Open.
- Recent Activity may show maintenance bills, receipts, meetings, or notices.

### 2. Review Society Dashboard

Use the dashboard to review:

- Society cash/bank balance
- Current month billing
- Pending member dues
- Open complaints
- Recent activity

Notes:

- Society balance should come from MitraBooks accounting balances.
- Billing and dues should come from maintenance bills and member-dues accounting.
- Recent activity should show important posted bills, receipts, notices, and similar operational events.

### 3. Configure Society Profile

Go to Settings and update:

- Society name
- Address
- Email
- Mobile or contact number
- Registration details where applicable

These details should appear in printed reports, vouchers, and downloaded outputs where supported.

### 4. Configure Flats And Blocks

Go to Settings, then Flats and Blocks.

Typical flow:

1. Define blocks or towers.
2. Add flat numbers.
3. Confirm flat area, occupancy capacity, and owner/resident assignment fields where used.
4. Save settings.

Expected result:

- Flats are available for member onboarding.
- Billing can use the flat list for per-flat and per-person calculations.

### 5. Configure Billing Rules

Go to Settings, then Billing Rules.

Common items:

- Maintenance rate by square foot, if area-based billing is used
- Sinking fund per flat
- Repair fund per flat
- Association fund per flat
- Other tenant-specific recurring charges
- Late fee or penalty rules

Notes:

- Billing rules are tenant-wise. One society can use a different rule set from another society.
- If billing rules are changed after bills are generated, regenerate or reverse existing bills as appropriate.

### 6. Configure Accounting Settings

Go to Settings, then Accounting Settings.

Confirm:

- Bank/cash account used for receipts and payments
- Member dues receivable account
- Monthly maintenance income account
- Expense accounts such as water, electricity, salary, repair, and common-area expenses

Important:

- Account names can be tenant-specific. For example, one society may rename a bank account to HDFC Bank Current Account and another may use SBI or Canara Bank.
- Account codes are normally stable/read-only; account names are editable for tenant nomenclature.

### 7. Initialize Chart Of Accounts

Go to Accounting, then Chart of Accounts.

If no accounts are visible:

1. Click Initialize Chart of Accounts.
2. Confirm default accounts are created.
3. Rename account names where needed.

Expected result:

- Default accounting accounts are available.
- Voucher posting and maintenance accounting can proceed.

### 8. Record Society Expenses

Go to Accounting, then Payment Voucher.

Use this for:

- Water tanker charges
- Electricity charges
- Watchman or security salary
- Repairs
- Bank charges
- Vendor payments

Recommended fields:

- Date
- For Month, when the expense belongs to a specific billing month
- Expense account
- Paid to
- Reference number
- Paid from bank/cash account
- Narration

Expected accounting behavior:

- Expense account is debited.
- Bank/cash account is credited.
- The entry appears in ledger and trial balance.

### 9. Record Receipts

Go to Accounting, then Receipt Voucher.

Use this for:

- Member maintenance collections
- Corpus receipts
- Other society receipts

Expected accounting behavior:

- Bank/cash account is debited.
- Appropriate income, liability, or member dues account is credited based on the selected workflow.

### 10. Generate Maintenance Bills

Go to Generate Bills or Maintenance.

Typical flow:

1. Select month and year.
2. Confirm maintenance base rules.
3. Confirm water charges or allow auto-calculation from selected water expense accounts.
4. Confirm fixed expense accounts for the selected month.
5. Confirm fund charges from Billing Rules.
6. Generate bills.

Expected result:

- Bills are generated per flat.
- Per-person charges such as water should use occupant counts.
- Per-flat charges such as sinking fund should apply flat-wise.
- Generated bills can be reviewed in the Existing Bills section.

### 11. Post Maintenance Bills To Accounting

After bills are generated, use Post to Accounting.

Expected accounting behavior:

- Member Dues Receivable is debited.
- Monthly Maintenance Charges is credited.
- The trial balance remains balanced.
- Dashboard billing and dues should reflect posted bills.

### 12. Record Maintenance Receipt

When a member pays:

1. Open Accounting or Maintenance receipt workflow.
2. Select flat/member or bill.
3. Enter payment details.
4. Post receipt.

Expected accounting behavior:

- Bank/cash account is debited.
- Member Dues Receivable is credited.
- Pending dues reduce after successful posting.
- Recent Activity should show the receipt.

### 13. View Member Dues

Go to Reports, then Member Dues Report.

Use this report to know:

- Which members/flats have dues
- Amount pending
- Bill period and payment status

This is the main admin view for collection follow-up.

### 14. Manage Members

Go to Members.

Admin can:

- Add a member
- Assign owner or tenant type
- Enter contact details
- Assign flat
- Set move-in date and occupant count
- Maintain active/inactive status

Important:

- Occupant count matters for per-person water charges and similar calculations.
- Member records must remain tenant-scoped to the society.

### 15. Manage Complaints

Go to Complaints.

Admin can:

- View complaints
- Assign or update status
- Add comments or actions
- Close complaints

Suggested statuses:

- Open
- In progress
- Resolved
- Closed

### 16. Manage Meetings

Go to Meetings.

Admin can:

- Schedule a meeting
- Add agenda items
- Send or mark notice as sent
- Record attendance
- Record minutes
- Add resolutions

Expected result:

- Admin can see meeting status and whether notice was sent.
- Eligible members should see meeting notices where the resident/member view supports it.

### 17. Send Messages

Go to Messages.

Use messages for:

- General announcements
- Maintenance updates
- Meeting reminders
- Service disruption notices

Notifications may depend on tenant configuration. If WhatsApp, SMS, email, or push notification providers are not configured, messages may remain visible inside the app only.

### 18. Generate Reports

Go to Reports or Accounting Reports.

Common reports:

- Society Summary
- Trial Balance
- General Ledger
- Receipts and Payments
- Income and Expenditure
- Balance Sheet
- Member Dues Report
- Asset Register

Printed and downloaded reports should use the tenant's society name and contact details where supported.

## Resident Guide

### 1. Login

1. Open the GruhaMitra login page.
2. Enter the resident demo email and password.
3. Confirm the resident dashboard or available resident menu opens.

Expected result:

- Resident sees society-related information permitted for their role.
- Resident should not see admin-only setup, billing generation, or accounting configuration unless explicitly granted.

### 2. View Dashboard

Residents can use the dashboard to review:

- Society notices
- Meeting notices
- Their own dues, if enabled
- Recent society activity visible to members
- Complaint or service-request shortcuts

### 3. View Dues And Bills

Residents should check their maintenance dues or bill details where enabled.

Typical information:

- Billing month
- Flat number
- Bill amount
- Paid amount
- Pending amount
- Due date
- Bill breakdown

Payment gateway may not be configured in every tenant. If online payment is not enabled, payment must be made through the society's instructed offline method.

### 4. Raise A Complaint

Go to Complaints or Service Requests.

Resident can:

- Create complaint
- Add category and description
- Add attachment if enabled
- Track status
- View admin response

Avoid entering sensitive personal information in a public demo tenant.

### 5. View Meetings And Notices

Residents can view meeting notices and society announcements where their role is eligible.

Typical details:

- Meeting title
- Date and time
- Venue or online meeting details
- Agenda
- Notice status

### 6. View Messages

Residents can open Messages or Notice Room to view society-level communications.

Examples:

- Maintenance updates
- Water or electricity notices
- Meeting reminders
- General circulars

### 7. Update Personal Information

Where enabled, residents may update profile information or request admin correction.

Examples:

- Phone number
- Email
- Family/occupant details
- Vehicle details

Some changes may require admin approval.

## Demo Walkthrough For Prospects

Suggested 15-minute demo sequence:

1. Open the public GruhaMitra page and show the value proposition.
2. Login as demo admin.
3. Show dashboard metrics.
4. Show flats and members.
5. Show billing rules.
6. Show April maintenance bill generation example.
7. Show accounting trial balance and ledger.
8. Show member dues report.
9. Show complaints.
10. Show meetings and notice sent status.
11. Login as demo resident and show what members can see.

## Troubleshooting

### Login Fails

Check:

- Correct email and password
- Demo seed has been run
- User is active
- User app key is `gruhamitra`
- User tenant is `gruhamitra-demo-society`

### Tenant Override Not Allowed

This usually means a user token belongs to one tenant while the frontend is trying to send another tenant in `X-Tenant-ID`.

Fix:

- Logout.
- Clear browser site data for GruhaMitra.
- Login again with the correct demo tenant user.
- Do not use Platform Owner credentials for prospect demos.

### Accounting Shows No Accounts

Fix:

- Initialize Chart of Accounts in the UI, or
- Run the demo seed script without `--skip-coa`.

### Bills Are Not Picking Up Expenses

Check:

- Expense voucher has the correct For Month value.
- Expense account is selected under fixed expense or water charge rules.
- Billing month/year matches the expense period.
- Bills were regenerated after rule or expense changes.

### Dashboard Dues Do Not Match Trial Balance

Check:

- Maintenance bills are posted to accounting.
- Receipts are posted correctly against member dues.
- Dashboard was refreshed after posting.
- Member Dues Receivable account balance matches expected dues.

## Admin Checklist Before Sharing Demo

- Demo admin login works.
- Demo resident login works.
- Dashboard opens without 403 errors.
- Chart of accounts is initialized.
- Flats and members are present.
- Billing rules are configured.
- At least one bill exists.
- At least one receipt exists.
- Member dues report opens.
- Complaints page opens.
- Meetings page shows at least one meeting or notice.
- Messages page opens.

## Contact

```text
WhatsApp: 7904942915
Email: contact@sanmitratech.in
Website: www.sanmitratech.in
GruhaMitra: www.gruhamitra.sanmitratech.in
```

