# import_wizard.py
import os, json, shutil, datetime
import pandas as pd
from datetime import datetime as dt


from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QFormLayout, QGroupBox, QDateEdit, QDialogButtonBox,
    QCheckBox, QStackedWidget, QAbstractItemView, QWidget   # <— added QWidget
)


from PySide6.QtCore import Qt

IMPORT_PROFILES_FILE = "import_profiles.json"

DATE_FORMAT_CHOICES = [
    ("Auto", None),
    ("YYYY-MM-DD", "%Y-%m-%d"),
    ("MM/DD/YYYY", "%m/%d/%Y"),
    ("DD/MM/YYYY", "%d/%m/%Y"),
    ("YYYY/MM/DD", "%Y/%m/%d"),
    ("DD-MMM-YYYY", "%d-%b-%Y"),
]

HEADER_FAMILIES = {
    "date": {"date", "posted", "transaction date", "date posted", "value date"},
    "vendor": {"description", "payee", "merchant", "name", "narrative", "details", "transaction"},
    "amount": {"amount", "amt", "value"},
    "debit": {"debit", "withdrawal", "payment", "charge", "spent"},
    "credit": {"credit", "deposit", "received"},
    "memo": {"memo", "note", "additional", "reference"},
    "balance": {"balance", "running balance", "current balance"},
    "external_id": {"id", "reference", "ref", "fitid", "transaction id", "trans id"},
    "type": {"type", "dr/cr", "debit/credit", "transaction type"}
}

def load_profiles():
    if os.path.exists(IMPORT_PROFILES_FILE):
        try:
            with open(IMPORT_PROFILES_FILE, "r") as f:
                return json.load(f).get("profiles", [])
        except Exception:
            return []
    return []

def save_profiles(profiles):
    with open(IMPORT_PROFILES_FILE, "w") as f:
        json.dump({"profiles": profiles}, f, indent=2)

def normalize_headers(headers):
    return [str(h).strip() for h in headers]

def lower_headers(headers):
    return [str(h).strip().lower() for h in headers]

def guess_mapping(headers):
    headers_norm = normalize_headers(headers)
    headers_lower = lower_headers(headers)
    date_col = vendor_col = amount_col = debit_col = credit_col = memo_col = ext_col = bal_col = type_col = ""

    for i, h in enumerate(headers_lower):
        if not date_col and any(k in h for k in HEADER_FAMILIES["date"]): date_col = headers_norm[i]
        if not vendor_col and any(k in h for k in HEADER_FAMILIES["vendor"]): vendor_col = headers_norm[i]
        if not amount_col and any(k in h for k in HEADER_FAMILIES["amount"]): amount_col = headers_norm[i]
        if not debit_col and any(k in h for k in HEADER_FAMILIES["debit"]): debit_col = headers_norm[i]
        if not credit_col and any(k in h for k in HEADER_FAMILIES["credit"]): credit_col = headers_norm[i]
        if not memo_col and any(k in h for k in HEADER_FAMILIES["memo"]): memo_col = headers_norm[i]
        if not ext_col and any(k in h for k in HEADER_FAMILIES["external_id"]): ext_col = headers_norm[i]
        if not bal_col and any(k in h for k in HEADER_FAMILIES["balance"]): bal_col = headers_norm[i]
        if not type_col and any(k in h for k in HEADER_FAMILIES["type"]): type_col = headers_norm[i]

    amount_mode = "single_amount"
    if debit_col and credit_col: amount_mode = "debit_credit"
    elif not amount_col and (debit_col or credit_col): amount_mode = "debit_credit"

    return {
        "date": date_col, "vendor": vendor_col,
        "amount_mode": amount_mode, "amount": amount_col,
        "debit": debit_col, "credit": credit_col,
        "memo": memo_col, "external_id": ext_col, "balance": bal_col, "type": type_col,
        "date_format": None, "strip_currency": True, "paren_negative": True, "thousands_sep": True, "invert_amount": False
    }

def match_profile(headers, ext, profiles):
    hl = set(lower_headers(headers))
    best = None; best_overlap = -1
    for p in profiles:
        fp = p.get("fingerprint", {})
        req = set([str(h).lower() for h in fp.get("headers", [])])
        if fp.get("ext") and fp.get("ext").lower() != ext.lower(): continue
        overlap = len(hl.intersection(req))
        if overlap > best_overlap:
            best_overlap = overlap; best = p
    return best if best and best_overlap >= 2 else None

