# Atlas Least-Privilege Database User Runbook

## Purpose

The SanMitra unified backend currently authenticates to MongoDB Atlas using a highly privileged
user (`jayamurli1954_db_user`, role `atlasAdmin` on **All Resources**). If that credential leaks,
the blast radius is the entire Atlas project/cluster.

This runbook replaces the application connection credential with a **least-privilege** database
user scoped to only the application database, so a future leak cannot administer the cluster. It
also records how the atlas-admin credential should be handled going forward.

This is an **operator action** performed in the MongoDB Atlas and Render consoles. It is not
code-changeable from this repository. No secrets are committed.

## Background (2026-07-18 incident)

During Stage 5 prep, the full Atlas connection string (including the `atlasAdmin` user password)
was exposed in a chat transcript and rotated the same day. `MONGODB_URI` was updated in Render
staging and the service redeployed green. This runbook is the recommended follow-up hardening so
the app no longer authenticates as an atlas admin at all.

## Target State

| Item | Current | Target |
| --- | --- | --- |
| App DB user | `atlasAdmin` on All Resources | `readWrite` on database `sanmitra` only |
| Atlas admin user | used by app connection string | kept for console/ops only, never in app `MONGODB_URI` |
| Blast radius on leak | whole cluster/project | single application database |

## Step 1 - Create the least-privilege database user (Atlas)

1. Atlas -> **Security -> Database Access -> + ADD NEW DATABASE USER**.
2. Authentication Method: **Password** (SCRAM).
3. Username: e.g. `sanmitra_app_staging` (do not reuse the admin username).
4. Password: **Autogenerate Secure Password** -> copy to the secret manager.
5. Database User Privileges -> **Specific Privileges** (not Atlas admin):
   - Role: `readWrite`
   - Database: `sanmitra`
   - Collection: leave blank (all collections in `sanmitra`).
   - `readWrite` permits creating collections and indexes the app needs; do **not** grant
     `dbAdmin`, `atlasAdmin`, or `readWriteAnyDatabase`.
6. If the app connects to more than one database (confirm `MONGO_DB_NAME`; default is `sanmitra`),
   add an additional `readWrite` entry per database. For staging today only `sanmitra` is used.
7. **Add User**.

Note the authentication database. Atlas SCRAM users authenticate against `admin`, so the
connection string uses `authSource=admin` even though privileges are scoped to `sanmitra`.

## Step 2 - Confirm network access

Atlas -> **Network Access** -> ensure Render's egress and any operator IP are allowlisted (this is
unchanged from the existing setup; creating a new user does not change IP rules).

## Step 3 - Point Render at the new user

1. Render -> **staging service (`sanmitra-unified-next-staging-sg`) -> Environment**.
2. Edit `MONGODB_URI`, replacing username and password with the new least-privilege user:
   ```
   mongodb+srv://sanmitra_app_staging:NEW_PASSWORD@cluster0.dgcpubr.mongodb.net/sanmitra?retryWrites=true&w=majority&appName=Cluster0&authSource=admin
   ```
   Keep the rest of the URI identical (host, `/sanmitra`, `authSource=admin`, options).
3. **Save** -> let Render redeploy.
4. Update the same value in the secret manager. Update any other service/worker that shares the URI.

## Step 4 - Verify

1. After redeploy, check health:
   ```powershell
   curl.exe https://sanmitra-unified-next-staging-sg.onrender.com/health
   ```
   Expect a healthy 200 response.
2. Run a read-only auth precheck against the hosted API to confirm DB-backed reads work end to end:
   ```powershell
   $env:STAGING_APP_KEY = "gruhamitra"
   $env:EXPECTED_TENANT_ID = "gruhamitra-demo-society"
   $env:EXPECTED_ORGANIZATION_TYPE = "HOUSING"
   $env:REQUIRED_MODULES = "housing,accounting,audit"
   $env:E2E_USER_EMAIL = "demo.admin@gruhamitra.sanmitratech.in"
   $env:E2E_USER_PASSWORD = "<gruha demo admin pwd>"
   python scripts/verify_staging_auth.py
   ```
   PASS confirms the app can authenticate to Atlas and read tenant/module context with the
   least-privilege user.
3. Optionally re-run the Stage 5 read-only gate for a broader DB-read confirmation.

## Step 5 - Restrict the atlas-admin credential

1. Keep an `atlasAdmin` user for **console/ops only**; never place it in an application
   `MONGODB_URI` again.
2. Confirm the atlas-admin password rotated on 2026-07-18 is stored only in the secret manager.
3. Do not paste any connection string or password into chat, issues, commits, or CI logs.

## Rollback

If the app fails to connect after Step 3 (for example `Authentication failed` in Render logs):

1. Re-check the new username/password and `authSource=admin` in `MONGODB_URI`.
2. Confirm the new user's `readWrite@sanmitra` privilege and that the database name matches
   `MONGO_DB_NAME`.
3. As a temporary fallback, restore `MONGODB_URI` to the **rotated** admin credential (not the
   leaked one) to restore service, then debug the least-privilege user offline.
4. Financial ledger data must not be edited during any rollback; corrections use reversal entries.

## Notes

- This is a security hardening step, not an accounting or tenant-isolation change.
- Repeat the same procedure for a production database user when `ENVIRONMENT=production` is enabled
  (Path B currently keeps staging), using a separate `sanmitra_app_prod` user and separate secret.
- Label: `[CRITICAL-SECURITY]`.
