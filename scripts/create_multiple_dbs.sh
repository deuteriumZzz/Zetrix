#!/bin/bash
set -e

for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        SELECT 'CREATE DATABASE $db' WHERE NOT EXISTS (
            SELECT FROM pg_database WHERE datname = '$db'
        )\\gexec
EOSQL
done

# bali_market needs PostGIS for the geo app's boundary/point fields; airflow's
# metadata DB has no geometry columns and doesn't need the extension.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "bali_market" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS postgis;
EOSQL
