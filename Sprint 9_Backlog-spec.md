# 🚀 Sprint 9 – Import Wizard Inline Account Setup

## 🎯 Goal
Enable users to create new accounts during import (especially credit cards) and initialize their balances correctly from either the imported transactions or a known statement balance. Ensure overlapping imports don’t double-count.

---

## 🧑‍💻 User Stories
1. **As a user**, I can create a new account inline during import so I don’t have to switch to the Accounts tab first.  
2. **As a user**, I can specify whether the account is an Asset or Credit Card so it behaves correctly in net-worth totals.  
3. **As a user**, I can initialize the account’s starting/current balance using the computed net of the imported file so my balances start aligned.  
4. **As a user**, I can override that computed net with the actual statement closing balance so the account matches reality even if the file covers partial history.  
5. **As a user**, I expect the transactions used for initialization to be marked as already applied so balances aren’t double-counted later.  
6. **As a user**, I expect overlapping imports (e.g., months 1–5 and then 3–8) to detect duplicates and not add them twice.

---

## 🔨 Dev Tasks
- [x] Add **Account Type** dropdown (Asset / Credit Card) in Import Wizard step 2.  
- [x] Add **Account Initialization** group in step 2 with:  
  - “Initialize from this import” checkbox  
  - Computed net label (updates in preview)  
  - Override balance input  
- [x] Update **build_preview()** to compute and display net of valid, non-duplicate rows.  
- [x] Extend **on_commit()**:  
  - Parse override, else use computed net if “init” checked  
  - Create/update account balances accordingly (`balance` and `starting_balance`)  
  - Mark imported rows `AppliedToBalance=True` if used for initialization  
- [x] Save `type` field with accounts in `accounts.json`.  
- [x] Ensure duplicate detection uses consistent `dup_key` logic (with `ExternalId`) across existing and preview rows.  
- [x] Persist `ExternalId` into transactions so future overlapping imports dedupe correctly.  
- [x] Update UI preview live when toggling flip-signs, account selection, or amount mode.  

---

## ✅ Acceptance Criteria
- [x] Import Wizard step 2 shows **Account Type** and **Account Initialization** controls.  
- [x] “Computed net” reflects sum of valid, non-duplicate rows in preview.  
- [x] If “Initialize from this import” is checked:  
  - Account `starting_balance` and `balance` = computed net  
  - Imported rows are `AppliedToBalance=True`  
- [x] If override provided:  
  - Account `starting_balance` and `balance` = override value  
  - Imported rows are `AppliedToBalance=True`  
- [x] If neither option is selected:  
  - Account is created with balance=0.0 (same as pre-Sprint 9 behavior)  
- [x] Overlapping imports flag duplicates and don’t re-commit them.  
- [x] New account appears on **Accounts** tab immediately with correct balance and type.  
- [x] Dashboard “Total Balance Across All Accounts” reflects Asset balances positive, Credit Card balances negative.  
