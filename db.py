# -*- coding: utf-8 -*-
"""SQLite 连接与表初始化"""
import sqlite3
import os
from config import DB_PATH, UPLOAD_TMP_DIR


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")  # 提升并发写入性能
    return conn


def init_db():
    os.makedirs(UPLOAD_TMP_DIR, exist_ok=True)
    conn = get_conn()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS customer_billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            city_company TEXT NOT NULL,
            account_type TEXT,
            email TEXT,
            usage_volume REAL,
            occurrence_month TEXT NOT NULL,
            billing_amount REAL,
            product_name TEXT,
            billing_month TEXT,
            attribute_16 TEXT,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_settled INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_attr16 ON customer_billing(attribute_16);
        CREATE INDEX IF NOT EXISTS idx_month ON customer_billing(occurrence_month);
        CREATE INDEX IF NOT EXISTS idx_city ON customer_billing(city_company);
        """)
        try:
            conn.execute("ALTER TABLE customer_billing ADD COLUMN is_settled INTEGER DEFAULT 0;")
        except sqlite3.OperationalError:
            pass
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("数据库初始化完成:", DB_PATH)
