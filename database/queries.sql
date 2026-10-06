-- =====================================================
-- IT Assist : SQL QUERIES FOR DEMO / VIVA
-- =====================================================
USE it_assist;

-- ---------- A. Basic DML (wrapped in a transaction so data is not lost) ----------
START TRANSACTION;
INSERT INTO departments (department_name, location) VALUES ('Legal', 'Building C - Floor 1');
UPDATE assets SET location = 'Head Office' WHERE asset_tag = 'LAP-001';
DELETE FROM departments WHERE department_name = 'Legal';
SELECT * FROM departments;
ROLLBACK;

-- ---------- B. Required queries ----------
-- 1. All assets
SELECT a.asset_id, a.asset_tag, a.asset_name, c.category_name, a.status, a.purchase_cost
FROM assets a JOIN asset_categories c ON c.category_id = a.category_id;
-- 2. Available assets
SELECT * FROM available_assets;
-- 3. Assigned assets
SELECT * FROM assigned_assets;
-- 4. Assets under maintenance
SELECT asset_tag, asset_name, location FROM assets WHERE status = 'Under Maintenance';
-- 5. Employees by department
SELECT d.department_name, e.employee_name, e.designation
FROM employees e INNER JOIN departments d ON d.department_id = e.department_id
ORDER BY d.department_name, e.employee_name;
-- 6. Assets assigned to employees
SELECT e.employee_name, a.asset_tag, a.asset_name, aa.assigned_date
FROM asset_assignments aa
JOIN employees e ON e.employee_id = aa.employee_id
JOIN assets a    ON a.asset_id = aa.asset_id
WHERE aa.assignment_status = 'Active';
-- 7. Warranty expiring in next 90 days
SELECT asset_tag, asset_name, warranty_expiry, DATEDIFF(warranty_expiry, CURDATE()) AS days_left
FROM assets
WHERE warranty_expiry BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 90 DAY)
ORDER BY warranty_expiry;
-- 8. Most expensive assets
SELECT asset_tag, asset_name, purchase_cost FROM assets ORDER BY purchase_cost DESC LIMIT 5;
-- 9. Average asset cost
SELECT ROUND(AVG(purchase_cost), 2) AS average_cost FROM assets;
-- 10. Count assets by category
SELECT c.category_name, COUNT(a.asset_id) AS total_assets
FROM asset_categories c LEFT JOIN assets a ON a.category_id = c.category_id
GROUP BY c.category_id, c.category_name;
-- 11. Count assets by department (currently assigned)
SELECT d.department_name, COUNT(aa.asset_id) AS assets_in_use
FROM departments d
LEFT JOIN employees e ON e.department_id = d.department_id
LEFT JOIN asset_assignments aa ON aa.employee_id = e.employee_id AND aa.assignment_status = 'Active'
GROUP BY d.department_id, d.department_name;
-- 12. Employees with assigned assets
SELECT DISTINCT e.employee_name FROM employees e
JOIN asset_assignments aa ON aa.employee_id = e.employee_id AND aa.assignment_status = 'Active';
-- 13. Assets with maintenance records
SELECT * FROM maintenance_summary;
-- 14. Total maintenance cost
SELECT SUM(cost) AS total_maintenance_cost FROM maintenance;
-- 15. High usage assets
SELECT * FROM asset_usage_summary WHERE usage_category = 'High Usage' ORDER BY utilization_rate DESC;
-- 16. Low usage assets
SELECT * FROM asset_usage_summary WHERE usage_category = 'Low Usage' ORDER BY utilization_rate;

-- ---------- C. JOINS ----------
-- INNER JOIN: only assets that have maintenance history
SELECT a.asset_tag, m.issue, m.cost
FROM assets a INNER JOIN maintenance m ON m.asset_id = a.asset_id;
-- LEFT JOIN: all employees, even those with no asset
SELECT e.employee_name, a.asset_tag
FROM employees e
LEFT JOIN asset_assignments aa ON aa.employee_id = e.employee_id AND aa.assignment_status = 'Active'
LEFT JOIN assets a ON a.asset_id = aa.asset_id;
-- LEFT JOIN + IS NULL: assets that never had any usage record
SELECT a.asset_tag, a.asset_name
FROM assets a LEFT JOIN asset_usage u ON u.asset_id = a.asset_id
WHERE u.usage_id IS NULL;

-- ---------- D. Aggregates: COUNT, SUM, AVG, MAX, MIN ----------
SELECT COUNT(*) AS total, SUM(purchase_cost) AS total_value, AVG(purchase_cost) AS avg_cost,
       MAX(purchase_cost) AS max_cost, MIN(purchase_cost) AS min_cost
FROM assets;

-- ---------- E. GROUP BY / HAVING ----------
-- Categories whose total value is above 5 lakh
SELECT c.category_name, COUNT(*) AS qty, SUM(a.purchase_cost) AS total_value
FROM assets a JOIN asset_categories c ON c.category_id = a.category_id
GROUP BY c.category_name
HAVING SUM(a.purchase_cost) > 500000;
-- Assets with more than one maintenance record
SELECT a.asset_tag, COUNT(m.maintenance_id) AS times_repaired
FROM assets a JOIN maintenance m ON m.asset_id = a.asset_id
GROUP BY a.asset_id, a.asset_tag
HAVING COUNT(m.maintenance_id) > 1;
-- Total usage and downtime by category
SELECT c.category_name, ROUND(AVG(u.usage_hours), 2) AS avg_hours, ROUND(SUM(u.downtime_hours), 1) AS downtime
FROM asset_usage u
JOIN assets a ON a.asset_id = u.asset_id
JOIN asset_categories c ON c.category_id = a.category_id
GROUP BY c.category_name;

-- ---------- F. SUBQUERIES ----------
-- Assets costing more than the average cost
SELECT asset_tag, asset_name, purchase_cost FROM assets
WHERE purchase_cost > (SELECT AVG(purchase_cost) FROM assets);
-- Employees who currently hold at least one asset
SELECT employee_name FROM employees
WHERE employee_id IN (SELECT employee_id FROM asset_assignments WHERE assignment_status = 'Active');
-- Assets that have never been repaired
SELECT asset_tag, asset_name FROM assets
WHERE NOT EXISTS (SELECT 1 FROM maintenance m WHERE m.asset_id = assets.asset_id);

-- ---------- G. Utilization analytics in SQL ----------
SELECT asset_tag, avg_usage_hours, utilization_rate, usage_category
FROM asset_usage_summary ORDER BY utilization_rate DESC;
