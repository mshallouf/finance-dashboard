# FinanceTool – Requirements Documentation

---

## 1. 📌 Project Vision
FinanceTool is a **personal finance management tool** inspired by Quicken and Monarch Money.  
It provides users with full control of their **transactions, budgets, accounts, and categories** in a **locally hosted, private, and fully customizable application**.  

The MVP focuses on **core tracking and reporting**, while the long-term goal is to evolve into a professional-grade financial advisory support tool.

---

## 2. 🎯 Goals
- Enable easy **transaction management** (manual entry + import from external data sources).
- Provide **budget tracking** with daily/weekly/monthly normalization.
- Maintain **account balances** with on-demand reconciliation.
- Offer a **clear dashboard** that shows spending, budgets, and trends.
- Keep the tool **local, private, and customizable**.

---

## 3. 📊 MVP Scope
The MVP includes:
1. Transactions (add/edit/delete, import CSV/XLS).
2. Budgets (set/edit/remove budgets, normalized to monthly equivalents).
3. Accounts (balances, adjustments via transactions).
4. Categories (dynamic management, new categories added during transactions).
5. Dashboard (budgets overview, MTD spend by account & category, recent transactions).
6. Reports (category spend charts).
7. Settings (override “Today” date, clear-all functionality).

---

## 4. 🔒 Non-Functional Requirements
- **Platform**: Windows 11 (desktop, local-only).
- **Security**: Single user; no authentication required for MVP.
- **Persistence**: Data stored in **CSV and JSON files** (ignored in Git for privacy).
- **Privacy**: All data is local; no external sync (Plaid integration planned post-MVP).
- **Performance**: Must handle **at least 10,000 transactions** without significant slowdown.
- **Usability**: Simple tabbed interface with dashboards and charts.
- **Extensibility**: Architecture should allow future integration of Plaid, AI insights, multi-currency, etc.

---

## 5. 📂 Data Model
### Transactions
- **Fields**: `date`, `account`, `vendor`, `category`, `amount`, `applied_to_balance` flag  
- **Storage**: `transactions.csv`  

### Budgets
- **Fields**: `category`, `budget_amount`, `period` (daily/weekly/monthly)  
- **Storage**: `budgets.json`  

### Accounts
- **Fields**: `name`, `starting_balance`, `current_balance`  
- **Storage**: `accounts.json`  

### Categories
- **Fields**: list of user-defined categories  
- **Storage**: `categories.json`  

### Settings
- **Fields**: `today_override` (optional custom “today” for reporting/tests)  
- **Storage**: `settings.json`  

---

## 6. 🚫 Out of Scope (MVP)
- Real bank synchronization (Plaid, Yodlee, etc.).  
- Notifications & reminders.  
- Multi-user support.  
- Advanced analytics (forecasting, net worth, AI optimization).  
- Mobile or cloud-hosted version.  

---

## 7. 📌 Constraints
- Must remain **local-only** (no online sync in MVP).  
- Must avoid dependency on paid APIs in MVP.  
- Must keep **UI simple** (desktop GUI only).  
- Data files must remain **human-readable** (CSV/JSON preferred).  

---

## 8. 🔮 Future Extensions (Post-MVP)
- **Plaid integration** for automatic bank feeds.  
- **Net worth tracking** across accounts, loans, assets.  
- **Forecasting & AI** to optimize financial decisions.  
- **Multi-currency** support.  
- **Mobile companion app**.  
- **Advisor mode** (for financial advisory practice).  

---

## 9. ✔ Acceptance Criteria (MVP Done)
- Users can **add, edit, delete, and import transactions**.  
- Users can **set budgets per category**, see **spending progress**, and budgets remain visible even if spending is zero.  
- Users can **add accounts**, reconcile balances via transactions, and reset if needed.  
- Dashboard shows:  
  - **Budget progress bars** (with overspending >100%).  
  - **MTD spend by account**.  
  - **MTD spend by category** (list + doughnut chart).  
  - **Recent transactions**.  
- Users can **manage categories** (add dynamically, edit/remove, clear all).  
- All data persists locally via CSV/JSON.  
- Users can **clear all data** (per tab or global).  

---
