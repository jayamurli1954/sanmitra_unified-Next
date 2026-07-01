const { test, expect } = require('@playwright/test');

function fulfillJson(route, body, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}

test.describe('MitraBooks CA invite acceptance', () => {
  test('loads public invite details and accepts with matching password', async ({ page }) => {
    const requests = [];
    await page.route('**/api/v1/business/ca/invite/good-token/preview', route => fulfillJson(route, {
      email: 'ca.ravi@example.com',
      full_name: 'CA Ravi',
      tenant_id: 'demo-mitrabooks-business',
    }));
    await page.route('**/api/v1/business/ca/invite/good-token/accept', async route => {
      requests.push(route.request().postDataJSON());
      return fulfillJson(route, {
        ok: true,
        user_id: 'ca-user-1',
        email: 'ca.ravi@example.com',
        full_name: 'CA Ravi',
        role: 'ca_viewer',
      });
    });

    await page.goto('/mitrabooks-erp/ca-invite-accept.html?token=good-token');

    await expect(page.getByRole('heading', { name: 'Accept CA Invite' })).toBeVisible();
    await expect(page.locator('#invite-name')).toContainText('CA Ravi');
    await expect(page.locator('#invite-email')).toContainText('ca.ravi@example.com');
    await expect(page.locator('#invite-tenant')).toContainText('demo-mitrabooks-business');
    await expect(page.locator('#invite-status')).toContainText('Create a password');

    await page.locator('#password').fill('Secret123!');
    await page.locator('#confirm-password').fill('Secret123!');
    await page.locator('#accept-submit').click();

    await expect(page.locator('#invite-status')).toContainText('Invite accepted');
    await expect(page.locator('#ca-invite-form')).toBeHidden();
    expect(requests).toEqual([{ password: 'Secret123!', full_name: 'CA Ravi' }]);
    await expect(page.locator('#password')).toHaveValue('');
    await expect(page.locator('#confirm-password')).toHaveValue('');
  });

  test('blocks mismatched passwords before calling accept endpoint', async ({ page }) => {
    let acceptCalls = 0;
    await page.route('**/api/v1/business/ca/invite/good-token/preview', route => fulfillJson(route, {
      email: 'ca.ravi@example.com',
      full_name: 'CA Ravi',
      tenant_id: 'demo-mitrabooks-business',
    }));
    await page.route('**/api/v1/business/ca/invite/good-token/accept', route => {
      acceptCalls += 1;
      return fulfillJson(route, { ok: true });
    });

    await page.goto('/mitrabooks-erp/ca-invite-accept.html?token=good-token');
    await page.locator('#password').fill('Secret123!');
    await page.locator('#confirm-password').fill('Different123!');
    await page.locator('#accept-submit').click();

    await expect(page.locator('#invite-status')).toContainText('Passwords do not match.');
    expect(acceptCalls).toBe(0);
  });

  test('shows a safe error for missing or expired invite links', async ({ page }) => {
    await page.goto('/mitrabooks-erp/ca-invite-accept.html');
    await expect(page.locator('#invite-name')).toContainText('Invite link is missing a token');
    await expect(page.locator('#ca-invite-form')).toBeHidden();

    await page.route('**/api/v1/business/ca/invite/expired-token/preview', route => fulfillJson(route, {
      detail: 'This invite link has expired. Ask the business to send a new invite.',
    }, 400));
    await page.goto('/mitrabooks-erp/ca-invite-accept.html?token=expired-token');
    await expect(page.locator('#invite-name')).toContainText('Invite unavailable');
    await expect(page.locator('#invite-status')).toContainText('This invite link has expired');
    await expect(page.locator('#ca-invite-form')).toBeHidden();
  });
});
