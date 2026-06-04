# Multi-Tenant Architecture Analysis
**Date:** 2026-06-02  
**Status:** Design Document  
**Scope:** Understanding how login credentials attach to multi-tenant scenarios

---

## Seeded Test Credentials (By App)

Current local/demo credentials must remain app-scoped. Do not reuse one app's tenant-admin login in another app context.

### MitraBooks ERP

Current tested local MitraBooks login:

```text
Email:    businessadmin@sanmitra.local
Password: businessadmin123
App Key:  mitrabooks
```

Planned/optional demo credentials such as `admin@mitrabooks.local` are valid only if the backend startup path explicitly creates that user.

### MandirMitra

```text
Email:    admin@sanmitra.local
Password: admin123
App Key:  mandirmitra
```

### Other Apps

Create separate users per app key. Do not mix MandirMitra, GruhaMitra, LegalMitra, InvestMitra, and MitraBooks credentials.

---

## 🏗️ Current Architecture (From Backend Code Review)

### **1. Authentication Flow**

```
User (email + password)
  ↓
POST /api/v1/auth/login
  ↓
Backend validates credentials via get_user_by_email()
  ↓
Generates JWT token with payload:
{
  "sub": "user_id_123",
  "email": "user@example.com",
  "role": "tenant_admin",
  "tenant_id": "tenant_a",      ← SINGLE tenant per token
  "app_key": "mitrabooks",        ← SINGLE app per token
  "exp": 1717356600,
  "iat": 1717342200
}
  ↓
Returns TokenResponse:
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "xyz123...",
  "token_type": "bearer"
}
```

### **2. Tenant Context Routing**

After login, protected browser API calls use the trusted token context plus the app key. The MitraBooks frontend must not send `X-Tenant-ID` for normal tenant-admin requests.

```text
GET /api/v1/modules/me
Headers:
  X-App-Key: mitrabooks
  Authorization: Bearer <token>

Backend context resolution:
  1. Decode the access token.
  2. Resolve tenant_id, app_key, organization_type, role, and permissions from trusted auth/module policy.
  3. Validate module access before returning tenant data.
  4. Scope all tenant-owned reads and writes to that trusted tenant context.
```

`X-Tenant-ID` is reserved only for explicit super-admin override paths if they are implemented, gated, and audited.
### **3. User-Tenant Relationship**

**Current:** Each user has a **SINGLE tenant_id** in their profile

```
User Document (MongoDB):
{
  "user_id": "user_123",
  "email": "ca@example.com",
  "hashed_password": "bcrypt...",
  "tenant_id": "tenant_a",         ← One tenant only
  "role": "tenant_admin",
  "app_key": "mitrabooks",
  "created_at": "2026-06-01...",
  "auth_provider": "password"
}
```

---

## ❓ Multi-Tenant Scenarios (Your Question)

### **Scenario 1: CA Practice Portal (Multiple Client Books)**

**User:** CA_Admin  
**Need:** Access Client A, Client B, Client C books

**Current System Behavior:**
```
❌ NOT SUPPORTED - User can only have ONE tenant_id
```

**Solution Options:**

**Option A: Multiple User Accounts** (Current Workaround)
```
ca@firm.com → Login for Client A → tenant_a
ca_clientb@firm.com → Login for Client B → tenant_b  
ca_clientc@firm.com → Login for Client C → tenant_c

Pro: Works with existing architecture
Con: Poor UX, multiple passwords, session switching
```

**Option B: Extend Schema** (Future Architecture)
```
User Document enhancement:
{
  "user_id": "user_123",
  "email": "ca@example.com",
  "tenant_ids": [           ← Array instead of single
    "tenant_a",
    "tenant_b",
    "tenant_c"
  ],
  "default_tenant": "tenant_a"
}

Login Response enhancement:
{
  "access_token": "...",
  "refresh_token": "...",
  "accessible_tenants": [   ← Return list
    {
      "tenant_id": "tenant_a",
      "tenant_name": "Client A Books",
      "organization_type": "CA_PRACTICE",
      "default": true
    },
    {
      "tenant_id": "tenant_b",
      "tenant_name": "Client B Books",
      "organization_type": "CA_PRACTICE"
    }
  ]
}

Frontend: Show tenant selector after login
User selects: "Client B Books"
Frontend requests new token for tenant_b
```

---

### **Scenario 2: Professional Bookkeeper (Multi-Organization)**

**User:** Bookkeeper_1  
**Companies:** Org X (BUSINESS), Org Y (PROFESSIONAL)

**Current:** Not supported - need separate accounts

**Future:** Use Option B above with `accessible_tenants`

---

### **Scenario 3: Multi-Branch Single Tenant**

**User:** Branch Manager  
**Company:** Single tenant with 3 branches

**Current Architecture:**
```
✅ SUPPORTED - Tenant controls branch-level access

Branch data is queried within single tenant context:
GET /api/v1/business/dashboard?branch=Mumbai
Headers:
  X-Tenant-ID: tenant_a

Backend filters: WHERE tenant_id='tenant_a' AND branch='Mumbai'
```

**Better approach:** Add branch context header:
```
Headers:
  X-Tenant-ID: tenant_a
  X-Branch: Mumbai
```

---

## 📋 How Credentials Attach (Current Design)

### **Step-by-Step:**

