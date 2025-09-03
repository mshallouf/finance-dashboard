# Sprint 2 Review

## Features Completed
- Budgets: Add/Edit/Remove per category
- Dashboard: Properly displays spend/budget/remaining with color coding
- Multi-account CRUD support

## Deferred
- Account balance auto-update via transactions

## Testing
- All features tested manually with edge cases
- Known issues documented

## Retrospective
- What went well: the implementation of the features, responsive, 4 tabs total now all working together and linked
- What didn’t: 
if a transaction had a category, and the category was assigned a budget, when the transaction was deleted, the category in budget disapperead, but it still appeared in the dashboard as it still retained the data - implemented manual deletion
The transactions are negative float, while budget was positive float, so remaninder calculation was wrong
differment of the account balance updating because it is not very relevant
- Improvements: 
We need to start working better on the UI and interface
We need to start making user centric approaches to formatting 
Monthly implementation must be done next
