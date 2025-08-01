-- This script is used by Dockerfile.postgres during container initialization
-- It runs after PostgreSQL is fully initialized
-- Execution order: 02-create-databases.sql (create databases)
--
-- Create databases for each microservice

-- User service database
CREATE DATABASE briefly_user;

-- Meetings service database
CREATE DATABASE briefly_meetings;

-- Shipments service database
CREATE DATABASE briefly_shipments;

-- Office service database
CREATE DATABASE briefly_office;

-- Chat service database
CREATE DATABASE briefly_chat;

-- Vector database (for embeddings)
CREATE DATABASE briefly_vector;

-- Grant privileges to postgres user on all databases
GRANT ALL PRIVILEGES ON DATABASE briefly_user TO postgres;
GRANT ALL PRIVILEGES ON DATABASE briefly_meetings TO postgres;
GRANT ALL PRIVILEGES ON DATABASE briefly_shipments TO postgres;
GRANT ALL PRIVILEGES ON DATABASE briefly_office TO postgres;
GRANT ALL PRIVILEGES ON DATABASE briefly_chat TO postgres;
GRANT ALL PRIVILEGES ON DATABASE briefly_vector TO postgres;