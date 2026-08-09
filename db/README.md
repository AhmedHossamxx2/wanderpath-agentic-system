# Database Architecture (`db/`)

## Overview
The `db/` directory contains the normalized relational database schemas, seed data, and ERD architectural definitions for **Wanderpath Travel B.** The database enforces strict ANSI-SQL data integrity constraints, Role-Based Access Control (RBAC) linking, and explicit security boundaries designed to isolate sensitive customer PII.

---

## File Manifest
* `schema.sql`: ANSI-SQL creation script establishing all tables, primary keys, foreign keys, and defensive check constraints.
* `seed.sql`: Seed data script populating normal operational records and targeted edge cases (non-refundable flight bookings, expired passports, pending cancellations).
* `schema.dbml`: DBML source file used to generate visual Entity-Relationship Diagrams (ERDs).

---

## Relational Entity Structure

[clients] ──┬──< [passports] (PII Isolation)
└──< [itineraries] >── [agents] (RBAC Assigned)
│
├──< [bookings] ──┬──> [flights]
│                 └──> [hotels]
└──< [payments]


### Table Specifications
1. `clients`: Root customer profile information (`id`, `first_name`, `last_name`, `email`, `phone`).
2. `passports`: Sensitive customer identification records (`passport_number`, `country_code`, `expiration_date`). Isolated from `clients` to prevent accidental PII exposure during routine queries.
3. `agents`: Role-based system users (`role`: `'junior_agent'` | `'senior_manager'`).
4. `itineraries`: Aggregates multi-segment travel plans under an assigned agent (`assigned_agent_id`).
5. `flights` & `hotels`: Read-only catalog inventory.
6. `bookings`: Polymorphic active reservation table linked to itineraries. Enforces refundability status (`is_refundable`) and cancellation fees.
7. `payments`: Tracks completed, pending, and refunded transactions.

---

## Key Safety & Design Decisions
* **PII Data Isolation**: Passport numbers and expiration dates are stored in a dedicated `passports` table rather than directly in `clients`. General itinerary retrieval tools query `clients` and `itineraries`, preventing PII from leaking into the LLM context window unless international entry validation is explicitly invoked.
* **Polymorphic Integrity Constraint**: The `bookings` table enforces a database-level `CHECK` constraint:
  ```sql
  CHECK (
      (booking_type = 'flight' AND flight_id IS NOT NULL AND hotel_id IS NULL) OR 
      (booking_type = 'hotel' AND hotel_id IS NOT NULL AND flight_id IS NULL)
  )