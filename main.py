import sys
import os
import json
import datetime
import pandas as pd
from datetime import datetime as dt

from PySide6.QtWidgets import (
    QApplication, QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QMessageBox, QMenu,QMenuBar, QMessageBox,
    QTabWidget, QHBoxLayout, QComboBox, QDateEdit, QGroupBox, QGridLayout,
    QProgressBar, QCheckBox
)
from PySide6.QtCore import Qt, QDate

from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtWidgets import QAbstractItemView
from PySide6.QtWidgets import QHBoxLayout


# Matplotlib (for Reports & Dashboard charts)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ----------------------------
# File paths / constants
# ----------------------------
TRANSACTIONS_FILE = "sample_transactions.csv"
AUTOCAT_FILE = "autocategorize.json"   # Sprint 12: vendor→category memory
UNCATEGORIZED = "Uncategorized"        # used throughout (normalize blank categories)
BUDGET_FILE = "budgets.json"
ACCOUNTS_FILE = "accounts.json"
SETTINGS_FILE = "settings.json"
CATEGORIES_FILE = "categories.json"
UNCATEGORIZED = "Uncategorized"
NEW_CATEGORY_OPTION = "➕ New category…"

SYSTEM_CATEGORIES = {"Transfer"}

def is_system_category(name: str) -> bool:
    return str(name or "").strip().lower() in {n.lower() for n in SYSTEM_CATEGORIES}


# Dark theme colors
DARK_FIG = "#121212"
DARK_AX = "#121212"
LIGHT_TEXT = "#FFFFFF"
GRID_COLOR = "#2a2a2a"


# ----------------------------
# Helper functions (dates/currency)
# ----------------------------
def start_of_month(date: datetime.date) -> datetime.date:
    return date.replace(day=1)

def end_of_month(date: datetime.date) -> datetime.date:
    next_month = date.replace(day=28) + datetime.timedelta(days=4)
    return next_month - datetime.timedelta(days=next_month.day)

def fmt_money(value) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return str(value)

# --- Sprint 12: Auto-categorize helpers (must be defined BEFORE FinanceApp) ---
import re
from difflib import SequenceMatcher

_WORD_RE = re.compile(r"[a-z0-9]+")

def _normalize_vendor(s: str) -> str:
    if s is None:
        return ""
    s = str(s).lower()
    # collapse punctuation/whitespace to single spaces
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _vendor_tokens(s: str) -> list[str]:
    s = _normalize_vendor(s)
    return _WORD_RE.findall(s)

def _vendor_stem(s: str, n: int = 2) -> str:
    """First N tokens as a coarse vendor root; ex: 'petro canada xyz' -> 'petro canada'."""
    toks = _vendor_tokens(s)
    return " ".join(toks[:n]) if toks else ""

def _token_overlap(a: str, b: str) -> int:
    at = set(_vendor_tokens(a))
    bt = set(_vendor_tokens(b))
    return len(at & bt)

def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_vendor(a), _normalize_vendor(b)).ratio()
# --- end helpers ---


