-- Apply once:
--   docker compose exec -T postgres psql -U catalog -d catalog < backend/schema.sql
-- or, for Supabase: psql "$DATABASE_URL" -f schema.sql (or the Supabase SQL editor).
CREATE TABLE IF NOT EXISTS products (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       text        NOT NULL,
    image_key  text        NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
