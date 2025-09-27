import sqlite3
import os

DB_FILENAME = os.path.join(os.path.dirname(__file__), "contacts.db")


def init_db():
    """Initializes the database and creates the contacts table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILENAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT
        )
        """
    )
    conn.commit()
    return conn


def add_contact_db(conn, name, phone, email):
    """Adds a new contact to the database."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO contacts (name, phone, email) VALUES (?, ?, ?)",
        (name, phone, email),
    )
    conn.commit()


def get_all_contacts_db(conn, search_term: str = None):
    """
    Retrieves all contacts from the database.
    If search_term is provided, performs a case-insensitive search on the name field.
    """
    cursor = conn.cursor()
    if search_term:
        like_term = f"%{search_term}%"
        cursor.execute(
            "SELECT id, name, phone, email FROM contacts WHERE name LIKE ? ORDER BY name COLLATE NOCASE",
            (like_term,),
        )
    else:
        cursor.execute("SELECT id, name, phone, email FROM contacts ORDER BY name COLLATE NOCASE")
    return cursor.fetchall()


def update_contact_db(conn, contact_id, name, phone, email):
    """Updates an existing contact in the database."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE contacts SET name = ?, phone = ?, email = ? WHERE id = ?",
        (name, phone, email, contact_id),
    )
    conn.commit()


def delete_contact_db(conn, contact_id):
    """Deletes a contact from the database."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()