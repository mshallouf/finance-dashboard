# FinanceTool — Project Snapshot (Pivot Checkpoint)

**Date:** 2025-08-25 
**Version/Tag:** v0.3.0 (Stable baseline before Sprint 3 pivot)

---

## ✅ Features Implemented So Far

### Transactions
- Import/export via CSV (`sample_transactions.csv`)
- Add/Edit/Delete transactions (Date, Vendor, Amount, Category)
- Context menu for edit/delete
- Input validation:
  - Dates must be `YYYY-MM-DD`
  - Amount must be numeric
  - Vendor and Category cannot be empty
- Categories are case-insensitive (`apple`, `APPLE` → `Apple`)
- Transactions auto-sorted by date
- **Independent date filter (new in Sprint 3 start):**
  - Presets: This Month (default), Last Month, Last 30 Days, This Year
  - Custom Range with From/To date pickers
  - Summary shows totals by category based on filter

### Budgets
- Add/Edit/Remove budget per category
- Categories shown = union of:
  - Categories in transactions
  - Categories with budgets
- Budgets persisted in JSON (`budgets.json`)
- Dashboard integration:
  - Correct math: Spent as positive outflows
  - Remaining = Budget − Spent
  - Over-budget highlighted red
  - No-budget categories shown in gray

### Accounts
- Add/Edit/Delete multiple accounts
- Accounts persisted in JSON (`accounts.json`)
- Dashboard shows:
  - Per-account list
  - Total balance across all accounts

### Dashboard
- Total balance across accounts
- Category table:
  - Spent (positive, outflows only)
  - Budget (if any)
  - Remaining (color-coded: green = under, red = over)
- Budgets shown first, then non-budget categories

---

## 📂 Current File Layout
FinanceTool/
├─ main.py
├─ .gitignore
├─ SPRINT-SUMMARY.md
├─ sample_transactions.csv # ignored by Git (local data)
├─ accounts.json # ignored by Git
└─ budgets.json # ignored by Git

---

## 🚧 Known Limitations / Deferred Items
- Dashboard does **not yet have its own date filter** (Transactions filter is independent)
- Budgets are monthly only (no weekly/yearly scaling yet)
- No “apply transactions to account balance” button/logic yet
- No auto-categorization of vendors yet
- No charts/visualizations yet

---

## 🏃 Sprint History
- **Sprint 1**  
  - CSV import + parsing  
  - Category totals  
  - Add/Edit/Delete transactions  
  - Input validation  
- **Sprint 2**  
  - Budgets (add/edit/remove, persist)  
  - Accounts (multi-account CRUD)  
  - Dashboard (spent/budget/remaining with correct sign)  
  - Bug fixes  
- **Sprint 3 (in progress)**  
  - Transactions tab **independent date filter** delivered  
  - Pivot planned before continuing further features

---

## 🔮 Pivot Notes / Next Priorities
- Add **Dashboard date filter** (independent from Transactions filter)
- Add **“Today override”** (for testing time-based views)
- Add **sorting/filtering options**:
  - Alphabetical
  - Spent amount
  - Budget / Remaining
  - Show only overspent / only under-budget
- Re-prioritize features:  
  - Weekly/yearly budgets  
  - Auto-categorization by vendor  
  - Apply transactions to accounts button  
  - Charts & visualizations
