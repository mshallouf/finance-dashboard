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

## 🌀 Sprint 9 – Import Wizard Inline Account Setup

### 🎯 Goal
Allow users to create new accounts during import (especially credit cards) and initialize balances correctly, even if the imported file spans only part of the history. Ensure overlapping imports don’t double-count.

### ✅ Delivered
- Added **Account Type** (Asset / Credit Card) in Import Wizard.
- Added **Account Initialization** group with:
  - “Initialize from this import” checkbox.
  - Computed net label (from valid, non-duplicate rows).
  - Override balance input for statement closing balance.
- On commit:
  - Account’s `starting_balance` and `balance` set from either computed net or override.
  - Rows used for initialization marked `AppliedToBalance=True`.
- Persisted account `type` in `accounts.json`.
- Persisted `ExternalId` from import into transactions for reliable dedupe.
- Updated duplicate detection to use consistent `dup_key` logic (date | vendor | amount | account | externalId).
- Preview shows computed net and updates live with flip signs, account selection, and amount mode.

### 🐛 Bugs / Fixes
- **NaN crash in `dup_key`:** fixed by converting `ExternalId` to string before `.strip()`.
- Minor adjustments to ensure overlapping imports (months 1–5, then 3–8) flag duplicates and skip them correctly.

### 📊 Outcome
- Credit card accounts can now be created seamlessly at import time.
- Balances reflect either the imported data net or the true statement balance.
- Duplicate protection hardened.
- Dashboard “Total Balance” now accurately accounts for negative CC balances.

---

## 🌀 Sprint 10 – Transfers (Manual Linking MVP)

### 🎯 Goal
Eliminate double-counting of credit card payments by allowing users to mark transactions as Transfers. Transfers should affect account balances but not budgets or spending reports.

### ✅ Delivered
- Added **Transfer transaction type**.
- Transactions tab:
  - Enabled multi-select in table (ExtendedSelection).
  - Added **“Mark Transfer”** button.
  - Added context-menu action **“Mark as Transfer (select two rows)”**.
- New method `_mark_selected_as_transfer`:
  - Validates exactly two rows selected.
  - Ensures opposite sign amounts and different accounts.
  - Optionally checks dates (warns if >10 days apart).
  - Assigns a shared `TransferGroup` ID (UUID).
  - Updates both rows’ `Type=Transfer`, `Category=Transfer`, `TransferGroup=<id>`.
- Excluded `Type=Transfer` from category totals in `update_summary`.
- Transfers now:
  - Reduce chequing balance.
  - Reduce credit card balance.
  - Do not appear in category spending or budgets.

### 🐛 Bugs / Fixes
- Needed schema extensions:
  - Added `ExternalId` (from Sprint 9) and new `TransferGroup` columns to transactions CSV.
- Adjusted save/load/reset paths to persist these fields.

### 📊 Outcome
- Bank → CC payment flows can now be reclassified as Transfers.
- Net worth and balances stay correct.
- Spending reports only reflect underlying charges, not payments.
- User workflow: import CC + bank → select the matching debit/credit rows → mark as transfer.

---

## 🌀 Sprint 11 – Monarch-Style UI & Transactions Cleanup

### 🎯 Goal
Move the app’s UI closer to a Monarch-like design by introducing a sidebar-style navigation, card-style dashboard layout, and simplifying the Transactions tab.

### ✅ Delivered
- Added a **sidebar navigation** (tabs on the left) for a cleaner layout.
- Applied stylesheet changes for a more modern, Monarch-like look.
- Transactions Tab:
  - Removed inline “new category” adder (categories now managed in Categories tab).
  - Improved table styling (alternating row colors, right-aligned amounts).
- Added Settings toggle to hide/show advanced columns (AppliedToBalance, ExternalId, TransferGroup).
- Dashboard and reports visually cleaned up (cards, groupboxes with consistent styling).

### 🐛 Bugs / Fixes
- Needed to restore visibility of tabs after sidebar refactor (real tab bar was hidden too early).
- Added missing imports (`QAbstractItemView`, `QCheckBox`, `QListWidget`, `QListWidgetItem`).
- Fixed layout issue where `_center_container` replaced the main tabs incorrectly.
- Hid the bottom “Total by Category” summary in Transactions.

### 📊 Outcome
- The app now has a **modern navigation sidebar** and **cleaner transactions UI**.
- Advanced transaction fields are hidden by default (accessible via Settings).
- Visual direction is aligned with Monarch-style dashboards, preparing for richer cards/charts.

---

## 🌀 Sprint 12 – Auto-Categorize Transactions (with Backfill)

