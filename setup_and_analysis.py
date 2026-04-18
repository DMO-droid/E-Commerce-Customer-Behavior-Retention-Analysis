import sqlite3
import pandas as pd
import os

DATA_DIR = "Sales & Profit"
DB_PATH = os.path.join(DATA_DIR, "sales_profit.db")

# SETUP

def create_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    DROP TABLE IF EXISTS order_items;
    DROP TABLE IF EXISTS reviews;
    DROP TABLE IF EXISTS events;
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS products;
    DROP TABLE IF EXISTS users;

    CREATE TABLE users (
        user_id     TEXT PRIMARY KEY,
        name        TEXT,
        email       TEXT,
        gender      TEXT,
        city        TEXT,
        signup_date DATE
    );

    CREATE TABLE products (
        product_id   TEXT PRIMARY KEY,
        product_name TEXT,
        category     TEXT,
        brand        TEXT,
        price        REAL,
        rating       REAL
    );

    CREATE TABLE orders (
        order_id     TEXT PRIMARY KEY,
        user_id      TEXT,
        order_date   DATETIME,
        order_status TEXT,
        total_amount REAL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE order_items (
        order_item_id TEXT PRIMARY KEY,
        order_id      TEXT,
        product_id    TEXT,
        user_id       TEXT,
        quantity      INTEGER,
        item_price    REAL,
        item_total    REAL,
        FOREIGN KEY (order_id)    REFERENCES orders(order_id),
        FOREIGN KEY (product_id)  REFERENCES products(product_id),
        FOREIGN KEY (user_id)     REFERENCES users(user_id)
    );

    CREATE TABLE reviews (
        review_id   TEXT PRIMARY KEY,
        order_id    TEXT,
        product_id  TEXT,
        user_id     TEXT,
        rating      REAL,
        review_text TEXT,
        review_date DATETIME,
        FOREIGN KEY (order_id)   REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id),
        FOREIGN KEY (user_id)    REFERENCES users(user_id)
    );

    CREATE TABLE events (
        event_id        TEXT PRIMARY KEY,
        user_id         TEXT,
        product_id      TEXT,
        event_type      TEXT,
        event_timestamp DATETIME,
        FOREIGN KEY (user_id)    REFERENCES users(user_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)
    conn.commit()
    return conn


def import_csv(conn):
    tables = {
        "users":       ("users.csv",       {"signup_date": "date"}),
        "products":    ("products.csv",    {}),
        "orders":      ("orders.csv",      {"order_date": "datetime"}),
        "order_items": ("order_items.csv", {}),
        "reviews":     ("reviews.csv",     {"review_date": "datetime"}),
        "events":      ("events.csv",      {"event_timestamp": "datetime"}),
    }
    for table, (fname, parse_dates) in tables.items():
        path = os.path.join(DATA_DIR, fname)
        df = pd.read_csv(path, parse_dates=list(parse_dates.keys()) if parse_dates else False)
        # Normalize date columns to ISO string for SQLite
        for col in parse_dates:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")
        df.to_sql(table, conn, if_exists="replace", index=False)
        print(f"  Imported {table}: {len(df):,} rows")


def data_quality_check(conn):
    print("\n=== DATA QUALITY CHECK ===")
    checks = {
        "NULL user_id in orders":        "SELECT COUNT(*) FROM orders WHERE user_id IS NULL",
        "NULL product_id in order_items": "SELECT COUNT(*) FROM order_items WHERE product_id IS NULL",
        "Duplicate order_id":            "SELECT COUNT(*)-COUNT(DISTINCT order_id) FROM orders",
        "Duplicate user_id":             "SELECT COUNT(*)-COUNT(DISTINCT user_id) FROM users",
        "Orphan orders (no user)":       "SELECT COUNT(*) FROM orders o LEFT JOIN users u ON o.user_id=u.user_id WHERE u.user_id IS NULL",
        "Orphan order_items (no order)": "SELECT COUNT(*) FROM order_items oi LEFT JOIN orders o ON oi.order_id=o.order_id WHERE o.order_id IS NULL",
        "Orphan reviews (no order)":     "SELECT COUNT(*) FROM reviews r LEFT JOIN orders o ON r.order_id=o.order_id WHERE o.order_id IS NULL",
        "Negative item_total":           "SELECT COUNT(*) FROM order_items WHERE item_total < 0",
        "Rating out of range (reviews)": "SELECT COUNT(*) FROM reviews WHERE rating < 1 OR rating > 5",
    }
    results = {}
    for label, sql in checks.items():
        val = pd.read_sql(sql, conn).iloc[0, 0]
        status = "OK" if val == 0 else f"WARN: {val}"
        print(f"  {label:<40} {status}")
        results[label] = val
    return results


if __name__ == "__main__":
    print("=== PHASE 1: SETUP ===")
    conn = create_db()
    import_csv(conn)
    data_quality_check(conn)
    conn.close()
    print("\nDB created:", DB_PATH)
