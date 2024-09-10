SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname in ('admin_db');
DROP DATABASE IF EXISTS admin_db;
DROP ROLE IF EXISTS admin_role;
CREATE ROLE admin_role WITH SUPERUSER
  LOGIN
  PASSWORD 'admin_password';
CREATE DATABASE admin_db OWNER admin_role;
