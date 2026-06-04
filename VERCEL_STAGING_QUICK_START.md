# Vercel Staging Setup - Quick Start Commands

**Run these commands on your local Windows machine (PowerShell or CMD)**

---

## 🚀 Step 1: Authenticate with Vercel

```powershell
# Open PowerShell and run:
npx vercel login

# Follow the prompts:
# 1. Choose "Continue with GitHub" (or your preferred auth method)
# 2. Browser opens for auth
# 3. Confirm access
# 4. You're authenticated!
```

---

## 📁 Step 2: Navigate to MitraBooks ERP Frontend

```powershell
cd D:\sanmitra_unified-Next\frontend\mitrabooks-erp
```

---

## 🎯 Step 3: Create Staging Project

```powershell
# Create new Vercel project for staging (MitraBooks ERP only)
npx vercel --prod --name mitrabooks-erp-staging

# When prompted:
# Set up and deploy? → YES (y)
# Which scope? → [Select your Vercel team/account]
# Link to existing project? → NO (n)
# Project name? → mitrabooks-erp-staging
# In which directory? → . (current directory)
# Want to modify vercel.json? → NO (n) - we'll use existing
# Build Command? → npm run build
# Output Directory? → build
# Development Command? → npm start

# ✅ Project created! Save the URLs shown
```

---

## 🔐 Step 4: Set Staging API Endpoint

```powershell
# Set environment variable for staging backend
npx vercel env add REACT_APP_API_BASE_URL --project mitrabooks-erp-staging

# When prompted for value:
# https://sanmitra-unified-next-staging-sg.onrender.com

# ✅ Environment variable set!
```

---

## 🌱 Step 5: Push develop Branch (Trigger Deployment)

```powershell
# Go back to repo root
cd D:\sanmitra_unified-Next

# Make sure develop branch exists
git branch -a

# If develop doesn't exist, create it:
# git checkout -b develop
# git push -u origin develop

# Otherwise, just push:
git push origin develop

# ✅ Auto-deployment started on Vercel!
```

---

## 🔗 Step 6: Add Custom Domain (Via Dashboard)

```
1. Open: https://vercel.com/dashboard
2. Select: mitrabooks-erp-staging
3. Go to: Settings → Domains
4. Click: Add Domain
5. Enter: staging.mitrabooks.sanmitratech.in
6. Copy the CNAME value Vercel shows
7. Keep this window open
```

---

## 📝 Step 7: Update DNS (At sanmitratech.in DNS Provider)

```
Add this CNAME record at your DNS provider:

Name/Host:  staging.mitrabooks.sanmitratech.in
Type:       CNAME
Value:      cname.vercel-dns.com (or the exact value from Step 6)
TTL:        3600

⏳ Wait 5-10 minutes for DNS propagation
```

---

## ✅ Step 8: Verify Setup

```powershell
# Check if staging is live (wait 2-3 minutes first)
$url = "https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/"
Invoke-WebRequest -Uri $url -UseBasicParsing

# Should return Status Code 200

# Test in browser:
# https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/
# Should show MitraBooks ERP dashboard
```

---

## 📊 What You'll Have After

| Item | Value |
|------|-------|
| **Staging URL** | https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/ |
| **Staging Project** | mitrabooks-erp-staging |
| **Auto-deploys from** | develop branch |
| **Production** | https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/ (unchanged) |
| **Production Project** | mitrabooks-erp (unchanged) |
| **GruhaMitra** | Unaffected ✅ |
| **MandirMitra** | Unaffected ✅ |

---

## 🔄 Daily Workflow After Setup

```powershell
# Feature development
git checkout -b feature/xyz
# ... make changes ...
git push origin feature/xyz
# → Auto-preview deployment

# When ready
git checkout develop
git merge feature/xyz
git push origin develop
# → Auto-deploy to staging.mitrabooks.sanmitratech.in

# After testing on staging
git checkout main
git merge develop
git push origin main
# → Auto-deploy to production
```

---

## 🆘 If Issues Arise

**Domain not resolving?**
```powershell
# Wait 10-15 minutes and test:
nslookup staging.mitrabooks.sanmitratech.in

# Or manually verify at: https://www.whatsmydns.net/
# Search: staging.mitrabooks.sanmitratech.in
```

**Deployment stuck?**
```powershell
# Trigger manual redeploy:
npx vercel redeploy --project mitrabooks-erp-staging
```

**Wrong API endpoint?**
```powershell
# Check current env var:
npx vercel env list --project mitrabooks-erp-staging

# Update if needed:
npx vercel env remove REACT_APP_API_BASE_URL --project mitrabooks-erp-staging
npx vercel env add REACT_APP_API_BASE_URL --project mitrabooks-erp-staging
# Re-enter: https://sanmitra-unified-next-staging-sg.onrender.com
```

---

## ✨ That's it!

You now have:
- ✅ Staging environment on Vercel
- ✅ Custom domain: staging.mitrabooks.sanmitratech.in
- ✅ Auto-deployment from develop branch
- ✅ Production unchanged
- ✅ GruhaMitra/MandirMitra unaffected

**Ready to test Phase 2 features!** 🚀
