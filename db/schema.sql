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