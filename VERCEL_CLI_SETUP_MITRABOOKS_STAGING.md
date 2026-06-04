# Vercel CLI: MitraBooks ERP Staging Setup

**⚠️ IMPORTANT:** This setup is for **MitraBooks ERP ONLY**. It will NOT affect GruhaMitra or MandirMitra projects.

---

## 🎯 What We're Building

**Staging Environment:**
- **Name:** mitrabooks-erp-staging
- **URL:** `staging.mitrabooks.sanmitratech.in`
- **Branch:** `develop`
- **Root:** `frontend`
- **Served app path:** `/mitrabooks-erp/`
- **Backend API:** Staging (https://sanmitra-unified-next-staging-sg.onrender.com)

**Production Remains Unchanged:**
- **Name:** mitrabooks-erp (existing)
- **URL:** `www.mitrabooks.sanmitratech.in`
- **Branch:** `main`
- **Backend API:** Production

---

## 📋 Prerequisites

✅ Vercel CLI installed
✅ Git repository with `develop` branch
✅ GitHub/GitLab/Bitbucket account
✅ Access to sanmitratech.in DNS (for custom domain)

---

## 🚀 Step-by-Step Setup

### **Step 1: Create a New Vercel Project (Staging)**

```bash
# Navigate to the frontend build root
cd D:\sanmitra_unified-Next\frontend

# Login to Vercel (if not already logged in)
vercel login

# Create a NEW project for staging
vercel --prod --name mitrabooks-erp-staging

# When prompted:
# - Set up and deploy?: YES
# - Which scope should contain your new project?: [Your Team/Account]
# - Link to existing project?: NO (create new)
# - What's your project's name?: mitrabooks-erp-staging
# - In which directory is your code?: . (current directory, since we're in frontend)
# - Want to modify your vercel.json?: YES
# - Build Command?: npm run build
# - Output Directory?: build
# - Development Command?: npm start
```

### **Step 2: Verify Project Creation**

```bash
# Check if vercel.json was created in the staging project directory
vercel projects

# Should list both:
# - mitrabooks-erp (production)
# - mitrabooks-erp-staging (new staging project)
```

### **Step 3: Configure Staging Project for develop Branch**

```bash
# Go back to project root
cd D:\sanmitra_unified-Next

# Link staging project to develop branch
vercel link --project mitrabooks-erp-staging

# When prompted:
# - Which scope should contain your new project?: [Same as above]
# - Link to existing project?: YES
# - Which existing project?: mitrabooks-erp-staging
```

### **Step 4: Create vercel.staging.json Configuration**

Create a separate config file for staging (to keep it isolated):

```bash
cd D:\sanmitra_unified-Next\frontend

# Copy production config to staging config
copy vercel.json vercel.staging.json
```

Edit `vercel.staging.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "create-react-app",
  "installCommand": "npm install",
  "buildCommand": "npm run build",
  "outputDirectory": "build",
  "redirects": [
    {
      "source": "/",
      "destination": "/mitrabooks-erp/",
      "permanent": false
    }
  ],
  "rewrites": [
    {
      "source": "/mitrabooks-erp/:path((?!.*\\.).*)",
      "destination": "/mitrabooks-erp/index.html"
    },
    {
      "source": "/:path*",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/index.html",
      "headers": [
        { "key": "Cache-Control", "value": "no-cache, no-store, must-revalidate" }
      ]
    },
    {
      "source": "/service-worker.js",
      "headers": [
        { "key": "Cache-Control", "value": "no-cache, no-store, must-revalidate" }
      ]
    },
    {
      "source": "/:path*",
      "headers": [
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Strict-Transport-Security", "value": "max-age=31536000; includeSubDomains" }
      ]
    }
  ]
}
```

### **Step 5: Set Environment Variables for Staging**

```bash
# Set staging API endpoint
vercel env add REACT_APP_API_BASE_URL --project mitrabooks-erp-staging

# When prompted for value:
# https://sanmitra-unified-next-staging-sg.onrender.com

# Verify environment variables
vercel env list --project mitrabooks-erp-staging
```

### **Step 6: Connect develop Branch to Staging Project**

```bash
# Push develop branch to trigger automatic deployment
git checkout develop
git push origin develop

# Verify deployment started
vercel deployments list --project mitrabooks-erp-staging --token YOUR_VERCEL_TOKEN

# Or check in Vercel Dashboard:
# https://vercel.com/dashboard → mitrabooks-erp-staging → Deployments
```

### **Step 7: Add Custom Domain to Staging**

**Option A: Via Vercel CLI**

```bash
# Add custom domain to staging project
vercel domains add staging.mitrabooks.sanmitratech.in --project mitrabooks-erp-staging

# When prompted, Vercel will give you DNS records to add
# Save this output!
```

**Option B: Via Vercel Dashboard (easier)**

```
1. Go to: https://vercel.com/dashboard
2. Select project: mitrabooks-erp-staging
3. Settings → Domains
4. Add Domain: staging.mitrabooks.sanmitratech.in
5. Copy the CNAME value Vercel shows
```

### **Step 8: Update DNS Records at sanmitratech.in**

At your DNS provider (where you manage sanmitratech.in):

```
Add CNAME Record:
Name:   staging.mitrabooks
Value:  cname.vercel-dns.com  (or the exact CNAME from Vercel)
TTL:    3600 (1 hour)
```

**Example (if using cPanel/Route53/Cloudflare):**
```
Type:   CNAME
Host:   staging.mitrabooks.sanmitratech.in
Value:  cname.vercel-dns.com
TTL:    3600
```

Wait 5-10 minutes for DNS propagation.

### **Step 9: Verify Staging Deployment**

```bash
# Check if domain is working
ping staging.mitrabooks.sanmitratech.in

# Should resolve to Vercel IP

# Test in browser
# https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/

# Should show MitraBooks ERP dashboard
```

### **Step 10: Configure GitHub Auto-Deployment**

```bash
# This should be automatic if linked correctly, but verify:

# Go to Vercel Dashboard → mitrabooks-erp-staging → Git
# Should show:
# - Repository: sanmitra_unified-Next
# - Branch: develop
# - Auto-deploy on push: ✅ Enabled
```

---

## ✅ Verification Checklist

Run these tests to confirm everything works:

```bash
# 1. Test staging URL
curl -I https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/
# Should return: 200 OK

# 2. Verify API endpoint
curl -I https://sanmitra-unified-next-staging-sg.onrender.com/api/v1/health
# Should return: 200 OK

# 3. Check environment variables
vercel env list --project mitrabooks-erp-staging
# Should show: REACT_APP_API_BASE_URL = https://sanmitra-unified-next-staging-sg.onrender.com

# 4. Verify production is unchanged
curl -I https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/
# Should return: 200 OK (production still working)

# 5. Check no GruhaMitra/MandirMitra changes
curl -I https://www.gruhamitra.sanmitratech.in/
curl -I https://www.mandirmitra.sanmitratech.in/
# Both should still return: 200 OK
```

---

## 🔄 Workflow After Setup

### **Day-to-Day Development:**

```
1. Create feature branch: git checkout -b feature/xyz
2. Make changes to MitraBooks ERP frontend
3. Push to GitHub: git push origin feature/xyz
4. Create PR to develop branch
5. GitHub shows preview deployment (Vercel bot)
6. Test on preview: https://pr-123-xyz.vercel.app/mitrabooks-erp/
7. Code review + merge to develop
8. Auto-deploys to: https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/
9. Run E2E tests on staging
10. When ready, create PR from develop → main
11. Merge to main
12. Auto-deploys to production: https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/
```

### **Promoting Staging to Production:**

```bash
# 1. Ensure all tests pass on staging
# https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/

# 2. Create PR from develop → main
git checkout main
git pull origin main
git merge develop
git push origin main

# 3. Vercel auto-deploys to production
# Monitor: https://vercel.com/dashboard → mitrabooks-erp → Deployments

# 4. Verify production
# https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/
```

---

## 🚨 Important: GruhaMitra & MandirMitra NOT Affected

```
✅ Changes to mitrabooks-erp-staging only affect MitraBooks ERP
✅ GruhaMitra project remains completely separate
✅ MandirMitra project remains completely separate
✅ Production (main branch) remains unchanged until you merge

Production Isolation:
mitrabooks-erp (main)      → Production
mitrabooks-erp-staging     → Staging (develops branch)
gruhamitra (main)          → GruhaMitra (unchanged)
mandirmitra (main)         → MandirMitra (unchanged)
```

---

## 🔧 Troubleshooting

### **Issue: "Command not found: vercel"**
```bash
# Install Vercel CLI globally
npm install -g vercel

# Verify installation
vercel --version
```

### **Issue: Domain not resolving**
```bash
# Wait 10-15 minutes for DNS propagation
# Check DNS status:
nslookup staging.mitrabooks.sanmitratech.in

# If still not working:
# 1. Verify CNAME record in DNS provider
# 2. Check Vercel shows domain as verified (green checkmark)
# 3. Clear DNS cache: ipconfig /flushdns (Windows)
```

### **Issue: Staging points to wrong API**
```bash
# Verify environment variable:
vercel env list --project mitrabooks-erp-staging

# Should show correct staging URL
# If wrong, update:
vercel env remove REACT_APP_API_BASE_URL --project mitrabooks-erp-staging
vercel env add REACT_APP_API_BASE_URL --project mitrabooks-erp-staging
# Enter correct URL when prompted
```

### **Issue: Changes not showing on staging**
```bash
# Trigger manual redeploy:
vercel redeploy --project mitrabooks-erp-staging

# Or just push to develop:
git push origin develop
```

---

## 📊 Final Architecture

```
GitHub Repository (sanmitra_unified-Next)
├── main branch
│   ├── frontend/mitrabooks-erp
│   │   └── → Vercel Project: mitrabooks-erp
│   │       └── → Production: www.mitrabooks.sanmitratech.in
│   │
│   └── frontend/gruhamitra (unchanged)
│       └── → GruhaMitra (unchanged)
│
└── develop branch
    ├── frontend/mitrabooks-erp
    │   └── → Vercel Project: mitrabooks-erp-staging
    │       └── → Staging: staging.mitrabooks.sanmitratech.in
    │
    └── frontend/gruhamitra (unchanged)
        └── → GruhaMitra (unchanged)
```

---

## 🎯 What You'll Have

| Item | Value |
|------|-------|
| **Staging URL** | https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/ |
| **Staging Project** | mitrabooks-erp-staging (on Vercel) |
| **Staging Branch** | develop |
| **Production URL** | https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/ (unchanged) |
| **Production Project** | mitrabooks-erp (existing, unchanged) |
| **Production Branch** | main |
| **GruhaMitra** | Completely unaffected ✅ |
| **MandirMitra** | Completely unaffected ✅ |

---

## 🚀 Ready to Deploy?

Run these commands in order:

```bash
# 1. Create staging project
cd D:\sanmitra_unified-Next\frontend
vercel --prod --name mitrabooks-erp-staging

# 2. Link to develop branch
cd D:\sanmitra_unified-Next
vercel link --project mitrabooks-erp-staging

# 3. Set environment variable
vercel env add REACT_APP_API_BASE_URL --project mitrabooks-erp-staging
# Value: https://sanmitra-unified-next-staging-sg.onrender.com

# 4. Push develop to trigger deployment
git push origin develop

# 5. Add custom domain in Vercel Dashboard (takes 5 min)
# https://vercel.com/dashboard → mitrabooks-erp-staging → Settings → Domains

# 6. Add CNAME to DNS at sanmitratech.in (takes 5-10 min)
```

---

**Need help with any step? Let me know! 🚀**
