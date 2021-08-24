# Generic single-database configuration.

## Building migrations:

Build a fresh database

`NBEX_DB_URL="sqlite:///test.db" nbexchange`

Create a migration:

`NBEX_DB_URL="sqlite:///test.db" python -m nbexchange.dbutil alembic revision --autogenerate -m "Change subscription column width"`

Apply a migration:

`NBEX_DB_URL="sqlite:///test.db" python -m nbexchange.dbutil alembic upgrade head`
