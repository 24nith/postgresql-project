_URL")
        if db_url and db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
```

2. What if `db_url` is NOT set?
If `db_url` is not set, report the missing environment variable:
`st.warning("DATABASE_URL environment variable is not set
