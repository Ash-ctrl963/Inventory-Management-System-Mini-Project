-- ============================================================
-- Inventory Management System - Database Setup
-- ============================================================

CREATE DATABASE IF NOT EXISTS inventory_db;
USE inventory_db;

CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,
    full_name   VARCHAR(100),
    role        ENUM('admin','manager','staff') DEFAULT 'staff',
    is_active   TINYINT(1) DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suppliers (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(150) NOT NULL,
    contact_person VARCHAR(100),
    phone          VARCHAR(20),
    email          VARCHAR(100),
    address        TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    name             VARCHAR(150) NOT NULL,
    sku              VARCHAR(50)  UNIQUE NOT NULL,
    barcode          VARCHAR(100),
    category_id      INT,
    supplier_id      INT,
    quantity         INT     DEFAULT 0,
    unit_price       DECIMAL(10,2) NOT NULL,
    selling_price    DECIMAL(10,2) NOT NULL,
    low_stock_alert  INT     DEFAULT 5,
    expiry_date      DATE    NULL,
    description      TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)  ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    supplier_id  INT,
    order_date   DATE NOT NULL,
    status       ENUM('pending','received','cancelled') DEFAULT 'pending',
    total_amount DECIMAL(12,2) DEFAULT 0,
    notes        TEXT,
    created_by   INT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by)  REFERENCES users(id)     ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    purchase_order_id INT NOT NULL,
    product_id        INT NOT NULL,
    quantity          INT NOT NULL,
    unit_price        DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id)        REFERENCES products(id)        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sales_orders (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(150),
    order_date    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status        ENUM('completed','refunded') DEFAULT 'completed',
    total_amount  DECIMAL(12,2) DEFAULT 0,
    discount      DECIMAL(10,2) DEFAULT 0,
    notes         TEXT,
    created_by    INT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sales_order_items (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    sales_order_id INT NOT NULL,
    product_id     INT NOT NULL,
    product_name   VARCHAR(150),
    quantity       INT NOT NULL,
    unit_price     DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (sales_order_id) REFERENCES sales_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id)     REFERENCES products(id)     ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stock_transactions (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    product_id       INT NOT NULL,
    transaction_type ENUM('purchase','sale','adjustment','return') NOT NULL,
    quantity         INT NOT NULL,
    unit_price       DECIMAL(10,2),
    reference_id     INT NULL,
    notes            TEXT,
    created_by       INT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)    ON DELETE SET NULL
);

-- ── Seed Data ─────────────────────────────────────────────────
INSERT IGNORE INTO users (username, password, full_name, role) VALUES
('admin',    'admin123',   'System Admin',  'admin'),
('manager1', 'manager123', 'Store Manager', 'manager'),
('staff1',   'staff123',   'Sales Staff',   'staff');

INSERT IGNORE INTO categories (name, description) VALUES
('Electronics',      'Devices and accessories'),
('Food & Beverages', 'Consumables'),
('Clothing',         'Apparel'),
('Medicines',        'Pharmaceuticals'),
('Office Supplies',  'Stationery');

INSERT IGNORE INTO suppliers (name, contact_person, phone, email) VALUES
('TechCorp',   'Raj Mehta',    '9876543210', 'raj@techcorp.com'),
('FreshMart',  'Priya Singh',  '9123456789', 'priya@freshmart.com'),
('PharmaDist', 'Dr. Suresh K', '9988776655', 'suresh@pharmadist.com');

INSERT IGNORE INTO products
  (name, sku, category_id, supplier_id, quantity, unit_price, selling_price, low_stock_alert, expiry_date) VALUES
('Laptop Dell i5',    'ELEC-001', 1, 1, 15, 45000, 55000, 5, NULL),
('USB 3.0 Hub',       'ELEC-002', 1, 1,  3,   500,   799, 5, NULL),
('Whole Wheat Bread', 'FOOD-001', 2, 2, 25,    40,    55, 5, DATE_ADD(CURDATE(), INTERVAL 7 DAY)),
('Orange Juice 1L',   'FOOD-002', 2, 2,  4,    80,   120, 5, DATE_ADD(CURDATE(), INTERVAL 3 DAY)),
('Milk 500ml',        'FOOD-003', 2, 2,  2,    25,    35, 5, DATE_ADD(CURDATE(), INTERVAL -2 DAY)),
('Paracetamol 500mg', 'MED-001',  4, 3, 50,     5,    12, 5, DATE_ADD(CURDATE(), INTERVAL 180 DAY)),
('Vitamin C 500mg',   'MED-002',  4, 3,  2,   150,   220, 5, DATE_ADD(CURDATE(), INTERVAL 30 DAY)),
('A4 Paper Ream',     'OFF-001',  5, 1,100,   250,   350, 5, NULL),
('Ballpoint Pens x10','OFF-002',  5, 1,  0,    60,    90, 5, NULL);

SELECT CONCAT('✅ Setup complete at ', NOW()) AS Status;
