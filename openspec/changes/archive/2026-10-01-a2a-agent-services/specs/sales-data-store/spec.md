# Spec Delta: sales-data-store

## Purpose

Defines PostgreSQL as the single system of record for sales data: schema lifecycle, seed data, concurrency expectations and cross-service notification delivery.

## ADDED Requirements

### Requirement: PostgreSQL system of record

All transactional sales data SHALL be stored in one PostgreSQL 16 database: accounts, contacts, opportunities, insights, actions, spend, quotes, carts, cart items, orders, order items, payments, payment events, payment rate limits, payment methods, fulfillments, customer master, notifications, notification dedup, products, and coverage. SQLite files SHALL NOT be used at runtime.

#### Scenario: Two gateway instances
- **WHEN** two gateway instances and multiple agent services write orders concurrently
- **THEN** all writes are visible to every service without file synchronization

### Requirement: Versioned migrations

Schema changes SHALL be applied by ordered, idempotent SQL migration files. The migration runner SHALL record applied versions and skip them on re-run.

#### Scenario: Re-running migrations
- **WHEN** the migration runner is executed twice against the same database
- **THEN** the second run applies nothing and exits 0

### Requirement: Seed data

A seed step SHALL load the demo dataset (the prospect accounts and related tables currently in `sales_agent.db`, the 16-SKU product catalog, and the coverage data). It SHALL be safe to run repeatedly without duplicating rows.

#### Scenario: Seed twice
- **WHEN** the seed step runs twice
- **THEN** row counts equal those after the first run

### Requirement: Notification outbox

Services other than customer communication SHALL request customer notifications by inserting a `notifications` row with status `pending`, in the same transaction as the business change that triggers it. The customer communication service SHALL deliver pending notifications:
- at least once
- after de-duplication
- marking each row `sent` or `failed` with an error message

#### Scenario: Order confirmation
- **WHEN** `order_agent` creates order `ORD-1` for a contact with an email address
- **THEN** a `notifications` row of type `order_confirmation` with status `pending` exists in the same commit, and is later marked `sent` (or `simulated` when SMTP is disabled)

#### Scenario: Communication service down
- **WHEN** the customer communication service is not running while an order is created
- **THEN** order creation still succeeds, and the notification is delivered after the service starts

### Requirement: Credentials never in source

Database credentials SHALL be supplied only through environment variables or Secret Manager, and SHALL NOT be logged.

#### Scenario: Startup logging
- **WHEN** a service logs its database target at startup
- **THEN** the password component of the URL is masked
