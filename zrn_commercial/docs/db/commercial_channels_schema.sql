CREATE TABLE IF NOT EXISTS zrn_commercial_commercial_channel (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    code VARCHAR,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    company_id BIGINT NOT NULL REFERENCES res_company(id) ON DELETE RESTRICT,
    description TEXT,
    notes TEXT,
    create_uid BIGINT REFERENCES res_users(id) ON DELETE SET NULL,
    create_date TIMESTAMP,
    write_uid BIGINT REFERENCES res_users(id) ON DELETE SET NULL,
    write_date TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS zrn_commercial_channel_company_code_uniq
    ON zrn_commercial_commercial_channel (company_id, code)
    WHERE code IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS zrn_commercial_channel_company_name_uniq
    ON zrn_commercial_commercial_channel (company_id, name);

CREATE INDEX IF NOT EXISTS zrn_commercial_channel_company_idx
    ON zrn_commercial_commercial_channel (company_id);

CREATE TABLE IF NOT EXISTS zrn_commercial_commercial_channel_partner (
    id BIGSERIAL PRIMARY KEY,
    sequence INTEGER NOT NULL DEFAULT 10,
    channel_id BIGINT NOT NULL REFERENCES zrn_commercial_commercial_channel(id) ON DELETE CASCADE,
    company_id BIGINT REFERENCES res_company(id) ON DELETE SET NULL,
    partner_id BIGINT NOT NULL REFERENCES res_partner(id) ON DELETE RESTRICT,
    commercial_partner_id BIGINT REFERENCES res_partner(id) ON DELETE SET NULL,
    vat VARCHAR,
    city VARCHAR,
    state_id BIGINT REFERENCES res_country_state(id) ON DELETE SET NULL,
    country_id BIGINT REFERENCES res_country(id) ON DELETE SET NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    create_uid BIGINT REFERENCES res_users(id) ON DELETE SET NULL,
    create_date TIMESTAMP,
    write_uid BIGINT REFERENCES res_users(id) ON DELETE SET NULL,
    write_date TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS zrn_commercial_channel_partner_partner_uniq
    ON zrn_commercial_commercial_channel_partner (partner_id);

CREATE INDEX IF NOT EXISTS zrn_commercial_channel_partner_channel_idx
    ON zrn_commercial_commercial_channel_partner (channel_id);

CREATE INDEX IF NOT EXISTS zrn_commercial_channel_partner_company_idx
    ON zrn_commercial_commercial_channel_partner (company_id);

CREATE INDEX IF NOT EXISTS zrn_commercial_channel_partner_commercial_partner_idx
    ON zrn_commercial_commercial_channel_partner (commercial_partner_id);
