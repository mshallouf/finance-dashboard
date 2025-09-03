# FinanceTool – Master Sprint Retrospective

---

## 📌 Overview
This document summarizes all sprints completed so far for FinanceTool, including **features delivered, bugs/issues identified, and fixes applied**.  
It serves as a historical record of progress and lessons learned.

---

## 🚀 Sprint 1 – CSV Import & Core Transactions
### Features Delivered
- Import `transactions.csv` manually.
- Parse CSV → date, vendor, amount, category.
- Manual category assignment.
- Automatic sum of categories.
- Basic transactions table.

### Bugs & Issues
- Categories case-sensitive (`FOOD` vs `food`).
- Invalid entries (e.g., text in amount field) caused crashes.
- Transactions not sorted.

### Fixes
- Standardized category casing.
- Input validation with error popups.
- Auto-sorting transactions by date.

---

## 🚀 Sprint 2 – Budgets & Accounts
### Features Delivered
- **Budgets Tab**: Add budgets per category.
- Budgets persisted via `budgets.json`.
- Categories synced dynamically across transactions & budgets.
- **Accounts Tab**: Manual account balance entry.
- **Dashboard Tab**: Shows budgets, balances, spend summaries.

### Bugs & Issues
- Budgets disappeared when categories had no transactions.
- Spent amounts were stored as negatives, causing budget math issues.

### Fixes
- Separated category lifecycle from transaction presence.
- Budget progress bar shows overspending correctly (100%+).
- Normalized spent values for consistency.

---

## 🚀 Sprint 3 – Filters & Time Ranges
### Features Delivered
- Independent filters for Transactions and Dashboard.
- Supported ranges: This Month, Last Month, YTD, Custom.
- Dashboard charts & category sums respect filters.
- Added “Today Override” in Settings.

### Bugs & Issues
- Dashboard filter state accidentally applied to Transactions.
- Ambiguity in monthly budget equivalence.

### Fixes
- Made Dashboard and Transaction filters independent.
- Clarified UI: “Monthly equivalents shown”.

---

## 🚀 Sprint 4 – Categories Management & Reports
### Features Delivered
- **Categories Tab**: Manage add/edit/remove categories.
- Transactions can create new categories on the fly.
- Reports Tab: Spend analysis with charts.
- Dark theme charts with legends (to fix overlapping labels).
- Dashboard upgraded: MTD spend by category (list + chart).

### Bugs & Issues
- New categories didn’t always propagate to Budgets Tab.
- Charts unreadable in dark mode.

### Fixes
- Synced categories across all tabs.
- Switched to doughnut charts with legends.

---

## 🚀 Sprint 5 – Dashboard Polish & Data Interactions
### Features Delivered
- Dashboard-first tab order.
- Budget progress bars allow overspending (100%+).
- Doughnut chart on Dashboard with total spend in center.
- Transactions can dynamically add new categories.
- Improved Reports tab charts with dark theme.

### Bugs & Issues
- Editing/deleting transactions sometimes failed (“Original row not found”).

### Fixes
- Rewrote row-edit tracking logic to always reference DataFrame index.

---

## 🚀 Sprint 6 – Accounts Reconciliation & Budget Clarity
### Features Delivered
- “Apply new transactions to balances” button on Accounts tab.
- Tracked applied transactions with `applied_to_balance` flag.
- Undo/reset balances: “Recalculate from zero”.
- Budgets Tab: Show period (Daily/Weekly/Monthly) + Monthly equivalent.
- Dashboard: Subtitle clarifying “Monthly equivalents shown”.
- Dashboard quick filters (This Month / Last Month / YTD / Custom).

### Bugs & Issues
- Pop-up missing confirmation after account rebalance.
- Clicking rebalance repeatedly had no feedback.

### Fixes
- Added confirmation popups:
  - ✅ “Balances updated”  
  - ⚠ “All transactions already applied”.

---

## 🚀 Sprint 7 – Data Import Wizard
### Features Delivered
- **Import Wizard** for external files:
  - Supports `.csv` and `.xls`.
  - Interactive mapping of source columns → (Date, Amount, Account, Vendor, Category).
- Commit imported transactions into app’s persistent storage.
- Data immediately reflected in Transactions tab.

### Bugs & Issues
- After commit, error: `refresh_all missing`.
- Duplicate imports if “Commit” pressed multiple times.
- Imported transactions couldn’t be edited/deleted initially.

### Fixes
- Added shim: `refresh_all()` → reloads tables/tabs.
- Added input guard to prevent double/triple imports.
- Fixed editing by saving imported rows into `transactions.csv` instead of holding them in memory only.

---

## 🚀 Sprint 8 – Testing Tools & Clear All
### Features Delivered
- “Clear All” buttons on:
  - Transactions  
  - Budgets  
  - Accounts  
  - Categories  
- Allows quick reset for testing and fresh starts.
- Added to persistence layer (resets CSV/JSON files to empty).

### Bugs & Issues
- Indentation error in refresh hook stub.
- Needed `.gitignore` to protect local data.

### Fixes
- Corrected indentation.
- Added `.gitignore` to exclude local data and `venv`.

---

## 📊 Lessons Learned
1. **Persistence Layer Matters**  
   Early reliance on in-memory edits caused confusion — CSV/JSON integration fixed long-term issues.  
2. **UI/UX Iteration**  
   Small usability changes (dark theme, legends, progress bar >100%) made huge differences.  
3. **Scrum Adaptation**  
   We stayed agile by reprioritizing (e.g., deferring some features like auto-categorization).  
4. **Testing Tools Help**  
   Adding “Clear All” boosted confidence in testing imports and resets.  

---

## ✅ Current State (Post Sprint 8)
- MVP features completed:
  - Transactions (manual + import)
  - Budgets
  - Accounts
  - Categories
  - Dashboard
  - Reports
  - Settings
- Data flows properly between tabs.
- App stable, with version history tracked in Git.

---

## 🔮 Next Steps
- Improve Import Wizard with duplicate detection.
- Auto-categorization by vendor history.
- Multi-period budgets (weekly roll-ups into months).
- SQLite backend for scalability.
- AI-powered financial insights.

---
