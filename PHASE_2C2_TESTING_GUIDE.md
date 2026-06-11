# Phase 2C.2 Testing Guide - Collapsible Dashboard Widgets

## Test Target

MitraBooks ERP dashboard widgets in `/mitrabooks-erp/`.

## Test Steps

1. Open the MitraBooks ERP app.
2. Log in with a test account.
3. Navigate to the dashboard.
4. Collapse and expand each widget:
   - KPI Strip
   - Finance Chart
   - CEO Insights
5. Refresh the page.
6. Confirm the collapsed or expanded state is preserved.
7. Repeat at desktop, tablet, and mobile viewport widths.

## Acceptance Criteria

- Collapse button hides only the selected widget content.
- Expand button restores the selected widget content.
- Widget state persists after refresh.
- Widgets remain independent.
- Layout does not overlap or shift unexpectedly.
- Browser console has no new runtime errors.

## Troubleshooting

If controls do not work:

- Check browser console errors.
- Confirm local storage is enabled.
- Hard refresh the page.
- Confirm the current deployment contains the latest frontend build.

If a route returns 404:

- Verify Vercel root directory is `frontend`.
- Verify output directory is `build`.
- Verify `/mitrabooks-erp/` rewrites to the MitraBooks app.
