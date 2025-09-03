# FinanceTool 💰  
*A personal finance dashboard inspired by Quicken & Monarch Money.*

---

## 📌 Overview  
FinanceTool is a **locally hosted personal finance app** that helps you track:  
- Transactions (manual or imported via CSV/XLS)  
- Budgets (daily, weekly, monthly, normalized for dashboard reporting)  
- Accounts (with on-demand balance adjustment)  
- Categories (with dynamic management)  
- Dashboards & Reports (budgets, MTD spend by account, MTD spend by category with doughnut charts)

Unlike cloud-based apps, FinanceTool is **private, local-only, and fully customizable**.  
The project follows **Agile (Scrum)** with iterative sprints, each adding features, bug fixes, and design improvements.

---

## ✅ Features (MVP Complete)

### Transactions Tab
- Add, edit, delete transactions  
- Import CSV/XLS with custom mapping (Import Wizard)  
- Clear All (reset testing data)  

### Budgets Tab
- Assign budgets to categories  
- Support for **daily, weekly, monthly budgets** (auto-normalized to monthly equivalents)  
- Remove/adjust budgets  

### Accounts Tab
- Add multiple accounts with starting balances  
- Apply new transactions to balances (on-demand)  
- Clear All  

### Categories Tab
- Manage categories directly or while adding transactions  
- Clear All  

### Dashboard
- Budget progress bars (supports >100% overspend)  
- MTD spend by account  
- MTD spend by category (**doughnut chart** with legend + total in center)  
- Recent transactions list  
- Dashboard-only quick filters (This Month, Last Month, YTD, Custom)  

### Reports
- Category spend breakdown with **dark-themed charts**  

### Settings
- Override “Today” date for testing/reporting  
- Clear All (global reset)  

---

## 🛠 Tech Stack
- **Python 3.11+**  
- **PySide6** (Qt for GUI)  
- **Pandas** (CSV/XLS parsing, data manipulation)  
- **Matplotlib** (charts & graphs)  
- **Git** (version control, with tags for sprint checkpoints)  

---

## 🚀 Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/yourusername/FinanceTool.git
   cd FinanceTool

2. Create a virtual environment:
   ```bash
    python -m venv venv
    venv\Scripts\activate   # Windows

3. Install dependencies:
   ```bash
   pip install -r requirements.txt

4. Run the app:
   ```bash
   python main.py

---

## 📂 File Structure  
FinanceTool/
│── main.py              # Core app logic & UI
│── import_wizard.py     # Import transactions (CSV/XLS) wizard
│── requirements.txt     # Dependencies
│── .gitignore           # Ignore local data & venv
│
├── data/                # Local data (ignored by Git)
│   ├── transactions.csv
│   ├── budgets.json
│   ├── accounts.json
│   ├── categories.json
│   └── settings.json
│
├── docs/                # Documentation
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_GUIDE.md
│   └── RETROSPECTIVE.md

---

## 🔄 Git Workflow 
- Checkpoint before new sprint
git add .
git commit -m "Sprint X complete – stable baseline"
git tag sprintX-stable

- Rollback if needed
git checkout sprintX-stable

---

## 🗺 Roadmap (Post-MVP 🚀)
- Bank sync (Plaid API)
- Net worth tracking
- Multi-currency support
- Forecasting & AI insights
- Mobile version

✍️ Developed iteratively using Scrum, with retrospectives & documentation after each sprint.