
CREATE DATABASE IF NOT EXISTS smart_curriculum
CHARACTER SET utf8mb4
COLLATE utf8mb4_0900_ai_ci;

USE smart_curriculum;

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id int NOT NULL AUTO_INCREMENT,
    name varchar(100) DEFAULT NULL,
    email varchar(100) DEFAULT NULL,
    password varchar(255) DEFAULT NULL,
    role varchar(20) DEFAULT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY email (email)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;

-- 2. SUBJECTS TABLE
CREATE TABLE IF NOT EXISTS subjects (
    id int NOT NULL AUTO_INCREMENT,
    subject_name varchar(100) DEFAULT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;

-- 3. ASSIGNMENTS TABLE
CREATE TABLE IF NOT EXISTS assignments (
    id int NOT NULL AUTO_INCREMENT,
    user_id int DEFAULT NULL,
    title varchar(200) DEFAULT NULL,
    description text,
    subject_id int DEFAULT NULL,
    status varchar(20) NOT NULL DEFAULT 'Pending',
    due_date date DEFAULT NULL,
    PRIMARY KEY (id),
    KEY subject_id (subject_id),
    KEY fk_assignments_user (user_id),
    CONSTRAINT assignments_ibfk_1
        FOREIGN KEY (subject_id) REFERENCES subjects (id),
    CONSTRAINT fk_assignments_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE SET NULL
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;

-- 4. RESULTS TABLE
CREATE TABLE IF NOT EXISTS results (
    id int NOT NULL AUTO_INCREMENT,
    user_id int DEFAULT NULL,
    assignment_id int DEFAULT NULL,
    marks int DEFAULT NULL,
    PRIMARY KEY (id),
    KEY user_id (user_id),
    KEY assignment_id (assignment_id),
    CONSTRAINT results_ibfk_1
        FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT results_ibfk_2
        FOREIGN KEY (assignment_id) REFERENCES assignments (id)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;
