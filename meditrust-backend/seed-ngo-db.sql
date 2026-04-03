-- Seed NGO Database (ngo_db)
-- Run this first: mysql -u root -p < seed-ngo-db.sql

CREATE DATABASE IF NOT EXISTS ngo_db;
USE ngo_db;

-- NGO Identity Table
CREATE TABLE IF NOT EXISTS ngo_identity (
  ngo_id INT PRIMARY KEY AUTO_INCREMENT,
  ngo_name VARCHAR(255) NOT NULL,
  contact_email VARCHAR(255) NOT NULL,
  phone_number VARCHAR(50),
  alternate_phone VARCHAR(50),
  headquarters_city VARCHAR(100),
  state VARCHAR(100),
  website_url VARCHAR(255),
  registration_number VARCHAR(100),
  INDEX idx_email (contact_email),
  INDEX idx_state (state)
);

-- NGO Medical Capability Table
CREATE TABLE IF NOT EXISTS ngo_medical_capability (
  ngo_id INT PRIMARY KEY,
  disease_cardiac TINYINT(1) DEFAULT 0,
  disease_cancer TINYINT(1) DEFAULT 0,
  disease_neuro TINYINT(1) DEFAULT 0,
  disease_kidney TINYINT(1) DEFAULT 0,
  disease_liver TINYINT(1) DEFAULT 0,
  disease_orthopedic TINYINT(1) DEFAULT 0,
  disease_eye TINYINT(1) DEFAULT 0,
  disease_rare TINYINT(1) DEFAULT 0,
  disease_general TINYINT(1) DEFAULT 0,
  supports_children TINYINT(1) DEFAULT 0,
  supports_adults TINYINT(1) DEFAULT 0,
  supports_elderly TINYINT(1) DEFAULT 0,
  FOREIGN KEY (ngo_id) REFERENCES ngo_identity(ngo_id)
);

-- NGO Funding Capacity Table
CREATE TABLE IF NOT EXISTS ngo_funding_capacity (
  ngo_id INT PRIMARY KEY,
  max_grant_per_patient_inr DECIMAL(10,2),
  avg_grant_per_patient_inr DECIMAL(10,2),
  annual_budget_range VARCHAR(100),
  csr_connected TINYINT(1) DEFAULT 0,
  government_support TINYINT(1) DEFAULT 0,
  registration_80G TINYINT(1) DEFAULT 0,
  FOREIGN KEY (ngo_id) REFERENCES ngo_identity(ngo_id)
);

-- NGO Eligibility & Application Table
CREATE TABLE IF NOT EXISTS ngo_eligibility_application (
  ngo_id INT PRIMARY KEY,
  income_eligibility_max_inr DECIMAL(10,2),
  online_application_available TINYINT(1) DEFAULT 0,
  processing_time_days INT,
  FOREIGN KEY (ngo_id) REFERENCES ngo_identity(ngo_id)
);

-- NGO System Info Table
CREATE TABLE IF NOT EXISTS ngo_system_info (
  ngo_id INT PRIMARY KEY,
  geographic_scope VARCHAR(50),
  primary_state VARCHAR(100),
  hospital_partnership_known VARCHAR(10),
  FOREIGN KEY (ngo_id) REFERENCES ngo_identity(ngo_id)
);