### 🎯 Goal
Automatically categorize transactions based on how the user has categorized similar vendors in the past, and backfill uncategorized history when new manual categorizations are made.

### ✅ Delivered
- Introduced **vendor → category memory map**, persisted in `autocategorize.json`.
- Added **auto-categorization engine**:
  - Normalization of vendor names (lowercase, punctuation stripped).
  - Matching rules: exact match, stem (first 2 words), contains/prefix, token overlap, fuzzy similarity (≥ 0.65).
- Applied auto-categorization:
  - On import (uncategorized rows get auto categories).
  - On manual edit (backfill of past uncategorized rows).
- Added **provenance flag** `CategorySource` (Manual vs Auto) to transactions.
  - Auto-categorized rows appear italicized with tooltip (“Auto-categorized”).
  - Hidden by default, visible via advanced columns toggle in Settings.
- Added **Settings toggle**: Enable/Disable auto-categorization.
- Added **“Auto-Categorize Now”** button in Transactions tab to trigger manual backfill/testing.

### 🐛 Bugs / Fixes
- Fixed crashes where `_normalize_vendor` helpers were not defined before use.
- Hardened uncategorized detection (empty, blank, None all treated as uncategorized).
- Corrected save/load schema to include `CategorySource`.
- Adjusted fuzzy threshold to 0.65 to catch common brand variations.

### 📊 Outcome
- Users no longer need to re-categorize recurring vendors.
- Past uncategorized transactions are automatically updated when a similar new transaction is categorized.
- Auto categories are clearly marked and overrideable.
- Auto-categorization can be toggled off for manual users.

---

## 🌀 Sprint 13 – Quick Wins

### 🎯 Goal
Deliver small but high-impact improvements for usability, seeding, and setup consistency.

### ✅ Delivered
- Added **seed categories** via `seeds/categories_seed.json` on first run.
  - Includes Fast Food vs. Restaurants split for more granular budgeting.
- Added **seed autocategorization map** for common Ontario/SW Ontario vendors via `seeds/autocategorize_seed_on_ca.json`.
- Budgets tab now **only shows categories with active budgets (> 0)**, reducing clutter.
- Generated and committed a **requirements.txt** file to support easy dependency installation.
- Created an initial **USER_GUIDE.md** with installation, setup, and usage instructions.

### 🐛 Bugs / Fixes
- Fixed missing `"type"` field on seeded categories by normalizing after merge.
- Corrected seeding logic so categories and vendor mappings only augment (idempotent) rather than overwrite user data.

### 📊 Outcome
- Users start with a rich set of categories and vendor mappings, reducing setup burden.
- Budgets are cleaner and only reflect active items.
- Installation is now reproducible with `pip install -r requirements.txt`.
- User guide improves onboarding and documentation consistency.

---

## 🌀 Sprint 14 – Import Wizard Simplification

### 🎯 Goal
Streamline the Import Wizard so that a typical user can import transactions from their bank in **3 easy steps**:
1. Upload CSV/XLS.
2. Map only the essential fields (Date, Vendor, Amount, Account).
3. Preview and Commit.

Advanced options are hidden by default but remain available for power users.

### ✅ Delivered
- **Step 2 (Mapping) redesigned**:
  - Shows only required fields: Date, Vendor, Amount (or Debit/Credit), Account.
  - Added green ✓ indicators when required fields are filled or auto-mapped.
  - Integrated **Debit/Credit toggle**:
    - Single Amount mode shows only the Amount field.
    - Debit/Credit mode shows only Debit and Credit fields.
  - Added collapsible **Advanced group** (collapsed by default) containing:
    - Memo, ExternalId, Balance, Type fields.
    - Cleaning options (strip currency symbols, parentheses negative, thousands separator, invert signs).
    - Account initialization (computed net + override).
    - Save profile controls.
- **Navigation buttons updated**:
  - Step 2 → “Next → Preview”.
  - Step 3 → “Commit”.
- **Main App**:
  - Added a dedicated **“Import Transactions…” button** on the Transactions tab, alongside Add/Edit/Delete.
  - Button reuses the existing `open_import_wizard()` function (mirrors File ▸ Import menu).

### 🐛 Bugs / Fixes
- Fixed UI confusion around Debit/Credit vs Single Amount mode:
  - Fields and their labels are now hidden when not in use, instead of just disabled.
- Ensured Advanced fields remain functional but hidden until expanded.

### 📊 Outcome
- Typical CSV import can now be completed in **3 clicks** without touching Advanced.
- Import Wizard feels lighter and less intimidating for first-time users.
- Advanced features (profiles, cleaning, initialization, duplicate detection) remain intact.
- Dedicated Import button reduces friction by making the feature easier to discover.

---