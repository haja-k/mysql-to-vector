-- Create migration_tracker table
CREATE TABLE migration_tracker (
    id SERIAL PRIMARY KEY,
    id_migrated INT DEFAULT 0
);

-- Initialize migration_tracker
INSERT INTO migration_tracker (id_migrated) VALUES (0);