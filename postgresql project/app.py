from flask import Flask, render_template, request, redirect, url_for, flash
import os
import psycopg2
from pgvector.psycopg2 import register_vector
import openai

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback-secret-key-for-session")

def is_database_url_configured():
    url = os.environ.get("DATABASE_URL")
    if not url:
        return False
    placeholders = ["your_database_url", "postgres://user:password@host:port/dbname", "postgresql://user:password@host:port/dbname", "placeholder"]
    if any(p in url.lower() for p in placeholders):
        return False
    return True

def get_connection():
    if not is_database_url_configured():
        return None
    database_url = os.environ.get("DATABASE_URL")
    try:
        conn = psycopg2.connect(database_url)
        register_vector(conn)
        return conn
    except Exception as e:
        return None

def check_live_database():
    if not is_database_url_configured():
        return False, "Not Configured"
    database_url = os.environ.get("DATABASE_URL")
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return True, "Connected"
    except Exception as e:
        return False, "Connection Error"

def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        return openai.OpenAI(api_key=api_key)
    except Exception as e:
        return None

@app.route("/")
def dashboard():
    is_live, db_status_text = check_live_database()
    db_status = db_status_text if is_live else ("Not Configured" if not is_database_url_configured() else "Error")
    ai_status = "Configured" if os.environ.get("OPENAI_API_KEY") else "Missing API Key"
    
    tables_count = 0
    tables = []
    error_msg = None
    
    if is_database_url_configured():
        conn = get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
                tables = [t[0] for t in cur.fetchall()]
                tables_count = len(tables)
                cur.close()
                conn.close()
            except Exception as e:
                error_msg = f"Error querying database catalog: {e}"
        else:
            try:
                database_url = os.environ.get("DATABASE_URL")
                psycopg2.connect(database_url)
            except Exception as e:
                error_msg = f"Database connection error: {e}"
    else:
        error_msg = "Configuration Error: DATABASE_URL is absent, invalid, or still set to a placeholder value."

    return render_template("dashboard.html", 
                           db_status=db_status, 
                           ai_status=ai_status, 
                           is_live=is_live, 
                           tables_count=tables_count, 
                           tables=tables, 
                           error_msg=error_msg)

@app.route("/explorer", methods=["GET", "POST"])
def explorer():
    if not is_database_url_configured():
        flash("Configuration Error: DATABASE_URL is absent, invalid, or still set to a placeholder value.", "danger")
        return render_template("explorer.html", tables=[], selected_table=None, rows=[], colnames=[])
    
    conn = get_connection()
    if not conn:
        flash("Database connection error.", "danger")
        return render_template("explorer.html", tables=[], selected_table=None, rows=[], colnames=[])
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;")
        tables = [t[0] for t in cur.fetchall()]
        
        selected_table = request.form.get("selected_table") or (tables[0] if tables else None)
        rows = []
        colnames = []
        
        if selected_table and selected_table in tables:
            cur.execute(f"SELECT * FROM {selected_table} LIMIT 100;")
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            
        cur.close()
        conn.close()
        return render_template("explorer.html", tables=tables, selected_table=selected_table, rows=rows, colnames=colnames)
    except Exception as e:
        flash(f"Error exploring database: {e}", "danger")
        return render_template("explorer.html", tables=[], selected_table=None, rows=[], colnames=[])

@app.route("/rag", methods=["GET", "POST"])
def rag():
    query_text = ""
    results = None
    if request.method == "POST":
        query_text = request.form.get("query_text", "")
        if not query_text:
            flash("Please enter a query.", "warning")
        elif not is_database_url_configured():
            flash("Configuration Error: DATABASE_URL is absent, invalid, or still set to a placeholder value.", "danger")
        else:
            client = get_openai_client()
            conn = get_connection()
            if not client:
                flash("OpenAI API key is missing or invalid.", "danger")
            elif not conn:
                flash("Database connection error.", "danger")
            else:
                try:
                    response = client.embeddings.create(
                        input=query_text,
                        model="text-embedding-ada-002"
                    )
                    query_embedding = response.data[0].embedding
                    flash("Embedding generated successfully! Vector search query prepared.", "success")
                except Exception as e:
                    flash(f"Error during vector search: {e}", "danger")
    return render_template("rag.html", query_text=query_text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
