## MODIFIED Requirements

### Requirement: PostgreSQL system of record

All transactional sales data SHALL be stored in one PostgreSQL 16 database: accounts, contacts, opportunities, insights, actions, spend, quotes, carts, cart items, orders, order items, payments, payment events, payment rate limits, payment methods, fulfillments, customer master, notifications, notification dedup, products, and coverage. No service SHALL use a local database file at runtime.

#### Scenario: Two gateway instances
- **WHEN** two gateway instances and multiple agent services write orders concurrently
- **THEN** all writes are visible to every service without file synchronization

### Requirement: Seed data

A seed step SHALL load the demo dataset (the prospect accounts and related tables in `db/seed/001_sales_data.sql`, the 16-SKU product catalog, and the coverage data). It SHALL be safe to run repeatedly without duplicating rows.

#### Scenario: Seed twice
- **WHEN** the seed step runs twice
- **THEN** row counts equal those after the first run
