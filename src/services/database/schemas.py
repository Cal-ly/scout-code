"""Database schema definitions for Scout.

This module contains SQL schema definitions for all database tables.
Schema version 2 introduces the User/Profile separation with normalized
related tables (skills, experiences, education, certifications, languages).
"""

# Schema version - increment when making schema changes
SCHEMA_VERSION = 2

# SQL schema for all tables
SCHEMA_SQL = """
-- Users table (identity/auth - future)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT,
    display_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Profiles table (career personas/CVs)
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    title TEXT,
    email TEXT,
    phone TEXT,
    location TEXT,
    summary TEXT,
    is_active INTEGER DEFAULT 0,
    is_demo INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Profile skills (normalized)
CREATE TABLE IF NOT EXISTS profile_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    level TEXT CHECK(level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    years INTEGER,
    category TEXT,
    sort_order INTEGER DEFAULT 0
);

-- Profile experiences (normalized)
CREATE TABLE IF NOT EXISTS profile_experiences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    description TEXT,
    achievements TEXT,
    sort_order INTEGER DEFAULT 0
);

-- Profile education (normalized)
CREATE TABLE IF NOT EXISTS profile_education (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    institution TEXT NOT NULL,
    degree TEXT,
    field TEXT,
    start_date TEXT,
    end_date TEXT,
    gpa TEXT,
    achievements TEXT,
    sort_order INTEGER DEFAULT 0
);

-- Profile certifications (normalized)
CREATE TABLE IF NOT EXISTS profile_certifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    issuer TEXT,
    date_obtained TEXT,
    expiry_date TEXT,
    credential_url TEXT,
    sort_order INTEGER DEFAULT 0
);

-- Profile languages (normalized)
CREATE TABLE IF NOT EXISTS profile_languages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    proficiency TEXT CHECK(
        proficiency IN ('basic', 'conversational', 'professional', 'fluent', 'native')
    ),
    sort_order INTEGER DEFAULT 0
);

-- Applications (updated with user_id)
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    profile_id INTEGER REFERENCES profiles(id),
    job_id TEXT UNIQUE NOT NULL,
    job_title TEXT,
    company_name TEXT,
    status TEXT DEFAULT 'pending',
    compatibility_score REAL,
    cv_path TEXT,
    cover_letter_path TEXT,
    job_text TEXT,
    analysis_data TEXT,
    pipeline_data TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_profiles_slug ON profiles(slug);
CREATE INDEX IF NOT EXISTS idx_profiles_is_active ON profiles(is_active);
CREATE INDEX IF NOT EXISTS idx_profile_skills_profile_id ON profile_skills(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_experiences_profile_id ON profile_experiences(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_education_profile_id ON profile_education(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_certs_profile_id ON profile_certifications(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_languages_profile_id ON profile_languages(profile_id);
CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_profile_id ON applications(profile_id);
CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);
"""


def get_drop_tables_sql() -> str:
    """Return SQL to drop all tables (for testing/reset).

    Tables are dropped in reverse dependency order to handle foreign keys.
    """
    return """
DROP TABLE IF EXISTS profile_languages;
DROP TABLE IF EXISTS profile_certifications;
DROP TABLE IF EXISTS profile_education;
DROP TABLE IF EXISTS profile_experiences;
DROP TABLE IF EXISTS profile_skills;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS profiles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS settings;
"""