-- Insert 20 Sample NGOs
INSERT INTO ngo_identity (ngo_id, ngo_name, contact_email, phone_number, alternate_phone, headquarters_city, state, website_url, registration_number) VALUES
(1, 'Genesis Foundation', 'contact@genesis-foundation.net', '+91 9681767118', '+91 9821456789', 'New Delhi', 'Delhi', 'https://genesis-foundation.org', 'DL/2023/NGO/12345'),
(2, 'Hope Trust', 'info@hopetrust.in', '+91 9845671234', '+91 9123456789', 'Mumbai', 'Maharashtra', 'https://hopetrust.in', 'MH/2022/NGO/67890'),
(3, 'Smile Foundation', 'donate@smilefoundation.org', '+91 9988776655', '+91 9765432109', 'Bangalore', 'Karnataka', 'https://smilefoundation.org', 'KA/2023/NGO/11111'),
(4, 'Care India', 'contact@careindia.org', '+91 9123456780', '+91 9876543210', 'Hyderabad', 'Telangana', 'https://careindia.org', 'TS/2022/NGO/22222'),
(5, 'HelpAge India', 'support@helpageindia.org', '+91 9876543211', '+91 9234567890', 'Chennai', 'Tamil Nadu', 'https://helpageindia.org', 'TN/2023/NGO/33333'),
(6, 'Child Rights and You', 'info@cry.org', '+91 9765432101', '+91 9123456781', 'Kolkata', 'West Bengal', 'https://cry.org', 'WB/2022/NGO/44444'),
(7, 'Nanhi Kali', 'donate@nanhikali.org', '+91 9988776652', '+91 9876543212', 'Pune', 'Maharashtra', 'https://nanhikali.org', 'MH/2023/NGO/55555'),
(8, 'Pratham', 'contact@pratham.org', '+91 9234567891', '+91 9765432102', 'Ahmedabad', 'Gujarat', 'https://pratham.org', 'GJ/2022/NGO/66666'),
(9, 'SEWA', 'info@sewa.org', '+91 9876543213', '+91 9123456782', 'Jaipur', 'Rajasthan', 'https://sewa.org', 'RJ/2023/NGO/77777'),
(10, 'Milaap Foundation', 'contact@milaap.org', '+91 9765432103', '+91 9988776653', 'Lucknow', 'Uttar Pradesh', 'https://milaap.org', 'UP/2022/NGO/88888'),
(11, 'GiveIndia', 'donate@giveindia.org', '+91 9123456783', '+91 9876543214', 'Bhopal', 'Madhya Pradesh', 'https://giveindia.org', 'MP/2023/NGO/99999'),
(12, 'Oxfam India', 'info@oxfamindia.org', '+91 9988776654', '+91 9234567892', 'Chandigarh', 'Punjab', 'https://oxfamindia.org', 'PB/2022/NGO/10101'),
(13, 'Save the Children India', 'contact@savethechildren.in', '+91 9876543215', '+91 9765432104', 'Indore', 'Madhya Pradesh', 'https://savethechildren.in', 'MP/2023/NGO/20202'),
(14, 'ActionAid India', 'info@actionaidindia.org', '+91 9234567893', '+91 9988776655', 'Nagpur', 'Maharashtra', 'https://actionaidindia.org', 'MH/2022/NGO/30303'),
(15, 'World Vision India', 'donate@worldvision.in', '+91 9765432105', '+91 9123456784', 'Coimbatore', 'Tamil Nadu', 'https://worldvision.in', 'TN/2023/NGO/40404'),
(16, 'UNICEF India', 'contact@unicef.in', '+91 9988776656', '+91 9876543216', 'Trivandrum', 'Kerala', 'https://unicef.in', 'KL/2022/NGO/50505'),
(17, 'Doctors Without Borders India', 'info@msf.in', '+91 9234567894', '+91 9765432106', 'Vijayawada', 'Andhra Pradesh', 'https://msf.in', 'AP/2023/NGO/60606'),
(18, 'Red Cross India', 'donate@redcross.in', '+91 9876543217', '+91 9123456785', 'Visakhapatnam', 'Andhra Pradesh', 'https://redcross.in', 'AP/2022/NGO/70707'),
(19, 'Lions Club India Foundation', 'contact@lionsclub.in', '+91 9765432107', '+91 9988776657', 'Mysore', 'Karnataka', 'https://lionsclub.in', 'KA/2023/NGO/80808'),
(20, 'Rotary Foundation India', 'info@rotary.org', '+91 9234567895', '+91 9876543218', 'Hubli', 'Karnataka', 'https://rotary.org', 'KA/2022/NGO/90909');

-- Insert Medical Capabilities
INSERT INTO ngo_medical_capability (ngo_id, disease_cardiac, disease_cancer, disease_neuro, disease_kidney, disease_liver, disease_orthopedic, disease_eye, disease_rare, disease_general, supports_children, supports_adults, supports_elderly) VALUES
(1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1),
(2, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0),
(3, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0),
(4, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1),
(5, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1),
(6, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0),
(7, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0),
(8, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0),
(9, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1),
(10, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1),
(11, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0),
(12, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1),
(13, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0),
(14, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1),
(15, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0),
(16, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1),
(17, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1),
(18, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0),
(19, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1),
(20, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0);