```
1. USER REGISTRATION/CREATION
   ├─ Create user with email + password
   ├─ Assign to ONE tenant_id
   ├─ Set role (tenant_admin, operator, etc.)
   └─ Store in users collection

2. LOGIN
   ├─ POST /api/v1/auth/login {email, password}
   ├─ Verify credentials
   ├─ Generate JWT with tenant_id in payload
   └─ Return access_token

3. API REQUEST
   ├─ Frontend: GET /api/v1/modules/me
   ├─ Header: X-Tenant-ID: tenant_a
   ├─ Header: Authorization: Bearer <token>
   ├─ Middleware: Extract tenant_id from header
   ├─ Middleware: Verify matches token payload
   └─ Execute with tenant context

4. RESPONSE
   └─ Data for ONLY that tenant
```

### **Security Model:**

- ✅ Token can't be reused for different tenant (header must match)
- ✅ User can't access other tenants (single tenant_id per user)
- ✅ Tenant context is immutable per request (ContextVar)
- ⚠️ No built-in mechanism for users with multiple tenants

---

## 🎯 Recommendations for Phase 2

### **Immediate (Phase 2A - Tenant Selection)**

For **now** (single-tenant per user model):

```
After Login Flow:
1. Check if response has "accessible_tenants" array
2. If count == 1: Auto-select that tenant
3. If count > 1: Show tenant selector dropdown
4. User selects tenant
5. Store selected tenant in localStorage
6. Pass X-Tenant-ID header on all API calls
```

### **Code in Frontend:**

```javascript
// After successful login
const response = await apiRequest(appKey, "/api/v1/auth/login", {
  method: "POST",
  body: JSON.stringify({email, password})
});

const payload = response.payload;

// Check if backend returns list of accessible tenants
if (payload.accessible_tenants && payload.accessible_tenants.length > 1) {
  // Show tenant selector UI
  showTenantSelector(payload.accessible_tenants);
} else if (payload.accessible_tenants && payload.accessible_tenants.length === 1) {
  // Auto-select single tenant
  selectTenant(payload.accessible_tenants[0]);
} else {
  // Fallback: Use tenant_id from token
  const tokenPayload = decodeToken(payload.access_token);
  selectTenant({
    tenant_id: tokenPayload.tenant_id,
    tenant_name: "Default Tenant"
  });
}

// Store selected tenant
function selectTenant(tenant) {
  localStorage.setItem("selected_tenant_id", tenant.tenant_id);
  localStorage.setItem("selected_tenant_name", tenant.tenant_name);
  
  // ALL subsequent API calls must include X-Tenant-ID header
  setConfiguredTenantId(tenant.tenant_id);
}
```

### **Future (Phase 3 - Multi-Tenant User Support)**

If backend adds user_tenants support:

```
1. Update User schema: tenant_ids array
2. Update login response: accessible_tenants array
3. Add tenant switching endpoint
4. Frontend: Implement tenant selector
5. Add branch selector (for multi-branch tenants)
```

---

## 🔑 Key Implementation Details

### **API Header Contract:**

```
Required Headers for ALL requests:
├─ X-App-Key: mitrabooks           (specifies app)
├─ X-Tenant-ID: tenant_a           (specifies tenant)
├─ Authorization: Bearer <token>   (validates user)
└─ X-Branch: Mumbai (optional)     (for branch-scoped queries)

Token Payload (JWT):
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "tenant_admin",
  "tenant_id": "tenant_a",
  "app_key": "mitrabooks"
}
```

### **Validation Flow:**

```
Request comes in
  ↓
TenantContextMiddleware
  ├─ Extract X-Tenant-ID header
  ├─ Validate Authorization header token
  ├─ Decode JWT → get token.tenant_id
  ├─ If token.tenant_id != X-Tenant-ID header
  │  └─ ❌ Reject request (403 Forbidden)
  └─ ✅ Set context var and proceed
```

---

## 📊 Credential Scoping Summary

| Scenario | User Setup | Login Flow | API Calls | Status |
|----------|-----------|-----------|-----------|--------|
| **Single Tenant, Single User** | 1 user → 1 tenant | Email/password | X-Tenant-ID header | ✅ Works |
| **Single Tenant, Multi-User** | N users → 1 tenant | Each user logins | Same X-Tenant-ID | ✅ Works |
| **Multi-Tenant, Single User** | 1 user → 1 tenant (can't have >1) | Email/password | Single tenant only | ❌ Not supported |
| **Multi-Branch, Single Tenant** | Users have branches | Email/password | X-Tenant-ID + X-Branch | ✅ Works |
| **CA Practice (Multi-Client)** | 1 CA → N clients | Multiple accounts needed | Each client has X-Tenant-ID | ⚠️ Workaround only |

---

## 🚀 Next Steps

### **Phase 2A Implementation:**

1. **Backend Check:**
   - Does `/api/v1/auth/login` return `accessible_tenants` array?
   - What's the response format?
   - How many test tenants are seeded in dev?

2. **Frontend Build:**
   - Tenant selector UI (dropdown or modal)
   - Store selected tenant in localStorage
   - Pass X-Tenant-ID on all API calls
   - Auto-select if only 1 tenant

3. **Testing:**
   - Login with multi-tenant user
   - Verify tenant context switches
   - Verify data is tenant-scoped

---

## 📞 Questions for Backend Team

1. **What does `/api/v1/auth/login` return?**
   - Just access_token?
   - Or also accessible_tenants array?

2. **Multi-tenant User Support?**
   - Is user_tenants schema planned?
   - Or stick with 1 tenant per user?

3. **Seeded Test Data?**
   - How many tenants in dev environment?
   - Test users available?

4. **Branch Support?**
   - Are branches part of tenant or separate?
   - How to query branch-specific data?

---

**Status:** Ready for Phase 2A implementation once backend responds  
**Document:** architecture/MULTI_TENANT.md