def parse_date_value(val, fmt):
    if val is None or str(val).strip() == "": return None
    s = str(val).strip()
    if fmt:
        try: return dt.strptime(s, fmt).date()
        except Exception: return None
    try:
        d = pd.to_datetime(s, errors="coerce", dayfirst=False)
        if pd.isna(d): d = pd.to_datetime(s, errors="coerce", dayfirst=True)
        return None if pd.isna(d) else d.date()
    except Exception:
        return None

def parse_amount_value(val, strip_currency=True, paren_negative=True, thousands_sep=True, invert=False):
    if val is None: return None
    s = str(val).strip()
    if s == "": return None
    neg = False
    if paren_negative and s.startswith("(") and s.endswith(")"):
        neg = True; s = s[1:-1]
    if strip_currency:
        for sym in ["$", "€", "£", "CAD", "USD"]: s = s.replace(sym, "")
    s = s.replace(" ", "")
    if thousands_sep: s = s.replace(",", "")
    try:
        num = float(s)
        if neg: num = -abs(num)
        if invert: num = -num
        return num
    except Exception:
        return None

def compute_amount_from_dc(debit, credit, **opts):
    d = parse_amount_value(debit, **opts) if debit not in [None, ""] else 0.0
    c = parse_amount_value(credit, **opts) if credit not in [None, ""] else 0.0
    return (c or 0.0) - (d or 0.0)

def clean_vendor(val):
    return " ".join(str(val or "").split())

def dup_key(row):
    ext_val = row.get("ExternalId", "")
    ext = str(ext_val).strip() if ext_val is not None else ""
    if ext and ext.lower() != "nan":
        return f"ext::{ext}"

    date = row.get("Date") or ""
    vendor = (row.get("Vendor") or "").lower().strip()
    try: amount = f"{float(row.get('Amount',0.0)):.2f}"
    except Exception: amount = "0.00"
    acct = row.get("Account") or ""
    return f"{date}|{vendor}|{amount}|{acct}"

