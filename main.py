import sys
import os
import json
import datetime
import pandas as pd
from datetime import datetime as dt

from PySide6.QtWidgets import (
    QApplication, QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QMessageBox, QMenu,
    QTabWidget, QHBoxLayout, QComboBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate

# ----------------------------
# File paths / constants
# ----------------------------
TRANSACTIONS_FILE = "sample_transactions.csv"
BUDGET_FILE = "budgets.json"
ACCOUNTS_FILE = "accounts.json"


# ----------------------------
# Helper functions (dates)
# ----------------------------
def start_of_month(date: datetime.date) -> datetime.date:
    return date.replace(day=1)

def end_of_month(date: datetime.date) -> datetime.date:
    # last day of the month trick
    next_month = date.replace(day=28) + datetime.timedelta(days=4)
    return next_month - datetime.timedelta(days=next_month.day)


# ----------------------------
# Dialogs
# ----------------------------
class AddTransactionDialog(QDialog):
    def __init__(self, parent=None, transaction=None):
        super().__init__(parent)
        self.setWindowTitle("Add Transaction" if transaction is None else "Edit Transaction")
        self.layout = QFormLayout(self)

        self.date_input = QLineEdit(self)
        self.vendor_input = QLineEdit(self)
        self.amount_input = QLineEdit(self)
        self.category_input = QLineEdit(self)

        self.layout.addRow("Date (YYYY-MM-DD):", self.date_input)
        self.layout.addRow("Vendor:", self.vendor_input)
        self.layout.addRow("Amount:", self.amount_input)
        self.layout.addRow("Category:", self.category_input)

        if transaction:
            self.date_input.setText(transaction["Date"])
            self.vendor_input.setText(transaction["Vendor"])
            self.amount_input.setText(str(transaction["Amount"]))
            self.category_input.setText(transaction["Category"])

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def getData(self):
        return {
            "Date": self.date_input.text(),
            "Vendor": self.vendor_input.text(),
            "Amount": self.amount_input.text(),
            "Category": self.category_input.text()
        }


class BudgetDialog(QDialog):
    def __init__(self, categories, current_budgets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set/Edit Budget")
        self.layout = QFormLayout(self)

        self.category_input = QLineEdit(self)
        self.category_input.setReadOnly(True)

        # Simple selector via a table (click to choose)
        self.category_dropdown = QTableWidget()
        self.category_dropdown.setRowCount(len(categories))
        self.category_dropdown.setColumnCount(1)
        self.category_dropdown.setHorizontalHeaderLabels(["Category"])
        for i, cat in enumerate(categories):
            self.category_dropdown.setItem(i, 0, QTableWidgetItem(cat))
        self.category_dropdown.cellClicked.connect(self.select_category)

        self.layout.addRow("Select Category (click):", self.category_dropdown)
        self.layout.addRow("Category:", self.category_input)

        self.budget_input = QLineEdit(self)
        self.layout.addRow("Budget Amount:", self.budget_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def select_category(self, row, col):
        cat = self.category_dropdown.item(row, 0).text()
        self.category_input.setText(cat)

    def getData(self):
        return {
            "Category": self.category_input.text(),
            "Budget": self.budget_input.text()
        }


class AccountDialog(QDialog):
    def __init__(self, account=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Account" if account is None else "Edit Account")
        self.layout = QFormLayout(self)

        self.name_input = QLineEdit(self)
        self.balance_input = QLineEdit(self)

        self.layout.addRow("Account Name:", self.name_input)
        self.layout.addRow("Balance:", self.balance_input)

        if account:
            self.name_input.setText(account["name"])
            self.balance_input.setText(str(account["balance"]))

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def getData(self):
        return {
            "name": self.name_input.text(),
            "balance": self.balance_input.text()
        }


# ----------------------------
# Main App
# ----------------------------
class FinanceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Finance Tool")
        self.setGeometry(100, 100, 950, 600)
        self.layout = QVBoxLayout(self)

        # ------- Load Data -------
        # Transactions
        try:
            self.df = pd.read_csv(TRANSACTIONS_FILE, dtype=str)
        except FileNotFoundError:
            self.df = pd.DataFrame(columns=['Date', 'Vendor', 'Amount', 'Category'])
        if not self.df.empty:
            self.df['Amount'] = self.df['Amount'].astype(float)

        # Budgets
        self.budgets = self.load_json(BUDGET_FILE, default={})

        # Accounts
        self.accounts = self.load_json(ACCOUNTS_FILE, default=[])

        # ------- Tabs -------
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # STATE for Transactions tab filtering (independent from dashboard)
        self.txn_filter_mode = "This Month"

        # Transactions tab
        self.trans_tab = QWidget()
        self.tabs.addTab(self.trans_tab, "Transactions")
        self.init_transactions_tab()

        # Budgets tab
        self.budget_tab = QWidget()
        self.tabs.addTab(self.budget_tab, "Budgets")
        self.init_budgets_tab()

        # Accounts tab
        self.accounts_tab = QWidget()
        self.tabs.addTab(self.accounts_tab, "Accounts")
        self.init_accounts_tab()

        # Dashboard tab
        self.dashboard_tab = QWidget()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.init_dashboard_tab()

        # Keep some tabs in sync
        self.tabs.currentChanged.connect(self.on_tab_change)

    # ---------------- Data utils ----------------
    def load_json(self, filename, default):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
        return default

    def save_json(self, filename, data):
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

    # ---------------- Transactions Tab (with date filter) ----------------
    def init_transactions_tab(self):
        layout = QVBoxLayout()

        # ---- Filter Bar ----
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Show:"))

        self.txn_filter_dropdown = QComboBox()
        self.txn_filter_dropdown.addItems([
            "This Month", "Last Month", "Last 30 Days", "This Year", "Custom Range"
        ])
        self.txn_filter_dropdown.setCurrentText("This Month")
        filter_bar.addWidget(self.txn_filter_dropdown)

        # Custom date pickers (hidden unless "Custom Range")
        filter_bar.addWidget(QLabel("From:"))
        self.txn_filter_from_picker = QDateEdit()
        self.txn_filter_from_picker.setCalendarPopup(True)
        self.txn_filter_from_picker.setDate(QDate.currentDate())
        filter_bar.addWidget(self.txn_filter_from_picker)

        filter_bar.addWidget(QLabel("To:"))
        self.txn_filter_to_picker = QDateEdit()
        self.txn_filter_to_picker.setCalendarPopup(True)
        self.txn_filter_to_picker.setDate(QDate.currentDate())
        filter_bar.addWidget(self.txn_filter_to_picker)

        # Initially hide custom pickers
        self.txn_filter_from_picker.hide()
        self.txn_filter_to_picker.hide()

        # Events
        self.txn_filter_dropdown.currentTextChanged.connect(self.on_txn_filter_changed)
        self.txn_filter_from_picker.dateChanged.connect(self.on_txn_filter_changed)
        self.txn_filter_to_picker.dateChanged.connect(self.on_txn_filter_changed)

        layout.addLayout(filter_bar)

        # ---- Table + controls ----
        self.table = QTableWidget()
        layout.addWidget(self.table)

        self.add_button = QPushButton("Add Transaction")
        self.add_button.clicked.connect(self.add_transaction)
        layout.addWidget(self.add_button)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        self.trans_tab.setLayout(layout)

        # Init fill
        self.update_table()
        self.update_summary()

        # Context menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)

    def on_txn_filter_changed(self, *args):
        mode = self.txn_filter_dropdown.currentText()
        if mode == "Custom Range":
            self.txn_filter_from_picker.show()
            self.txn_filter_to_picker.show()
        else:
            self.txn_filter_from_picker.hide()
            self.txn_filter_to_picker.hide()
        self.update_table()
        self.update_summary()

    def get_filtered_transactions(self) -> pd.DataFrame:
        if self.df.empty:
            return self.df.copy()
        df = self.df.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        mode = self.txn_filter_dropdown.currentText()
        today = QDate.currentDate().toPython()  # independent for Transactions tab; dashboard will get its own later

        if mode == "This Month":
            start = start_of_month(today)
            end = end_of_month(today)
        elif mode == "Last Month":
            first_this_month = start_of_month(today)
            last_month_end = first_this_month - datetime.timedelta(days=1)
            start = start_of_month(last_month_end)
            end = end_of_month(last_month_end)
        elif mode == "Last 30 Days":
            end = today
            start = today - datetime.timedelta(days=29)
        elif mode == "This Year":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
        elif mode == "Custom Range":
            start = self.txn_filter_from_picker.date().toPython()
            end = self.txn_filter_to_picker.date().toPython()
        else:
            start = df['Date'].min().date()
            end = df['Date'].max().date()

        mask = (df['Date'] >= pd.Timestamp(start)) & (df['Date'] <= pd.Timestamp(end))
        return df.loc[mask].reset_index(drop=True)

    def update_table(self):
        filtered_df = self.get_filtered_transactions()
        if not filtered_df.empty:
            filtered_df['Date'] = pd.to_datetime(filtered_df['Date'], errors='coerce')
            filtered_df = filtered_df.sort_values('Date', ascending=True)
            filtered_df['Date'] = filtered_df['Date'].dt.strftime('%Y-%m-%d')

        self.table.setRowCount(filtered_df.shape[0])
        self.table.setColumnCount(filtered_df.shape[1])
        self.table.setHorizontalHeaderLabels(filtered_df.columns)
        for r in range(filtered_df.shape[0]):
            for c in range(filtered_df.shape[1]):
                self.table.setItem(r, c, QTableWidgetItem(str(filtered_df.iloc[r, c])))

    def update_summary(self):
        filtered_df = self.get_filtered_transactions()
        if filtered_df.empty:
            self.summary_label.setText("No data.")
            return
        filtered_df['Category'] = filtered_df['Category'].str.lower().str.capitalize()
        category_totals = filtered_df.groupby('Category')['Amount'].sum()
        lines = ["Total by Category:"]
        for cat, total in category_totals.items():
            lines.append(f"{cat}: ${total:,.2f}")
        self.summary_label.setText("\n".join(lines))

    def add_transaction(self):
        dialog = AddTransactionDialog(self)
        while True:
            result = dialog.exec()
            if result == QDialog.Rejected:
                return
            new = dialog.getData()
            try:
                dt.strptime(new["Date"], "%Y-%m-%d")
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Date must be in YYYY-MM-DD format.")
                continue
            try:
                new["Amount"] = float(new["Amount"])
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Amount must be a number.")
                continue
            if not (new["Vendor"].strip() and new["Category"].strip()):
                QMessageBox.warning(self, "Input Error", "Vendor and Category cannot be empty.")
                continue
            new["Category"] = new["Category"].strip().lower().capitalize()
            break

        self.df.loc[len(self.df)] = new
        self.save_and_refresh()

    def open_context_menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        menu = QMenu(self)
        a_edit = menu.addAction("Edit Transaction")
        a_del = menu.addAction("Delete Transaction")
        action = menu.exec(self.table.mapToGlobal(pos))
        if action == a_edit:
            self.edit_transaction(idx.row())
        elif action == a_del:
            self.delete_transaction(idx.row())

    def edit_transaction(self, row):
        # row maps to filtered table; find corresponding index in df by matching displayed row
        filtered_df = self.get_filtered_transactions()
        if row < 0 or row >= len(filtered_df):
            return
        current = filtered_df.iloc[row].to_dict()

        dialog = AddTransactionDialog(self, current)
        while True:
            result = dialog.exec()
            if result == QDialog.Rejected:
                return
            new = dialog.getData()
            try:
                dt.strptime(new["Date"], "%Y-%m-%d")
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Date must be in YYYY-MM-DD format.")
                continue
            try:
                new["Amount"] = float(new["Amount"])
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Amount must be a number.")
                continue
            if not (new["Vendor"].strip() and new["Category"].strip()):
                QMessageBox.warning(self, "Input Error", "Vendor and Category cannot be empty.")
                continue
            new["Category"] = new["Category"].strip().lower().capitalize()
            break

        # Locate the original row in self.df by a unique combination (Date, Vendor, Amount, Category).
        # If duplicates exist, fallback to first match.
        mask = (
            (self.df['Date'] == current['Date']) &
            (self.df['Vendor'] == current['Vendor']) &
            (self.df['Amount'] == float(current['Amount'])) &
            (self.df['Category'] == current['Category'])
        )
        indices = self.df.index[mask]
        if len(indices) == 0:
            # if not found, do nothing safely
            QMessageBox.warning(self, "Not Found", "Original transaction row could not be located.")
            return

        i = indices[0]
        self.df.at[i, 'Date'] = new['Date']
        self.df.at[i, 'Vendor'] = new['Vendor']
        self.df.at[i, 'Amount'] = new['Amount']
        self.df.at[i, 'Category'] = new['Category']
        self.save_and_refresh()

    def delete_transaction(self, row):
        filtered_df = self.get_filtered_transactions()
        if row < 0 or row >= len(filtered_df):
            return
        current = filtered_df.iloc[row].to_dict()

        reply = QMessageBox.question(self, "Delete", "Delete this transaction?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        mask = (
            (self.df['Date'] == current['Date']) &
            (self.df['Vendor'] == current['Vendor']) &
            (self.df['Amount'] == float(current['Amount'])) &
            (self.df['Category'] == current['Category'])
        )
        indices = self.df.index[mask]
        if len(indices) == 0:
            QMessageBox.warning(self, "Not Found", "Original transaction row could not be located.")
            return

        self.df = self.df.drop(indices[0]).reset_index(drop=True)
        self.save_and_refresh()

    def save_and_refresh(self):
        self.df.to_csv(TRANSACTIONS_FILE, index=False)
        self.update_table()
        self.update_summary()
        # keep budgets/dashboard fresh when switching tabs
        # (we do the actual refresh in on_tab_change)

    # ---------------- Budgets Tab ----------------
    def init_budgets_tab(self):
        layout = QVBoxLayout()

        self.budget_table = QTableWidget()
        self.budget_table.setColumnCount(2)
        self.budget_table.setHorizontalHeaderLabels(["Category", "Budget"])
        layout.addWidget(self.budget_table)

        row_btns = QHBoxLayout()
        btn_edit = QPushButton("Add/Edit Budget")
        btn_remove = QPushButton("Remove Budget")
        row_btns.addWidget(btn_edit)
        row_btns.addWidget(btn_remove)
        layout.addLayout(row_btns)

        btn_edit.clicked.connect(self.add_edit_budget)
        btn_remove.clicked.connect(self.remove_budget)

        self.budget_tab.setLayout(layout)
        self.update_budgets_table()

    def update_budgets_table(self):
        # Categories displayed = categories from transactions ∪ categories that have a budget
        txn_cats = set(self.df['Category'].str.lower().str.capitalize()) if not self.df.empty else set()
        budget_cats = set(self.budgets.keys())
        all_cats = sorted(txn_cats | budget_cats)

        self.budget_table.setRowCount(len(all_cats))
        for r, cat in enumerate(all_cats):
            self.budget_table.setItem(r, 0, QTableWidgetItem(cat))
            budget = self.budgets.get(cat, "None")
            self.budget_table.setItem(r, 1, QTableWidgetItem(str(budget)))

    def add_edit_budget(self):
        txn_cats = set(self.df['Category'].str.lower().str.capitalize()) if not self.df.empty else set()
        budget_cats = set(self.budgets.keys())
        all_cats = sorted(txn_cats | budget_cats)

        dialog = BudgetDialog(all_cats, self.budgets, self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.getData()
        cat = data["Category"].strip()
        if not cat:
            QMessageBox.warning(self, "Input Error", "Please select a category.")
            return
        try:
            amt = float(data["Budget"])
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Budget must be a number.")
            return

        self.budgets[cat] = amt
        self.save_json(BUDGET_FILE, self.budgets)
        self.update_budgets_table()
        self.update_dashboard_tab()

    def remove_budget(self):
        row = self.budget_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select a category to remove its budget.")
            return
        cat = self.budget_table.item(row, 0).text()
        if cat not in self.budgets:
            QMessageBox.warning(self, "No Budget", f"No budget set for {cat}.")
            return
        reply = QMessageBox.question(self, "Remove Budget", f"Remove budget for '{cat}'?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        del self.budgets[cat]
        self.save_json(BUDGET_FILE, self.budgets)
        self.update_budgets_table()
        self.update_dashboard_tab()

    # ---------------- Accounts Tab ----------------
    def init_accounts_tab(self):
        layout = QVBoxLayout()

        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(2)
        self.accounts_table.setHorizontalHeaderLabels(["Account Name", "Balance"])
        layout.addWidget(self.accounts_table)

        row_btns = QHBoxLayout()
        btn_add = QPushButton("Add Account")
        btn_edit = QPushButton("Edit Account")
        btn_del = QPushButton("Delete Account")
        row_btns.addWidget(btn_add)
        row_btns.addWidget(btn_edit)
        row_btns.addWidget(btn_del)
        layout.addLayout(row_btns)

        btn_add.clicked.connect(self.add_account)
        btn_edit.clicked.connect(self.edit_account)
        btn_del.clicked.connect(self.delete_account)

        self.accounts_tab.setLayout(layout)
        self.update_accounts_table()

    def update_accounts_table(self):
        self.accounts_table.setRowCount(len(self.accounts))
        for r, acct in enumerate(self.accounts):
            self.accounts_table.setItem(r, 0, QTableWidgetItem(acct["name"]))
            self.accounts_table.setItem(r, 1, QTableWidgetItem(f"${float(acct['balance']):,.2f}"))

    def add_account(self):
        dialog = AccountDialog(parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.getData()
        name = data["name"].strip()
        if not name:
            QMessageBox.warning(self, "Input Error", "Account name cannot be empty.")
            return
        try:
            bal = float(data["balance"])
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Balance must be a number.")
            return
        self.accounts.append({"name": name, "balance": bal})
        self.save_json(ACCOUNTS_FILE, self.accounts)
        self.update_accounts_table()
        self.update_dashboard_tab()

    def edit_account(self):
        row = self.accounts_table.currentRow()
        if row < 0 or row >= len(self.accounts):
            QMessageBox.warning(self, "No Selection", "Please select an account to edit.")
            return
        acct = self.accounts[row]
        dialog = AccountDialog(account=acct, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.getData()
        name = data["name"].strip()
        if not name:
            QMessageBox.warning(self, "Input Error", "Account name cannot be empty.")
            return
        try:
            bal = float(data["balance"])
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Balance must be a number.")
            return
        self.accounts[row] = {"name": name, "balance": bal}
        self.save_json(ACCOUNTS_FILE, self.accounts)
        self.update_accounts_table()
        self.update_dashboard_tab()

    def delete_account(self):
        row = self.accounts_table.currentRow()
        if row < 0 or row >= len(self.accounts):
            QMessageBox.warning(self, "No Selection", "Please select an account to delete.")
            return
        reply = QMessageBox.question(self, "Delete", f"Delete account '{self.accounts[row]['name']}'?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self.accounts.pop(row)
        self.save_json(ACCOUNTS_FILE, self.accounts)
        self.update_accounts_table()
        self.update_dashboard_tab()

    # ---------------- Dashboard Tab ----------------
    def init_dashboard_tab(self):
        layout = QVBoxLayout()

        self.dashboard_balance_label = QLabel()
        layout.addWidget(self.dashboard_balance_label)

        self.dashboard_table = QTableWidget()
        self.dashboard_table.setColumnCount(4)
        self.dashboard_table.setHorizontalHeaderLabels(["Category", "Spent", "Budget", "Remaining"])
        layout.addWidget(self.dashboard_table)

        self.dashboard_tab.setLayout(layout)
        self.update_dashboard_tab()

    def update_dashboard_tab(self):
        # total across all accounts
        total = sum(float(a["balance"]) for a in self.accounts)
        self.dashboard_balance_label.setText(f"Total Balance Across All Accounts: <b>${total:,.2f}</b>")

        # Build category view using ALL transactions (dashboard will get its own filter in a later step of Sprint 3)
        if self.df.empty and not self.budgets:
            self.dashboard_table.setRowCount(0)
            return

        df = self.df.copy()
        if not df.empty:
            df['Category'] = df['Category'].str.lower().str.capitalize()

        # Spent = sum of absolute negatives (outflows) by category
        if not df.empty:
            category_spent = df.groupby('Category')['Amount'].apply(lambda x: abs(x[x < 0].sum())).to_dict()
        else:
            category_spent = {}

        all_categories = set(category_spent.keys()) | set(self.budgets.keys())

        rows = []
        for cat in all_categories:
            spent = category_spent.get(cat, 0.0)
            budget = self.budgets.get(cat, None)
            remaining = (budget - spent) if budget is not None else ""
            rows.append({
                "category": cat,
                "spent": spent,
                "budget": budget,
                "remaining": remaining
            })

        rows.sort(key=lambda x: (0 if x['budget'] is not None else 1, x['category']))

        self.dashboard_table.setRowCount(len(rows))
        for r, data in enumerate(rows):
            cat_item = QTableWidgetItem(data["category"])
            spent_item = QTableWidgetItem(f"${data['spent']:,.2f}")
            budget_item = QTableWidgetItem("" if data["budget"] is None else f"${float(data['budget']):,.2f}")

            if data["budget"] is not None:
                rem_val = data["remaining"]
                rem_item = QTableWidgetItem(f"${rem_val:,.2f}")
                if rem_val < 0:
                    rem_item.setForeground(Qt.red)
                    rem_item.setText(f"Over by ${-rem_val:,.2f}")
                else:
                    rem_item.setForeground(Qt.darkGreen)
            else:
                rem_item = QTableWidgetItem("No budget set")
                rem_item.setForeground(Qt.gray)

            self.dashboard_table.setItem(r, 0, cat_item)
            self.dashboard_table.setItem(r, 1, spent_item)
            self.dashboard_table.setItem(r, 2, budget_item)
            self.dashboard_table.setItem(r, 3, rem_item)

    # ---------------- Tab change hook ----------------
    def on_tab_change(self, index):
        name = self.tabs.tabText(index)
        if name == "Budgets":
            self.update_budgets_table()
        elif name == "Accounts":
            self.update_accounts_table()
        elif name == "Dashboard":
            self.update_dashboard_tab()


# ----------------------------
# Entrypoint
# ----------------------------
if __name__ == "__main__":
    print("Launching app...")
    app = QApplication(sys.argv)
    try:
        window = FinanceApp()
        window.show()
        sys.exit(app.exec())
    except Exception:
        import traceback
        print("Exception occurred:")
        traceback.print_exc()
        input("Press Enter to exit...")
