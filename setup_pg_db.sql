-- Create migration_tracker table
CREATE TABLE migration_tracker (
    id SERIAL PRIMARY KEY,
    id_migrated INT DEFAULT 0
);

-- Initialize migration_tracker
INSERT INTO migration_tracker (id_migrated) VALUES (0);

-- Grant permission to user
GRANT SELECT, INSERT, UPDATE ON migration_tracker TO sainschat_user;
GRANT ALL ON SEQUENCE migration_tracker_id_seq TO sainschat_user;