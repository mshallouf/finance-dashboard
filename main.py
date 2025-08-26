import sys
import os
import json
import datetime
import pandas as pd
from datetime import datetime as dt

from PySide6.QtWidgets import (
    QApplication, QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QMessageBox, QMenu,
    QTabWidget, QHBoxLayout, QComboBox, QDateEdit, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt, QDate

# ----------------------------
# File paths / constants
# ----------------------------
TRANSACTIONS_FILE = "sample_transactions.csv"
BUDGET_FILE = "budgets.json"
ACCOUNTS_FILE = "accounts.json"
SETTINGS_FILE = "settings.json"


# ----------------------------
# Helper functions (dates/currency)
# ----------------------------
def start_of_month(date: datetime.date) -> datetime.date:
    return date.replace(day=1)

def end_of_month(date: datetime.date) -> datetime.date:
    next_month = date.replace(day=28) + datetime.timedelta(days=4)
    return next_month - datetime.timedelta(days=next_month.day)

def days_in_month(date: datetime.date) -> int:
    return (end_of_month(date) - start_of_month(date)).days + 1

def fmt_money(value) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return str(value)


# ----------------------------
# Dialogs
# ----------------------------
class AddTransactionDialog(QDialog):
    """
    Add/Edit Transaction.
    - Date uses QDateEdit (calendar)
    - Type (Expense/Income)
    - Account dropdown
    """
    def __init__(self, parent=None, transaction=None, account_names=None):
        super().__init__(parent)
        self.setWindowTitle("Add Transaction" if transaction is None else "Edit Transaction")
        self.layout = QFormLayout(self)

        self.date_input = QDateEdit(self)
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")

        self.vendor_input = QLineEdit(self)
        self.amount_input = QLineEdit(self)

        self.type_dropdown = QComboBox(self)
        self.type_dropdown.addItems(["Expense", "Income"])

        self.category_input = QLineEdit(self)

        self.account_dropdown = QComboBox(self)
        account_names = account_names or []
        if "Unassigned" not in account_names:
            account_names = ["Unassigned"] + list(account_names)
        self.account_dropdown.addItems(account_names)

        self.layout.addRow("Date:", self.date_input)
        self.layout.addRow("Vendor:", self.vendor_input)
        self.layout.addRow("Amount:", self.amount_input)
        self.layout.addRow("Type:", self.type_dropdown)
        self.layout.addRow("Category:", self.category_input)
        self.layout.addRow("Account:", self.account_dropdown)

        # Prefill if editing
        if transaction:
            try:
                d = dt.strptime(str(transaction["Date"]), "%Y-%m-%d").date()
            except Exception:
                d = datetime.date.today()
            self.date_input.setDate(QDate(d.year, d.month, d.day))
            self.vendor_input.setText(str(transaction["Vendor"]))
            self.amount_input.setText(str(transaction["Amount"]))
            self.category_input.setText(str(transaction["Category"]))
            # Type by sign (or provided)
            t = transaction.get("Type", "Expense")
            if t not in ["Expense", "Income"]:
                t = "Expense" if float(transaction.get("Amount", 0)) < 0 else "Income"
            self.type_dropdown.setCurrentText(t)
            # Account
            acct = str(transaction.get("Account", "Unassigned")) or "Unassigned"
            idx = self.account_dropdown.findText(acct)
            if idx >= 0:
                self.account_dropdown.setCurrentIndex(idx)
        else:
            today = datetime.date.today()
            self.date_input.setDate(QDate(today.year, today.month, today.day))

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def getData(self):
        date_py = self.date_input.date().toPython()
        return {
            "Date": date_py.strftime("%Y-%m-%d"),
            "Vendor": self.vendor_input.text(),
            "Amount": self.amount_input.text(),
            "Type": self.type_dropdown.currentText(),
            "Category": self.category_input.text(),
            "Account": self.account_dropdown.currentText()
        }


class BudgetDialog(QDialog):
    """
    Add/Edit a budget for a category.
    Period: Monthly/Weekly/Daily
    """
    def __init__(self, categories, budgets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set/Edit Budget")
        self.budgets = budgets  # {cat: {"amount": float, "period": "daily|weekly|monthly"}}

        self.layout = QFormLayout(self)

        self.category_dropdown = QComboBox(self)
        self.category_dropdown.addItems(categories)
        self.layout.addRow("Category:", self.category_dropdown)

        self.amount_input = QLineEdit(self)
        self.layout.addRow("Amount:", self.amount_input)

        self.period_dropdown = QComboBox(self)
        self.period_dropdown.addItems(["Monthly", "Weekly", "Daily"])
        self.layout.addRow("Period:", self.period_dropdown)

        self.category_dropdown.currentTextChanged.connect(self.on_category_changed)
        self.on_category_changed(self.category_dropdown.currentText())

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def on_category_changed(self, cat):
        data = self.budgets.get(cat)
        if isinstance(data, dict):
            amt = data.get("amount", "")
            period = (data.get("period") or "monthly").capitalize()
            self.amount_input.setText(str(amt))
            idx = self.period_dropdown.findText(period)
            if idx >= 0:
                self.period_dropdown.setCurrentIndex(idx)
        else:
            self.amount_input.setText("")
            self.period_dropdown.setCurrentIndex(self.period_dropdown.findText("Monthly"))

    def getData(self):
        return {
            "Category": self.category_dropdown.currentText().strip(),
            "Amount": self.amount_input.text(),
            "Period": self.period_dropdown.currentText().lower()
        }


class AccountDialog(QDialog):
    """Add/Edit Account (name + balance)."""
    def __init__(self, account=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Account" if account is None else "Edit Account")
        self.layout = QFormLayout(self)

        self.name_input = QLineEdit(self)
        self.balance_input = QLineEdit(self)

        self.layout.addRow("Account Name:", self.name_input)
        self.layout.addRow("Balance:", self.balance_input)

        if account:
            self.name_input.setText(str(account["name"]))
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
        self.setGeometry(80, 80, 1150, 780)
        self.layout = QVBoxLayout(self)

        # ------- Load Data -------
        self.df = self.load_transactions()
        self.budgets = self.migrate_budgets(self.load_json(BUDGET_FILE, default={}))
        self.accounts = self.load_json(ACCOUNTS_FILE, default=[])
        self.settings = self.load_json(SETTINGS_FILE, default={"today_override": None})

        # ------- Tabs (Dashboard first) -------
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Dashboard first
        self.dashboard_tab = QWidget()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.init_dashboard_tab()

        # Transactions
        self.trans_tab = QWidget()
        self.tabs.addTab(self.trans_tab, "Transactions")
        self.init_transactions_tab()

        # Budgets
        self.budget_tab = QWidget()
        self.tabs.addTab(self.budget_tab, "Budgets")
        self.init_budgets_tab()

        # Accounts
        self.accounts_tab = QWidget()
        self.tabs.addTab(self.accounts_tab, "Accounts")
        self.init_accounts_tab()

        # Settings
        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "Settings")
        self.init_settings_tab()

        self.tabs.currentChanged.connect(self.on_tab_change)

    # ---------------- Data utils ----------------
    def load_json(self, filename, default):
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    return json.load(f)
            except Exception:
                return default
        return default

    def save_json(self, filename, data):
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

    def migrate_budgets(self, raw):
        """Normalize budgets to dict with amount+period."""
        migrated = {}
        for cat, val in (raw or {}).items():
            if isinstance(val, dict):
                amt = float(val.get("amount", 0))
                period = (val.get("period") or "monthly").lower()
            else:
                try:
                    amt = float(val)
                except Exception:
                    amt = 0.0
                period = "monthly"
            migrated[cat] = {"amount": amt, "period": period}
        if migrated != raw:
            self.save_json(BUDGET_FILE, migrated)
        return migrated

    def load_transactions(self) -> pd.DataFrame:
        cols = ['Id', 'Date', 'Vendor', 'Amount', 'Type', 'Category', 'Account']
        try:
            df = pd.read_csv(TRANSACTIONS_FILE, dtype=str)
        except FileNotFoundError:
            df = pd.DataFrame(columns=cols)

        # Ensure columns exist
        for c in cols:
            if c not in df.columns:
                if c == 'Id':
                    continue
                df[c] = "" if c not in ['Amount'] else "0"
        # Id column
        if "Id" not in df.columns or df["Id"].isna().all():
            # assign incremental Ids
            df["Id"] = ""
            next_id = 1
            for i in df.index:
                df.at[i, "Id"] = str(next_id)
                next_id += 1

        # Dtypes
        if not df.empty:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
            # Type inference if missing
            if "Type" in df.columns:
                df['Type'] = df['Type'].replace("", pd.NA)
            if "Type" not in df.columns or df['Type'].isna().any():
                df['Type'] = df['Amount'].apply(lambda x: "Expense" if float(x) < 0 else "Income")
            # Account default
            if "Account" in df.columns:
                df['Account'] = df['Account'].replace("", "Unassigned")
            else:
                df['Account'] = "Unassigned"
        else:
            df = pd.DataFrame(columns=cols)

        # Reorder columns
        df = df[['Id', 'Date', 'Vendor', 'Amount', 'Type', 'Category', 'Account']]
        return df

    def save_transactions(self):
        # Ensure proper order
        cols = ['Id', 'Date', 'Vendor', 'Amount', 'Type', 'Category', 'Account']
        for c in cols:
            if c not in self.df.columns:
                self.df[c] = ""
        self.df[cols].to_csv(TRANSACTIONS_FILE, index=False)

    def get_today(self) -> datetime.date:
        ov = self.settings.get("today_override")
        if ov:
            try:
                return dt.strptime(ov, "%Y-%m-%d").date()
            except Exception:
                pass
        return datetime.date.today()

    # ---------------- Budget math ----------------
    def monthly_equivalent(self, amount: float, period: str, today: datetime.date) -> float:
        period = (period or "monthly").lower()
        dim = days_in_month(today)
        if period == "monthly":
            return float(amount)
        elif period == "weekly":
            return float(amount) * (dim / 7.0)
        elif period == "daily":
            return float(amount) * dim
        else:
            return float(amount)

    # ---------------- Transactions Tab ----------------
    def init_transactions_tab(self):
        self.txn_sort_mode = "Date: Newest→Oldest"

        layout = QVBoxLayout()

        # ---- Filter + Sort bar
        filter_bar = QHBoxLayout()

        filter_bar.addWidget(QLabel("Show:"))
        self.txn_filter_dropdown = QComboBox()
        self.txn_filter_dropdown.addItems([
            "This Month", "Last Month", "Last 30 Days", "This Year", "Last 7 Days", "Custom Range"
        ])
        self.txn_filter_dropdown.setCurrentText("This Month")
        filter_bar.addWidget(self.txn_filter_dropdown)

        filter_bar.addWidget(QLabel("From:"))
        self.txn_filter_from_picker = QDateEdit()
        self.txn_filter_from_picker.setCalendarPopup(True)
        self.txn_filter_from_picker.setDisplayFormat("yyyy-MM-dd")
        self.txn_filter_from_picker.setDate(QDate.currentDate())
        filter_bar.addWidget(self.txn_filter_from_picker)

        filter_bar.addWidget(QLabel("To:"))
        self.txn_filter_to_picker = QDateEdit()
        self.txn_filter_to_picker.setCalendarPopup(True)
        self.txn_filter_to_picker.setDisplayFormat("yyyy-MM-dd")
        self.txn_filter_to_picker.setDate(QDate.currentDate())
        filter_bar.addWidget(self.txn_filter_to_picker)

        self.txn_filter_from_picker.hide()
        self.txn_filter_to_picker.hide()

        filter_bar.addSpacing(20)
        filter_bar.addWidget(QLabel("Sort by:"))
        self.txn_sort_dropdown = QComboBox()
        self.txn_sort_dropdown.addItems([
            "Date: Newest→Oldest",
            "Date: Oldest→Newest",
            "Amount: High→Low",
            "Amount: Low→High",
            "Category: A→Z",
            "Category: Z→A",
            "Vendor: A→Z",
            "Vendor: Z→A",
            "Account: A→Z",
            "Account: Z→A"
        ])
        self.txn_sort_dropdown.setCurrentText(self.txn_sort_mode)
        filter_bar.addWidget(self.txn_sort_dropdown)

        layout.addLayout(filter_bar)

        # ---- Table
        self.table = QTableWidget()
        layout.addWidget(self.table)

        # ---- Buttons row
        btn_row = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        btn_row.addWidget(self.add_button)
        btn_row.addWidget(self.edit_button)
        btn_row.addWidget(self.delete_button)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        # Wire events
        self.txn_filter_dropdown.currentTextChanged.connect(self.on_txn_filter_changed)
        self.txn_filter_from_picker.dateChanged.connect(self.on_txn_filter_changed)
        self.txn_filter_to_picker.dateChanged.connect(self.on_txn_filter_changed)
        self.txn_sort_dropdown.currentTextChanged.connect(self.on_txn_sort_changed)

        self.add_button.clicked.connect(self.add_transaction)
        self.edit_button.clicked.connect(self._edit_selected_transaction)
        self.delete_button.clicked.connect(self._delete_selected_transaction)

        self.trans_tab.setLayout(layout)

        # Init fill
        self.update_table()
        self.update_summary()

        # Context menu (still available)
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
        if mode == "Custom Range":
            from_d = self.txn_filter_from_picker.date().toPython()
            to_d = self.txn_filter_to_picker.date().toPython()
            if from_d > to_d:
                QMessageBox.warning(self, "Invalid Range", "From date must be on or before To date.")
                return
        self.update_table()
        self.update_summary()

    def on_txn_sort_changed(self, *_):
        self.txn_sort_mode = self.txn_sort_dropdown.currentText()
        self.update_table()

    def compute_date_window(self, mode: str) -> tuple[datetime.date, datetime.date]:
        today = self.get_today()
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
        elif mode == "Last 7 Days":
            end = today
            start = today - datetime.timedelta(days=6)
        elif mode == "This Year":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
        elif mode == "Custom Range":
            start = self.txn_filter_from_picker.date().toPython()
            end = self.txn_filter_to_picker.date().toPython()
        else:
            if self.df.empty:
                start = today
                end = today
            else:
                dts = pd.to_datetime(self.df['Date'], errors='coerce').dropna()
                start = dts.min().date()
                end = dts.max().date()
        return start, end

    def get_filtered_transactions(self) -> pd.DataFrame:
        if self.df.empty:
            return self.df.copy()
        df = self.df.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        mode = self.txn_filter_dropdown.currentText()
        start, end = self.compute_date_window(mode)
        mask = (df['Date'] >= pd.Timestamp(start)) & (df['Date'] <= pd.Timestamp(end))
        return df.loc[mask].reset_index(drop=True)

    def sort_transactions_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        mode = self.txn_sort_mode
        df = df.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        key_lower = lambda s: s.astype(str).str.lower()

        if mode == "Date: Newest→Oldest":
            return df.sort_values('Date', ascending=False, na_position='last')
        if mode == "Date: Oldest→Newest":
            return df.sort_values('Date', ascending=True, na_position='last')
        if mode == "Amount: High→Low":
            return df.sort_values('Amount', ascending=False, na_position='last')
        if mode == "Amount: Low→High":
            return df.sort_values('Amount', ascending=True, na_position='last')
        if mode == "Category: A→Z":
            return df.sort_values('Category', ascending=True, na_position='last', key=key_lower)
        if mode == "Category: Z→A":
            return df.sort_values('Category', ascending=False, na_position='last', key=key_lower)
        if mode == "Vendor: A→Z":
            return df.sort_values('Vendor', ascending=True, na_position='last', key=key_lower)
        if mode == "Vendor: Z→A":
            return df.sort_values('Vendor', ascending=False, na_position='last', key=key_lower)
        if mode == "Account: A→Z":
            return df.sort_values('Account', ascending=True, na_position='last', key=key_lower)
        if mode == "Account: Z→A":
            return df.sort_values('Account', ascending=False, na_position='last', key=key_lower)
        return df

    def update_table(self):
        filtered_df = self.get_filtered_transactions()
        sorted_df = self.sort_transactions_df(filtered_df)

        # Display: Id, Date, Vendor, Amount, Type, Category, Account
        display_df = sorted_df.copy()
        if not display_df.empty:
            display_df['Date'] = pd.to_datetime(display_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')

        self.table.setRowCount(display_df.shape[0])
        self.table.setColumnCount(display_df.shape[1])
        self.table.setHorizontalHeaderLabels(display_df.columns)

        for r in range(display_df.shape[0]):
            for c in range(display_df.shape[1]):
                col = display_df.columns[c]
                val = display_df.iloc[r, c]
                if col == "Amount" and pd.notna(val):
                    item = QTableWidgetItem(fmt_money(val))
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item = QTableWidgetItem(str(val))
                self.table.setItem(r, c, item)

        # Hide Id from view but keep it in the model for selection mapping
        id_col = list(display_df.columns).index("Id") if "Id" in display_df.columns else -1
        if id_col >= 0:
            self.table.setColumnHidden(id_col, True)

        self.table.resizeColumnsToContents()

    def update_summary(self):
        filtered_df = self.get_filtered_transactions()
        if filtered_df.empty:
            self.summary_label.setText("No data.")
            return
        filtered_df['Category'] = filtered_df['Category'].astype(str).str.lower().str.capitalize()
        category_totals = filtered_df.groupby('Category')['Amount'].sum()
        lines = ["Total by Category:"]
        for cat, total in category_totals.items():
            lines.append(f"{cat}: {fmt_money(total)}")
        self.summary_label.setText("\n".join(lines))

    def _next_tx_id(self) -> str:
        if self.df.empty or self.df['Id'].isna().all():
            return "1"
        try:
            m = self.df['Id'].astype(int).max()
            return str(m + 1)
        except Exception:
            # fallback: use row count + 1
            return str(len(self.df) + 1)

    def _account_names(self):
        return [a["name"] for a in self.accounts] if self.accounts else ["Unassigned"]

    def add_transaction(self):
        dialog = AddTransactionDialog(self, account_names=self._account_names())
        while True:
            result = dialog.exec()
            if result == QDialog.Rejected:
                return
            new = dialog.getData()
            # Validate amount
            try:
                amount = float(new["Amount"])
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Amount must be a number.")
                continue
            t = new.get("Type", "Expense")
            amount = -abs(amount) if t == "Expense" else abs(amount)
            new["Amount"] = amount

            if not (new["Vendor"].strip() and new["Category"].strip()):
                QMessageBox.warning(self, "Input Error", "Vendor and Category cannot be empty.")
                continue
            new["Category"] = new["Category"].strip().lower().capitalize()
            if not new.get("Account"):
                new["Account"] = "Unassigned"
            break

        # Assign Id
        new_row = {
            "Id": self._next_tx_id(),
            "Date": new["Date"],
            "Vendor": new["Vendor"],
            "Amount": new["Amount"],
            "Type": new["Type"],
            "Category": new["Category"],
            "Account": new["Account"]
        }
        self.df.loc[len(self.df)] = new_row
        self.save_and_refresh()

    def _selected_row_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        # The table model has hidden Id column; find it and read value
        for c in range(self.table.columnCount()):
            header = self.table.horizontalHeaderItem(c).text()
            if header == "Id":
                item = self.table.item(row, c)
                return item.text() if item else None
        # fallback: try to compute from filtered view
        filtered_df = self.sort_transactions_df(self.get_filtered_transactions())
        if row < len(filtered_df) and "Id" in filtered_df.columns:
            return str(filtered_df.iloc[row]["Id"])
        return None

    def _edit_selected_transaction(self):
        row_id = self._selected_row_id()
        if not row_id:
            QMessageBox.warning(self, "No Selection", "Please select a transaction to edit.")
            return
        self._edit_transaction_by_id(row_id)

    def _delete_selected_transaction(self):
        row_id = self._selected_row_id()
        if not row_id:
            QMessageBox.warning(self, "No Selection", "Please select a transaction to delete.")
            return
        self._delete_transaction_by_id(row_id)

    def open_context_menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        menu = QMenu(self)
        a_edit = menu.addAction("Edit Transaction")
        a_del = menu.addAction("Delete Transaction")
        action = menu.exec(self.table.mapToGlobal(pos))
        # map selected row to Id
        row_id = self._selected_row_id()
        if action == a_edit and row_id:
            self._edit_transaction_by_id(row_id)
        elif action == a_del and row_id:
            self._delete_transaction_by_id(row_id)

    def _edit_transaction_by_id(self, row_id: str):
        matches = self.df.index[self.df['Id'].astype(str) == str(row_id)]
        if len(matches) == 0:
            QMessageBox.warning(self, "Not Found", "Original transaction row could not be located.")
            return
        i = int(matches[0])
        current_data = self.df.loc[i].to_dict()

        dialog = AddTransactionDialog(self, transaction=current_data, account_names=self._account_names())
        while True:
            result = dialog.exec()
            if result == QDialog.Rejected:
                return
            new = dialog.getData()
            try:
                amount = float(new["Amount"])
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Amount must be a number.")
                continue
            t = new.get("Type", "Expense")
            amount = -abs(amount) if t == "Expense" else abs(amount)
            if not (new["Vendor"].strip() and new["Category"].strip()):
                QMessageBox.warning(self, "Input Error", "Vendor and Category cannot be empty.")
                continue
            new_cat = new["Category"].strip().lower().capitalize()
            acct = new.get("Account") or "Unassigned"
            # Passed validation
            break

        self.df.at[i, 'Date'] = new['Date']
        self.df.at[i, 'Vendor'] = new['Vendor']
        self.df.at[i, 'Amount'] = amount
        self.df.at[i, 'Type'] = t
        self.df.at[i, 'Category'] = new_cat
        self.df.at[i, 'Account'] = acct
        self.save_and_refresh()

    def _delete_transaction_by_id(self, row_id: str):
        matches = self.df.index[self.df['Id'].astype(str) == str(row_id)]
        if len(matches) == 0:
            QMessageBox.warning(self, "Not Found", "Original transaction row could not be located.")
            return
        i = int(matches[0])
        reply = QMessageBox.question(self, "Delete", "Delete this transaction?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self.df = self.df.drop(i).reset_index(drop=True)
        self.save_and_refresh()

    def save_and_refresh(self):
        self.save_transactions()
        self.update_table()
        self.update_summary()
        # Immediate refresh for other tabs so changes are visible right away
        self.update_budgets_table()
        self.update_dashboard_tab()

    # ---------------- Budgets Tab ----------------
    def init_budgets_tab(self):
        layout = QVBoxLayout()

        self.budget_table = QTableWidget()
        self.budget_table.setColumnCount(4)
        self.budget_table.setHorizontalHeaderLabels(["Category", "Period", "Entered Amount", "Monthly Equivalent"])
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

    def _all_categories_for_budget(self):
        txn_cats = set(self.df['Category'].astype(str).str.lower().str.capitalize()) if not self.df.empty else set()
        budget_cats = set(self.budgets.keys())
        return sorted(txn_cats | budget_cats)

    def update_budgets_table(self):
        all_cats = self._all_categories_for_budget()
        today = self.get_today()

        self.budget_table.setRowCount(len(all_cats))
        for r, cat in enumerate(all_cats):
            self.budget_table.setItem(r, 0, QTableWidgetItem(cat))
            bdata = self.budgets.get(cat)
            if isinstance(bdata, dict):
                period = (bdata.get("period") or "monthly").capitalize()
                amount = bdata.get("amount", 0.0)
                monthly_eq = self.monthly_equivalent(float(amount), bdata.get("period", "monthly"), today)
                self.budget_table.setItem(r, 1, QTableWidgetItem(period))
                amt_item = QTableWidgetItem(fmt_money(amount))
                amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.budget_table.setItem(r, 2, amt_item)
                me_item = QTableWidgetItem(fmt_money(monthly_eq))
                me_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.budget_table.setItem(r, 3, me_item)
            else:
                self.budget_table.setItem(r, 1, QTableWidgetItem("—"))
                self.budget_table.setItem(r, 2, QTableWidgetItem("None"))
                self.budget_table.setItem(r, 3, QTableWidgetItem("—"))

        self.budget_table.resizeColumnsToContents()

    def add_edit_budget(self):
        all_cats = self._all_categories_for_budget()
        dialog = BudgetDialog(all_cats, self.budgets, self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.getData()
        cat = data["Category"].strip()
        if not cat:
            QMessageBox.warning(self, "Input Error", "Please choose a category.")
            return
        try:
            amt = float(data["Amount"])
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Budget amount must be a number.")
            return
        period = data["Period"].lower()
        self.budgets[cat] = {"amount": amt, "period": period}
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
            self.accounts_table.setItem(r, 1, QTableWidgetItem(fmt_money(acct["balance"])))
        self.accounts_table.resizeColumnsToContents()

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
        main_layout = QVBoxLayout()

        self.dashboard_balance_label = QLabel()
        main_layout.addWidget(self.dashboard_balance_label)

        grid = QGridLayout()

        # Budgets summary
        budgets_group = QGroupBox("Budgets Summary (Month-to-Date)")
        budgets_layout = QVBoxLayout()
        self.dashboard_budget_table = QTableWidget()
        self.dashboard_budget_table.setColumnCount(4)
        self.dashboard_budget_table.setHorizontalHeaderLabels(["Category", "Spent", "Budget (Monthly Eq.)", "Remaining"])
        budgets_layout.addWidget(self.dashboard_budget_table)
        budgets_group.setLayout(budgets_layout)
        grid.addWidget(budgets_group, 0, 0)

        # Recent transactions
        recent_group = QGroupBox("Recent Transactions")
        recent_layout = QVBoxLayout()
        self.dashboard_recent_table = QTableWidget()
        self.dashboard_recent_table.setColumnCount(4)
        self.dashboard_recent_table.setHorizontalHeaderLabels(["Date", "Vendor", "Amount", "Category"])
        recent_layout.addWidget(self.dashboard_recent_table)
        self.btn_view_all_tx = QPushButton("View All Transactions")
        self.btn_view_all_tx.clicked.connect(lambda: self.tabs.setCurrentWidget(self.trans_tab))
        recent_layout.addWidget(self.btn_view_all_tx)
        recent_group.setLayout(recent_layout)
        grid.addWidget(recent_group, 0, 1)

        # Spend by Account (MTD)
        acct_group = QGroupBox("MTD Spend by Account")
        acct_layout = QVBoxLayout()
        self.dashboard_spend_by_acct_table = QTableWidget()
        self.dashboard_spend_by_acct_table.setColumnCount(2)
        self.dashboard_spend_by_acct_table.setHorizontalHeaderLabels(["Account", "Spent"])
        acct_layout.addWidget(self.dashboard_spend_by_acct_table)
        acct_group.setLayout(acct_layout)
        grid.addWidget(acct_group, 1, 0, 1, 2)

        main_layout.addLayout(grid)
        self.dashboard_tab.setLayout(main_layout)

        self.update_dashboard_tab()

    def get_spend_by_category_month_to_date(self) -> dict[str, float]:
        if self.df.empty:
            return {}
        today = self.get_today()
        start = start_of_month(today)
        end = end_of_month(today)
        df = self.df.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df[(df['Date'] >= pd.Timestamp(start)) & (df['Date'] <= pd.Timestamp(end))]
        if df.empty:
            return {}
        df['Category'] = df['Category'].astype(str).str.lower().str.capitalize()
        spent = df.groupby('Category')['Amount'].apply(lambda x: abs(x[x < 0].sum())).to_dict()
        return spent

    def get_spend_by_account_month_to_date(self) -> dict[str, float]:
        if self.df.empty:
            return {}
        today = self.get_today()
        start = start_of_month(today)
        end = end_of_month(today)
        df = self.df.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df[(df['Date'] >= pd.Timestamp(start)) & (df['Date'] <= pd.Timestamp(end))]
        if df.empty:
            return {}
        df['Account'] = df['Account'].fillna("Unassigned")
        spent = df.groupby('Account')['Amount'].apply(lambda x: abs(x[x < 0].sum())).to_dict()
        return spent

    def get_recent_transactions(self, n=10) -> pd.DataFrame:
        if self.df.empty:
            return self.df.copy()
        df = self.df.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.sort_values('Date', ascending=False)
        return df.head(n).reset_index(drop=True)

    def get_total_balance(self) -> float:
        return sum(float(a["balance"]) for a in self.accounts) if self.accounts else 0.0

    def update_dashboard_tab(self):
        total = self.get_total_balance()
        eff_today = self.get_today().strftime("%Y-%m-%d")
        self.dashboard_balance_label.setText(
            f"Total Balance Across All Accounts: <b>{fmt_money(total)}</b> &nbsp;&nbsp; "
            f"<span style='color:gray;'>[Today: {eff_today}]</span>"
        )

        # Budgets summary using monthly equivalent vs MTD spend
        spent_by_cat = self.get_spend_by_category_month_to_date()
        all_categories = set(spent_by_cat.keys()) | set(self.budgets.keys())
        today = self.get_today()
        rows = []
        for cat in all_categories:
            spent = spent_by_cat.get(cat, 0.0)
            bdata = self.budgets.get(cat)
            if isinstance(bdata, dict):
                meq = self.monthly_equivalent(bdata.get("amount", 0.0), bdata.get("period", "monthly"), today)
            else:
                meq = None
            remaining = (meq - spent) if meq is not None else ""
            rows.append({"category": cat, "spent": spent, "budget_meq": meq, "remaining": remaining})
        rows.sort(key=lambda x: (0 if x['budget_meq'] is not None else 1, x['category']))

        self.dashboard_budget_table.setRowCount(len(rows))
        for r, data in enumerate(rows):
            self.dashboard_budget_table.setItem(r, 0, QTableWidgetItem(data["category"]))
            spent_item = QTableWidgetItem(fmt_money(data["spent"]))
            spent_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.dashboard_budget_table.setItem(r, 1, spent_item)

            if data["budget_meq"] is not None:
                me_item = QTableWidgetItem(fmt_money(data["budget_meq"]))
                me_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.dashboard_budget_table.setItem(r, 2, me_item)

                rem_val = data["remaining"]
                rem_item = QTableWidgetItem(fmt_money(rem_val))
                rem_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if rem_val < 0:
                    rem_item.setForeground(Qt.red)
                    rem_item.setText(f"Over by {fmt_money(-rem_val)}")
                else:
                    rem_item.setForeground(Qt.darkGreen)
                self.dashboard_budget_table.setItem(r, 3, rem_item)
            else:
                self.dashboard_budget_table.setItem(r, 2, QTableWidgetItem("No budget"))
                nb = QTableWidgetItem("No budget set")
                nb.setForeground(Qt.gray)
                self.dashboard_budget_table.setItem(r, 3, nb)

        self.dashboard_budget_table.resizeColumnsToContents()

        # Recent transactions
        recent = self.get_recent_transactions(n=10)
        if not recent.empty:
            recent_display = recent.copy()
            recent_display['Date'] = pd.to_datetime(recent_display['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        else:
            recent_display = recent
        self.dashboard_recent_table.setRowCount(recent_display.shape[0])
        self.dashboard_recent_table.setColumnCount(4)
        self.dashboard_recent_table.setHorizontalHeaderLabels(["Date", "Vendor", "Amount", "Category"])
        for r in range(recent_display.shape[0]):
            self.dashboard_recent_table.setItem(r, 0, QTableWidgetItem(str(recent_display.iloc[r]['Date'])))
            self.dashboard_recent_table.setItem(r, 1, QTableWidgetItem(str(recent_display.iloc[r]['Vendor'])))
            amt_item = QTableWidgetItem(fmt_money(recent_display.iloc[r]['Amount']))
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.dashboard_recent_table.setItem(r, 2, amt_item)
            self.dashboard_recent_table.setItem(r, 3, QTableWidgetItem(str(recent_display.iloc[r]['Category'])))
        self.dashboard_recent_table.resizeColumnsToContents()

        # Spend by Account (MTD)
        spend_acct = self.get_spend_by_account_month_to_date()
        accts = sorted(spend_acct.keys())
        self.dashboard_spend_by_acct_table.setRowCount(len(accts))
        for r, name in enumerate(accts):
            self.dashboard_spend_by_acct_table.setItem(r, 0, QTableWidgetItem(name))
            amt_item = QTableWidgetItem(fmt_money(spend_acct[name]))
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.dashboard_spend_by_acct_table.setItem(r, 1, amt_item)
        self.dashboard_spend_by_acct_table.resizeColumnsToContents()

    # ---------------- Settings Tab ----------------
    def init_settings_tab(self):
        layout = QVBoxLayout()

        self.settings_info = QLabel()
        layout.addWidget(self.settings_info)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Today (override):"))
        self.today_picker = QDateEdit()
        self.today_picker.setCalendarPopup(True)
        self.today_picker.setDisplayFormat("yyyy-MM-dd")
        eff_today = self.get_today()
        self.today_picker.setDate(QDate(eff_today.year, eff_today.month, eff_today.day))
        controls.addWidget(self.today_picker)

        self.btn_save_today = QPushButton("Save")
        self.btn_reset_today = QPushButton("Reset to System Date")
        controls.addWidget(self.btn_save_today)
        controls.addWidget(self.btn_reset_today)
        layout.addLayout(controls)

        self.settings_tab.setLayout(layout)

        self.btn_save_today.clicked.connect(self.on_save_today)
        self.btn_reset_today.clicked.connect(self.on_reset_today)

        self.update_settings_info()

    def update_settings_info(self):
        ov = self.settings.get("today_override")
        if ov:
            self.settings_info.setText(f"Effective Today: <b>{ov}</b> (Override)")
        else:
            sysd = datetime.date.today().strftime("%Y-%m-%d")
            self.settings_info.setText(f"Effective Today: <b>{sysd}</b> (System)")

    def on_save_today(self):
        d = self.today_picker.date().toPython()
        self.settings["today_override"] = d.strftime("%Y-%m-%d")
        self.save_json(SETTINGS_FILE, self.settings)
        self.update_settings_info()
        # Refresh everywhere that depends on date/time
        self.update_table()
        self.update_summary()
        self.update_budgets_table()
        self.update_dashboard_tab()
        QMessageBox.information(self, "Saved", "Today override saved.")

    def on_reset_today(self):
        self.settings["today_override"] = None
        self.save_json(SETTINGS_FILE, self.settings)
        sysd = datetime.date.today()
        self.today_picker.setDate(QDate(sysd.year, sysd.month, sysd.day))
        self.update_settings_info()
        self.update_table()
        self.update_summary()
        self.update_budgets_table()
        self.update_dashboard_tab()
        QMessageBox.information(self, "Reset", "Today override cleared. Using system date.")

    # ---------------- Tab change hook ----------------
    def on_tab_change(self, index):
        name = self.tabs.tabText(index)
        if name == "Budgets":
            self.update_budgets_table()
        elif name == "Accounts":
            self.update_accounts_table()
        elif name == "Dashboard":
            self.update_dashboard_tab()
        elif name == "Transactions":
            self.update_table()
            self.update_summary()


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