-- Insert Funding Capacity
INSERT INTO ngo_funding_capacity (ngo_id, max_grant_per_patient_inr, avg_grant_per_patient_inr, annual_budget_range, csr_connected, government_support, registration_80G) VALUES
(1, 500000.00, 250000.00, '5-10 Crore', 1, 1, 1),
(2, 300000.00, 150000.00, '2-5 Crore', 1, 0, 1),
(3, 750000.00, 400000.00, '10-20 Crore', 1, 1, 1),
(4, 200000.00, 100000.00, '1-2 Crore', 0, 1, 1),
(5, 150000.00, 75000.00, '50 Lakh - 1 Crore', 1, 0, 1),
(6, 400000.00, 200000.00, '5-10 Crore', 1, 1, 1),
(7, 100000.00, 50000.00, '20-50 Lakh', 0, 0, 1),
(8, 250000.00, 125000.00, '2-5 Crore', 1, 0, 1),
(9, 180000.00, 90000.00, '1-2 Crore', 0, 1, 1),
(10, 350000.00, 175000.00, '5-10 Crore', 1, 1, 1),
(11, 600000.00, 300000.00, '10-20 Crore', 1, 1, 1),
(12, 220000.00, 110000.00, '2-5 Crore', 0, 1, 1),
(13, 280000.00, 140000.00, '5-10 Crore', 1, 0, 1),
(14, 320000.00, 160000.00, '5-10 Crore', 1, 1, 1),
(15, 450000.00, 225000.00, '10-20 Crore', 1, 1, 1),
(16, 800000.00, 400000.00, '20-50 Crore', 1, 1, 1),
(17, 550000.00, 275000.00, '10-20 Crore', 1, 1, 1),
(18, 170000.00, 85000.00, '1-2 Crore', 0, 0, 1),
(19, 260000.00, 130000.00, '5-10 Crore', 1, 1, 1),
(20, 380000.00, 190000.00, '10-20 Crore', 1, 1, 1);

-- Insert Eligibility & Application
INSERT INTO ngo_eligibility_application (ngo_id, income_eligibility_max_inr, online_application_available, processing_time_days) VALUES
(1, 800000.00, 1, 7),
(2, 500000.00, 1, 10),
(3, 1200000.00, 1, 5),
(4, 300000.00, 0, 14),
(5, 400000.00, 1, 10),
(6, 600000.00, 1, 7),
(7, 200000.00, 1, 21),
(8, 350000.00, 1, 14),
(9, 250000.00, 0, 10),
(10, 700000.00, 1, 7),
(11, 1000000.00, 1, 5),
(12, 280000.00, 1, 10),
(13, 450000.00, 1, 7),
(14, 330000.00, 1, 10),
(15, 650000.00, 1, 7),
(16, 1500000.00, 1, 3),
(17, 900000.00, 1, 5),
(18, 220000.00, 0, 14),
(19, 380000.00, 1, 10),
(20, 750000.00, 1, 7);

-- Insert System Info
INSERT INTO ngo_system_info (ngo_id, geographic_scope, primary_state, hospital_partnership_known) VALUES
(1, 'National', 'Delhi', 'Yes'),
(2, 'State', 'Maharashtra', 'Yes'),
(3, 'National', 'Karnataka', 'Yes'),
(4, 'State', 'Telangana', 'No'),
(5, 'National', 'Tamil Nadu', 'Yes'),
(6, 'National', 'West Bengal', 'Yes'),
(7, 'Regional', 'Maharashtra', 'No'),
(8, 'State', 'Gujarat', 'Yes'),
(9, 'State', 'Rajasthan', 'Yes'),
(10, 'National', 'Uttar Pradesh', 'Yes'),
(11, 'National', 'Madhya Pradesh', 'Yes'),
(12, 'State', 'Punjab', 'No'),
(13, 'State', 'Madhya Pradesh', 'Yes'),
(14, 'National', 'Maharashtra', 'Yes'),
(15, 'National', 'Tamil Nadu', 'Yes'),
(16, 'National', 'Kerala', 'Yes'),
(17, 'National', 'Andhra Pradesh', 'Yes'),
(18, 'State', 'Andhra Pradesh', 'Yes'),
(19, 'State', 'Karnataka', 'No'),
(20, 'National', 'Karnataka', 'Yes');

-- Verify counts
SELECT 'NGO Identity' as table_name, COUNT(*) as count FROM ngo_identity
UNION ALL
SELECT 'NGO Medical Capability', COUNT(*) FROM ngo_medical_capability
UNION ALL
SELECT 'NGO Funding Capacity', COUNT(*) FROM ngo_funding_capacity
UNION ALL
SELECT 'NGO Eligibility Application', COUNT(*) FROM ngo_eligibility_application
UNION ALL
SELECT 'NGO System Info', COUNT(*) FROM ngo_system_info;
