# 📅 Upcoming Sprints

This document outlines the planned work for Sprints 14 through 17.  
Each sprint is scoped to deliver usable improvements while keeping the work manageable.

---

## 🌀 Sprint 14 — Import Wizard Simplification

### 🎯 Goal
Make the Import Wizard easier for typical users by showing only essential fields up front, while still providing advanced controls when needed.

### 👤 User Stories
- As a user, I want to see only the required fields (Date, Vendor, Amount, Account) so the wizard feels simple.
- As a user, I want advanced options hidden until I need them, so I’m not overwhelmed.
- As a user, I want a clear preview and commit step, so I feel confident about what will happen.

### 🔨 Development Tasks
- Restructure **Step 2 (Mapping)**:
  - Show required fields: Date, Vendor, Amount / Debit-Credit toggle, Account (with “➕ New account…”).
  - Place all other fields into a **collapsible Advanced group** (collapsed by default).
- Advanced group includes:
  - Memo, ExternalId, Balance, Type
  - Cleaning options: strip currency, parentheses as negative, thousands separator, flip signs
  - Account initialization (net from import / override balance)
  - Save profile controls
- Add small helper text for required fields.
- Add green tick indicators for auto-mapped fields.
- Update button labels: “Next → Preview”, “Commit”.

### ✅ Acceptance Criteria
- Default view of Step 2 shows only required fields.
- Advanced controls are hidden until expanded.
- A typical CSV import can be done with just 3 steps: select file → map required fields → commit.
- No regressions in duplicate detection, account creation, initialization, or profile saving.

---

## 🌀 Sprint 15 — Auto-Categorizer Engine MVP

### 🎯 Goal
Implement the core **TF-IDF + vendor signature engine** with exact + signature matching only, plus dry-run preview and conflict handling.

### 👤 User Stories
- As a user, I want high-confidence matches auto-applied so I save time.
- As a user, I want a dry-run preview of auto-categorization changes so I can see what would happen before committing.
- As a user, I want conflicts handled safely so I don’t get incorrect assignments.

### 🔨 Development Tasks
- Create `autocategorize.py` module:
  - Tokenizer + IDF over last N months (default 9).
  - Signature extraction: top-K (K=2) tokens, min token length ≥ 3.
  - Store memories:
    - `autocat_str.json` (normalized vendor → category counts).
    - `autocat_sig.json` (signature → category counts).
    - `idf.json` (token IDFs).
    - `autocat_metadata.json` (last rebuild, correction count, false positive signatures).
  - Matching pipeline:
    - Exact string match.
    - Signature match (requires ≥ 2 confirmations and ≥ 1.5× dominance).
    - Compute confidence score.
  - Dry-run function: returns list of would-change transactions without committing.
  - Conflict handling: if multiple categories tied, only suggest (no auto-apply).
- Integrate in `main.py`:
  - Load/save engine at startup/shutdown.
  - On manual categorize: update memories, backfill uncategorized, migrate AUTO on second consistent correction.
  - On import: auto-apply only exact/signature matches that pass dominance.

### ✅ Acceptance Criteria
- “Dollarama Guelph” never auto-categorized as Gas.
- Only exact/signature matches with dominance auto-apply.
- Dry-run preview lists would-change transactions.
- Corrections immediately update memory; repeated corrections migrate AUTO rows.
- 1000+ transactions categorized in < 10 seconds.

---

## 🌀 Sprint 16 — Auto-Categorizer Balanced Mode

### 🎯 Goal
Expand coverage safely by adding IDF-weighted overlap and guarded fuzzy stages, with user mode toggle and recency weighting.

### 👤 User Stories
- As a user, I want a High-precision mode (strict) and Balanced mode (broader coverage) so I can choose the right trade-off.
- As a user, I want recent vendor corrections to matter more than old ones.

### 🔨 Development Tasks
- Add weighted-overlap stage:
  - Compute IDF-weighted Jaccard similarity.
  - Pre-filter: candidate must share ≥ 1 high-IDF token.
- Add guarded fuzzy stage:
  - Char-trigram similarity.
  - Pre-filter as above.
  - Threshold ~0.8 for suggestions or cautious auto-apply.
- Add Settings toggle:
  - **High precision**: only exact + signature auto-apply; others suggest only.
  - **Balanced**: allow overlap/fuzzy auto-apply if dominance + confidence threshold (≥ 0.6) are met.
- Implement recency weighting in IDF counts (decay factor, e.g., 0.9^months).
- Recompute IDF on startup and after imports.

### ✅ Acceptance Criteria
- Balanced mode increases auto-coverage without false city-based matches.
- High-precision mode behaves exactly like Sprint 15.
- Recency weighting ensures new habits adapt quickly.
- Performance acceptable up to 5000 transactions.

---

## 🌀 Sprint 17 — Auto-Categorizer Explainability & Review

### 🎯 Goal
Provide transparency into auto-categorization and tools for bulk correction and blocking misbehaving signatures.

### 👤 User Stories
- As a user, I want to see **why** a category was chosen so I can trust or correct it.
- As a user, I want to bulk review suggestions so I can approve or fix them quickly.
- As a user, I want to block bad rules so they never apply again.

### 🔨 Development Tasks
- Add “Why this?” tooltip:
  - Show signature tokens and confidence score.
- Add bulk review view/filter for **Suggestions**:
  - Approve or reject multiple transactions at once.
- Add blocklist feature:
  - Store `(signature → category)` pairs that should never auto-apply.
  - Update engine to respect blocklist.
- Update metadata with correction counts, false-positive signatures, last rebuild timestamp.

### ✅ Acceptance Criteria
- Every auto/suggested categorization shows “Why this?” explanation.
- Bulk review workflows (approve/reject) are functional and update engine.
- Blocklisted signatures are never applied again.
- Metadata reflects corrections and false positives.