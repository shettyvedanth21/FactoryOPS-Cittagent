-- ============================================================
-- ENERGY PLATFORM - DATABASE BOOTSTRAP SCRIPT
-- Idempotent and safe to re-run
-- ============================================================

-- 1️⃣ Create application user (if not exists)
CREATE USER IF NOT EXISTS 'energy'@'%' IDENTIFIED BY 'energy';

-- 2️⃣ Create databases
CREATE DATABASE IF NOT EXISTS energy_device_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS energy_rule_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS energy_analytics_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS energy_export_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS energy_reporting_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 3️⃣ Grant privileges per database (least privilege model)
GRANT ALL PRIVILEGES ON energy_device_db.* TO 'energy'@'%';
GRANT ALL PRIVILEGES ON energy_rule_db.* TO 'energy'@'%';
GRANT ALL PRIVILEGES ON energy_analytics_db.* TO 'energy'@'%';
GRANT ALL PRIVILEGES ON energy_export_db.* TO 'energy'@'%';
GRANT ALL PRIVILEGES ON energy_reporting_db.* TO 'energy'@'%';

-- 4️⃣ Apply privilege changes
FLUSH PRIVILEGES;

-- ============================================================
-- END OF BOOTSTRAP
-- ============================================================
