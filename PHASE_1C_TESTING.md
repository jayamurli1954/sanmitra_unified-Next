# Phase 1C Testing Guide
## Manual Verification Checklist

**Server Status:** ✅ Running on http://localhost:8000  
**App Location:** http://localhost:8000/mitrabooks-erp/  

---

## 📋 Pre-Testing Verification

### ✅ File Loading Tests (PASSED)
```
✓ theme-tokens.css: 200 OK
✓ app-shell.css: 200 OK
✓ mitrabooks/index.css: 200 OK
✓ service-worker.js: 200 OK
✓ sw-register.js: 200 OK
✓ index.html: 200 OK
```

### ✅ Code Verification (PASSED)
```
✓ setTheme() function: Found
✓ getTheme() function: Found
✓ initializeTheme(): Found (2 occurrences)
✓ Service worker registration: Found
```

---

## 🧪 Manual Testing Steps

### **Test 1: App Loads & Default Theme**
1. Open http://localhost:8000/mitrabooks-erp/ in Chrome/Firefox
2. **Expected:** Dark theme appears by default
3. **Check:** 
   - Sidebar has dark background
   - Text is light colored
   - No console errors (check DevTools)

### **Test 2: Theme Toggle (NOT YET IMPLEMENTED)**
⏳ **Pending Step 6** - Theme buttons will be added to sidebar footer
- For now: You can manually test theme change via DevTools Console
  ```javascript
  // In DevTools Console:
  setTheme('light')  // Switch to light mode
  setTheme('dark')   // Switch back to dark
  ```

### **Test 3: Theme Persistence**
1. Open http://localhost:8000/mitrabooks-erp/
2. In DevTools Console, run: `setTheme('light')`
3. Reload the page (F5 or Ctrl+R)
4. **Expected:** Light theme should still be active
5. **Verify:** localStorage saved the preference
   - In DevTools → Application → Local Storage
   - Look for key: `mitrabooks-theme`
   - Value should be: `light`

### **Test 4: System Preference Detection**
1. Test in different scenarios:
   - **Dark Mode System:** Should default to dark theme
   - **Light Mode System:** Should default to light theme
   - **First Visit:** Should respect OS preference

2. How to test on Windows:
   - Windows → Settings → Personalization → Colors
   - Toggle between Dark/Light theme
   - Reload the page

### **Test 5: Service Worker Registration**
1. Open http://localhost:8000/mitrabooks-erp/
2. Open DevTools (F12)
3. Go to: **Application → Service Workers**
4. **Expected:** Service worker should show as "registered"
5. **URL:** Should be `/service-worker.js`
6. **Status:** Should show "activated and running" (green dot)

### **Test 6: Service Worker Caching**
1. With DevTools open, go to **Application → Cache Storage**
2. **Expected:** Cache named `mitrabooks-erp-v1` should exist
3. Inside the cache, you should see:
   - `http://localhost:8000/mitrabooks-erp/`
   - `http://localhost:8000/shared/theme-tokens.css`
   - `http://localhost:8000/shared/app-shell.css`
   - `http://localhost:8000/mitrabooks-erp/index.css`
   - `http://localhost:8000/mitrabooks-erp/manifest.webmanifest`

### **Test 7: Offline Mode (Simulated)**
1. Open http://localhost:8000/mitrabooks-erp/
2. Open DevTools (F12)
3. Go to: **Network tab**
4. Check: **"Offline" checkbox** at the top right
5. Try to reload the page (F5)
6. **Expected:** 
   - Page should still load (from cache)
   - Service worker should show "activated and running"
   - Fallback message for missing APIs (if visible)

### **Test 8: CSS Variables Working**
1. Open DevTools (F12)
2. Go to: **Elements/Inspector tab**
3. Select: `<html>` element
4. In Styles panel, look for CSS variables:
   - Should see `--bg-primary`, `--text-primary`, etc.
   - Values should match theme (light or dark)
