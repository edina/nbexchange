# Generic single-database configuration.

## Building migrations:

Build a fresh database

`NBEX_DB_URL="sqlite:///test.db" nbexchange`

Create a migration:

`NBEX_DB_URL="sqlite:///test.db" python -m nbexchange.dbutil alembic revision --autogenerate -m "Change subscription column width"`

Apply a migration:

`NBEX_DB_URL="sqlite:///test.db" python -m nbexchange.dbutil alembic upgrade head`


## Sequence

This is the sequence, as of 2025-01-15, is:


| file | revision | down_revision |
| --- | --- | --- |
| 9794df114fd9_initialise | 9794df114fd9 | |
| d500457efb3b_create_nb_exchange_tables | d500457efb3b | 9794df114fd9 |
| 20190402_add_collected_action | 20190202 |  d500457efb3b |
| f26d6a79159d_add_checksum_column | f26d6a79159d | 20190202 |
| 2805bf7747e5_change_feedback_timestamp_column_type_ | 2805bf7747e5 | f26d6a79159d |
| 6f2a6c00affb_add_feedback_to_ation_enum_type | 6f2a6c00affb | 2805bf7747e5 |
| f3345539f08d_change_assignment_name_data_type | f3345539f08d | 6f2a6c00affb |
| bfe19408f64f_add_full_name_to_user | bfe19408f64f | f3345539f08d |
| 2021-08-20-15-24-21_change_subscription_column_width | 2540572282f2 | bfe19408f64f |
| 2024093001_add_emal_and_lms_to_user | 2024093001 | 2540572282f2 |