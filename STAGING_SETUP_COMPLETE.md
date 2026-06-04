# ✅ MitraBooks ERP Staging Setup - COMPLETE!

**Status:** Staging project created and deployed ✅
**Date:** 2026-06-04
**Time:** Setup completed successfully

---

## 🎯 What Was Done

### ✅ Step 1: Vercel Project Created
- **Project Name:** `mitrabooks-erp-staging`
- **Status:** Active & Deployed ✅
- **Current URL:** https://mitrabooks-erp-staging.vercel.app
- **Project ID:** prj_SeLkzIY6Ll48BSCMHxavftQhQBOu

### ✅ Step 2: Project Linked to Git
- **Location:** `D:\sanmitra_unified-Next\frontend\mitrabooks-erp`
- **Configuration:** `.vercel/project.json` created ✅
- **Ready for:** Git branch auto-deployment

### ✅ Step 3: Initial Deployment
- **Deployment ID:** dpl_7qgaTEKdUvc2tUB5jAkpcRhWJRj1
- **Status:** READY ✅
- **URL:** https://mitrabooks-erp-staging-ren7gwd32-jayamurli1954s-projects.vercel.app

### ✅ Step 4: Custom Domain Added
- **Domain:** `staging.mitrabooks.sanmitratech.in`
- **Status:** Added to project (awaiting DNS configuration)

---

## 🔧 What You Need to Do Now

### **Critical: Update DNS Records**

At your domain registrar (sanmitratech.in), add this DNS record:

**Option A: A Record (Recommended)**
```
Name:     staging.mitrabooks.sanmitratech.in
Type:     A
Value:    76.76.21.21
TTL:      3600 (1 hour)
```

**Option B: CNAME Record (Alternative)**
```
Name:     staging.mitrabooks
Type:     CNAME
Value:    cname.vercel-dns.com
TTL:      3600
```

**OR: Change Nameservers to Vercel**
```
Current Nameservers:    ns1.dns-parking.com, ns2.dns-parking.com
Change To (Vercel):     ns1.vercel-dns.com, ns2.vercel-dns.com
```

⏳ **Wait 5-10 minutes for DNS propagation after adding the record**

---

## 📝 Next: Set Environment Variable

After DNS is configured, you need to set the staging API endpoint:

### **On Your Local Machine (PowerShell):**

```powershell
# Navigate to mitrabooks-erp directory
cd D:\sanmitra_unified-Next\frontend\mitrabooks-erp

# Set token (use your Vercel token from https://vercel.com/account/tokens)
$env:VERCEL_TOKEN = "your_vercel_token_here"

# Set environment variable (create a temp file with the API URL)
"https://sanmitra-unified-next-staging-sg.onrender.com" | Out-File -FilePath env_value.txt -Encoding ASCII

# Add the environment variable to the project
npx vercel env add REACT_APP_API_BASE_URL production < env_value.txt

# Clean up
Remove-Item env_value.txt
```

**OR use Vercel Dashboard:**
1. Go to: https://vercel.com/dashboard/mitrabooks-erp-staging
2. Click: Settings → Environment Variables
3. Add New Variable:
   - **Name:** `REACT_APP_API_BASE_URL`
   - **Value:** `https://sanmitra-unified-next-staging-sg.onrender.com`
   - **Environments:** Production

---

## 🔄 Link develop Branch for Auto-Deployment

### **On Your Local Machine (PowerShell):**

```powershell
# Navigate to repo root
cd D:\sanmitra_unified-Next

# Ensure develop branch exists
git branch -a

# If develop doesn't exist, create it:
# git checkout -b develop
# git push -u origin develop

# Push to develop (this will trigger auto-deployment to staging)
git push origin develop
```

**Result:** Every push to `develop` branch will auto-deploy to `staging.mitrabooks.sanmitratech.in`

---

## 🎯 Current Architecture

```
GitHub Repository
├── main branch
│   ├── Code
│   └── → Auto-deploys to production
│       └── https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/
│           (Uses mitrabooks-erp project)
│
└── develop branch
    ├── Code
    └── → Will auto-deploy to staging
        └── https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/
            (Uses mitrabooks-erp-staging project) ✅

Additional Projects (Unchanged):
├── gruhamitra → https://gharmitra.vercel.app ✅
├── mandir-mitra → https://mandir-mitra-alpha.vercel.app ✅
├── legalmitra-frontend → (unchanged) ✅
└── invest-mitra → (unchanged) ✅
```

---

## 📋 Staging Environment Details

| Property | Value |
|----------|-------|
| **Project Name** | mitrabooks-erp-staging |
| **Project ID** | prj_SeLkzIY6Ll48BSCMHxavftQhQBOu |
| **Organization** | jayamurli1954s-projects |
| **Custom Domain** | staging.mitrabooks.sanmitratech.in |
| **Vercel URL** | mitrabooks-erp-staging.vercel.app |
| **Git Branch** | develop (will auto-deploy) |
| **Build Command** | npm run build |
| **Output Directory** | build |
| **Node Version** | 24.x |
| **API Endpoint** | https://sanmitra-unified-next-staging-sg.onrender.com |

---

## 🔗 Links

- **Staging Dashboard (via Vercel):** https://vercel.com/dashboard/mitrabooks-erp-staging
- **Production Dashboard (via Vercel):** https://vercel.com/dashboard/mitrabooks-erp
- **Production URL:** https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/

---

## ✅ Verification Checklist

After completing the DNS setup:

```
⬜ DNS record added at sanmitratech.in
⬜ DNS propagated (wait 5-10 minutes, then: nslookup staging.mitrabooks.sanmitratech.in)
⬜ Staging API endpoint set (REACT_APP_API_BASE_URL)
⬜ develop branch pushed to GitHub
⬜ Auto-deployment triggered (check: https://vercel.com/dashboard/mitrabooks-erp-staging/deployments)
⬜ Test staging URL: https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/
⬜ Verify Phase 2 features working (Parties, Vouchers, Dashboard)
```

---

## 🚀 Ready for Testing!

Once DNS is configured and the develop branch is pushed:

1. **Staging will auto-deploy** every time you push to `develop`
2. **Test Phase 2 features** on: https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/
3. **Run E2E tests** on staging environment
4. **Verify all components:**
   - Party Master (Phase 2A)
   - Account Selector (Phase 2B.1)
   - Voucher Forms (Phase 2B.2-2B.4)
   - Dashboard API (Phase 2C.1)
5. **When ready, merge develop → main** for production deployment

---

## 📞 Summary

✅ **Staging project created on Vercel**
✅ **Custom domain added** (pending DNS configuration)
✅ **Initial deployment live** at mitrabooks-erp-staging.vercel.app
⏳ **DNS setup required** at sanmitratech.in (5-10 min)
⏳ **Environment variables** need to be set via Dashboard
⏳ **develop branch** needs to be pushed for auto-deployment

**Once you complete the DNS and env setup (next 10-15 minutes), staging will be fully operational!** 🚀

---

**Configuration Date:** 2026-06-04  
**Configured By:** Claude (Vercel CLI)  
**Project:** MitraBooks ERP Staging  
**Status:** ✅ Ready for DNS & Env Configuration