class ImportWizard(QDialog):
    def __init__(self, parent_app):
        super().__init__(parent_app)
        self.app = parent_app
        self.setWindowTitle("Import Transactions")
        self.resize(920, 640)

        self.profiles = load_profiles()
        self.file_path = ""; self.file_ext = ""; self.raw_df = None; self.headers = []
        self.mapping = {}; self.account_choice = ""
        self.preview_rows = []; self.preview_flags = []

        # Stack
        self.stack = QStackedWidget(self)
        outer = QVBoxLayout(self); outer.addWidget(self.stack)

        # Nav
        nav = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.btn_next = QPushButton("Next")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_import = QPushButton("Commit")
        nav.addWidget(self.btn_back); nav.addWidget(self.btn_next); nav.addStretch()
        nav.addWidget(self.btn_cancel); nav.addWidget(self.btn_import)
        outer.addLayout(nav)
        self.btn_back.clicked.connect(self.on_back)
        self.btn_next.clicked.connect(self.on_next)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_import.clicked.connect(self.on_commit)

        # --- Step 1: pick file
        self.step1 = QDialog(self); s1 = QVBoxLayout(self.step1)
        s1.addWidget(QLabel("Select a CSV / XLS / XLSX file to import."))
        row = QHBoxLayout()
        self.path_edit = QLineEdit(); self.path_edit.setReadOnly(True)
        self.btn_browse = QPushButton("Browse…"); row.addWidget(self.path_edit); row.addWidget(self.btn_browse)
        self.detect_label = QLabel("")
        s1.addLayout(row); s1.addWidget(self.detect_label)
        self.btn_browse.clicked.connect(self.choose_file)
        self.stack.addWidget(self.step1)

        # --- Step 2: mapping
        self.step2 = QDialog(self); s2 = QFormLayout(self.step2)
        self.s2 = s2  # keep a reference to Step-2 form layout for later additions


        # ====== Sprint 14: streamlined Step 2 (essentials + collapsible Advanced) ======
        # --- Controls (same variables as before; we’re just reorganizing layout) ---
        self.map_date = QComboBox(); self.map_vendor = QComboBox()

        # Amount mode + fields
        self.amount_mode = QComboBox(); self.amount_mode.addItems(["Single Amount column", "Debit/Credit columns"])
        self.map_amount = QComboBox(); self.map_debit = QComboBox(); self.map_credit = QComboBox()

        # Quick “flip signs” control (kept visible per user request: “positive vs negative”)
        if not hasattr(self, "chk_flip_signs"):
            self.chk_flip_signs = QCheckBox("Flip amounts so expenses become negative")
            self.chk_flip_signs.setToolTip(
                "Enable this if your file uses credit-card style: purchases are positive and payments are negative.\n"
                "When checked, the wizard will multiply all Amounts by -1 before import."
            )
            self.chk_flip_signs.toggled.connect(self._rebuild_preview_if_on_step3)

        # Advanced-only controls (we’ll add them into the collapsible panel)
        self.date_format = QComboBox()
        for label, _fmt in DATE_FORMAT_CHOICES: self.date_format.addItem(label)

        self.chk_strip_currency = QCheckBox("Strip currency symbols"); self.chk_strip_currency.setChecked(True)
        self.chk_paren_negative = QCheckBox("Parentheses indicate negative"); self.chk_paren_negative.setChecked(True)
        self.chk_thousands = QCheckBox("Remove thousands separators"); self.chk_thousands.setChecked(True)
        self.chk_invert = QCheckBox("Invert sign for Amount (rare)")

        self.map_memo = QComboBox(); self.map_external_id = QComboBox(); self.map_balance = QComboBox(); self.map_type = QComboBox()

        self.account_combo = QComboBox()
        self.account_combo.addItems([a["name"] for a in self.app.accounts] + ["➕ Add new account…"])
        self.account_combo.currentTextChanged.connect(self.on_account_changed)

        # Account Type (used on new account creation; moved to Advanced)
        self.account_type_combo = QComboBox()
        self.account_type_combo.addItems(["Asset", "Credit Card"])
        self.account_type_combo.setToolTip("Used when creating a new account here. Optional for existing accounts.")

        # Account Initialization group (Advanced)
        self.init_group = QGroupBox("Account Initialization")
        init_layout = QFormLayout(self.init_group)
        self.chk_init_from_import = QCheckBox("Initialize account balance from this import")
        self.chk_init_from_import.setChecked(False)
        self.init_net_label = QLabel("Computed net from this import: —")  # updated in preview
        self.override_balance_edit = QLineEdit()
        self.override_balance_edit.setPlaceholderText("Optional. Example: -2400 (use instead of computed net)")
        init_layout.addRow(self.chk_init_from_import)
        init_layout.addRow("Computed net:", self.init_net_label)
        init_layout.addRow("Override balance:", self.override_balance_edit)

        # Profiles (Advanced)
        self.chk_remember = QCheckBox("Remember this mapping as a profile")
        self.profile_name_edit = QLineEdit(); self.profile_name_edit.setPlaceholderText("Profile name")

        # ---- Essentials rows (with green ✓ when auto-mapped) ----
        def _row_with_icon(widget):
            holder = QWidget()
            h = QHBoxLayout(holder); h.setContentsMargins(0,0,0,0)
            h.addWidget(widget); icon = QLabel("✓"); icon.setToolTip("Auto-mapped / complete")
            icon.setStyleSheet("color:#1b8f3a; font-weight:bold;")
            icon.setFixedWidth(16); icon.setAlignment(Qt.AlignCenter); icon.setVisible(False)
            h.addWidget(icon)
            return holder, icon

        date_row, self.icon_date = _row_with_icon(self.map_date)
        vendor_row, self.icon_vendor = _row_with_icon(self.map_vendor)

        # Amount cluster (mode + conditional fields share one row label)
        amt_widget = QWidget(); amt_layout = QHBoxLayout(amt_widget); amt_layout.setContentsMargins(0,0,0,0)
        amt_layout.addWidget(self.amount_mode)
        amt_layout.addWidget(QLabel(" | Amount:"))
        amt_layout.addWidget(self.map_amount)
        amt_layout.addWidget(QLabel(" | Debit:"))
        amt_layout.addWidget(self.map_debit)
        amt_layout.addWidget(QLabel("Credit:"))
        amt_layout.addWidget(self.map_credit)
        amt_layout.addWidget(QLabel(" | "))
        amt_layout.addWidget(self.chk_flip_signs)
        amt_row, self.icon_amount = _row_with_icon(amt_widget)

        acct_row, self.icon_account = _row_with_icon(self.account_combo)

        # Build essentials into Step-2 form
        s2.addRow(QLabel("<b>Required</b>"))
        s2.addRow("Date column:", date_row)
        s2.addRow("Vendor/Description column:", vendor_row)
        s2.addRow("Amount mapping:", amt_row)
        s2.addRow("Account:", acct_row)

        # ---- Collapsible Advanced panel ----
        self.adv_toggle = QPushButton("Show Advanced ▸")
        self.adv_toggle.setCheckable(True); self.adv_toggle.setChecked(False)
        self.adv_toggle.setStyleSheet("text-align:left; padding:6px;")
        s2.addRow(self.adv_toggle)

        self.adv_container = QWidget()
        adv = QFormLayout(self.adv_container)

        adv.addRow(QLabel("<b>Date & Amount Options</b>"))
        adv.addRow("Date format:", self.date_format)
        adv.addRow(self.chk_strip_currency)
        adv.addRow(self.chk_paren_negative)
        adv.addRow(self.chk_thousands)
        adv.addRow(self.chk_invert)

        adv.addRow(QLabel("<b>Optional Columns</b>"))
        adv.addRow("Memo/Notes:", self.map_memo)
        adv.addRow("External Id:", self.map_external_id)
        adv.addRow("Balance:", self.map_balance)
        adv.addRow("Type:", self.map_type)

        adv.addRow(QLabel("<b>Account Settings</b>"))
        adv.addRow("Account Type:", self.account_type_combo)
        adv.addRow(self.init_group)

        adv.addRow(QLabel("<b>Profile</b>"))
        adv.addRow(self.chk_remember)
        adv.addRow("Profile name:", self.profile_name_edit)

        s2.addRow(self.adv_container)
        self.adv_container.setVisible(False)

        def _toggle_advanced(checked):
            self.adv_container.setVisible(checked)
            self.adv_toggle.setText("Hide Advanced ▾" if checked else "Show Advanced ▸")
        self.adv_toggle.toggled.connect(_toggle_advanced)
        # ====== End Sprint 14 Step 2 block ======

        self.amount_mode.currentTextChanged.connect(self.on_amount_mode_changed)

        self.stack.addWidget(self.step2)

        # --- Step 3: preview
        self.step3 = QDialog(self); s3 = QVBoxLayout(self.step3)
        self.preview_table = QTableWidget(); self.preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview_info = QLabel("")
        s3.addWidget(self.preview_table); s3.addWidget(self.preview_info)
        self.stack.addWidget(self.step3)

        self.stack.setCurrentIndex(0); self._update_nav()

    # ---------- Navigation
    def _update_nav(self):
        idx = self.stack.currentIndex()
        self.btn_back.setEnabled(idx > 0)
        self.btn_next.setEnabled(idx < self.stack.count() - 1)
        self.btn_import.setEnabled(idx == self.stack.count() - 1)
        # Friendly label: Step 2 points to Preview
        if idx == 1:
            self.btn_next.setText("Next → Preview")
        else:
            self.btn_next.setText("Next")


    def on_back(self):
        self.stack.setCurrentIndex(self.stack.currentIndex() - 1)
        self._update_nav()

    def on_next(self):
        idx = self.stack.currentIndex()
        if idx == 0:
            if not self.file_path:
                QMessageBox.warning(self, "No file", "Please select a file first.")
                return
            self.populate_mapping_controls()
            self.stack.setCurrentIndex(1)
        elif idx == 1:
            if not self.validate_mapping():
                return
            self.build_preview()
            self.stack.setCurrentIndex(2)
        self._update_nav()

    # ---------- Step 1
    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Data Files (*.csv *.xls *.xlsx);;All Files (*)")
        if not path: return
        self.file_path = path
        self.file_ext = os.path.splitext(path)[1].lower().lstrip(".")
        self.path_edit.setText(self.file_path)

        try:
            if self.file_ext == "csv":
                self.raw_df = pd.read_csv(self.file_path, dtype=str, keep_default_na=False)
            elif self.file_ext in ("xls", "xlsx"):
                self.raw_df = pd.read_excel(self.file_path, dtype=str, keep_default_na=False, engine=None)
            else:
                QMessageBox.warning(self, "Unsupported", f"Unsupported file type: .{self.file_ext}")
                self.raw_df = None; return
        except Exception as e:
            QMessageBox.critical(self, "Load error", f"Could not read the file:\n{e}")
            self.raw_df = None; return

        if self.raw_df is None or self.raw_df.empty:
            self.detect_label.setText("<span style='color:orange'>File is empty or unreadable.</span>"); return

        self.headers = list(self.raw_df.columns)
        prof = match_profile(self.headers, self.file_ext, self.profiles)
        if prof:
            self.mapping = prof.get("mapping", {})
            cleaners = prof.get("cleaners", {})
            self.mapping["strip_currency"] = cleaners.get("strip_currency", True)
            self.mapping["paren_negative"] = cleaners.get("paren_negative", True)
            self.mapping["thousands_sep"] = cleaners.get("thousands_sep", True)
            self.mapping["invert_amount"] = cleaners.get("invert_amount", False)
            self.detect_label.setText(f"Matched profile: <b>{prof.get('name','(unnamed)')}</b>")
        else:
            self.mapping = guess_mapping(self.headers)
            self.detect_label.setText("No profile matched. Mapping guessed — please review.")

    # ---------- Step 2
    def populate_mapping_controls(self):
        if self.raw_df is None: return
        cols = [""] + normalize_headers(self.headers)

        def fill(combo, pre):
            combo.clear(); combo.addItems(cols)
            if pre and pre in cols: combo.setCurrentText(pre)

        fill(self.map_date, self.mapping.get("date",""))
        fill(self.map_vendor, self.mapping.get("vendor",""))
        fill(self.map_amount, self.mapping.get("amount",""))
        fill(self.map_debit, self.mapping.get("debit",""))
        fill(self.map_credit, self.mapping.get("credit",""))
        fill(self.map_memo, self.mapping.get("memo",""))
        fill(self.map_external_id, self.mapping.get("external_id",""))
        fill(self.map_balance, self.mapping.get("balance",""))
        fill(self.map_type, self.mapping.get("type",""))

        amode = self.mapping.get("amount_mode","single_amount")
        self.amount_mode.setCurrentText("Single Amount column" if amode == "single_amount" else "Debit/Credit columns")
        self.on_amount_mode_changed(self.amount_mode.currentText())

        fmt = self.mapping.get("date_format")
        label = next((lab for lab, ff in DATE_FORMAT_CHOICES if ff == fmt), "Auto")
        self.date_format.setCurrentText(label)

        self.chk_strip_currency.setChecked(bool(self.mapping.get("strip_currency", True)))
        self.chk_paren_negative.setChecked(bool(self.mapping.get("paren_negative", True)))
        self.chk_thousands.setChecked(bool(self.mapping.get("thousands_sep", True)))
        self.chk_invert.setChecked(bool(self.mapping.get("invert_amount", False)))

        # --- Normalization option (quick toggle) ---
        if not hasattr(self, "chk_flip_signs"):
            self.chk_flip_signs = QCheckBox("Flip amounts so expenses become negative")
            self.chk_flip_signs.setToolTip(
                "Enable this if your file uses credit-card style: purchases are positive and payments are negative.\n"
                "When checked, the wizard will multiply all Amounts by -1 before import."
            )
            # Add into Step-2 form, on its own row
            self.s2.addRow("", self.chk_flip_signs)
            # Optional: live-update preview if user is on Step 3
            self.chk_flip_signs.toggled.connect(self._rebuild_preview_if_on_step3)

        # Sprint 14: connect change signals to update green ✓ once
        if not getattr(self, "_req_icon_signals_connected", False):
            self.map_date.currentTextChanged.connect(self._update_required_icons)
            self.map_vendor.currentTextChanged.connect(self._update_required_icons)
            self.map_amount.currentTextChanged.connect(self._update_required_icons)
            self.map_debit.currentTextChanged.connect(self._update_required_icons)
            self.map_credit.currentTextChanged.connect(self._update_required_icons)
            self.amount_mode.currentTextChanged.connect(self._update_required_icons)
            self.account_combo.currentTextChanged.connect(self._update_required_icons)
            self._req_icon_signals_connected = True

        # Initial tick state now that combos are filled
        if hasattr(self, "_update_required_icons"):
            self._update_required_icons()


        # account default
        if self.app.accounts:
            self.account_combo.setCurrentText(self.app.accounts[0]["name"])
            self.account_choice = self.app.accounts[0]["name"]
        else:
            self.account_choice = "Unassigned"

        # profile name suggestion
        base = os.path.basename(self.file_path)
        self.profile_name_edit.setText(os.path.splitext(base)[0])

    def on_amount_mode_changed(self, txt):
        is_single = txt.startswith("Single")

        # Toggle visibility of fields inside the Amount cluster
        self.map_amount.setVisible(is_single)
        # Hide its " | Amount:" label too (it’s the item right before map_amount)
        self.map_amount.parentWidget().layout().itemAt(1).widget().setVisible(is_single)

        self.map_debit.setVisible(not is_single)
        self.map_credit.setVisible(not is_single)
        # Hide their labels too (they’re just before each field)
        self.map_debit.parentWidget().layout().itemAt(3).widget().setVisible(not is_single)
        self.map_credit.parentWidget().layout().itemAt(5).widget().setVisible(not is_single)

        # Flip-signs control stays visible in both modes

        # Rebuild preview if on Step 3
        self._rebuild_preview_if_on_step3()

        if hasattr(self, "_update_required_icons"):
            self._update_required_icons()


    # Sprint 14: show green ✓ when essentials are mapped/complete
    def _update_required_icons(self):
        try:
            self.icon_date.setVisible(bool(self.map_date.currentText().strip()))
            self.icon_vendor.setVisible(bool(self.map_vendor.currentText().strip()))
            # Amount considered “ready” if (single & amount chosen) OR (DC & at least one of debit/credit chosen)
            if self.amount_mode.currentText().startswith("Single"):
                amt_ok = bool(self.map_amount.currentText().strip())
            else:
                amt_ok = bool(self.map_debit.currentText().strip() or self.map_credit.currentText().strip())
            self.icon_amount.setVisible(amt_ok)
            # Account ✓ when a real account (not the “Add new…” sentinel) is selected
            acct = self.account_combo.currentText().strip()
            self.icon_account.setVisible(bool(acct and not acct.startswith("➕")))
        except Exception:
            # Icons are purely cosmetic; fail-safe if widgets are not ready
            pass


    def on_account_changed(self, val):
        if val == "➕ Add new account…":
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(self, "New Account", "Account name:")
            if ok and name.strip():
                try:
                    # create with zero starting balance; parent app persists
                    self.app.accounts.append({
                        "name": name.strip(),
                        "balance": 0.0,
                        "starting_balance": 0.0,
                        "type": self.account_type_combo.currentText() if hasattr(self, "account_type_combo") else "Asset"
                    })
                    self.app.save_json("accounts.json", self.app.accounts)
                except Exception as e:
                    QMessageBox.critical(self, "Account", f"Could not create account:\n{e}")
                self.account_combo.clear()
                self.account_combo.addItems([a["name"] for a in self.app.accounts] + ["➕ Add new account…"])
                self.account_combo.setCurrentText(name.strip())
                self.account_choice = name.strip()
            else:
                if self.app.accounts:
                    self.account_combo.setCurrentText(self.app.accounts[0]["name"])
                    self.account_choice = self.app.accounts[0]["name"]
                else:
                    self.account_choice = "Unassigned"
        else:
            self.account_choice = val
            self._rebuild_preview_if_on_step3()  # NEW Sprint 9

    def validate_mapping(self):
        if not self.map_date.currentText().strip() or not self.map_vendor.currentText().strip():
            QMessageBox.warning(self, "Mapping", "Please select Date and Vendor columns."); return False
        if self.amount_mode.currentText().startswith("Single"):
            if not self.map_amount.currentText().strip():
                QMessageBox.warning(self, "Mapping", "Please select the Amount column."); return False
        else:
            if not (self.map_debit.currentText().strip() or self.map_credit.currentText().strip()):
                QMessageBox.warning(self, "Mapping", "Select at least one of Debit or Credit columns."); return False
        return True

    # ---------- Step 3
    def build_preview(self):
        # collect mapping
        self.mapping["date"] = self.map_date.currentText().strip()
        self.mapping["vendor"] = self.map_vendor.currentText().strip()
        self.mapping["amount_mode"] = "single_amount" if self.amount_mode.currentText().startswith("Single") else "debit_credit"
        self.mapping["amount"] = self.map_amount.currentText().strip()
        self.mapping["debit"] = self.map_debit.currentText().strip()
        self.mapping["credit"] = self.map_credit.currentText().strip()
        self.mapping["memo"] = self.map_memo.currentText().strip()
        self.mapping["external_id"] = self.map_external_id.currentText().strip()
        self.mapping["balance"] = self.map_balance.currentText().strip()
        self.mapping["type"] = self.map_type.currentText().strip()
        label = self.date_format.currentText()
        self.mapping["date_format"] = next((ff for lab, ff in DATE_FORMAT_CHOICES if lab == label), None)
        self.mapping["strip_currency"] = self.chk_strip_currency.isChecked()
        self.mapping["paren_negative"] = self.chk_paren_negative.isChecked()
        self.mapping["thousands_sep"] = self.chk_thousands.isChecked()
        self.mapping["invert_amount"] = self.chk_invert.isChecked()

        df = self.raw_df.copy()
        existing_keys = set()
        if not self.app.df.empty:
            for _, ex in self.app.df.iterrows():
                ex_row = {
                    "Date": ex.get("Date", ""),
                    "Vendor": (ex.get("Vendor") or ""),
                    "Amount": ex.get("Amount", 0.0),
                    "Account": ex.get("Account", ""),
                    "ExternalId": (ex.get("ExternalId") or ""),
                }
                existing_keys.add(dup_key(ex_row))

        self.preview_rows = []; self.preview_flags = []; seen = set()
        flip_quick = bool(getattr(self, "chk_flip_signs", None) and self.chk_flip_signs.isChecked())
        invert_effective = bool(self.mapping.get("invert_amount", False)) ^ flip_quick  # XOR: only flip once

        opts = dict(
            strip_currency=self.mapping["strip_currency"],
            paren_negative=self.mapping["paren_negative"],
            thousands_sep=self.mapping["thousands_sep"],
            invert=invert_effective
        )


        for _, row in df.iterrows():
            date_val = parse_date_value(row.get(self.mapping["date"]), self.mapping["date_format"])
            vendor = clean_vendor(row.get(self.mapping["vendor"]))
            if self.mapping["amount_mode"] == "single_amount":
                amount = parse_amount_value(row.get(self.mapping["amount"]), **opts)
            else:
                amount = compute_amount_from_dc(row.get(self.mapping["debit"]), row.get(self.mapping["credit"]), **opts)

            norm = {
                "Date": date_val.strftime("%Y-%m-%d") if date_val else "",
                "Vendor": vendor,
                "Amount": amount if amount is not None else "",
                "Memo": (row.get(self.mapping["memo"]) if self.mapping["memo"] else "") or "",
                "ExternalId": (row.get(self.mapping["external_id"]) if self.mapping["external_id"] else "") or "",
                "Account": self.account_choice or "Unassigned"
            }

            valid = True; err = ""
            if not norm["Date"]: valid = False; err = "Bad date"
            if norm["Amount"] in ["", None]:
                valid = False; err = (err + ", " if err else "") + "Bad amount"

            key = dup_key(norm)
            is_dup = key in existing_keys or key in seen
            if not is_dup: seen.add(key)

            self.preview_rows.append(norm)
            self.preview_flags.append({"valid": valid, "duplicate": is_dup, "error": err})

        cols = ["Date", "Vendor", "Amount", "Account", "Duplicate?", "Valid?", "Error", "ExternalId", "Memo"]
        self.preview_table.setColumnCount(len(cols))
        self.preview_table.setHorizontalHeaderLabels(cols)
        self.preview_table.setRowCount(len(self.preview_rows))

        dup_cnt = inv_cnt = 0
        for r, row in enumerate(self.preview_rows):
            flags = self.preview_flags[r]
            self.preview_table.setItem(r, 0, QTableWidgetItem(row["Date"]))
            self.preview_table.setItem(r, 1, QTableWidgetItem(row["Vendor"]))
            amt_item = QTableWidgetItem("" if row["Amount"] in ["", None] else f"${float(row['Amount']):,.2f}")
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.preview_table.setItem(r, 2, amt_item)
            self.preview_table.setItem(r, 3, QTableWidgetItem(row["Account"]))
            self.preview_table.setItem(r, 4, QTableWidgetItem("Yes" if flags["duplicate"] else "No"))
            self.preview_table.setItem(r, 5, QTableWidgetItem("Yes" if flags["valid"] else "No"))
            self.preview_table.setItem(r, 6, QTableWidgetItem(flags["error"]))
            self.preview_table.setItem(r, 7, QTableWidgetItem(row["ExternalId"]))
            self.preview_table.setItem(r, 8, QTableWidgetItem(row["Memo"]))

            if flags["duplicate"]:
                dup_cnt += 1
                for c in range(self.preview_table.columnCount()):
                    it = self.preview_table.item(r, c)
                    if it: it.setBackground(Qt.darkYellow)
            if not flags["valid"]:
                inv_cnt += 1
                for c in range(self.preview_table.columnCount()):
                    it = self.preview_table.item(r, c)
                    if it:
                        it.setBackground(Qt.darkRed); it.setForeground(Qt.white)

        self.preview_table.resizeColumnsToContents()
        ok = len(self.preview_rows) - dup_cnt - inv_cnt
        self.preview_info.setText(f"Rows: {len(self.preview_rows)}  |  Valid (non-dup): {ok}  |  Duplicates: {dup_cnt}  |  Invalid: {inv_cnt}")

        # ---- NEW: compute net for initialization preview (valid + non-duplicate rows only) ----
        net = 0.0
        for i, row in enumerate(self.preview_rows):
            flags = self.preview_flags[i]
            if not flags["valid"] or flags["duplicate"]:
                continue
            try:
                amt = float(row.get("Amount") or 0.0)
            except Exception:
                amt = 0.0
            net += amt

        # Update the Step-2 label so user sees the expected initialization value
        # Note: account assignment is uniform for this import (Account column already set per row)
        self.init_net_label.setText(f"{'$' + format(net, ',.2f')}")

    def _rebuild_preview_if_on_step3(self, *_):
        if self.stack.currentIndex() == 2:
            self.build_preview()

    # ---------- Commit
    def on_commit(self):
        if not self.preview_rows:
            QMessageBox.information(self, "Import", "No rows to import.")
            return

        # Keep only valid, non-duplicate rows
        rows = []
        for i, row in enumerate(self.preview_rows):
            f = self.preview_flags[i]
            if f["valid"] and not f["duplicate"]:
                rows.append(row)
        if not rows:
            QMessageBox.information(self, "Import", "All rows are invalid or duplicates. Nothing to import.")
            return

        # Backup transactions csv before write (best effort)
        try:
            tx_path = "sample_transactions.csv"
            if os.path.exists(tx_path):
                stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                shutil.copy(tx_path, f"sample_transactions.backup-{stamp}.csv")
        except Exception as e:
            QMessageBox.warning(self, "Backup", f"Backup failed (continuing):\n{e}")

        # ---- NEW: determine initialization path and final init value (inside method) ----
        def _parse_override(txt):
            if not txt or not str(txt).strip():
                return None
            try:
                return float(str(txt).strip())
            except Exception:
                return None

        use_init = bool(self.chk_init_from_import.isChecked())
        override_val = _parse_override(self.override_balance_edit.text())

        # Compute net using exactly the rows we will commit (valid + non-dup)
        net_for_init = 0.0
        for r in rows:
            try:
                net_for_init += float(r.get("Amount") or 0.0)
            except Exception:
                pass

        init_value = None
        if override_val is not None:
            init_value = override_val
        elif use_init:
            init_value = net_for_init

        # Append to parent df
        appended = 0
        for r in rows:
            try:
                new_id = self.app._next_tx_id()
                applied_flag = "True" if init_value is not None else "False"  # mark applied if used for init
                self.app.df.loc[len(self.app.df)] = {
                    "Id": int(new_id),
                    "Date": r["Date"],
                    "Vendor": r["Vendor"],
                    "Amount": float(r["Amount"]),
                    # Type remains based on sign; Transfer support comes in next sprint
                    "Type": "Expense" if float(r["Amount"]) < 0 else "Income",
                    "Category": "Uncategorized",
                    "Account": r.get("Account") or "Unassigned",
                    "AppliedToBalance": applied_flag,
                    "ExternalId": r.get("ExternalId", ""),
                }
                appended += 1
            except Exception:
                pass

        # If initializing, set the selected/new account's balances now (starting_balance and balance)
        try:
            if init_value is not None:
                acct_name = self.account_choice or "Unassigned"
                # Update (or create) the account record in app.accounts
                idx = next((i for i, a in enumerate(self.app.accounts) if a.get("name") == acct_name), None)
                acct_type = self.account_type_combo.currentText() if hasattr(self, "account_type_combo") else "Asset"
                if idx is None:
                    # Should not happen (wizard already created account), but guard anyway
                    self.app.accounts.append({
                        "name": acct_name,
                        "balance": float(init_value),
                        "starting_balance": float(init_value),
                        "type": acct_type
                    })
                else:
                    # Update balances and type (non-breaking: main app ignores 'type' if unused)
                    self.app.accounts[idx]["balance"] = float(init_value)
                    self.app.accounts[idx]["starting_balance"] = float(init_value)
                    self.app.accounts[idx]["type"] = acct_type
                self.app.save_json("accounts.json", self.app.accounts)
        except Exception as e:
            QMessageBox.warning(self, "Account Initialization", f"Could not set account balance:\n{e}")

        # Save & refresh
        self.app.save_transactions()
        self.app.refresh_all()

        # Save profile (optional)
        if self.chk_remember.isChecked():
            name = self.profile_name_edit.text().strip() or "Unnamed profile"
            prof = {
                "name": name,
                "fingerprint": {"headers": lower_headers(self.headers), "ext": self.file_ext},
                "mapping": {
                    "date": self.mapping.get("date", ""),
                    "vendor": self.mapping.get("vendor", ""),
                    "amount_mode": self.mapping.get("amount_mode", "single_amount"),
                    "amount": self.mapping.get("amount", ""),
                    "debit": self.mapping.get("debit", ""),
                    "credit": self.mapping.get("credit", ""),
                    "memo": self.mapping.get("memo", ""),
                    "external_id": self.mapping.get("external_id", ""),
                    "balance": self.mapping.get("balance", ""),
                    "type": self.mapping.get("type", ""),
                    "date_format": self.mapping.get("date_format", None),
                },
                "cleaners": {
                    "strip_currency": self.mapping.get("strip_currency", True),
                    "paren_negative": self.mapping.get("paren_negative", True),
                    "thousands_sep": self.mapping.get("thousands_sep", True),
                    "invert_amount": self.mapping.get("invert_amount", False),
                },
            }
            profiles = load_profiles()
            # overwrite by name if exists
            for i, p in enumerate(profiles):
                if p.get("name", "") == name:
                    profiles[i] = prof
                    break
            else:
                profiles.append(prof)
            save_profiles(profiles)

        QMessageBox.information(self, "Import complete", f"Imported {appended} transaction(s).")
        self.accept()

