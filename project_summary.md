Finance Tool Project – Summary & Context
🎯 Project Vision

The goal is to build a locally hosted personal finance tool, inspired by Monarch Money but open-source, that helps a single user:

Aggregate their financial information in one place.

Track transactions, budgets, and accounts.

View net worth snapshots, spending by category, and budget progress.

Auto-detect subscriptions and recurring expenses.

Run financial scenarios ("what if" simulations).

Eventually add AI-powered insights, auto-categorization rules, and investment/crypto portfolio tracking.

Be a private, offline-first tool that can later be open-sourced and shared on GitHub.

✅ What We’ve Done So Far
Setup

Installed Python 3.12, VS Code, and Git.

Project uses PySide6 (Qt for UI), pandas for data handling, and JSON/CSV for persistence.

Git initialized and used to checkpoint stable versions after each sprint.

Sprint History

Sprint 0 – Environment setup

Virtual environment, editor, git repo.

Chose tech stack (Python + PySide6 + pandas).

Designed CSV schema for sample transactions.

Sprint 1 – Core Transactions MVP

Import CSV transactions.

Parse into Date, Vendor, Amount, Category.

Show transactions in table.

Sum by category.

Basic manual add/edit/delete transactions.

Categories case-insensitive.

Transactions auto-sorted by date.

Sprint 2 – Budgets & Accounts

Added Budgets tab with ability to set budgets per category.

Budget persistence in JSON.

Dashboard added (show budgets + spending).

Added Accounts tab with manual balances.

Categories auto-refresh in budgets when new transactions are added.

Fixed negative/positive handling of expenses vs budgets.

Added "Remove budget" functionality.

Sprint 3 – Filters & Reports

Added date filters (This Month, Last Month, Custom).

Separate filters for Transactions vs Dashboard.

Reports tab introduced.

Dashboard enhancements:

Show budget progress bars.

Added charts (monthly spend by category, doughnut graphs).

Dark mode styling for charts.

Sprint 4–5 – UX Enhancements

Dashboard shows: balances, budgets, recent transactions, MTD by account, MTD by category.

Transaction tab improved: add/edit/delete with dedicated buttons.

"New Category" option in dropdown to create categories on the fly.

Reports tab styled with dark theme charts.

Dashboard charts redesigned as doughnut with central total.

Sprint 6 – Accounts & Budget Normalization

Account balance “Apply new transactions” button with popups for success/already-applied.

Budgets show their period (Daily/Weekly/Monthly) as chips, with monthly equivalents.

Dashboard filter controls independent of Transactions filters.

Import Wizard (post-Sprint 6 pivot)

Added Import Wizard to support external files (CSV, XLS).

User maps file columns to required fields (Date, Amount, Vendor, Category, Account).

Supports different banking conventions (expenses negative vs positive).

Added “Flip signs” checkbox to normalize amounts consistently.

Imported data integrated into the app’s JSON-backed storage.

Known bug: editing imported rows initially failed → fixed by ensuring transactions are stored in app’s master store (not just preview).

Utility Features

Added Clear All buttons for Transactions, Budgets, Accounts, Categories (testing convenience).

Stable commits maintained after each sprint.

📊 Current State of the App

Right now, the app can:

Import and manage transactions (CSV, XLS).

Add, edit, and delete transactions (with category management).

Maintain a persistent Budgets tab with flexible period entry.

Show dashboards with:

Net account balances (manual).

Budgets vs spend (with over-budget detection).

Recent transactions.

Month-to-date (MTD) spend by account.

MTD spend by category (list + doughnut chart).

Accounts tab for multiple accounts with balances.

Categories tab for adding/removing categories.

Reports tab for longer-term breakdowns (with dark-themed charts).

Clear-all feature for quick resets.

🐛 Bugs & Fixes

Editing imported transactions: fixed by ensuring imported rows are written into the app’s JSON-backed transaction store, not transient preview.

Budget disappearing if category deleted: added “remove budget” explicitly.

Progress bars capped at 100%: fixed so overspending shows >100%.

Graph labels overlapping: replaced with doughnut chart + legend.

Import triplicates when Commit pressed multiple times: prevented with AppliedToBalance flag and unique import IDs.

Menu bar AttributeError: fixed by moving from QWidget to QMainWindow for FinanceApp.

📌 Backlog
MVP (to finish before GitHub release)

Import Wizard stabilization

Full edit/delete support for imported transactions.

Deduplicate imports.

Save import mapping templates per account (future).

Budgets

Normalize across daily/weekly/monthly/yearly with rollups.

Dashboard clarity ("Monthly equivalents").

Dashboard

Show Net Worth (sum of accounts).

Better category filtering & budget-only view.

Reports

Month-over-month comparisons.

Filter categories over time.

User Settings

"Today override" (for testing).

Persistent dark/light theme toggle.

Documentation & Release

Finalize README, Requirements, Architecture doc.

Master retrospective (done).

License (MIT).

Push to GitHub.

Post-MVP (Future)

Bank API integration (Plaid).

Auto-categorization based on rules/history.

Subscription detection.

Scenario planning / financial simulations.

Investments & crypto tracking.

Multi-user profiles.

AI insights & anomaly detection.

🚀 How To Continue

Finish polishing MVP backlog (esp. import/edit consistency).

Write clean documentation.

Push repo to GitHub (public).

Collect feedback → plan feature roadmap (Monarch-like).