# ----------------------------
# Matplotlib canvas (dark theme)
# ----------------------------
class MplCanvas(FigureCanvas):
    def __init__(self, width=4, height=3, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        fig.set_facecolor(DARK_FIG)
        self.ax = fig.add_subplot(111)
        self.ax.set_facecolor(DARK_AX)
        self.ax.tick_params(colors=LIGHT_TEXT)
        self.ax.xaxis.label.set_color(LIGHT_TEXT)
        self.ax.yaxis.label.set_color(LIGHT_TEXT)
        self.ax.title.set_color(LIGHT_TEXT)
        super().__init__(fig)

    def set_dark(self):
        self.figure.set_facecolor(DARK_FIG)
        self.ax.set_facecolor(DARK_AX)
        self.ax.tick_params(colors=LIGHT_TEXT)
        self.ax.xaxis.label.set_color(LIGHT_TEXT)
        self.ax.yaxis.label.set_color(LIGHT_TEXT)
        self.ax.title.set_color(LIGHT_TEXT)


# ----------------------------
# Dialogs
# ----------------------------
class CategoryDialog(QDialog):
    """Add/Edit Category (name + type)."""
    def __init__(self, category=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Category" if category is None else "Edit Category")
        self.layout = QFormLayout(self)

        self.name_input = QLineEdit(self)
        self.type_dropdown = QComboBox(self)
        self.type_dropdown.addItems(["Expense", "Income"])

        self.layout.addRow("Category Name:", self.name_input)
        self.layout.addRow("Type:", self.type_dropdown)

        if category:
            self.name_input.setText(str(category["name"]))
            self.type_dropdown.setCurrentText(str(category["type"]).capitalize())

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def getData(self):
        return {
            "name": self.name_input.text().strip(),
            "type": self.type_dropdown.currentText()
        }


class ReassignDialog(QDialog):
    """Prompt to reassign a category to another one on delete."""
    def __init__(self, old_category, choices, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Reassign '{old_category}' to...")
        self.layout = QFormLayout(self)

        self.choice = QComboBox(self)
        self.choice.addItems(sorted(choices))
        self.layout.addRow("Move to Category:", self.choice)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def getSelection(self):
        return self.choice.currentText()


class AddTransactionDialog(QDialog):
    """
    Add/Edit Transaction.
    - Date: QDateEdit (calendar)
    - Type: Expense/Income
    - Category: dropdown from list + "New category…" to add on the fly
    - Account: dropdown
    """
    def __init__(self, parent=None, transaction=None, account_names=None, category_names=None):
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

        # Category dropdown (managed list + new)
        self.category_dropdown = QComboBox(self)
        category_names = category_names or [UNCATEGORIZED]
        names = list(category_names)
        if UNCATEGORIZED not in names:
            names = [UNCATEGORIZED] + names
        if NEW_CATEGORY_OPTION not in names:
            names = names + [NEW_CATEGORY_OPTION]
        names = [n for n in names if not is_system_category(n)]
        self.category_dropdown.addItems(sorted([n for n in names if n not in [NEW_CATEGORY_OPTION, UNCATEGORIZED]])
                                       + [UNCATEGORIZED, NEW_CATEGORY_OPTION])

        # Account dropdown
        self.account_dropdown = QComboBox(self)
        account_names = account_names or []
        if "Unassigned" not in account_names:
            account_names = ["Unassigned"] + list(account_names)
        self.account_dropdown.addItems(account_names)

        self.layout.addRow("Date:", self.date_input)
        self.layout.addRow("Vendor:", self.vendor_input)
        self.layout.addRow("Amount:", self.amount_input)
        self.layout.addRow("Type:", self.type_dropdown)
        self.layout.addRow("Category:", self.category_dropdown)
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
            t = transaction.get("Type", "Expense")
            if t not in ["Expense", "Income"]:
                t = "Expense" if float(transaction.get("Amount", 0)) < 0 else "Income"
            self.type_dropdown.setCurrentText(t)
            # Category
            cat = str(transaction.get("Category", UNCATEGORIZED)) or UNCATEGORIZED
            idxc = self.category_dropdown.findText(cat)
            if idxc >= 0:
                self.category_dropdown.setCurrentIndex(idxc)
            # Account
            acct = str(transaction.get("Account", "Unassigned")) or "Unassigned"
            idxa = self.account_dropdown.findText(acct)
            if idxa >= 0:
                self.account_dropdown.setCurrentIndex(idxa)
        else:
            today = datetime.date.today()
            self.date_input.setDate(QDate(today.year, today.month, today.day))

        # Hook "New category…" behavior
        self.category_dropdown.currentTextChanged.connect(self._maybe_add_new_category)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def _maybe_add_new_category(self, text):
        if text == NEW_CATEGORY_OPTION:
            # Launch create-category dialog
            dlg = CategoryDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                data = dlg.getData()
                name = data["name"]
                ctype = data["type"]
                if not name:
                    QMessageBox.warning(self, "Input Error", "Category name cannot be empty.")
                    # reset selection
                    self._reset_category_selection()
                    return
                # Ask parent (FinanceApp) to persist and refresh master list
                app = self.parent()
                if hasattr(app, "add_category_programmatically"):
                    ok = app.add_category_programmatically(name, ctype)
                    if not ok:
                        QMessageBox.warning(self, "Exists", f"Category '{name}' already exists.")
                        self._reset_category_selection()
                        return
                    # Refresh dropdown options (append before special items)
                    items = [self.category_dropdown.itemText(i) for i in range(self.category_dropdown.count())]
                    base = [it for it in items if it not in [NEW_CATEGORY_OPTION]]
                    if name not in base:
                        base.insert(0, name)
                    # rebuild list: sorted (except keep special items order)
                    base = sorted([b for b in base if b not in [UNCATEGORIZED, NEW_CATEGORY_OPTION]])
                    self.category_dropdown.clear()
                    for b in base:
                        self.category_dropdown.addItem(b)
                    self.category_dropdown.addItem(UNCATEGORIZED)
                    self.category_dropdown.addItem(NEW_CATEGORY_OPTION)
                    # select new category
                    idx = self.category_dropdown.findText(name)
                    if idx >= 0:
                        self.category_dropdown.setCurrentIndex(idx)
                else:
                    self._reset_category_selection()
            else:
                self._reset_category_selection()

    def _reset_category_selection(self):
        # pick UNCATEGORIZED as safe default
        idx = self.category_dropdown.findText(UNCATEGORIZED)
        if idx >= 0:
            self.category_dropdown.setCurrentIndex(idx)

    def getData(self):
        date_py = self.date_input.date().toPython()
        return {
            "Date": date_py.strftime("%Y-%m-%d"),
            "Vendor": self.vendor_input.text(),
            "Amount": self.amount_input.text(),
            "Type": self.type_dropdown.currentText(),
            "Category": self.category_dropdown.currentText(),
            "Account": self.account_dropdown.currentText()
        }


class BudgetDialog(QDialog):
    """
    Add/Edit a budget for a category.
    Period: Monthly/Weekly/Daily
    Only Expense categories are shown.
    """
    def __init__(self, categories_expense, budgets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set/Edit Budget")
        self.budgets = budgets  # {cat: {"amount": float, "period": "daily|weekly|monthly"}}
        self.layout = QFormLayout(self)

        self.category_dropdown = QComboBox(self)
        cats = categories_expense or [UNCATEGORIZED]
        # Drop system categories like Transfer
        cats = [c for c in cats if not is_system_category(c)]
        if UNCATEGORIZED not in cats:
            cats = [UNCATEGORIZED] + list(cats)
        self.category_dropdown.addItems(sorted(cats))


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
import re
from difflib import SequenceMatcher
import os, json

def _normalize_vendor(s: str) -> str:
    if s is None:
        return ""
    s = str(s).lower()
    # collapse punctuation and whitespace
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

# --- Seed loaders/mergers for external JSON files (Sprint 13) ---
def _read_json_file(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _merge_seed_categories_from_file(existing: list[dict], seed_path: str) -> list[dict]:
    seed = _read_json_file(seed_path, {"categories": []})
    seed_list = seed.get("categories", []) or []
    existing = existing or []
    have = {str(c.get("name","")).strip().lower() for c in existing}
    out = existing[:]
    for c in seed_list:
        nm = str(c.get("name","")).strip()
        if nm and nm.lower() not in have:
            out.append({"name": nm})
            have.add(nm.lower())
    return out

def _merge_seed_autocat_from_file(existing: dict, seed_path: str) -> dict:
    seed = _read_json_file(seed_path, {"vendors": {}})
    vendors = seed.get("vendors", {}) or {}
    out = dict(existing or {})
    for k, v in vendors.items():
        if k not in out:
            out[k] = v  # seed as string; runtime upgrades to counters after confirmations
    return out

def _project_path(*parts: str) -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)

    

class FinanceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Finance Tool")
        self.setGeometry(80, 80, 1300, 900)

        # Root layout for the whole window (QWidget doesn't have .menuBar())
        self.layout = QVBoxLayout(self)

        # ------- Load Data -------
        self.df = self.load_transactions()
        self.repair_transaction_ids(save=True)
        self.budgets = self.migrate_budgets(self.load_json(BUDGET_FILE, default={}))
        self.accounts = self.ensure_accounts_fields(self.load_json(ACCOUNTS_FILE, default=[]))
        self.settings = self.load_json(SETTINGS_FILE, default={"today_override": None})
        
        # Sprint 12: load vendor→category memory and defaults
        self.autocat = self.load_json(AUTOCAT_FILE, default={})
        # Default settings for auto-categorization
        if "auto_categorize_enabled" not in self.settings:
            self.settings["auto_categorize_enabled"] = True
        if "auto_categorize_threshold" not in self.settings:
            self.settings["auto_categorize_threshold"] = 0.70
        # persist defaults if we added them
        self.save_json(SETTINGS_FILE, self.settings)

        self.categories = self.ensure_categories(self.load_json(CATEGORIES_FILE, default=[]))
        # Seed/merge categories from seeds/categories_seed.json (idempotent)
        try:
            seed_path = _project_path("seeds", "categories_seed.json")
            merged = _merge_seed_categories_from_file(self.categories, seed_path)
            if merged != self.categories:
                self.categories = merged
                self.save_json(CATEGORIES_FILE, self.categories)
        except Exception:
            pass

        # Seed/merge Ontario/SW-ON vendor map from seeds/autocategorize_seed_on_ca.json (idempotent)
        try:
            seed_path = _project_path("seeds", "autocategorize_seed_on_ca.json")
            merged = _merge_seed_autocat_from_file(self.autocat, seed_path)
            if merged != self.autocat:
                self.autocat = merged
                self.save_json(AUTOCAT_FILE, self.autocat)
        except Exception:
            pass



        # Dashboard local filter state
        self.dashboard_filter_mode = "This Month"
        self.dashboard_from_date = None
        self.dashboard_to_date = None

        # === Menu Bar for QWidget ===
        self.menubar = QMenuBar(self)
        file_menu = self.menubar.addMenu("&File")

        # Import option 🚀
        act_import = file_menu.addAction("Import Transactions…")
        act_import.triggered.connect(self.open_import_wizard)

        file_menu.addSeparator()
        act_exit = file_menu.addAction("Exit")
        act_exit.triggered.connect(self.close)

        # Attach the menubar to the top of the QWidget via its layout
        self.layout.setMenuBar(self.menubar)

        # ------- Tabs (Dashboard first) -------
        self.tabs = QTabWidget()
        
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

        # Categories
        self.categories_tab = QWidget()
        self.tabs.addTab(self.categories_tab, "Categories")
        self.init_categories_tab()

        # Reports
        self.reports_tab = QWidget()
        self.tabs.addTab(self.reports_tab, "Reports")
        self.init_reports_tab()

        # Settings
        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "Settings")
        self.init_settings_tab()
        
        # --- Faux sidebar with horizontal labels (build AFTER all tabs exist) ---
        self.sidebar = QListWidget()
        self.sidebar.setSelectionMode(QAbstractItemView.SingleSelection)
        self.sidebar.setUniformItemSizes(True)
        self.sidebar.setSpacing(4)
        self.sidebar.setFixedWidth(180)

        # Mirror current tab labels into the sidebar
        self.sidebar.clear()
        for i in range(self.tabs.count()):
            item = QListWidgetItem(self.tabs.tabText(i))
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.sidebar.addItem(item)

        # Keep sidebar and tabs in sync
        def _side_to_tab(row):
            if 0 <= row < self.tabs.count():
                self.tabs.setCurrentIndex(row)

        def _tab_to_side(idx):
            if 0 <= idx < self.sidebar.count():
                self.sidebar.setCurrentRow(idx)

        self.sidebar.currentRowChanged.connect(_side_to_tab)
        self.tabs.currentChanged.connect(_tab_to_side)

        # Hide the real tab bar (we’ll click in the sidebar instead)
        self.tabs.setTabPosition(QTabWidget.North)  # position irrelevant once hidden
        self.tabs.tabBar().show()  # show first to avoid Qt quirks
        self.tabs.tabBar().hide()

        # Container for sidebar + tabs
        self._center_container = QWidget()
        _center_layout = QHBoxLayout(self._center_container)
        _center_layout.setContentsMargins(0, 0, 0, 0)
        _center_layout.setSpacing(0)
        _center_layout.addWidget(self.sidebar)
        _center_layout.addWidget(self.tabs, 1)

        # Ensure something is selected
        if self.tabs.count() > 0:
            self.tabs.setCurrentIndex(0)
            self.sidebar.setCurrentRow(0)

        self.sidebar.setStyleSheet("""
        QListWidget {
        border: 0;
        background: transparent;
        }
        QListWidget::item {
        padding: 10px 12px;
        margin: 2px 6px;
        border-radius: 8px;
        }
        QListWidget::item:selected {
        background: #2a2f36;
        color: #ffffff;
        font-weight: 600;
        }
        QListWidget::item:hover {
        background: rgba(42,47,54,0.5);
        }
        """)

        # Show the container that holds sidebar + tabs
        self.layout.addWidget(self._center_container)

        self.tabs.currentChanged.connect(self.on_tab_change)

    # Import wizard call
    def open_import_wizard(self):
        try:
            from import_wizard import ImportWizard
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Could not load import wizard:\n{e}")
            return

        dlg = ImportWizard(self)
        dlg.exec()  # Import wizard appends to CSV on "Commit"

        # After dialog closes, reload from disk, repair Ids, and refresh UI
        try:
            self.df = self.load_transactions()
            self.repair_transaction_ids(save=True)
            self.update_table()
            self.update_summary()
            self.update_budgets_table()
            self.update_dashboard_tab()
            self.refresh_reports()
        except Exception as e:
            QMessageBox.warning(self, "Import", f"Imported, but refresh encountered an issue:\n{e}")


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

    def ensure_categories(self, raw_list):
        """
        Normalize categories to list of {"name": str, "type": "Expense|Income"}.
        Ensure 'Uncategorized' exists (Expense).
        """
        norm = []
        seen = set()
        if isinstance(raw_list, list):
            for it in raw_list:
                if isinstance(it, dict) and "name" in it:
                    name = str(it["name"]).strip()
                    if not name:
                        continue
                    ctype = str(it.get("type", "Expense")).capitalize()
                    if ctype not in ["Expense", "Income"]:
                        ctype = "Expense"
                    key = name.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    norm.append({"name": name, "type": ctype})
        # Ensure UNCATEGORIZED
        if UNCATEGORIZED.lower() not in [c["name"].lower() for c in norm]:
            norm.insert(0, {"name": UNCATEGORIZED, "type": "Expense"})
        # Save normalized if changed
        if norm != raw_list:
            self.save_json(CATEGORIES_FILE, norm)
        return norm

    def get_category_names(self):
        return [c["name"] for c in self.categories]

    def get_category_names_by_type(self, ctype):
        return [c["name"] for c in self.categories if c["type"].lower() == ctype.lower()]

    def add_category_programmatically(self, name: str, ctype: str) -> bool:
        """Add category from transaction dialog; return False if exists."""
        if name.lower() in [c["name"].lower() for c in self.categories]:
            return False
        self.categories.append({"name": name, "type": ctype})
        self.save_json(CATEGORIES_FILE, self.categories)
        self.update_categories_table()
        return True

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

    def ensure_accounts_fields(self, raw):
        """
        Ensure each account has name, balance (float), and starting_balance (float).
        If starting_balance missing, set starting_balance = balance.
        """
        if not isinstance(raw, list):
            return []
        changed = False
        for acct in raw:
            if "balance" in acct:
                try:
                    acct["balance"] = float(acct["balance"])
                except Exception:
                    acct["balance"] = 0.0
            else:
                acct["balance"] = 0.0
                changed = True
            if "name" not in acct:
                acct["name"] = "Unnamed"
                changed = True
            if "starting_balance" not in acct:
                acct["starting_balance"] = acct["balance"]
                changed = True
        if changed:
            self.save_json(ACCOUNTS_FILE, raw)
        return raw

    def load_transactions(self) -> pd.DataFrame:
        cols = ['Id', 'Date', 'Vendor', 'Amount', 'Type', 'Category', 'Account',
            'AppliedToBalance', 'ExternalId', 'TransferGroup', 'CategorySource']

        try:
            df = pd.read_csv(TRANSACTIONS_FILE, dtype=str)

        except FileNotFoundError:
            df = pd.DataFrame(columns=cols)

        # Ensure columns exist
        for c in cols:
            if c not in df.columns:
                if c == 'Id':
                    continue
                if c == 'AppliedToBalance':
                    df[c] = "False"
                elif c == 'Amount':
                    df[c] = "0"
                else:
                    df[c] = ""
        # Id column
        if "Id" not in df.columns or df["Id"].isna().all():
            df["Id"] = ""
            next_id = 1
            for i in df.index:
                df.at[i, "Id"] = str(next_id)
                next_id += 1



        # Dtypes and defaults
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
            # Category default
            if "Category" in df.columns:
                df['Category'] = df['Category'].replace("", UNCATEGORIZED)
            else:
                df['Category'] = UNCATEGORIZED
            # AppliedToBalance -> bool
            df['AppliedToBalance'] = df['AppliedToBalance'].astype(str).str.strip().str.lower().isin(["true", "1", "yes"])
        else:
            df = pd.DataFrame(columns=cols)
        
        # Default empty categories to 'Uncategorized'
        if "Category" in df.columns:
            df['Category'] = df['Category'].fillna("").replace("", UNCATEGORIZED)
        else:
            df['Category'] = UNCATEGORIZED

        # Ensure CategorySource exists
        if "CategorySource" not in df.columns:
            df["CategorySource"] = ""

        df = df[['Id', 'Date', 'Vendor', 'Amount', 'Type', 'Category', 'Account',
         'AppliedToBalance', 'ExternalId', 'TransferGroup']]

        return df

    def save_transactions(self):
        cols = ['Id', 'Date', 'Vendor', 'Amount', 'Type', 'Category', 'Account',
            'AppliedToBalance', 'ExternalId', 'TransferGroup', 'CategorySource']

        for c in cols:
            if c not in self.df.columns:
                self.df[c] = ""
        # Cast AppliedToBalance to string for CSV
        df_out = self.df.copy()
        df_out['AppliedToBalance'] = df_out['AppliedToBalance'].map(lambda x: "True" if bool(x) else "False")
        df_out[cols].to_csv(TRANSACTIONS_FILE, index=False)

        # -------- Sprint 12: Auto-categorize engine --------
    def _autocat_suggest(self, raw_vendor: str) -> str | None:
        if not raw_vendor or not self.settings.get("auto_categorize_enabled", True):
            return None

        thr = float(self.settings.get("auto_categorize_threshold", 0.65))
        v_full = _normalize_vendor(raw_vendor)
        v_stem = _vendor_stem(raw_vendor)
        if not v_full or not self.autocat:
            return None

        def _best_cat_from_counter(counter):
            if isinstance(counter, str):
                return counter
            if not isinstance(counter, dict) or not counter:
                return None
            # pick the category with the highest count
            return max(counter.items(), key=lambda kv: kv[1])[0]

        # 1) exact full
        if v_full in self.autocat:
            return _best_cat_from_counter(self.autocat[v_full])
        # 2) exact stem
        if v_stem and v_stem in self.autocat:
            return _best_cat_from_counter(self.autocat[v_stem])

        # Build candidate list with weights
        candidates = {}  # cat -> weight
        for k, counter in self.autocat.items():
            cat = _best_cat_from_counter(counter)
            if not cat:
                continue

            # contains/prefix both ways
            if v_full.startswith(k) or k in v_full or k.startswith(v_full) or v_full in k:
                candidates[cat] = candidates.get(cat, 0) + 3  # strong signal
                continue

            # token overlap
            ov = _token_overlap(v_full, k)
            if ov >= 2:
                candidates[cat] = candidates.get(cat, 0) + 2
                continue

            # fuzzy
            score = _sim(v_full, k)
            if score >= thr:
                # weight by similarity
                candidates[cat] = candidates.get(cat, 0) + score

        if not candidates:
            return None
        # pick category with max weight
        return max(candidates.items(), key=lambda kv: kv[1])[0]


        thr = float(self.settings.get("auto_categorize_threshold", 0.70))
        v = _normalize_vendor(raw_vendor)
        if not v or not self.autocat:
            return None

        # 1) exact
        if v in self.autocat:
            return self.autocat.get(v)

        # 2) prefix/contains
        for k, cat in self.autocat.items():
            if v.startswith(k) or k in v:
                return cat

        # 3) fuzzy
        best_cat = None
        best = 0.0
        for k, cat in self.autocat.items():
            score = _sim(v, k)
            if score > best:
                best = score
                best_cat = cat
        return best_cat if best >= thr else None

    def _autocat_update_memory(self, raw_vendor: str, category: str):
        """Record a manual decision into memory using counters for full & stem keys."""
        v_full = _normalize_vendor(raw_vendor)
        v_stem = _vendor_stem(raw_vendor)
        if not category or category == UNCATEGORIZED:
            return

        def _bump(key: str):
            if not key:
                return
            cur = self.autocat.get(key)
            if isinstance(cur, str):  # migrate old format "key": "Category"
                cur = {cur: 1}
            if not isinstance(cur, dict):
                cur = {}
            cur[category] = int(cur.get(category, 0)) + 1
            self.autocat[key] = cur

        _bump(v_full)
        if v_stem and v_stem != v_full:
            _bump(v_stem)

        try:
            self.save_json(AUTOCAT_FILE, self.autocat)
        except Exception:
            pass


    def _autocat_apply_to_uncategorized(self) -> int:
        """
        Auto-categorize all rows where Category is empty/Uncategorized.
        Returns number of rows updated.
        """
        if self.df.empty:
            return 0
        changed = 0
        for i, row in self.df.iterrows():
            cat = str(row.get("Category", "") or "").strip()
            if cat and cat.lower() != "uncategorized":
                continue
            vendor = row.get("Vendor", "")
            sugg = self._autocat_suggest(vendor)
            if sugg:
                self.df.at[i, "Category"] = sugg
                # mark provenance
                if "CategorySource" not in self.df.columns:
                    self.df["CategorySource"] = ""
                self.df.at[i, "CategorySource"] = "Auto"
                changed += 1
        return changed

    def _autocat_backfill_after_manual(self, raw_vendor: str, category: str) -> int:
        """
        After a manual assignment, backfill past uncategorized matches.
        """
        self._autocat_update_memory(raw_vendor, category)
        return self._autocat_apply_to_uncategorized()
    
    def _autocat_migrate_auto_rows(self, raw_vendor: str, target_category: str, min_confirmations: int = 2) -> int:
        """
        If we have >= min_confirmations for target_category on this vendor,
        migrate *AUTO* rows that match (by our matching rules) to the new category.
        """
        # Check confirmations on keys (full + stem)
        v_full = _normalize_vendor(raw_vendor)
        v_stem = _vendor_stem(raw_vendor)

        def _count_for(key):
            cur = self.autocat.get(key)
            if isinstance(cur, dict):
                return int(cur.get(target_category, 0))
            if isinstance(cur, str):
                return 1 if cur == target_category else 0
            return 0

        conf = _count_for(v_full) + (0 if v_stem == v_full else _count_for(v_stem))
        if conf < min_confirmations:
            return 0

        # Migrate AUTO rows only
        changed = 0
        for i, row in self.df.iterrows():
            # Only touch uncategorized or auto rows (don't touch Manual)
            src = str(row.get("CategorySource", "") or "")
            if src.lower() == "manual":
                continue

            vendor = row.get("Vendor", "")
            # Reuse our suggestor to determine if this row matches the same vendor family
            sugg = self._autocat_suggest(vendor)
            if sugg == target_category:
                if str(row.get("Category", "")) != target_category:
                    self.df.at[i, "Category"] = target_category
                    self.df.at[i, "CategorySource"] = "Auto"
                    changed += 1

        return changed


    def repair_transaction_ids(self, save: bool = False):
        """
        Ensure every row in self.df has a unique, non-empty Id (as string).
        Assigns incrementing Ids for any blank/NaN/duplicate Ids.
        """
        if self.df.empty:
            return

        # Normalize to string and strip
        if "Id" not in self.df.columns:
            self.df["Id"] = ""

        ids = self.df["Id"].astype(str).fillna("").str.strip()

        # Find next numeric seed
        numeric_ids = pd.to_numeric(ids, errors="coerce").dropna()
        next_id = (int(numeric_ids.max()) + 1) if not numeric_ids.empty else 1

        # Track seen Ids to avoid duplicates
        seen = set()
        new_ids = []
        for raw in ids.tolist():
            if raw == "" or raw in seen:
                new_ids.append(str(next_id))
                seen.add(str(next_id))
                next_id += 1
            else:
                new_ids.append(raw)
                seen.add(raw)

        self.df["Id"] = new_ids

        if save:
            self.save_transactions()


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
        dim = (end_of_month(today) - start_of_month(today)).days + 1
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
        # Make selection operate on full rows (so Edit/Delete can find the right Id)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)

        layout.addWidget(self.table)

        # ---- Buttons row
        btn_row = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        self.clear_tx_button = QPushButton("Clear All")  # NEW Sprint 6
        self.mark_transfer_button = QPushButton("Mark Transfer") # Sprint 10
        self.run_autocat_button = QPushButton("Auto-Categorize Now")  # Sprint 12 test button
        # respect settings default visibility
        try:
            self.run_autocat_button.setVisible(bool(self.settings.get("show_autocat_button", False)))
        except Exception:
            pass

        # >>> Dedicated Import button Sprint 14<<<
        self.import_button = QPushButton("Import Transactions…")  
        btn_row.addWidget(self.import_button)                      

        btn_row.addWidget(self.add_button)
        btn_row.addWidget(self.edit_button)
        btn_row.addWidget(self.delete_button)
        btn_row.addSpacing(12)
        btn_row.addWidget(self.clear_tx_button)  # NEW
        btn_row.addSpacing(8)
        btn_row.addWidget(self.mark_transfer_button)  # NEW sprint 10
        btn_row.addStretch()
        btn_row.addWidget(self.run_autocat_button)  # Sprint 12 test button

        layout.addLayout(btn_row)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)
        self.summary_label.hide()  # hide the bottom summary on Transactions per Sprint 11

        # Wire events
        self.txn_filter_dropdown.currentTextChanged.connect(self.on_txn_filter_changed)
        self.txn_filter_from_picker.dateChanged.connect(self.on_txn_filter_changed)
        self.txn_filter_to_picker.dateChanged.connect(self.on_txn_filter_changed)
        self.txn_sort_dropdown.currentTextChanged.connect(self.on_txn_sort_changed)

        self.import_button.clicked.connect(self.open_import_wizard)      # Sprint 14
        self.add_button.clicked.connect(self.add_transaction)
        self.edit_button.clicked.connect(self._edit_selected_transaction)
        self.delete_button.clicked.connect(self._delete_selected_transaction)
        self.clear_tx_button.clicked.connect(self.clear_all_transactions)
        self.mark_transfer_button.clicked.connect(self._mark_selected_as_transfer) # Sprint 10
        self.run_autocat_button.clicked.connect(self._run_autocat_now) # Sprint 12


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
            # inclusive end = today for Tx view
            end = today
        elif mode == "Last Month":
            first_this_month = start_of_month(today)
            last_month_end = first_this_month - datetime.timedelta(days=1)
            start = start_of_month(last_month_end)
            end = last_month_end
        elif mode == "Last 30 Days":
            end = today
            start = today - datetime.timedelta(days=29)
        elif mode == "Last 7 Days":
            end = today
            start = today - datetime.timedelta(days=6)
        elif mode == "This Year":
            start = today.replace(month=1, day=1)
            end = today
        elif mode == "Custom Range":
            start = self.txn_filter_from_picker.date().toPython()
            end = self.txn_filter_to_picker.date().toPython()
        else:
            # default: full span
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
                    # Sprint 12: if this is the Category column and source is Auto, italicize + tooltip
                    if col == "Category":
                        try:
                            # Use the underlying sorted_df to read CategorySource for this row
                            src = str(sorted_df.iloc[r].get("CategorySource", "") or "")
                            if src.lower() == "auto":
                                font = item.font()
                                font.setItalic(True)
                                item.setFont(font)
                                item.setToolTip("Auto-categorized")
                        except Exception:
                            pass
                self.table.setItem(r, c, item)

        # Hide Id column
        if "Id" in display_df.columns:
            id_col = list(display_df.columns).index("Id")
            self.table.setColumnHidden(id_col, True)

        self.table.resizeColumnsToContents()
        # Sprint 11: hide advanced columns unless turned on in Settings
        self._apply_advanced_cols_visibility()

    def _apply_advanced_cols_visibility(self):
        # read setting (default False)
        show = False
        try:
            show = bool(self.settings.get("show_advanced_columns", False))
        except Exception:
            pass

        # Map header -> index from the live table
        header_to_idx = {}
        try:
            for c in range(self.table.columnCount()):
                header = self.table.horizontalHeaderItem(c).text()
                header_to_idx[header] = c
        except Exception:
            return

        for name in ["AppliedToBalance", "ExternalId", "TransferGroup", "CategorySource"]:
            if name in header_to_idx:
                self.table.setColumnHidden(header_to_idx[name], not show)


    def update_summary(self):
        filtered_df = self.get_filtered_transactions()
        # Exclude Transfers from category totals
        filtered_df = filtered_df[filtered_df['Type'] != 'Transfer']

        if filtered_df.empty:
            self.summary_label.setText("No data.")
            return
        filtered_df['Category'] = filtered_df['Category'].astype(str).str.lower().str.capitalize()
        category_totals = filtered_df.groupby('Category')['Amount'].sum()
        lines = ["Total by Category:"]
        for cat, total in category_totals.items():
            lines.append(f"{cat}: {fmt_money(total)}")
        self.summary_label.setText("\n".join(lines))

    def _next_tx_id(self):
        if self.df.empty or "Id" not in self.df.columns:
            return 1
        ids = pd.to_numeric(self.df["Id"], errors="coerce").dropna()
        return int(ids.max()) + 1 if not ids.empty else 1


    def _account_names(self):
        return [a["name"] for a in self.accounts] if self.accounts else ["Unassigned"]

    def add_transaction(self):
        dialog = AddTransactionDialog(
            self,
            account_names=self._account_names(),
            category_names=self.get_category_names()
        )
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

            if not new["Vendor"].strip():
                QMessageBox.warning(self, "Input Error", "Vendor cannot be empty.")
                continue
            if new["Category"] not in self.get_category_names():
                QMessageBox.warning(self, "Input Error", "Category must be chosen from the Categories tab or created via 'New category…'.")
                continue
            if not new.get("Account"):
                new["Account"] = "Unassigned"
            break

        new_row = {
            "Id": self._next_tx_id(),
            "Date": new["Date"],
            "Vendor": new["Vendor"],
            "Amount": new["Amount"],
            "Type": new["Type"],
            "Category": new["Category"],
            "Account": new["Account"],
            "AppliedToBalance": False,
            "ExternalId": "",
            "TransferGroup": "",
            "CategorySource": "Manual"
        }

        self.df.loc[len(self.df)] = new_row
        self.save_and_refresh()
    
    def refresh_all(self):
        # Sprint 12: apply auto-categorization to any uncategorized rows
        try:
            changed = self._autocat_apply_to_uncategorized()
            if changed:
                # Persist silently; UI refresh follows below
                self.save_transactions()
        except Exception:
            pass

        """UI refresh hook used by the import wizard."""
        # Do NOT save here; just refresh views from current in-memory data.
        self.update_table()
        self.update_summary()
        self.update_budgets_table()
        self.update_accounts_table()
        self.update_categories_table()
        self.update_dashboard_tab()
        self.refresh_reports()


    def _selected_row_id(self) -> str | None:
        """
        Returns the Id (as a string) for the currently selected row in the Transactions table.
        First, try to read the hidden 'Id' column directly; if not found, fall back to
        mapping the selected row index back to the filtered+sorted DataFrame.
        """
        row = self.table.currentRow()
        if row < 0:
            return None

        # Preferred: read hidden Id column directly
        for c in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(c)
            if header_item and header_item.text() == "Id":
                item = self.table.item(row, c)
                if item and item.text():
                    return item.text()
                break

        # Fallback: map row -> filtered+sorted df and read its Id
        filtered_df = self.sort_transactions_df(self.get_filtered_transactions())
        if 0 <= row < len(filtered_df) and "Id" in filtered_df.columns:
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
        a_tx = menu.addAction("Mark as Transfer (select two rows)")  # NEW Sprint 10
        action = menu.exec(self.table.mapToGlobal(pos))
        row_id = self._selected_row_id()
        if action == a_edit and row_id:
            self._edit_transaction_by_id(row_id)
        elif action == a_del and row_id:
            self._delete_transaction_by_id(row_id)
        elif action == a_tx:
            self._mark_selected_as_transfer()  # NEW sprint 10

    def _run_autocat_now(self):
        """Manually trigger auto-categorization/backfill over uncategorized rows."""
        try:
            if not self.settings.get("auto_categorize_enabled", True):
                QMessageBox.information(self, "Auto-Categorize", "Auto-categorization is disabled in Settings.")
                return
            changed = self._autocat_apply_to_uncategorized()
            if changed:
                self.save_transactions()
                self.update_table()
                self.update_summary()
                QMessageBox.information(self, "Auto-Categorize", f"Auto-categorized {changed} transaction(s).")
            else:
                QMessageBox.information(self, "Auto-Categorize", "No uncategorized matches found.")
        except Exception as e:
            QMessageBox.warning(self, "Auto-Categorize", f"Could not complete auto-categorization:\n{e}")

    def _mark_selected_as_transfer(self):
        # Gather exactly two selected rows
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if len(rows) != 2:
            QMessageBox.warning(self, "Mark Transfer", "Please select exactly two rows to mark as a transfer.")
            return

        # Helper: read a display row into fields by column name
        display_df = self.sort_transactions_df(self.get_filtered_transactions())
        def row_to_obj(r):
            # Map visible row -> original Id (your table shows all columns, so we can map by position)
            row_id = str(display_df.iloc[r]["Id"])
            amt = float(display_df.iloc[r]["Amount"])
            return {
                "Id": row_id,
                "Date": str(display_df.iloc[r]["Date"]),
                "Vendor": str(display_df.iloc[r]["Vendor"]),
                "Amount": amt,
                "Type": str(display_df.iloc[r]["Type"]),
                "Category": str(display_df.iloc[r]["Category"]),
                "Account": str(display_df.iloc[r]["Account"]),
            }

        a = row_to_obj(rows[0])
        b = row_to_obj(rows[1])

        # Must be different accounts
        if a["Account"] == b["Account"]:
            QMessageBox.warning(self, "Mark Transfer", "The two transactions must be on different accounts.")
            return

        # Must be opposite signs
        if a["Amount"] * b["Amount"] >= 0:
            QMessageBox.warning(self, "Mark Transfer", "Amounts must be opposite in sign (one outflow, one inflow).")
            return

        # Optional: date proximity check (<= 10 days)
        try:
            da = dt.strptime(a["Date"], "%Y-%m-%d").date()
            db = dt.strptime(b["Date"], "%Y-%m-%d").date()
            if abs((da - db).days) > 10:
                reply = QMessageBox.question(self, "Mark Transfer",
                                            "Dates are more than 10 days apart. Link anyway?",
                                            QMessageBox.Yes | QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
        except Exception:
            pass

        # Link via a shared TransferGroup id
        import uuid
        tg = str(uuid.uuid4())

        # Update backing df by Id
        for row_id in (a["Id"], b["Id"]):
            idx = self.df.index[self.df["Id"].astype(str) == str(row_id)]
            if len(idx) == 1:
                i = idx[0]
                self.df.at[i, "Type"] = "Transfer"
                self.df.at[i, "Category"] = "Transfer"
                if "TransferGroup" not in self.df.columns:
                    self.df["TransferGroup"] = ""
                self.df.at[i, "TransferGroup"] = tg

        # Persist & refresh
        self.save_transactions()
        self.update_table()
        self.update_summary()
        QMessageBox.information(self, "Transfer", "The two rows have been linked as a transfer.")
    
    def clear_all_transactions(self):
        if self.df.empty:
            QMessageBox.information(self, "Clear Transactions", "There are no transactions to clear.")
            return
        reply = QMessageBox.question(
            self, "Clear ALL Transactions",
            "This will delete ALL transactions and cannot be undone.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # Recreate empty dataframe with the expected columns
        cols = ['Id', 'Date', 'Vendor', 'Amount', 'Type', 'Category', 'Account',
            'AppliedToBalance', 'ExternalId', 'TransferGroup', 'CategorySource']

        self.df = pd.DataFrame(columns=cols)
        self.save_and_refresh()
        QMessageBox.information(self, "Transactions", "All transactions cleared.")

    def _edit_transaction_by_id(self, row_id: str):
        matches = self.df.index[self.df['Id'].astype(str) == str(row_id)]
        if len(matches) == 0:
            QMessageBox.warning(self, "Not Found", "Original transaction row could not be located.")
            return
        i = int(matches[0])
        current_data = self.df.loc[i].to_dict()

        dialog = AddTransactionDialog(
            self,
            transaction=current_data,
            account_names=self._account_names(),
            category_names=self.get_category_names()
        )
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
            if not new["Vendor"].strip():
                QMessageBox.warning(self, "Input Error", "Vendor cannot be empty.")
                continue
            if new["Category"] not in self.get_category_names():
                QMessageBox.warning(self, "Input Error", "Category must be chosen from the Categories tab or created via 'New category…'.")
                continue
            break

        self.df.at[i, 'Date'] = new['Date']
        self.df.at[i, 'Vendor'] = new['Vendor']
        self.df.at[i, 'Amount'] = amount
        self.df.at[i, 'Type'] = t
        self.df.at[i, 'Category'] = new['Category']
        self.df.at[i, 'Account'] = new['Account']
       
        # Mark provenance for manual edit
        if "CategorySource" not in self.df.columns:
            self.df["CategorySource"] = ""
        self.df.at[i, "CategorySource"] = "Manual"

        # Sprint 12: backfill uncategorized matches after this manual assignment
        try:
            backfilled = self._autocat_backfill_after_manual(new['Vendor'], new['Category'])
            if backfilled:
                self.save_json(AUTOCAT_FILE, self.autocat)
        except Exception:
            pass
        
        # After backfill, consider migrating past AUTO rows if we have enough confirmations
        try:
            migrated = self._autocat_migrate_auto_rows(new['Vendor'], new['Category'], min_confirmations=2)
            if migrated:
                self.save_transactions()
        except Exception:
            pass

        # Keep AppliedToBalance as-is for edited row
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
        # Sprint 12: opportunistic auto-categorize before save/refresh
        try:
            changed = self._autocat_apply_to_uncategorized()
            if changed:
                # mark will be saved with the main save below
                pass
        except Exception:
            pass

        self.save_transactions()
        self.update_table()
        self.update_summary()
        # Immediate refresh everywhere
        self.update_budgets_table()
        self.update_dashboard_tab()
        self.refresh_reports()


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
        btn_clear = QPushButton("Clear All")  # NEW
        row_btns.addWidget(btn_edit)
        row_btns.addWidget(btn_remove)
        row_btns.addSpacing(12)
        row_btns.addWidget(btn_clear)  # NEW
        layout.addLayout(row_btns)

        btn_edit.clicked.connect(self.add_edit_budget)
        btn_remove.clicked.connect(self.remove_budget)
        btn_clear.clicked.connect(self.clear_all_budgets)  # NEW

        self.budget_tab.setLayout(layout)
        self.update_budgets_table()

    def _all_categories_for_budget(self):
        """
        Only show categories that actually have a budget > 0 set.
        (Hides zero/empty budgets and categories without a budget.)
        """
        out = []
        for cat, data in (self.budgets or {}).items():
            amt = 0.0
            if isinstance(data, dict):
                try:
                    amt = float(data.get("amount", 0) or 0)
                except Exception:
                    amt = 0.0
            # keep only positive budgets
            if amt > 0:
                out.append(cat)
        return sorted(set(out))


    def update_budgets_table(self):
        # One-time cleanup: remove budgets for system categories (e.g., Transfer)
        if any(is_system_category(k) for k in (self.budgets or {}).keys()):
            self.budgets = {k: v for k, v in self.budgets.items() if not is_system_category(k)}
            self.save_json(BUDGET_FILE, self.budgets)

        all_cats = self._all_categories_for_budget()
        today = self.get_today()

        self.budget_table.setRowCount(len(all_cats))
        for r, cat in enumerate(all_cats):
            self.budget_table.setItem(r, 0, QTableWidgetItem(cat))
            bdata = self.budgets.get(cat)
            if isinstance(bdata, dict):
                try:
                    amount = float(bdata.get("amount", 0) or 0)
                except Exception:
                    amount = 0.0
                if amount <= 0:
                    # skip rendering this row defensively
                    continue

                period_code = (bdata.get("period") or "monthly").lower()
                period = period_code.capitalize()
                monthly_eq = self.monthly_equivalent(float(amount), period_code, today)

                self.budget_table.setItem(r, 1, QTableWidgetItem(period))
                amt_item = QTableWidgetItem(fmt_money(amount))
                amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.budget_table.setItem(r, 2, amt_item)

                me_item = QTableWidgetItem(fmt_money(monthly_eq))
                me_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.budget_table.setItem(r, 3, me_item)
            else:
                # (Shouldn’t happen with new _all_categories_for_budget, but safe.)
                self.budget_table.setItem(r, 1, QTableWidgetItem("—"))
                self.budget_table.setItem(r, 2, QTableWidgetItem("None"))
                self.budget_table.setItem(r, 3, QTableWidgetItem("—"))

            self.budget_table.resizeColumnsToContents()

    def add_edit_budget(self):
        cats_expense = self.get_category_names_by_type("Expense")
        dialog = BudgetDialog(cats_expense, self.budgets, self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.getData()
        cat = data["Category"].strip() or UNCATEGORIZED
        # Do not allow budgets for system categories (e.g., Transfer)
        if is_system_category(cat):
            QMessageBox.warning(self, "Budget", f"'{cat}' is a system category and cannot have a budget.")
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

    def clear_all_budgets(self):
        if not self.budgets:
            QMessageBox.information(self, "Clear Budgets", "There are no budgets to clear.")
            return
        reply = QMessageBox.question(
            self, "Clear ALL Budgets",
            "This will remove ALL budgets and cannot be undone.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self.budgets = {}
        self.save_json(BUDGET_FILE, self.budgets)
        self.update_budgets_table()
        self.update_dashboard_tab()
        QMessageBox.information(self, "Budgets", "All budgets cleared.")


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
        btn_clear = QPushButton("Clear All")              # NEW
        btn_apply = QPushButton("Apply New Transactions")
        btn_recalc = QPushButton("Recalculate Balances")

        row_btns.addWidget(btn_add)
        row_btns.addWidget(btn_edit)
        row_btns.addWidget(btn_del)
        row_btns.addSpacing(12)
        row_btns.addWidget(btn_clear)                      # NEW
        row_btns.addStretch()
        row_btns.addWidget(btn_apply)
        row_btns.addWidget(btn_recalc)
        layout.addLayout(row_btns)

        btn_add.clicked.connect(self.add_account)
        btn_edit.clicked.connect(self.edit_account)
        btn_del.clicked.connect(self.delete_account)
        btn_clear.clicked.connect(self.clear_all_accounts)  # NEW
        btn_apply.clicked.connect(self.apply_new_transactions_to_balances)
        btn_recalc.clicked.connect(self.recalculate_balances_from_start)


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
        self.accounts.append({"name": name, "balance": bal, "starting_balance": bal})
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
        # If balance changed, we don't change starting_balance silently
        self.accounts[row] = {"name": name, "balance": bal, "starting_balance": acct.get("starting_balance", bal)}
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

    def clear_all_accounts(self):
        if not self.accounts:
            QMessageBox.information(self, "Clear Accounts", "There are no accounts to clear.")
            return
        reply = QMessageBox.question(
            self, "Clear ALL Accounts",
            "This will delete ALL accounts and cannot be undone.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self.accounts = []
        self.save_json(ACCOUNTS_FILE, self.accounts)
        self.update_accounts_table()
        self.update_dashboard_tab()
        QMessageBox.information(self, "Accounts", "All accounts cleared.")


    # ------- Balance Adjuster Logic -------
    def apply_new_transactions_to_balances(self):
        if not self.accounts:
            QMessageBox.information(self, "No Accounts", "No accounts found. Add an account first.")
            return
        if self.df.empty:
            QMessageBox.information(self, "No Transactions", "There are no transactions to apply.")
            return

        unapplied_mask = ~self.df['AppliedToBalance']
        # Only count rows that match existing accounts (ignore Unassigned)
        ac_names = {a["name"] for a in self.accounts}
        acct_mask = self.df['Account'].isin(ac_names)
        mask = unapplied_mask & acct_mask

        if not mask.any():
            QMessageBox.information(self, "Up to date", "All transactions are already applied to balances.")
            return

        # Sum by account and update balances
        changed = 0
        df_to_apply = self.df.loc[mask].copy()
        if not df_to_apply.empty:
            sums = df_to_apply.groupby('Account')['Amount'].sum()
            for i, acct in enumerate(self.accounts):
                inc = float(sums.get(acct["name"], 0.0))
                if abs(inc) > 0.000001:
                    self.accounts[i]["balance"] = float(self.accounts[i]["balance"]) + inc
            changed = len(df_to_apply)

        # Mark applied
        self.df.loc[mask, 'AppliedToBalance'] = True

        # Persist
        self.save_json(ACCOUNTS_FILE, self.accounts)
        self.save_transactions()
        self.update_accounts_table()
        self.update_dashboard_tab()

        QMessageBox.information(self, "Balances Updated", f"Balances updated. {changed} transaction(s) applied.")

    def recalculate_balances_from_start(self):
        if not self.accounts:
            QMessageBox.information(self, "No Accounts", "No accounts found.")
            return

        # Reset balances to starting
        for i, acct in enumerate(self.accounts):
            self.accounts[i]["balance"] = float(acct.get("starting_balance", acct.get("balance", 0.0)))

        # Reapply all transactions that were previously applied
        if not self.df.empty:
            df_applied = self.df[self.df['AppliedToBalance']]
            if not df_applied.empty:
                sums = df_applied.groupby('Account')['Amount'].sum()
                for i, acct in enumerate(self.accounts):
                    inc = float(sums.get(acct["name"], 0.0))
                    if abs(inc) > 0.000001:
                        self.accounts[i]["balance"] = float(self.accounts[i]["balance"]) + inc

        # Save + refresh
        self.save_json(ACCOUNTS_FILE, self.accounts)
        self.update_accounts_table()
        self.update_dashboard_tab()

        QMessageBox.information(self, "Recalculated", "Balances recalculated from starting balances.")

    # ---------------- Categories Tab ----------------
    def init_categories_tab(self):
        layout = QVBoxLayout()

        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(2)
        self.categories_table.setHorizontalHeaderLabels(["Category Name", "Type"])
        layout.addWidget(self.categories_table)

        btns = QHBoxLayout()
        btn_add = QPushButton("Add Category")
        btn_edit = QPushButton("Edit Category")
        btn_del = QPushButton("Delete Category")
        btn_clear = QPushButton("Clear All")  # NEW
        btns.addWidget(btn_add)
        btns.addWidget(btn_edit)
        btns.addWidget(btn_del)
        btns.addSpacing(12)
        btns.addWidget(btn_clear)             # NEW
        btns.addStretch()
        layout.addLayout(btns)


        btn_add.clicked.connect(self.add_category)
        btn_edit.clicked.connect(self.edit_category)
        btn_del.clicked.connect(self.delete_category)
        btn_clear.clicked.connect(self.clear_all_categories)  # NEW

        self.categories_tab.setLayout(layout)
        self.update_categories_table()

    def update_categories_table(self):
        self.categories_table.setRowCount(len(self.categories))
        for r, c in enumerate(sorted(self.categories, key=lambda x: x["name"].lower())):
            self.categories_table.setItem(r, 0, QTableWidgetItem(c["name"]))
            self.categories_table.setItem(r, 1, QTableWidgetItem(c["type"]))
        self.categories_table.resizeColumnsToContents()

    def add_category(self):
        dialog = CategoryDialog(parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.getData()
        name = data["name"]
        if not name:
            QMessageBox.warning(self, "Input Error", "Category name cannot be empty.")
            return
        if name.lower() in [c["name"].lower() for c in self.categories]:
            QMessageBox.warning(self, "Exists", "A category with this name already exists.")
            return
        self.categories.append({"name": name, "type": data["type"]})
        self.save_json(CATEGORIES_FILE, self.categories)
        self.update_categories_table()

    def edit_category(self):
        row = self.categories_table.currentRow()
        if row < 0 or row >= self.categories_table.rowCount():
            QMessageBox.warning(self, "No Selection", "Select a category to edit.")
            return
        name = self.categories_table.item(row, 0).text()
        orig = next((c for c in self.categories if c["name"] == name), None)
        if not orig:
            QMessageBox.warning(self, "Not Found", "Category not found.")
            return
        dialog = CategoryDialog(category=orig, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        data = dialog.getData()
        new_name = data["name"]
        new_type = data["type"]
        if not new_name:
            QMessageBox.warning(self, "Input Error", "Category name cannot be empty.")
            return
        # If name changed and collides
        if new_name.lower() != orig["name"].lower() and new_name.lower() in [c["name"].lower() for c in self.categories]:
            QMessageBox.warning(self, "Exists", "Another category with that name already exists.")
            return

        # Update references if renamed
        old_name = orig["name"]
        if new_name != old_name:
            # Update transactions
            if not self.df.empty:
                self.df.loc[self.df['Category'] == old_name, 'Category'] = new_name
                self.save_transactions()
            # Update budgets
            if old_name in self.budgets:
                if new_name in self.budgets:
                    # Keep destination's budget; drop old
                    del self.budgets[old_name]
                else:
                    self.budgets[new_name] = self.budgets.pop(old_name)
                self.save_json(BUDGET_FILE, self.budgets)

        # Update category list
        orig["name"] = new_name
        orig["type"] = new_type
        self.save_json(CATEGORIES_FILE, self.categories)
        self.update_categories_table()
        self.save_and_refresh()

    def delete_category(self):
        row = self.categories_table.currentRow()
        if row < 0 or row >= self.categories_table.rowCount():
            QMessageBox.warning(self, "No Selection", "Select a category to delete.")
            return
        cat = self.categories_table.item(row, 0).text()
        if cat.lower() == UNCATEGORIZED.lower():
            QMessageBox.warning(self, "Protected", "You cannot delete the Uncategorized category.")
            return

        # determine if in use
        used = False
        tx_count = 0
        if not self.df.empty:
            tx_count = int((self.df['Category'] == cat).sum())
            used = used or tx_count > 0
        bud_used = cat in self.budgets
        used = used or bud_used

        if used:
            # choices: all other categories + UNCATEGORIZED
            choices = [c["name"] for c in self.categories if c["name"] != cat]
            if UNCATEGORIZED not in [x for x in choices]:
                choices.append(UNCATEGORIZED)
            dlg = ReassignDialog(cat, choices, parent=self)
            if dlg.exec() != QDialog.Accepted:
                return
            target = dlg.getSelection()
            if target == cat:
                QMessageBox.warning(self, "Invalid", "Reassignment target cannot be the same category.")
                return

            # Reassign transactions
            if tx_count > 0:
                self.df.loc[self.df['Category'] == cat, 'Category'] = target
                self.save_transactions()
            # Reassign budgets
            if bud_used:
                if target in self.budgets:
                    # keep target budget; drop the deleted one
                    del self.budgets[cat]
                else:
                    self.budgets[target] = self.budgets.pop(cat)
                self.save_json(BUDGET_FILE, self.budgets)

        # Remove from categories list
        self.categories = [c for c in self.categories if c["name"] != cat]
        self.save_json(CATEGORIES_FILE, self.categories)
        self.update_categories_table()
        self.save_and_refresh()
    
    def clear_all_categories(self):
        # Protect against leaving transactions with dangling categories:
        # we reset categories to only 'Uncategorized' and remap all tx to it.
        reply = QMessageBox.question(
            self, "Clear ALL Categories",
            "This will remove ALL categories and set every transaction's Category to 'Uncategorized'.\n"
            "This cannot be undone.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # Reset category list
        self.categories = [{"name": "Uncategorized", "type": "Expense"}]
        self.save_json(CATEGORIES_FILE, self.categories)

        # Remap all transactions to 'Uncategorized'
        if not self.df.empty and "Category" in self.df.columns:
            self.df["Category"] = "Uncategorized"
            self.save_transactions()

        # Remove any budgets (optional—but recommended because their categories vanish)
        if self.budgets:
            self.budgets = {}
            self.save_json(BUDGET_FILE, self.budgets)

        self.update_categories_table()
        self.save_and_refresh()
        QMessageBox.information(self, "Categories", "All categories cleared (transactions set to 'Uncategorized').")


    # ---------------- Dashboard Tab ----------------
    def init_dashboard_tab(self):
        main_layout = QVBoxLayout()

        # Top: Net worth + today + local range controls
        header_row = QHBoxLayout()
        self.dashboard_balance_label = QLabel()
        header_row.addWidget(self.dashboard_balance_label)
        header_row.addStretch()

        header_row.addWidget(QLabel("Range:"))
        self.dashboard_range_dropdown = QComboBox()
        self.dashboard_range_dropdown.addItems(["This Month", "Last Month", "YTD", "Custom"])
        self.dashboard_range_dropdown.setCurrentText(self.dashboard_filter_mode)
        header_row.addWidget(self.dashboard_range_dropdown)

        self.dashboard_from_picker = QDateEdit()
        self.dashboard_from_picker.setCalendarPopup(True)
        self.dashboard_from_picker.setDisplayFormat("yyyy-MM-dd")
        self.dashboard_to_picker = QDateEdit()
        self.dashboard_to_picker.setCalendarPopup(True)
        self.dashboard_to_picker.setDisplayFormat("yyyy-MM-dd")
        header_row.addWidget(QLabel("From:"))
        header_row.addWidget(self.dashboard_from_picker)
        header_row.addWidget(QLabel("To:"))
        header_row.addWidget(self.dashboard_to_picker)

        main_layout.addLayout(header_row)

        # Initially hide pickers unless Custom
        self.dashboard_from_picker.hide()
        self.dashboard_to_picker.hide()

        # Wire range controls
        self.dashboard_range_dropdown.currentTextChanged.connect(self.on_dashboard_range_changed)
        self.dashboard_from_picker.dateChanged.connect(lambda *_: self.update_dashboard_tab())
        self.dashboard_to_picker.dateChanged.connect(lambda *_: self.update_dashboard_tab())

        # Grid layout for widgets
        grid = QGridLayout()

        # Budgets summary (budgeted only) with progress bars + subtitle
        budgets_group = QGroupBox("Budgets (Budgeted Categories Only)")
        budgets_layout = QVBoxLayout()
        subtitle = QLabel("<i>Monthly equivalents shown</i>")
        budgets_layout.addWidget(subtitle)
        self.dashboard_budget_table = QTableWidget()
        self.dashboard_budget_table.setColumnCount(5)
        self.dashboard_budget_table.setHorizontalHeaderLabels(["Category", "Spent (in range)", "Budget (Monthly Eq.)", "Remaining", "Progress"])
        budgets_layout.addWidget(self.dashboard_budget_table)
        budgets_group.setLayout(budgets_layout)
        grid.addWidget(budgets_group, 0, 0, 1, 2)

        # Recent transactions (respecting dashboard range)
        recent_group = QGroupBox("Recent Transactions (within range)")
        recent_layout = QVBoxLayout()
        self.dashboard_recent_table = QTableWidget()
        self.dashboard_recent_table.setColumnCount(4)
        self.dashboard_recent_table.setHorizontalHeaderLabels(["Date", "Vendor", "Amount", "Category"])
        recent_layout.addWidget(self.dashboard_recent_table)
        self.btn_view_all_tx = QPushButton("View All Transactions")
        self.btn_view_all_tx.clicked.connect(lambda: self.tabs.setCurrentWidget(self.trans_tab))
        recent_layout.addWidget(self.btn_view_all_tx)
        recent_group.setLayout(recent_layout)
        grid.addWidget(recent_group, 1, 0)

        # Spend by Account (range)
        acct_group = QGroupBox("Spend by Account (Expenses in range)")
        acct_layout = QVBoxLayout()
        self.dashboard_spend_by_acct_table = QTableWidget()
        self.dashboard_spend_by_acct_table.setColumnCount(2)
        self.dashboard_spend_by_acct_table.setHorizontalHeaderLabels(["Account", "Spent"])
        acct_layout.addWidget(self.dashboard_spend_by_acct_table)
        acct_group.setLayout(acct_layout)
        grid.addWidget(acct_group, 1, 1)

        # Row 2: Spend by Category (list + donut) in range
        # Left: list
        cat_list_group = QGroupBox("Spend by Category (Expenses in range) — List")
        cat_list_layout = QVBoxLayout()
        self.dashboard_spend_by_cat_table = QTableWidget()
        self.dashboard_spend_by_cat_table.setColumnCount(2)
        self.dashboard_spend_by_cat_table.setHorizontalHeaderLabels(["Category", "Spent"])
        cat_list_layout.addWidget(self.dashboard_spend_by_cat_table)
        cat_list_group.setLayout(cat_list_layout)
        grid.addWidget(cat_list_group, 2, 0)

        # Right: donut pie
        pie_group = QGroupBox("Spend by Category (Expenses in range) — Chart")
        pie_layout = QVBoxLayout()
        self.mtd_category_pie = MplCanvas(width=4.5, height=3.6, dpi=100)
        pie_layout.addWidget(self.mtd_category_pie)
        pie_group.setLayout(pie_layout)
        grid.addWidget(pie_group, 2, 1)

        main_layout.addLayout(grid)
        self.dashboard_tab.setLayout(main_layout)

        self.update_dashboard_tab()

    # Dashboard range helpers
    def compute_dashboard_range(self):
        today = self.get_today()
        mode = self.dashboard_range_dropdown.currentText()
        if mode == "This Month":
            return start_of_month(today), today
        if mode == "Last Month":
            first_this = start_of_month(today)
            last_end = first_this - datetime.timedelta(days=1)
            return start_of_month(last_end), last_end
        if mode == "YTD":
            return today.replace(month=1, day=1), today
        if mode == "Custom":
            f = self.dashboard_from_picker.date().toPython()
            t = self.dashboard_to_picker.date().toPython()
            if f > t:
                f, t = t, f
            return f, t
        return start_of_month(today), today

    # Generic spend aggregations for any range
    def get_spend_by_category_in_range(self, start: datetime.date, end: datetime.date) -> dict[str, float]:
        if self.df.empty:
            return {}
        df = self.df.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df[(df['Date'] >= pd.Timestamp(start)) & (df['Date'] <= pd.Timestamp(end))]
        
        # NEW: exclude transfers from dashboard/report spend math Sprint 13
        if 'Type' in df.columns:
            df = df[df['Type'].astype(str).str.lower() != 'transfer']
        if 'Category' in df.columns:
            df = df[df['Category'].astype(str).str.lower() != 'transfer']

        if df.empty:
            return {}
        df['Category'] = df['Category'].astype(str)
        spent = df.groupby('Category')['Amount'].apply(lambda x: abs(x[x < 0].sum())).to_dict()
        return spent

    def get_spend_by_account_in_range(self, start: datetime.date, end: datetime.date) -> dict[str, float]:
        if self.df.empty:
            return {}
        df = self.df.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df[(df['Date'] >= pd.Timestamp(start)) & (df['Date'] <= pd.Timestamp(end))]

        # NEW: exclude transfers
        if 'Type' in df.columns:
            df = df[df['Type'].astype(str).str.lower() != 'transfer']

        if df.empty:
            return {}
        df['Account'] = df['Account'].fillna("Unassigned")
        spent = df.groupby('Account')['Amount'].apply(lambda x: abs(x[x < 0].sum())).to_dict()
        return spent

    def get_recent_transactions_in_range(self, start: datetime.date, end: datetime.date, n=10) -> pd.DataFrame:
        if self.df.empty:
            return self.df.copy()
        df = self.df.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df[(df['Date'] >= pd.Timestamp(start)) & (df['Date'] <= pd.Timestamp(end))]
        df = df.sort_values('Date', ascending=False)

        # NEW: exclude transfers from dashboard recent list
        if 'Type' in df.columns:
            df = df[df['Type'].astype(str).str.lower() != 'transfer']

        return df.head(n).reset_index(drop=True)

    def _draw_donut(self, ax, labels, values, center_text):
        ax.clear()
        self.mtd_category_pie.set_dark()
        wedges, _ = ax.pie(
            values,
            labels=None,  # legend instead
            startangle=90,
            wedgeprops=dict(width=0.42, edgecolor=DARK_FIG)
        )
        ax.text(0, 0, center_text, ha='center', va='center', color=LIGHT_TEXT, fontsize=12, fontweight='bold')
        ax.axis('equal')
        ax.legend(wedges, labels, loc='center left', bbox_to_anchor=(1.0, 0.5),
                  facecolor=DARK_AX, labelcolor=LIGHT_TEXT, framealpha=0.0)

    def _draw_category_donut_for_range(self, start: datetime.date, end: datetime.date):
        spent_by_cat = self.get_spend_by_category_in_range(start, end)
        spent_by_cat = {k: v for k, v in spent_by_cat.items() if v > 0}
        labels = []
        sizes = []
        total = 0.0
        if spent_by_cat:
            pairs = sorted(spent_by_cat.items(), key=lambda x: -x[1])
            top = pairs[:10]
            others = pairs[10:]
            labels = [k for k, _ in top]
            sizes = [v for _, v in top]
            if others:
                labels.append("Other")
                sizes.append(sum(v for _, v in others))
            total = sum(sizes)

        ax = self.mtd_category_pie.ax
        if sizes:
            self._draw_donut(ax, labels, sizes, fmt_money(total))
        else:
            ax.clear()
            self.mtd_category_pie.set_dark()
            ax.text(0.5, 0.5, "No expense data", ha='center', va='center', color=LIGHT_TEXT)
            ax.axis('off')
        self.mtd_category_pie.draw()

    def on_dashboard_range_changed(self, *_):
        mode = self.dashboard_range_dropdown.currentText()
        if mode == "Custom":
            self.dashboard_from_picker.show()
            self.dashboard_to_picker.show()
            # initialize to current month
            today = self.get_today()
            self.dashboard_from_picker.setDate(QDate(start_of_month(today).year, start_of_month(today).month, start_of_month(today).day))
            self.dashboard_to_picker.setDate(QDate(today.year, today.month, today.day))
        else:
            self.dashboard_from_picker.hide()
            self.dashboard_to_picker.hide()
        self.update_dashboard_tab()

    def update_dashboard_tab(self):
        # Net worth + today
        total = sum(float(a["balance"]) for a in self.accounts) if self.accounts else 0.0
        eff_today = self.get_today().strftime("%Y-%m-%d")
        self.dashboard_balance_label.setText(
            f"Total Balance Across All Accounts: <b>{fmt_money(total)}</b> &nbsp;&nbsp; "
            f"<span style='color:gray;'>[Today: {eff_today}]</span>"
        )

        # Range
        start, end = self.compute_dashboard_range()
        # Exclude transfers from dashboard spend/income
        df = self.df.copy()
        df = df[df['Type'] != 'Transfer']


        # Budgets summary: ONLY budgeted categories; spent within range; budget = monthly eq (subtitle explains)
        today = self.get_today()
        spent_by_cat = self.get_spend_by_category_in_range(start, end)
        rows = []
        for cat in sorted(self.budgets.keys(), key=lambda x: x.lower()):
            bdata = self.budgets.get(cat)
            meq = self.monthly_equivalent(bdata.get("amount", 0.0), bdata.get("period", "monthly"), today)
            spent = spent_by_cat.get(cat, 0.0)
            remaining = meq - spent
            rows.append({"category": cat, "spent": spent, "budget_meq": meq, "remaining": remaining})

        self.dashboard_budget_table.setRowCount(len(rows))
        for r, data in enumerate(rows):
            self.dashboard_budget_table.setItem(r, 0, QTableWidgetItem(data["category"]))

            spent_item = QTableWidgetItem(fmt_money(data["spent"]))
            spent_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.dashboard_budget_table.setItem(r, 1, spent_item)

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

            # Progress bar: allow >100%
            bar = QProgressBar()
            pct = 0
            if data["budget_meq"] > 0:
                pct = round((data["spent"] / data["budget_meq"]) * 100)
            max_val = max(100, int(pct)) if pct > 0 else 100
            if pct < 0:
                pct = 0
            bar.setRange(0, max_val)
            bar.setValue(int(pct))
            bar.setFormat(f"{int(pct)}%")
            if data["remaining"] < 0:
                bar.setStyleSheet("QProgressBar::chunk { background-color: #c62828; } QProgressBar { color: white; }")
            else:
                bar.setStyleSheet("QProgressBar::chunk { background-color: #2e7d32; } QProgressBar { color: white; }")
            self.dashboard_budget_table.setCellWidget(r, 4, bar)

        self.dashboard_budget_table.resizeColumnsToContents()

        # Recent transactions (within range)
        recent = self.get_recent_transactions_in_range(start, end, n=10)
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

        # Spend by Account (range)
        spend_acct = self.get_spend_by_account_in_range(start, end)
        accts = sorted(spend_acct.keys())
        self.dashboard_spend_by_acct_table.setRowCount(len(accts))
        for r, name in enumerate(accts):
            self.dashboard_spend_by_acct_table.setItem(r, 0, QTableWidgetItem(name))
            amt_item = QTableWidgetItem(fmt_money(spend_acct[name]))
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.dashboard_spend_by_acct_table.setItem(r, 1, amt_item)
        self.dashboard_spend_by_acct_table.resizeColumnsToContents()

        # Spend by Category (range) — list
        spend_cat_pairs = sorted(self.get_spend_by_category_in_range(start, end).items(), key=lambda x: (-x[1], x[0]))
        self.dashboard_spend_by_cat_table.setRowCount(len(spend_cat_pairs))
        for r, (cat, amt) in enumerate(spend_cat_pairs):
            self.dashboard_spend_by_cat_table.setItem(r, 0, QTableWidgetItem(cat))
            amt_item = QTableWidgetItem(fmt_money(amt))
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.dashboard_spend_by_cat_table.setItem(r, 1, amt_item)
        self.dashboard_spend_by_cat_table.resizeColumnsToContents()

        # Category donut (range)
        self._draw_category_donut_for_range(start, end)

    # ---------------- Reports Tab ----------------
    def init_reports_tab(self):
        layout = QVBoxLayout()

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Range:"))
        self.reports_filter_dropdown = QComboBox()
        self.reports_filter_dropdown.addItems(["This Month", "Last Month", "Last 3 Months", "This Year", "Custom Range"])
        filter_bar.addWidget(self.reports_filter_dropdown)

        filter_bar.addWidget(QLabel("From:"))
        self.reports_from_picker = QDateEdit()
        self.reports_from_picker.setCalendarPopup(True)
        self.reports_from_picker.setDisplayFormat("yyyy-MM-dd")
        self.reports_from_picker.setDate(QDate.currentDate())
        filter_bar.addWidget(self.reports_from_picker)

        filter_bar.addWidget(QLabel("To:"))
        self.reports_to_picker = QDateEdit()
        self.reports_to_picker.setCalendarPopup(True)
        self.reports_to_picker.setDisplayFormat("yyyy-MM-dd")
        self.reports_to_picker.setDate(QDate.currentDate())
        filter_bar.addWidget(self.reports_to_picker)

        self.reports_from_picker.hide()
        self.reports_to_picker.hide()

        self.reports_filter_dropdown.currentTextChanged.connect(self.on_reports_filter_changed)
        self.reports_from_picker.dateChanged.connect(self.refresh_reports)
        self.reports_to_picker.dateChanged.connect(self.refresh_reports)

        layout.addLayout(filter_bar)

        charts_grid = QGridLayout()

        # Pie: Spending by Category (donut, dark)
        self.reports_pie_group = QGroupBox("Spending by Category (Expenses Only)")
        pie_layout = QVBoxLayout()
        self.reports_pie = MplCanvas(width=5, height=4, dpi=100)
        pie_layout.addWidget(self.reports_pie)
        self.reports_pie_group.setLayout(pie_layout)
        charts_grid.addWidget(self.reports_pie_group, 0, 0)

        # Bar: Income vs Expenses by Month (dark)
        self.reports_bar_group = QGroupBox("Income vs Expenses by Month")
        bar_layout = QVBoxLayout()
        self.reports_bar = MplCanvas(width=6, height=4, dpi=100)
        bar_layout.addWidget(self.reports_bar)
        self.reports_bar_group.setLayout(bar_layout)
        charts_grid.addWidget(self.reports_bar_group, 0, 1)

        layout.addLayout(charts_grid)
        self.reports_tab.setLayout(layout)

        self.refresh_reports()

    def on_reports_filter_changed(self, *_):
        mode = self.reports_filter_dropdown.currentText()
        if mode == "Custom Range":
            self.reports_from_picker.show()
            self.reports_to_picker.show()
        else:
            self.reports_from_picker.hide()
            self.reports_to_picker.hide()
        self.refresh_reports()

    def compute_reports_range(self):
        today = self.get_today()
        mode = self.reports_filter_dropdown.currentText()
        if mode == "This Month":
            return start_of_month(today), end_of_month(today)
        if mode == "Last Month":
            first_this = start_of_month(today)
            last_end = first_this - datetime.timedelta(days=1)
            return start_of_month(last_end), last_end
        if mode == "Last 3 Months":
            end = end_of_month(today)
            # subtract 2 months from start of current month
            mm = today.month
            yy = today.year
            mm2 = mm - 2
            yy2 = yy
            while mm2 <= 0:
                mm2 += 12
                yy2 -= 1
            start = datetime.date(yy2, mm2, 1)
            return start, end
        if mode == "This Year":
            return today.replace(month=1, day=1), today.replace(month=12, day=31)
        if mode == "Custom Range":
            return self.reports_from_picker.date().toPython(), self.reports_to_picker.date().toPython()
        return start_of_month(today), end_of_month(today)

    def refresh_reports(self):
        ax_p = self.reports_pie.ax
        ax_b = self.reports_bar.ax
        self.reports_pie.set_dark()
        self.reports_bar.set_dark()

        if self.df.empty:
            ax_p.clear(); ax_b.clear()
            self.reports_pie.set_dark(); self.reports_bar.set_dark()
            ax_p.text(0.5, 0.5, "No data", ha='center', va='center', color=LIGHT_TEXT); ax_p.axis('off')
            ax_b.text(0.5, 0.5, "No data", ha='center', va='center', color=LIGHT_TEXT); ax_b.axis('off')
            self.reports_pie.draw(); self.reports_bar.draw()
            return

        start, end = self.compute_reports_range()
        df = self.df.copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df[(df['Date'] >= pd.Timestamp(start)) & (df['Date'] <= pd.Timestamp(end))]

        # Pie: Spending by Category (expenses only, donut)
        ax_p.clear(); self.reports_pie.set_dark()
        if df.empty:
            ax_p.text(0.5, 0.5, "No data", ha='center', va='center', color=LIGHT_TEXT); ax_p.axis('off')
        else:
            exp = df[df['Amount'] < 0].copy()
            if exp.empty:
                ax_p.text(0.5, 0.5, "No expense data", ha='center', va='center', color=LIGHT_TEXT); ax_p.axis('off')
            else:
                sums = exp.groupby('Category')['Amount'].sum().abs().sort_values(ascending=False)
                labels = sums.index.tolist()
                values = sums.values.tolist()
                total = sums.sum()
                if len(labels) > 12:
                    top_labels = labels[:12]; top_values = values[:12]
                    other_val = sum(values[12:])
                    top_labels.append("Other"); top_values.append(other_val)
                    labels, values = top_labels, top_values
                wedges, _ = ax_p.pie(
                    values, labels=None, startangle=90,
                    wedgeprops=dict(width=0.42, edgecolor=DARK_FIG)
                )
                ax_p.text(0, 0, fmt_money(total), ha='center', va='center', color=LIGHT_TEXT, fontsize=12, fontweight='bold')
                ax_p.axis('equal')
                ax_p.legend(wedges, labels, loc='center left', bbox_to_anchor=(1.0, 0.5),
                            facecolor=DARK_AX, labelcolor=LIGHT_TEXT, framealpha=0.0)
        self.reports_pie.draw()

        # Bar: Income vs Expenses by Month (dark)
        ax_b.clear(); self.reports_bar.set_dark()
        if df.empty:
            ax_b.text(0.5, 0.5, "No data", ha='center', va='center', color=LIGHT_TEXT); ax_b.axis('off')
        else:
            temp = df.copy()
            temp['YearMonth'] = temp['Date'].dt.to_period('M').astype(str)
            inc = temp[temp['Amount'] > 0].groupby('YearMonth')['Amount'].sum()
            exp = temp[temp['Amount'] < 0].groupby('YearMonth')['Amount'].sum().abs()
            months = sorted(set(inc.index).union(set(exp.index)))
            inc_vals = [inc.get(m, 0.0) for m in months]
            exp_vals = [exp.get(m, 0.0) for m in months]
            x = range(len(months))
            width = 0.38
            ax_b.bar([i - width/2 for i in x], inc_vals, width, label="Income")
            ax_b.bar([i + width/2 for i in x], exp_vals, width, label="Expenses")
            ax_b.set_xticks(list(x))
            ax_b.set_xticklabels(months, rotation=45, ha='right', color=LIGHT_TEXT)
            ax_b.legend(facecolor=DARK_AX, labelcolor=LIGHT_TEXT, framealpha=0.0)
            ax_b.set_ylabel("Amount", color=LIGHT_TEXT)
            ax_b.grid(axis='y', color=GRID_COLOR, alpha=0.5)
        self.reports_bar.draw()

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

        #Sprint 13: Re-seed categories
        self.btn_seed_data = QPushButton("Re-seed default categories & Ontario vendor map")
        layout.addWidget(self.btn_seed_data)

        def _on_seed_data():
            try:
                cpath = _project_path("seeds", "categories_seed.json")
                apath = _project_path("seeds", "autocategorize_seed_on_ca.json")
                # categories
                merged_c = _merge_seed_categories_from_file(self.categories, cpath)
                if merged_c != self.categories:
                    self.categories = merged_c
                    self.save_json("categories.json", self.categories)
                # autocat
                merged_a = _merge_seed_autocat_from_file(self.autocat, apath)
                if merged_a != self.autocat:
                    self.autocat = merged_a
                    self.save_json(AUTOCAT_FILE, self.autocat)

                # light feedback
                QMessageBox.information(self, "Seed Data", "Seed data merged. New defaults added if missing.")
                # optional: refresh budgets/categories UIs if present
                try: self.update_budgets_table()
                except Exception: pass
            except Exception as e:
                QMessageBox.warning(self, "Seed Data", f"Could not merge seed data:\n{e}")

        self.btn_seed_data.clicked.connect(_on_seed_data)


        # --- Sprint 12: Auto-categorization toggle ---
        self.chk_show_autocat_button = QCheckBox("Show 'Auto-Categorize Now' button (for testing)")
        show_btn = bool(self.settings.get("show_autocat_button", False))
        self.chk_show_autocat_button.setChecked(show_btn)
        layout.addWidget(self.chk_show_autocat_button)

        def _on_toggle_autocat_btn(checked):
            self.settings["show_autocat_button"] = bool(checked)
            self.save_json(SETTINGS_FILE, self.settings)
            try:
                self.run_autocat_button.setVisible(bool(checked))
            except Exception:
                pass

        self.chk_show_autocat_button.toggled.connect(_on_toggle_autocat_btn)

        self.chk_auto_cat = QCheckBox("Enable auto-categorization of transactions (experimental)")
        auto_on = bool(self.settings.get("auto_categorize_enabled", True))
        self.chk_auto_cat.setChecked(auto_on)
        layout.addWidget(self.chk_auto_cat)

        def _on_toggle_auto_cat(checked):
            self.settings["auto_categorize_enabled"] = bool(checked)
            self.save_json(SETTINGS_FILE, self.settings)
            if checked:
                # apply immediately to any uncategorized rows
                changed = self._autocat_apply_to_uncategorized()
                if changed:
                    self.save_transactions()
                    self.update_table()

        self.chk_auto_cat.toggled.connect(_on_toggle_auto_cat)


        # --- Sprint 11: debug toggle for advanced transaction columns ---
        self.chk_show_adv_cols = QCheckBox("Show advanced transaction columns (AppliedToBalance, ExternalId, TransferGroup)")
        val = False
        try:
            val = bool(self.settings.get("show_advanced_columns", False))
        except Exception:
            pass
        self.chk_show_adv_cols.setChecked(val)
        layout.addWidget(self.chk_show_adv_cols)


        def _on_toggle_adv_cols(checked):
            try:
                self.settings["show_advanced_columns"] = bool(checked)
                self.save_json("settings.json", self.settings)
            except Exception:
                pass
            # Reapply visibility if Transactions table is visible
            try:
                self._apply_advanced_cols_visibility()
            except Exception:
                pass

        self.chk_show_adv_cols.toggled.connect(_on_toggle_adv_cols)

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
        # Refresh everywhere
        self.update_table()
        self.update_summary()
        self.update_budgets_table()
        self.update_dashboard_tab()
        self.refresh_reports()
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
        self.refresh_reports()
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
        elif name == "Categories":
            self.update_categories_table()
        elif name == "Reports":
            self.refresh_reports()


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
