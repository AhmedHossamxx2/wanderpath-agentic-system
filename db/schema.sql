-- Enable foreign key enforcement in SQLite (required for every connection)
PRAGMA foreign_keys = ON;

-- Table: clients
CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    phone VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: passports
CREATE TABLE passports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    passport_number VARCHAR UNIQUE NOT NULL,
    country_code VARCHAR(3) NOT NULL,
    expiration_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

-- Table: agents
CREATE TABLE agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    role VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Defensive constraint based on DBML note
    CHECK (role IN ('junior_agent', 'senior_manager'))
);

-- Table: itineraries
CREATE TABLE itineraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    assigned_agent_id INTEGER NOT NULL,
    title VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_agent_id) REFERENCES agents(id),
    -- Defensive constraint based on DBML note
    CHECK (status IN ('draft', 'confirmed', 'completed', 'cancelled'))
);

-- Table: flights
CREATE TABLE flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_number VARCHAR NOT NULL,
    airline VARCHAR NOT NULL,
    origin_airport VARCHAR(3) NOT NULL,
    destination_airport VARCHAR(3) NOT NULL,
    departure_time TIMESTAMP NOT NULL,
    arrival_time TIMESTAMP NOT NULL,
    base_price DECIMAL(10,2) NOT NULL
);

-- Table: hotels
CREATE TABLE hotels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    city VARCHAR NOT NULL,
    country VARCHAR NOT NULL,
    default_cancellation_policy VARCHAR NOT NULL,
    price_per_night DECIMAL(10,2) NOT NULL,
    -- Defensive constraint based on DBML note
    CHECK (default_cancellation_policy IN ('refundable', 'nonrefundable'))
);

-- Table: bookings
CREATE TABLE bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id INTEGER NOT NULL,
    booking_type VARCHAR NOT NULL,
    flight_id INTEGER,
    hotel_id INTEGER,
    status VARCHAR NOT NULL,
    is_refundable BOOLEAN NOT NULL DEFAULT 1,
    cancellation_fee DECIMAL(10,2) DEFAULT 0.00,
    total_price DECIMAL(10,2) NOT NULL,
    check_in_date DATE,
    check_out_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (itinerary_id) REFERENCES itineraries(id) ON DELETE CASCADE,
    FOREIGN KEY (flight_id) REFERENCES flights(id),
    FOREIGN KEY (hotel_id) REFERENCES hotels(id),
    -- Defensive constraint based on DBML note
    CHECK (status IN ('active', 'pending_cancellation', 'cancelled')),
    CHECK (booking_type IN ('flight', 'hotel')),
    -- Polymorphic integrity constraint: Ensures exclusively one FK is populated based on type
    CHECK (
        (booking_type = 'flight' AND flight_id IS NOT NULL AND hotel_id IS NULL) OR 
        (booking_type = 'hotel' AND hotel_id IS NOT NULL AND flight_id IS NULL)
    )
);

-- Table: payments
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id INTEGER NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_status VARCHAR NOT NULL,
    payment_method VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (itinerary_id) REFERENCES itineraries(id) ON DELETE CASCADE,
    -- Defensive constraint based on DBML note
    CHECK (payment_status IN ('pending', 'completed', 'refunded'))
);

-- ============================================================================
-- FINAL PROJECT STATE GRAPH PERSISTENCE & RECOVERY SCHEMAS
-- ============================================================================

-- Table: state_checkpoints (Durable Checkpoint Storage for Crash-and-Resume)
CREATE TABLE IF NOT EXISTS state_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id VARCHAR NOT NULL,
    checkpoint_id VARCHAR UNIQUE NOT NULL,
    parent_checkpoint_id VARCHAR,
    graph_name VARCHAR NOT NULL,
    current_node VARCHAR NOT NULL,
    state_data TEXT NOT NULL, -- JSON serialized graph state
    step_number INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: hitl_tasks (Expected Human-in-the-Loop Escalations)
CREATE TABLE IF NOT EXISTS hitl_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR UNIQUE NOT NULL,
    thread_id VARCHAR NOT NULL,
    graph_name VARCHAR NOT NULL,
    node_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'PENDING',
    reason VARCHAR NOT NULL,
    threshold_info VARCHAR,
    payload TEXT, -- JSON contextual snapshot
    admin_decision VARCHAR, -- APPROVED / REJECTED
    admin_notes TEXT,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'))
);

-- Table: failure_tickets (Unplanned Mid-Node Runtime Failures & Recovery)
CREATE TABLE IF NOT EXISTS failure_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id VARCHAR UNIQUE NOT NULL,
    thread_id VARCHAR NOT NULL,
    graph_name VARCHAR NOT NULL,
    failed_node VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'OPEN',
    error_message TEXT NOT NULL,
    error_traceback TEXT,
    checkpoint_id VARCHAR,
    state_data TEXT, -- JSON state snapshot at moment of crash
    resolution_notes TEXT,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('OPEN', 'INVESTIGATING', 'RESOLVED', 'ABORTED'))
);