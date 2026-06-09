# Maintenance scripts

Run from the project root, for example:

```bat
python scripts/make_user.py
python scripts/import_master_rules.py
python scripts/architecture_check.py
python scripts/data_flow_check.py
python scripts/mee_inventory_check.py
python scripts/mbe_inventory_check.py
```

These are one-off CLI tools for imports and database maintenance. They are not used by the Streamlit app at runtime.
