CREATE TABLE IF NOT EXISTS zrn_prodigyn_commercial_brand (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    code VARCHAR,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    company_id BIGINT NOT NULL REFERENCES res_company(id) ON DELETE RESTRICT,
    owner_name VARCHAR,
    logo BYTEA,
    website VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    country_id BIGINT REFERENCES res_country(id) ON DELETE SET NULL,
    launch_date DATE,
    description TEXT,
    notes TEXT,
    create_uid BIGINT REFERENCES res_users(id) ON DELETE SET NULL,
    create_date TIMESTAMP,
    write_uid BIGINT REFERENCES res_users(id) ON DELETE SET NULL,
    write_date TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS zrn_prodigyn_commercial_brand_company_code_uniq
    ON zrn_prodigyn_commercial_brand (company_id, code)
    WHERE code IS NOT NULL;

CREATE INDEX IF NOT EXISTS zrn_prodigyn_commercial_brand_company_idx
    ON zrn_prodigyn_commercial_brand (company_id);

CREATE TABLE IF NOT EXISTS zrn_prodigyn_commercial_brand_product (
    id BIGSERIAL PRIMARY KEY,
    sequence INTEGER NOT NULL DEFAULT 10,
    brand_id BIGINT NOT NULL REFERENCES zrn_prodigyn_commercial_brand(id) ON DELETE CASCADE,
    company_id BIGINT REFERENCES res_company(id) ON DELETE SET NULL,
    product_id BIGINT NOT NULL REFERENCES product_product(id) ON DELETE RESTRICT,
    product_tmpl_id BIGINT REFERENCES product_template(id) ON DELETE SET NULL,
    default_code VARCHAR,
    categ_id BIGINT REFERENCES product_category(id) ON DELETE SET NULL,
    uom_id BIGINT REFERENCES uom_uom(id) ON DELETE SET NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    create_uid BIGINT REFERENCES res_users(id) ON DELETE SET NULL,
    create_date TIMESTAMP,
    write_uid BIGINT REFERENCES res_users(id) ON DELETE SET NULL,
    write_date TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS zrn_prodigyn_commercial_brand_product_product_uniq
    ON zrn_prodigyn_commercial_brand_product (product_id);

CREATE INDEX IF NOT EXISTS zrn_prodigyn_commercial_brand_product_brand_idx
    ON zrn_prodigyn_commercial_brand_product (brand_id);

CREATE INDEX IF NOT EXISTS zrn_prodigyn_commercial_brand_product_company_idx
    ON zrn_prodigyn_commercial_brand_product (company_id);

CREATE INDEX IF NOT EXISTS zrn_prodigyn_commercial_brand_product_template_idx
    ON zrn_prodigyn_commercial_brand_product (product_tmpl_id);
