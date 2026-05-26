def migrate(cr, version):
    """
    Migrate online_minimum_stock data from JSONB (company_dependent storage in Odoo 18)
    to a regular float field.
    
    In Odoo 18, company_dependent fields store their values as JSONB directly in the
    model's table column with format: {"company_id": value, ...}
    e.g., {"1": 5.0, "2": 10.0}
    """
    if not version:
        return

    # Check if the column exists and get its data type
    cr.execute("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'product_template' AND column_name = 'online_minimum_stock'
    """)
    result = cr.fetchone()

    if not result:
        # Column doesn't exist, just add it as float (no data to migrate)
        cr.execute("ALTER TABLE product_template ADD COLUMN online_minimum_stock DOUBLE PRECISION")
        return

    if result[0] == 'jsonb':
        # Column exists as JSONB, need to convert to float
        # First, create a temporary column to store the float values
        cr.execute("ALTER TABLE product_template ADD COLUMN online_minimum_stock_temp DOUBLE PRECISION")

        # Extract the first value from JSON object
        # This gets the first available value from the JSON object (any company's value)
        cr.execute("""
            UPDATE product_template
            SET online_minimum_stock_temp = (
                SELECT (jsonb_each_text(online_minimum_stock)).value::DOUBLE PRECISION
                LIMIT 1
            )
            WHERE online_minimum_stock IS NOT NULL
              AND online_minimum_stock != '{}'::jsonb
        """)

        # Drop the old JSONB column
        cr.execute("ALTER TABLE product_template DROP COLUMN online_minimum_stock")

        # Rename the temp column to the original name
        cr.execute("ALTER TABLE product_template RENAME COLUMN online_minimum_stock_temp TO online_minimum_stock")
    # If column already exists as a numeric type, no migration needed
