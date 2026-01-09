-- AgentVerse Database Initialization
-- This script runs when PostgreSQL container starts for the first time

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create custom types if needed
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('user', 'admin', 'enterprise');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE user_tier AS ENUM ('free', 'pro', 'team', 'enterprise');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE simulation_status AS ENUM ('pending', 'running', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE scenario_status AS ENUM ('draft', 'ready', 'running', 'completed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE agentverse TO postgres;
