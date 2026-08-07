-- Enable foreign key enforcement for SQLite
PRAGMA foreign_keys = ON;

-- Clear existing data for a clean reset
DELETE FROM payments;
DELETE FROM bookings;
DELETE FROM itineraries;
DELETE FROM passports;
DELETE FROM clients;
DELETE FROM agents;
DELETE FROM flights;
DELETE FROM hotels;

-- Reset SQLite autoincrement primary key sequences
DELETE FROM sqlite_sequence;

-- ============================================================================
-- 1. AGENTS
-- Supports: Role-Based Access Control (RBAC) & Notification Push Triggers
-- ============================================================================
INSERT INTO agents (id, name, email, role) VALUES
(1, 'Alice Walker', 'alice.walker@wanderpath.com', 'junior_agent'),
(2, 'Bob Vance', 'bob.vance@wanderpath.com', 'senior_manager');

-- ============================================================================
-- 2. CLIENTS
-- ============================================================================
INSERT INTO clients (id, first_name, last_name, email, phone) VALUES
(1, 'Liam', 'Neeson', 'liam.neeson@example.com', '+1-555-0101'),
(2, 'Sophia', 'Chen', 'sophia.chen@example.com', '+1-555-0102'),
(3, 'Marcus', 'Vance', 'marcus.vance@example.com', '+1-555-0103'),
(4, 'Elena', 'Rostova', 'elena.rostova@example.com', '+1-555-0104');

-- ============================================================================
-- 3. PASSPORTS (Normal & Edge Cases)
-- EDGE CASE 1: Expired Passport (Sophia Chen - expired 2024) -> Fails international flight policy resource check
-- EDGE CASE 2: Expiring Soon (Marcus Vance - <6 months validity) -> Triggers passport rule warning
-- NORMAL CASE: Valid Passport (Liam Neeson - expires 2030)
-- ============================================================================
INSERT INTO passports (id, client_id, passport_number, country_code, expiration_date) VALUES
(1, 1, 'US987654321', 'USA', '2030-12-31'), -- Normal: Valid passport
(2, 2, 'US123456789', 'USA', '2024-05-15'), -- EDGE CASE: Expired passport
(3, 3, 'US555444333', 'USA', '2026-09-30'), -- EDGE CASE: Expiring within 6 months
(4, 4, 'GB998877665', 'GBR', '2029-08-20'); -- Normal: Valid passport

-- ============================================================================
-- 4. FLIGHTS CATALOG
-- ============================================================================
INSERT INTO flights (id, flight_number, airline, origin_airport, destination_airport, departure_time, arrival_time, base_price) VALUES
(1, 'WP-101', 'WanderAir', 'JFK', 'LHR', '2026-10-15 08:00:00', '2026-10-15 20:00:00', 850.00),
(2, 'WP-202', 'PacificFly', 'SFO', 'HND', '2026-11-01 11:30:00', '2026-11-02 15:30:00', 1250.00),
(3, 'WP-303', 'EuroLink', 'LHR', 'CDG', '2026-10-20 09:00:00', '2026-10-20 11:15:00', 180.00),
(4, 'WP-404', 'IslandAir', 'LAX', 'DPS', '2026-12-05 22:00:00', '2026-12-07 06:00:00', 1400.00);

-- ============================================================================
-- 5. HOTELS CATALOG
-- ============================================================================
INSERT INTO hotels (id, name, city, country, default_cancellation_policy, price_per_night) VALUES
(1, 'The Ritz London', 'London', 'United Kingdom', 'refundable', 650.00),
(2, 'Tokyo Grand Palace', 'Tokyo', 'Japan', 'refundable', 320.00),
(3, 'Bali Sun & Sand Resort', 'Bali', 'Indonesia', 'nonrefundable', 450.00),
(4, 'Le Meurice Paris', 'Paris', 'France', 'refundable', 780.00);

-- ============================================================================
-- 6. ITINERARIES
-- Covers: Draft, Confirmed, Completed, Cancelled states & Ownership split
-- ============================================================================
INSERT INTO itineraries (id, client_id, assigned_agent_id, title, status, start_date, end_date) VALUES
(1, 1, 1, 'London Autumn Break', 'confirmed', '2026-10-15', '2026-10-22'), -- Junior Agent Alice
(2, 2, 1, 'Tokyo Cultural Tour', 'confirmed', '2026-11-01', '2026-11-10'), -- Junior Agent Alice (Contains Expired Passport client!)
(3, 3, 2, 'Luxury Bali Escape', 'draft', '2026-12-05', '2026-12-15'),     -- Senior Manager Bob
(4, 4, 1, 'Paris Weekend Getaway', 'completed', '2026-06-01', '2026-06-05'),-- Past trip
(5, 1, 1, 'Cancelled Rome Trip', 'cancelled', '2026-08-01', '2026-08-07');  -- Cancelled trip

-- ============================================================================
-- 7. BOOKINGS (Normal & Edge Cases)
-- EDGE CASE 1: Non-refundable Flight (`is_refundable = 0`) -> Calling cancellation tool MUST trigger MCP Elicitation!
-- EDGE CASE 2: Non-refundable Hotel with status `pending_cancellation`
-- Polymorphic Constraint: Strictly enforces (flight_id XOR hotel_id)
-- ============================================================================
INSERT INTO bookings (id, itinerary_id, booking_type, flight_id, hotel_id, status, is_refundable, cancellation_fee, total_price, check_in_date, check_out_date) VALUES
-- Itinerary 1: London Autumn Break (Standard Refundable)
(1, 1, 'flight', 1, NULL, 'active', 1, 0.00, 850.00, NULL, NULL),
(2, 1, 'hotel', NULL, 1, 'active', 1, 0.00, 4550.00, '2026-10-15', '2026-10-22'),

-- Itinerary 2: Tokyo Cultural Tour (EDGE CASE: Non-Refundable Flight -> Triggers Elicitation)
(3, 2, 'flight', 2, NULL, 'active', 0, 250.00, 1250.00, NULL, NULL), -- NON-REFUNDABLE FLIGHT
(4, 2, 'hotel', NULL, 2, 'active', 1, 0.00, 2880.00, '2026-11-02', '2026-11-11'),

-- Itinerary 3: Luxury Bali Escape (EDGE CASE: Non-refundable Hotel Pending Cancellation)
(5, 3, 'flight', 4, NULL, 'active', 1, 0.00, 1400.00, NULL, NULL),
(6, 3, 'hotel', NULL, 3, 'pending_cancellation', 0, 450.00, 4500.00, '2026-12-07', '2026-12-17'),

-- Itinerary 4: Completed Paris Trip
(7, 4, 'flight', 3, NULL, 'active', 1, 0.00, 180.00, NULL, NULL),
(8, 4, 'hotel', NULL, 4, 'active', 1, 0.00, 3120.00, '2026-06-01', '2026-06-05'),

-- Itinerary 5: Cancelled Rome Trip
(9, 5, 'flight', 1, NULL, 'cancelled', 1, 50.00, 850.00, NULL, NULL);

-- ============================================================================
-- 8. PAYMENTS
-- Covers: completed, pending, and refunded transactions
-- ============================================================================
INSERT INTO payments (id, itinerary_id, amount, payment_status, payment_method) VALUES
(1, 1, 5400.00, 'completed', 'credit_card'),
(2, 2, 4130.00, 'completed', 'credit_card'),
(3, 3, 5900.00, 'pending', 'bank_transfer'),
(4, 4, 3300.00, 'completed', 'credit_card'),
(5, 5, 800.00, 'refunded', 'credit_card');