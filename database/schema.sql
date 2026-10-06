-- =====================================================
-- IT Assist - Inventory Management System : SCHEMA
-- Requires MySQL 8.0.16+ (for CHECK constraints)
-- =====================================================
CREATE DATABASE IF NOT EXISTS it_assist CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE it_assist;

SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW  IF EXISTS available_assets;
DROP VIEW  IF EXISTS assigned_assets;
DROP VIEW  IF EXISTS asset_usage_summary;
DROP VIEW  IF EXISTS maintenance_summary;
DROP TABLE IF EXISTS asset_usage;
DROP TABLE IF EXISTS maintenance;
DROP TABLE IF EXISTS asset_assignments;
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS vendors;
DROP TABLE IF EXISTS asset_categories;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS departments;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. departments -------------------------------------
CREATE TABLE departments (
    department_id   INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(60)  NOT NULL UNIQUE,
    location        VARCHAR(100)
);

-- 2. employees ---------------------------------------
CREATE TABLE employees (
    employee_id   INT AUTO_INCREMENT PRIMARY KEY,
    employee_name VARCHAR(80)  NOT NULL,
    email         VARCHAR(100) NOT NULL UNIQUE,
    phone         VARCHAR(15),
    department_id INT NOT NULL,
    designation   VARCHAR(60),
    joining_date  DATE NOT NULL,
    status        VARCHAR(10) NOT NULL DEFAULT 'Active',
    CONSTRAINT fk_emp_dept FOREIGN KEY (department_id)
        REFERENCES departments(department_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_emp_status CHECK (status IN ('Active', 'Inactive'))
);

-- 3. asset_categories --------------------------------
CREATE TABLE asset_categories (
    category_id   INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    description   VARCHAR(200)
);

-- 4. vendors -----------------------------------------
CREATE TABLE vendors (
    vendor_id      INT AUTO_INCREMENT PRIMARY KEY,
    vendor_name    VARCHAR(80) NOT NULL,
    contact_person VARCHAR(80),
    phone          VARCHAR(15),
    email          VARCHAR(100)
);

-- 5. assets ------------------------------------------
CREATE TABLE assets (
    asset_id        INT AUTO_INCREMENT PRIMARY KEY,
    asset_tag       VARCHAR(20)  NOT NULL UNIQUE,
    asset_name      VARCHAR(100) NOT NULL,
    category_id     INT NOT NULL,
    vendor_id       INT NULL,
    brand           VARCHAR(50),
    model           VARCHAR(60),
    serial_number   VARCHAR(50) NOT NULL UNIQUE,
    purchase_date   DATE NOT NULL,
    purchase_cost   DECIMAL(12,2) NOT NULL,
    warranty_expiry DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'Available',
    location        VARCHAR(100),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_asset_category FOREIGN KEY (category_id)
        REFERENCES asset_categories(category_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_asset_vendor FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_asset_cost   CHECK (purchase_cost >= 0),
    CONSTRAINT chk_asset_status CHECK (status IN ('Available', 'Assigned', 'Under Maintenance', 'Retired'))
);

-- 6. asset_assignments (employee <-> asset history) ---
CREATE TABLE asset_assignments (
    assignment_id     INT AUTO_INCREMENT PRIMARY KEY,
    asset_id          INT NOT NULL,
    employee_id       INT NOT NULL,
    assigned_date     DATE NOT NULL,
    returned_date     DATE NULL,
    assignment_status VARCHAR(10) NOT NULL DEFAULT 'Active',
    remarks           VARCHAR(200),
    CONSTRAINT fk_assign_asset FOREIGN KEY (asset_id)
        REFERENCES assets(asset_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_assign_emp FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_assign_status CHECK (assignment_status IN ('Active', 'Returned')),
    CONSTRAINT chk_assign_dates  CHECK (returned_date IS NULL OR returned_date >= assigned_date)
);

-- 7. maintenance -------------------------------------
CREATE TABLE maintenance (
    maintenance_id   INT AUTO_INCREMENT PRIMARY KEY,
    asset_id         INT NOT NULL,
    issue            VARCHAR(200) NOT NULL,
    maintenance_date DATE NOT NULL,
    cost             DECIMAL(10,2) NOT NULL DEFAULT 0,
    status           VARCHAR(15) NOT NULL DEFAULT 'Pending',
    remarks          VARCHAR(200),
    CONSTRAINT fk_maint_asset FOREIGN KEY (asset_id)
        REFERENCES assets(asset_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_maint_cost   CHECK (cost >= 0),
    CONSTRAINT chk_maint_status CHECK (status IN ('Pending', 'In Progress', 'Completed'))
);

-- 8. asset_usage -------------------------------------
CREATE TABLE asset_usage (
    usage_id          INT AUTO_INCREMENT PRIMARY KEY,
    asset_id          INT NOT NULL,
    usage_date        DATE NOT NULL,
    usage_hours       DECIMAL(4,1) NOT NULL,
    performance_score INT NOT NULL,
    downtime_hours    DECIMAL(4,1) NOT NULL DEFAULT 0,
    CONSTRAINT fk_usage_asset FOREIGN KEY (asset_id)
        REFERENCES assets(asset_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_usage_hours    CHECK (usage_hours BETWEEN 0 AND 24),
    CONSTRAINT chk_usage_perf     CHECK (performance_score BETWEEN 0 AND 100),
    CONSTRAINT chk_usage_downtime CHECK (downtime_hours >= 0)
);

-- Helpful indexes on foreign keys / search columns
CREATE INDEX idx_assets_status     ON assets(status);
CREATE INDEX idx_assign_asset      ON asset_assignments(asset_id, assignment_status);
CREATE INDEX idx_usage_asset       ON asset_usage(asset_id);

-- =====================================================
-- VIEWS
-- =====================================================
CREATE VIEW available_assets AS
SELECT a.asset_id, a.asset_tag, a.asset_name, c.category_name, a.brand, a.model,
       a.purchase_cost, a.location
FROM assets a
JOIN asset_categories c ON c.category_id = a.category_id
WHERE a.status = 'Available';

CREATE VIEW assigned_assets AS
SELECT aa.assignment_id, a.asset_id, a.asset_tag, a.asset_name,
       e.employee_name, d.department_name, aa.assigned_date
FROM asset_assignments aa
JOIN assets a      ON a.asset_id = aa.asset_id
JOIN employees e   ON e.employee_id = aa.employee_id
JOIN departments d ON d.department_id = e.department_id
WHERE aa.assignment_status = 'Active';

-- utilization_rate = avg daily usage hours / 8 expected hours * 100 (capped at 100)
CREATE VIEW asset_usage_summary AS
SELECT a.asset_id, a.asset_tag, a.asset_name,
       COUNT(u.usage_id)                                  AS usage_records,
       ROUND(AVG(u.usage_hours), 2)                       AS avg_usage_hours,
       ROUND(AVG(u.performance_score), 1)                 AS avg_performance,
       ROUND(SUM(u.downtime_hours), 1)                    AS total_downtime,
       ROUND(LEAST(AVG(u.usage_hours) / 8 * 100, 100), 1) AS utilization_rate,
       CASE WHEN LEAST(AVG(u.usage_hours) / 8 * 100, 100) <= 40 THEN 'Low Usage'
            WHEN LEAST(AVG(u.usage_hours) / 8 * 100, 100) <= 75 THEN 'Normal Usage'
            ELSE 'High Usage' END                         AS usage_category
FROM assets a
JOIN asset_usage u ON u.asset_id = a.asset_id
GROUP BY a.asset_id, a.asset_tag, a.asset_name;

CREATE VIEW maintenance_summary AS
SELECT a.asset_id, a.asset_tag, a.asset_name,
       COUNT(m.maintenance_id) AS total_records,
       SUM(m.cost)             AS total_cost,
       MAX(m.maintenance_date) AS last_maintenance
FROM assets a
JOIN maintenance m ON m.asset_id = a.asset_id
GROUP BY a.asset_id, a.asset_tag, a.asset_name;