5. In dark mode:
   - `--bg-primary` should be dark (#090c14 or similar)
   - `--text-primary` should be light (#f8fafc or similar)
6. In light mode:
   - `--bg-primary` should be light (#f8fafc or similar)
   - `--text-primary` should be dark (#0f172a or similar)

### **Test 9: No Broken Features**
Verify existing functionality still works:
- [ ] Sidebar navigation loads
- [ ] Module switching works (MitraBooks, Platform, MandirMitra, GruhaMitra)
- [ ] Login form displays correctly
- [ ] API configuration options visible
- [ ] Cards and panels render properly
- [ ] No JavaScript errors in console

### **Test 10: Responsive Design**
1. Test on different screen sizes using DevTools Device Emulation
2. Sizes to test:
   - Desktop (1920x1080)
   - Tablet (768x1024)
   - Mobile (375x667)
3. **Expected:** Layout adapts, text is readable, no overflow

---

## 🔍 Console Checks

### What You Should See
```
✓ [App] Service Worker registered
✓ [SW] Installing service worker...
✓ [SW] Caching critical assets
✓ [SW] Activating service worker...
✓ [App] Service Worker controller changed
```

### What You Should NOT See
```
❌ Uncaught SyntaxError
❌ Failed to register ServiceWorker
❌ CORS error
❌ 404 errors for CSS files
❌ Refused to execute inline script
```

---

## 📊 Expected Results Summary

| Test | Expected Result | Status |
|------|-----------------|--------|
| 1. Default Theme | Dark theme loads | ⏳ TBD |
| 2. Theme Toggle | Switch between dark/light | ⏳ TBD |
| 3. Persistence | Theme saved in localStorage | ⏳ TBD |
| 4. OS Preference | Respects system setting | ⏳ TBD |
| 5. SW Registration | Shows in DevTools | ⏳ TBD |
| 6. SW Caching | Cache storage visible | ⏳ TBD |
| 7. Offline Mode | Page loads without network | ⏳ TBD |
| 8. CSS Variables | Theme colors applied | ⏳ TBD |
| 9. No Broken Features | All existing features work | ⏳ TBD |
| 10. Responsive | Adapts to screen size | ⏳ TBD |

---

## 🚨 Troubleshooting

### Issue: Service Worker Not Registering
**Cause:** Path is incorrect or script failed to load
**Solution:**
1. Check DevTools → Network tab
2. Verify `sw-register.js` loads (200 status)
3. Check Console for errors

### Issue: CSS Colors Not Changing
**Cause:** theme-tokens.css not loaded or CSS variables not applied
**Solution:**
1. Check DevTools → Network tab
2. Verify `theme-tokens.css` loads
3. In Inspector, check `<html>` element has `data-theme="dark"`

### Issue: Theme Not Persisting
**Cause:** localStorage not available or key not set correctly
**Solution:**
1. Check DevTools → Application → Local Storage
2. Look for key: `mitrabooks-theme`
3. Verify browser allows localStorage

### Issue: Offline Mode Fails
**Cause:** Service worker didn't cache files or scope is wrong
**Solution:**
1. Clear all caches (DevTools → Application → Clear Site Data)
2. Refresh page to trigger cache again
3. Try offline mode

---

## ✅ Sign-Off Checklist

Once testing is complete, check:

- [ ] Dark theme loads by default ✅
- [ ] All CSS files load (200 status) ✅
- [ ] No 404 errors in Network tab
- [ ] No JavaScript errors in Console
- [ ] Service Worker appears in DevTools
- [ ] Cache storage shows mitrabooks-erp-v1
- [ ] Theme persists across page reloads
- [ ] Offline mode works
- [ ] All existing features still work
- [ ] No breaking changes

---

## 📝 Testing Notes

### What to Document
If you find any issues:
1. Take a screenshot of the issue
2. Note the exact steps to reproduce
3. Check the browser console error
4. Note your browser version

### When to Proceed to Step 6
✅ **All tests pass** → Proceed immediately to Step 6 (Sidebar JS)

⚠️ **Some tests fail** → Debug and fix before proceeding

---

## 🎯 Next After Testing

Once verified:
1. ✅ All components working
2. ✅ No breaking changes
3. ✅ Service worker active

**Then:** Proceed to **Step 6: Sidebar UI JavaScript Wiring**
- Add theme toggle buttons
- Wire org selector dropdown
- Wire FY selector dropdown

---

**Server:** http://localhost:8000/mitrabooks-erp/  
**Testing Guide:** This file  
**Status:** Ready for manual testing  

Good luck! 🚀
