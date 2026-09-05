import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="mydb",
    user="postgres",
    password="YOUR_POSTGRES_PASSWORD"
)

print("PostgreSQL connected successfully!")