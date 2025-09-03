# FinanceTool – Architecture & Design Documentation

---

## 1. 🏗 System Overview
FinanceTool is a **desktop-based personal finance management application** built with **Python (3.12+)** and **PySide6** for GUI.  
The system follows a **modular, layered architecture** with:
- **Presentation Layer (UI Tabs & Widgets)** – PySide6 QWidgets (Transactions, Budgets, Accounts, Categories, Dashboard, Reports, Settings).
- **Business Logic Layer** – Python classes & functions for transactions, budgets, accounts, categories, filtering, and reporting.
- **Persistence Layer** – Local storage in **CSV (transactions)** and **JSON (budgets, accounts, categories, settings)** files.

All features run **locally on Windows 11** with no external dependencies beyond open-source libraries.

---

## 2. ⚙ Technology Stack
- **Language**: Python 3.12+
- **Framework**: PySide6 (Qt for Python)
- **Data Storage**:  
  - CSV (`transactions.csv`)  
  - JSON (`budgets.json`, `accounts.json`, `categories.json`, `settings.json`)  
- **Visualization**: Matplotlib (embedded charts)  
- **Version Control**: Git (GitHub local repo)  

---

## 3. 🧩 Core Components
### 3.1 User Interface (UI Layer)
- **Main Window (`FinanceApp`)**  
  - Uses `QTabWidget` with tabs:  
    - Dashboard  
    - Transactions  
    - Budgets  
    - Accounts  
    - Categories  
    - Reports  
    - Settings  

- **Dialogs & Widgets**  
  - Add/Edit Transaction dialog  
  - Budget entry dialog (with period chips: daily/weekly/monthly)  
  - Calendar widget for selecting dates  
  - Import Wizard for mapping external CSV/XLS columns  

---

### 3.2 Business Logic Layer
- **Transactions Manager**  
  - Handles add/edit/delete transactions  
  - Tracks `applied_to_balance` flag for account reconciliation  
  - Supports imports from multiple formats (CSV, XLS)  

- **Budgets Manager**  
  - Stores category budgets  
  - Normalizes budgets to monthly equivalents  
  - Provides progress data for dashboard  

- **Accounts Manager**  
  - Maintains account balances  
  - Allows on-demand recalculation from transaction history  
  - Supports multiple accounts  

- **Categories Manager**  
  - Manages user-defined categories  
  - Allows dynamic category creation from transaction entry  
  - Supports edit/remove  

- **Reports & Dashboard Logic**  
  - Aggregates transactions into time-based views  
  - Provides spend breakdowns (MTD, YTD, Custom)  
  - Generates Matplotlib charts (doughnut charts with dark theme)  

---

### 3.3 Persistence Layer
- **Transactions** → `transactions.csv`  
  - Columns: `date, account, vendor, category, amount, applied_to_balance`  
- **Budgets** → `budgets.json`  
  - `{ "Food": {"amount": 200, "period": "Monthly"} }`  
- **Accounts** → `accounts.json`  
  - `[{"name": "Checking", "starting_balance": 1000, "current_balance": 1200}]`  
- **Categories** → `categories.json`  
  - `["Food", "Shopping", "Rent"]`  
- **Settings** → `settings.json`  
  - `{"today_override": "2025-03-01"}`  

---

## 4. 🔄 Data Flow
1. **User Interaction** → User adds/edits transactions, budgets, accounts, or imports data.  
2. **Business Logic** → Validates input, updates in-memory objects.  
3. **Persistence Layer** → Changes are saved immediately to CSV/JSON.  
4. **UI Refresh** → Dashboard/Reports re-compute summaries and re-render charts.  

---

## 5. 📐 Design Decisions
- **Local-first**: All data is stored locally in simple human-readable formats.  
- **Separation of Concerns**: UI tabs interact only with business logic methods; persistence is abstracted away.  
- **Incremental Extensibility**: Architecture supports future integrations (Plaid, AI insights, forecasting).  
- **Testing Support**: “Clear All” buttons per tab allow easy reset and re-import during development.  

---

## 6. 🎨 UI/UX Design Principles
- **Tabbed navigation** for clear separation of features.  
- **Dashboard-first** design (like Monarch Money).  
- **Charts**:  
  - Doughnut charts for spend breakdowns  
  - Dark theme consistency with app UI  
  - Legends instead of overlapping labels  
- **Progress bars** show budget utilization (can exceed 100% if overspent).  
- **Dialogs** for adding/editing items (transactions, budgets, categories).  
- **Data filters**: Time-based filters for Transactions & Dashboard, independent of each other.  

---

## 7. 🔮 Future Design Considerations
- Migrate from CSV/JSON → SQLite (for scalability).  
- Abstract data imports into a **mapping template system** for different banks.  
- Add **multi-user support** with authentication.  
- Consider **web-based frontend** for cross-device access.  

---

## 8. 📌 Current Limitations
- Imported data is persistent but not yet tracked for duplicates across imports.  
- Large datasets may impact performance (CSV parsing overhead).  
- No automated backup/recovery.  
- Basic error handling in Import Wizard (still being hardened).  

---
