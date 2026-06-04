# Phase 2C.2-2C.3: Dashboard Widgets Implementation Plan

**Status:** In Progress  
**Date:** 2026-06-04  
**Target:** Collapsible and Customizable Dashboard Widgets

---

## 📋 Overview

Transform the static MitraBooks dashboard into a dynamic, customizable workspace where users can:
- ✅ Collapse/expand individual widgets
- ✅ Hide/show widgets based on preferences
- ✅ Reorder widgets with drag-and-drop (Phase 2C.3)
- ✅ Persist all preferences to localStorage

---

## 🎯 Phase 2C.2: Collapsible Widgets

### Current Dashboard Structure
```
Executive Dashboard
├── Executive Hero (KPI Strip)
│   ├── Income
│   ├── Expenses
│   └── Net Position
├── Finance Chart Card (Sales & Expenses Trend)
└── CEO Panel (CEO Insights)
```

### Implementation Plan

#### Step 1: Widget Wrapper Structure
- Wrap each dashboard section in a collapsible widget container
- Add collapse/expand button to each widget header
- Implement smooth collapse/expand animation

**Files to modify:**
- `app.js` - Update `renderBusinessExecutiveDashboard()` to add widget wrappers
- `index.css` - Add collapse animation styles

#### Step 2: Collapse State Management
- Create widget state object: `{widgetId: {collapsed: true/false}}`
- Store in localStorage: `"mitrabooks-widget-states"`
- Load state on dashboard initialization
- Update state on user interaction

#### Step 3: User Interface
- Add collapse button (⌄/⌃ icon) to each widget header
- Add visual feedback when collapsing/expanding
- Smooth height animation (0-auto)

**Expected Outcome:**
- 3 main widgets, each independently collapsible
- User preferences persist across sessions
- Smooth animations for professional feel

---

## 🎨 Phase 2C.3: Customizable Layout

### Features to Implement

#### 1. Widget Visibility Control
- Toggle buttons to show/hide individual widgets
- Settings panel with visibility checkboxes
- Quick access via settings icon on dashboard

#### 2. Widget Reordering (Optional - Nice-to-Have)
- Drag-and-drop to reorder widgets
- CSS Grid dynamic reordering
- Save order to localStorage

#### 3. Customization Settings Panel
- Small settings UI on dashboard header
- Checkboxes for widget visibility
- "Reset to Defaults" button
- Save/Apply button

#### 4. Persistent Layout State
- localStorage schema:
```javascript
{
  "mitrabooks-dashboard-layout": {
    "widgets": {
      "kpi-strip": { visible: true, collapsed: false, order: 1 },
      "finance-chart": { visible: true, collapsed: false, order: 2 },
      "ceo-panel": { visible: true, collapsed: false, order: 3 }
    }
  }
}
```

---

## 🔧 Technical Implementation

### JavaScript Functions to Create

```javascript
// Widget state management
function getWidgetStates() { ... }
function setWidgetState(widgetId, state) { ... }
function saveWidgetStates() { ... }
function resetWidgetStates() { ... }

// Widget visibility management
function getVisibleWidgets() { ... }
function toggleWidgetVisibility(widgetId) { ... }

// Collapse/expand functionality
function toggleWidgetCollapse(widgetId) { ... }
function applyCollapsedState(widgetId, isCollapsed) { ... }

// Customization UI
function renderWidgetSettings() { ... }
function openCustomizationPanel() { ... }
function saveCustomizationPreferences() { ... }
```

### CSS Classes to Add

```css
/* Widget wrapper */
.dashboard-widget {
  position: relative;
  transition: all 0.3s ease;
}

/* Collapsed state */
.dashboard-widget.collapsed .widget-content {
  max-height: 0;
  overflow: hidden;
  opacity: 0;
  transition: max-height 0.3s ease, opacity 0.3s ease;
}

.dashboard-widget .widget-content {
  max-height: 999px;
  opacity: 1;
  transition: max-height 0.3s ease, opacity 0.3s ease;
}

/* Collapse button */
.widget-header-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.widget-collapse-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 18px;
  padding: 4px 8px;
  transition: color 0.2s ease;
}

.widget-collapse-btn:hover {
  color: var(--text-primary);
}

/* Hidden widget */
.dashboard-widget.hidden {
  display: none;
}

/* Customization panel */
.dashboard-customization-panel {
  position: fixed;
  top: 80px;
  right: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  min-width: 280px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  z-index: 1000;
}
```

---

## 📊 Widget Details

### Widget 1: Executive KPI Strip
- **ID:** `kpi-strip`
- **Content:** Income, Expenses, Net Position cards
- **Default:** Visible, Expanded
- **Size:** Full width

### Widget 2: Finance Chart
- **ID:** `finance-chart`
- **Content:** Sales & Expenses Trend bar chart
- **Default:** Visible, Expanded
- **Size:** 60% width (left)

### Widget 3: CEO Insights
- **ID:** `ceo-panel`
- **Content:** AI insights, cash coverage, receivables data
- **Default:** Visible, Expanded
- **Size:** 40% width (right)

---

## ✅ Testing Checklist

### Phase 2C.2: Collapse Functionality
- [ ] Click collapse button on each widget
- [ ] Widget content smoothly collapses to header only
- [ ] Click expand button to restore widget
- [ ] Refresh page - collapse state is preserved
- [ ] Icons rotate/change on collapse/expand

### Phase 2C.3: Customization
- [ ] Open settings panel
- [ ] Toggle widget visibility
- [ ] Verify widget hides/shows immediately
- [ ] Refresh page - visibility state preserved
- [ ] Click "Reset to Defaults" - all widgets visible, expanded
- [ ] Drag and drop widget (if implemented)
- [ ] Close customization panel without saving - changes persist

### Mobile Responsiveness
- [ ] All features work on small screens
- [ ] Settings panel accessible on mobile
- [ ] Collapse/expand works with touch

---

## 📈 Expected Metrics (Phase 2)

- **Lines of Code:** 400-500 (CSS + JS)
- **Functions Added:** 8-10
- **localStorage Keys:** 1 (widget-states)
- **User Interactions:** Collapse, Visibility Toggle, Reset
- **Browser Support:** All modern browsers (localStorage support)

---

## 🚀 Staging Deployment

Once implemented:
1. Commit to develop branch: `git push origin develop`
2. Auto-deploys to: `https://staging.mitrabooks.sanmitratech.in/`
3. Test: Login → Dashboard → Try widget controls
4. Verify localStorage persistence across refreshes

---

## 📝 Next Steps

1. ✅ Implement collapsible widget structure (Phase 2C.2)
2. ✅ Add collapse/expand animations (Phase 2C.2)
3. ✅ Create customization UI panel (Phase 2C.3)
4. ✅ Implement widget visibility toggles (Phase 2C.3)
5. ✅ Add localStorage persistence (Both phases)
6. ✅ Test all features
7. ✅ Commit and push to develop

---

**Timeline:** ~2 hours for full implementation + testing  
**Complexity:** Medium (state management + DOM manipulation)  
**Risk Level:** Low (isolated to dashboard, no API changes)

