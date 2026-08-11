-- InventorySaaS schema, generated from SQLAlchemy models
-- Run in Supabase: Dashboard -> SQL Editor -> New query -> paste -> Run

CREATE TABLE IF NOT EXISTS locations (
	id SERIAL NOT NULL, 
	merchant_id INTEGER NOT NULL, 
	square_location_id VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	address TEXT, 
	timezone VARCHAR(64), 
	is_active BOOLEAN, 
	PRIMARY KEY (id), 
	UNIQUE (square_location_id)
);

CREATE INDEX IF NOT EXISTS ix_locations_id ON locations (id);
CREATE INDEX IF NOT EXISTS ix_locations_merchant_id ON locations (merchant_id);

CREATE TABLE IF NOT EXISTS merchants (
	id SERIAL NOT NULL, 
	square_merchant_id VARCHAR(64) NOT NULL, 
	access_token TEXT NOT NULL, 
	refresh_token TEXT NOT NULL, 
	token_expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	business_name VARCHAR(255), 
	email VARCHAR(255), 
	stripe_customer_id VARCHAR(64), 
	subscription_status VARCHAR(32), 
	trial_ends_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_merchants_square_merchant_id ON merchants (square_merchant_id);
CREATE INDEX IF NOT EXISTS ix_merchants_id ON merchants (id);

CREATE TABLE IF NOT EXISTS recipes (
	id SERIAL NOT NULL, 
	merchant_id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	selling_price NUMERIC(10, 2), 
	portions INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_recipes_id ON recipes (id);
CREATE INDEX IF NOT EXISTS ix_recipes_merchant_id ON recipes (merchant_id);

CREATE TABLE IF NOT EXISTS waste_events (
	id SERIAL NOT NULL, 
	merchant_id INTEGER NOT NULL, 
	location_id INTEGER NOT NULL, 
	square_catalog_object_id VARCHAR(64) NOT NULL, 
	item_name VARCHAR(255) NOT NULL, 
	variation_name VARCHAR(255), 
	quantity NUMERIC(10, 2) NOT NULL, 
	unit VARCHAR(32), 
	reason VARCHAR(64) NOT NULL, 
	cost_per_unit NUMERIC(10, 4), 
	total_cost NUMERIC(10, 2), 
	notes TEXT, 
	recorded_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_waste_events_merchant_id ON waste_events (merchant_id);
CREATE INDEX IF NOT EXISTS ix_waste_events_location_id ON waste_events (location_id);
CREATE INDEX IF NOT EXISTS ix_waste_events_id ON waste_events (id);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
	id SERIAL NOT NULL, 
	recipe_id INTEGER NOT NULL, 
	square_catalog_object_id VARCHAR(64) NOT NULL, 
	item_name VARCHAR(255) NOT NULL, 
	quantity NUMERIC(10, 4) NOT NULL, 
	unit VARCHAR(32) NOT NULL, 
	cost_per_unit NUMERIC(10, 4), 
	PRIMARY KEY (id), 
	FOREIGN KEY(recipe_id) REFERENCES recipes (id)
);

CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_recipe_id ON recipe_ingredients (recipe_id);
CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_id ON recipe_ingredients (id);

