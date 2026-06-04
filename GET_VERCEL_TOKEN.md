# How to Get Your Vercel Token

---

## 🎯 Step 1: Go to Vercel Account Settings

1. **Open:** https://vercel.com/account/tokens
2. Or manually navigate:
   - Go to: https://vercel.com/dashboard
   - Click your profile icon (top-right corner)
   - Click **Settings**
   - Click **Tokens** (left sidebar)

---

## 🔑 Step 2: Create a New Token

1. **Click:** "Create Token" button
2. **Token Name:** Give it a descriptive name
   - Example: `mitrabooks-staging-setup`
3. **Token Expiration:** Choose expiration (optional)
   - Recommended: 90 days (for security)
   - Or: No expiration (for permanent token)
4. **Scope:** Select scope
   - Keep default: **Full Account**
5. **Click:** "Create Token"

---

## 📋 Step 3: Copy Your Token

```
You'll see a screen with:
┌─────────────────────────────────────┐
│ Your new token:                     │
│ [xxxxxxxxxxxxxxxxxxxxxxxxxxxxx]      │
│                  [Copy Button]      │
└─────────────────────────────────────┘
```

**⚠️ IMPORTANT:** 
- Copy it NOW - it won't be shown again!
- Keep it safe (don't share publicly)
- You can regenerate it anytime if you lose it

---

## 💻 Step 4: Use Token in Command Line

**Option A: Set as Environment Variable (Recommended)**

### **Windows PowerShell:**

```powershell
# Set the environment variable for this session
$env:VERCEL_TOKEN = "your_token_here"

# Verify it's set
echo $env:VERCEL_TOKEN

# Now run Vercel commands
npx vercel --version
npx vercel projects
```

### **Windows CMD:**

```cmd
# Set the environment variable for this session
set VERCEL_TOKEN=your_token_here

# Verify it's set
echo %VERCEL_TOKEN%

# Now run Vercel commands
npx vercel --version
npx vercel projects
```

---

## 🔄 Step 5: Run Staging Setup with Token

Once you have the token set as environment variable:

```powershell
# Navigate to MitraBooks ERP frontend
cd D:\sanmitra_unified-Next\frontend\mitrabooks-erp

# Create staging project (uses VERCEL_TOKEN automatically)
npx vercel --prod --name mitrabooks-erp-staging

# If asked to login, you're already authenticated via token!
```

---

## ✅ Complete Staging Setup (With Token)

```powershell
# 1. Set token
$env:VERCEL_TOKEN = "your_actual_token_here"

# 2. Go to MitraBooks ERP
cd D:\sanmitra_unified-Next\frontend\mitrabooks-erp

# 3. Create staging project
npx vercel --prod --name mitrabooks-erp-staging

# When prompted, select options:
# - Scope: [Your account]
# - Project name: mitrabooks-erp-staging
# - Build: npm run build
# - Output: build

# 4. Set environment variable
npx vercel env add REACT_APP_API_BASE_URL --project mitrabooks-erp-staging
# Value: https://sanmitra-unified-next-staging-sg.onrender.com

# 5. Go to repo root and push develop
cd D:\sanmitra_unified-Next
git push origin develop

# 6. Add custom domain (via dashboard)
# https://vercel.com/dashboard → mitrabooks-erp-staging → Settings → Domains

# 7. Add DNS CNAME at sanmitratech.in

# 8. Wait 5-10 min and test
# https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/
```

---

## 🛡️ Security Best Practices

✅ **DO:**
- Keep token private
- Use environment variables (don't hardcode)
- Regenerate if accidentally exposed
- Use short expiration (90 days)
- Use for automation/CI/CD

❌ **DON'T:**
- Share token in chat/email
- Commit token to GitHub
- Use in public scripts
- Share with team members (create separate tokens)

---

## 🔁 If You Lose the Token

No problem! You can generate a new one:

1. Go to: https://vercel.com/account/tokens
2. Click "Create Token" again
3. Use the new token

---

## 📖 Visual Guide

```
Vercel Dashboard
├── Click Profile Icon (top-right)
├── Settings
│   ├── Account (general settings)
│   ├── Teams (team management)
│   ├── Tokens ← YOU ARE HERE
│   ├── Billing
│   ├── Email & Notifications
│   └── Security
│
└── Click "Create Token"
    ├── Name: mitrabooks-staging-setup
    ├── Expiration: 90 days (recommended)
    ├── Scope: Full Account
    └── Click "Create"
        └── Copy token immediately!
```

---

## ✨ You're All Set!

Now you have:
- ✅ Vercel account
- ✅ Vercel token
- ✅ Ready to run staging setup

**Next:** Run the staging setup commands with your token!

---

## 🆘 Troubleshooting

**Token not working?**
```powershell
# Check if token is set
echo $env:VERCEL_TOKEN

# If empty, set it again:
$env:VERCEL_TOKEN = "your_token_here"

# Try command again:
npx vercel projects
```

**Token expired?**
```
- Generate a new token (same steps)
- Update the environment variable
- Try again
```

**Still having issues?**
```powershell
# Try without token (will prompt login)
npx vercel login
# Follow browser prompt
```

---

**Have your token? Let me know and we'll complete the staging setup!** 🚀
