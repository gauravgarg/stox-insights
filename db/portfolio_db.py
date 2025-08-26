import sqlite3
import pandas as pd

DB_FILE = "portfolio.db"

class PortfolioDB:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        demat TEXT,
                        symbol TEXT,
                        qty INTEGER,
                        price REAL,
                        side TEXT,
                        strategy TEXT
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS cash_ledger (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        demat TEXT,
                        amount REAL,
                        note TEXT
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS watchlist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT,
                        tag TEXT,
                        note TEXT
                    )''')
        conn.commit()
        conn.close()


    def insert_transaction(self, date, demat, symbol, qty, price, side, strategy):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''INSERT INTO transactions (date, demat, symbol, qty, price, side, strategy)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (date, demat, symbol, qty, price, side, strategy))
        conn.commit()
        conn.close()

    def insert_cash(self, date, demat, amount, note):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''INSERT INTO cash_ledger (date, demat, amount, note)
                     VALUES (?, ?, ?, ?)''',
                  (date, demat, amount, note))
        conn.commit()
        conn.close()

    def fetch_transactions(self):
        conn = sqlite3.connect(self.db_file)
        df = pd.read_sql("SELECT * FROM transactions", conn)
        conn.close()
        return df

    def fetch_cash(self):
        conn = sqlite3.connect(self.db_file)
        df = pd.read_sql("SELECT * FROM cash_ledger", conn)
        conn.close()
        return df

    def add_to_watchlist(self, symbol, tag, note):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''INSERT INTO watchlist (symbol, tag, note) VALUES (?, ?, ?)''', (symbol, tag, note))
        conn.commit()
        conn.close()

    def fetch_watchlist(self):
        conn = sqlite3.connect(self.db_file)
        df = pd.read_sql("SELECT * FROM watchlist", conn)
        conn.close()
        return df

    def remove_from_watchlist(self, watchlist_id):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''DELETE FROM watchlist WHERE id = ?''', (watchlist_id,))
        conn.commit()
        conn.close()
