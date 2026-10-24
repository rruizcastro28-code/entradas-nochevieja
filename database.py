"""
Database management for Fiesta Fin de Año ticket system.
Uses standard Python sqlite3 with thread safety.
"""
import sqlite3
import os
import uuid
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tickets.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Tickets table
    c.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_number INTEGER UNIQUE NOT NULL,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        surname TEXT NOT NULL,
        dni TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT DEFAULT '',
        price REAL DEFAULT 0.0,
        payment_method TEXT DEFAULT 'Efectivo',
        notes TEXT DEFAULT '',
        status TEXT DEFAULT 'VALIDA', -- VALIDA, USADA, ANULADA
        created_at TEXT NOT NULL,
        used_at TEXT DEFAULT NULL,
        used_by TEXT DEFAULT NULL
    )
    """)
    
    # Indexes for fast lookup
    c.execute("CREATE INDEX IF NOT EXISTS idx_code ON tickets(code)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_dni ON tickets(dni)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_status ON tickets(status)")
    
    # Scan logs table (tracks every scan attempt, valid or invalid)
    c.execute("""
    CREATE TABLE IF NOT EXISTS scan_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER,
        code_scanned TEXT,
        result TEXT NOT NULL, -- VALID, ALREADY_USED, NOT_FOUND
        scanned_at TEXT NOT NULL,
        details TEXT DEFAULT ''
    )
    """)
    
    # Settings table
    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    # Default settings
    defaults = {
        "event_name": "Gran Fiesta Fin de Año 2026",
        "event_date": "31 de Diciembre de 2026",
        "event_time": "A partir de las 23:30 h",
        "event_venue": "Sala / Finca Privada",
        "max_capacity": "499",
        "default_price": "35.00",
        "smtp_host": "",
        "smtp_port": "587",
        "smtp_user": "",
        "smtp_pass": "",
        "smtp_from": "entradas@fiestanochevieja.com",
        "poster_url": "",
        "admin_pin": "2026",
        "door_pin": "puerta"
    }
    
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    conn.commit()
    conn.close()

def get_settings():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    rows = c.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def update_settings(settings_dict):
    conn = get_connection()
    c = conn.cursor()
    for k, v in settings_dict.items():
        c.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (k, str(v)))
    conn.commit()
    conn.close()

def get_next_ticket_number():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT MAX(ticket_number) as max_num FROM tickets")
    row = c.fetchone()
    conn.close()
    max_num = row["max_num"] if row and row["max_num"] is not None else 0
    return max_num + 1

def get_stats():
    conn = get_connection()
    c = conn.cursor()
    
    settings = get_settings()
    max_capacity = int(settings.get("max_capacity", 499))
    
    c.execute("SELECT COUNT(*) as count FROM tickets WHERE status != 'ANULADA'")
    sold = c.fetchone()["count"]
    
    c.execute("SELECT COUNT(*) as count FROM tickets WHERE status = 'USADA'")
    checked_in = c.fetchone()["count"]
    
    c.execute("SELECT COALESCE(SUM(price), 0) as total FROM tickets WHERE status != 'ANULADA'")
    total_revenue = c.fetchone()["total"]
    
    c.execute("SELECT COUNT(*) as count FROM tickets WHERE status = 'ANULADA'")
    cancelled = c.fetchone()["count"]
    
    conn.close()
    
    return {
        "max_capacity": max_capacity,
        "sold": sold,
        "remaining": max(0, max_capacity - sold),
        "checked_in": checked_in,
        "total_revenue": total_revenue,
        "cancelled": cancelled
    }

def create_ticket(name, surname, dni, email, phone="", price=0.0, payment_method="Efectivo", notes=""):
    conn = get_connection()
    c = conn.cursor()
    
    # Clean inputs
    name = name.strip()
    surname = surname.strip()
    dni = dni.strip().upper()
    email = email.strip().lower()
    phone = phone.strip()
    
    # Check max capacity
    settings = get_settings()
    max_capacity = int(settings.get("max_capacity", 499))
    
    c.execute("SELECT COUNT(*) as count FROM tickets WHERE status != 'ANULADA'")
    current_count = c.fetchone()["count"]
    if current_count >= max_capacity:
        conn.close()
        raise ValueError(f"Aforo completo. Ya se han vendido las {max_capacity} entradas permitidas.")
    
    # Generate unique ticket number and cryptographic UUID code
    c.execute("SELECT MAX(ticket_number) as max_num FROM tickets")
    row = c.fetchone()
    next_num = (row["max_num"] or 0) + 1
    
    code = f"NYE-{next_num:03d}-{uuid.uuid4().hex[:12].upper()}"
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("""
        INSERT INTO tickets (ticket_number, code, name, surname, dni, email, phone, price, payment_method, notes, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VALIDA', ?)
    """, (next_num, code, name, surname, dni, email, phone, float(price), payment_method, notes, created_at))
    
    ticket_id = c.lastrowid
    conn.commit()
    
    c.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    new_ticket = dict(c.fetchone())
    conn.close()
    
    return new_ticket

def get_ticket_by_code_or_id(identifier):
    conn = get_connection()
    c = conn.cursor()
    
    # Try by code
    c.execute("SELECT * FROM tickets WHERE code = ?", (identifier,))
    row = c.fetchone()
    
    if not row:
        # Try by ticket number if numeric
        if str(identifier).isdigit():
            c.execute("SELECT * FROM tickets WHERE ticket_number = ?", (int(identifier),))
            row = c.fetchone()
            
    conn.close()
    return dict(row) if row else None

def get_tickets(search=None, status=None):
    conn = get_connection()
    c = conn.cursor()
    
    query = "SELECT * FROM tickets WHERE 1=1"
    params = []
    
    if status and status != 'ALL':
        query += " AND status = ?"
        params.append(status)
        
    if search:
        search_term = f"%{search.strip()}%"
        query += " AND (name LIKE ? OR surname LIKE ? OR dni LIKE ? OR email LIKE ? OR code LIKE ? OR CAST(ticket_number AS TEXT) LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term, search_term, search_term])
        
    query += " ORDER BY ticket_number DESC"
    
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def check_dni_exists(dni):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE dni = ? AND status != 'ANULADA'", (dni.strip().upper(),))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def validate_ticket_scan(code_or_dni):
    """
    Validates a ticket scan from door.
    Returns: (result_status, ticket_dict_or_none, message)
    """
    conn = get_connection()
    c = conn.cursor()
    
    query_str = code_or_dni.strip()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Look up ticket by code, or DNI, or ticket_number
    ticket = None
    c.execute("SELECT * FROM tickets WHERE code = ?", (query_str,))
    row = c.fetchone()
    
    if not row:
        # Try by DNI
        c.execute("SELECT * FROM tickets WHERE dni = ? AND status != 'ANULADA'", (query_str.upper(),))
        row = c.fetchone()
        
    if not row and query_str.isdigit():
        c.execute("SELECT * FROM tickets WHERE ticket_number = ?", (int(query_str),))
        row = c.fetchone()
        
    if not row:
        # Log invalid scan
        c.execute("INSERT INTO scan_logs (code_scanned, result, scanned_at, details) VALUES (?, 'NOT_FOUND', ?, 'Código o DNI no encontrado')",
                  (query_str, now_str))
        conn.commit()
        conn.close()
        return ("NOT_FOUND", None, "Entrada no encontrada o código falsificado.")
        
    ticket = dict(row)
    
    # Check if cancelled
    if ticket["status"] == "ANULADA":
        c.execute("INSERT INTO scan_logs (ticket_id, code_scanned, result, scanned_at, details) VALUES (?, ?, 'CANCELLED', ?, 'Entrada anulada previamente')",
                  (ticket["id"], query_str, now_str))
        conn.commit()
        conn.close()
        return ("CANCELLED", ticket, "Esta entrada fue ANULADA y no permite acceso.")
        
    # Check if already used
    if ticket["status"] == "USADA":
        used_time = ticket.get("used_at") or "hora desconocida"
        c.execute("INSERT INTO scan_logs (ticket_id, code_scanned, result, scanned_at, details) VALUES (?, ?, 'ALREADY_USED', ?, ?)",
                  (ticket["id"], query_str, now_str, f"Intento duplicado. Usada a las {used_time}"))
        conn.commit()
        conn.close()
        return ("ALREADY_USED", ticket, f"¡ALERTA! Entrada YA USADA anteriormente a las {used_time}.")
        
    # Valid ticket! Mark as used
    c.execute("UPDATE tickets SET status = 'USADA', used_at = ? WHERE id = ?", (now_str, ticket["id"]))
    c.execute("INSERT INTO scan_logs (ticket_id, code_scanned, result, scanned_at, details) VALUES (?, ?, 'VALID', ?, 'Acceso concedido')",
              (ticket["id"], query_str, now_str))
    conn.commit()
    
    # Refresh ticket
    c.execute("SELECT * FROM tickets WHERE id = ?", (ticket["id"],))
    updated_ticket = dict(c.fetchone())
    conn.close()
    
    return ("VALID", updated_ticket, "¡Entrada VÁLIDA! Acceso concedido.")

def reset_ticket_status(ticket_id, new_status="VALIDA"):
    conn = get_connection()
    c = conn.cursor()
    if new_status == "VALIDA":
        c.execute("UPDATE tickets SET status = 'VALIDA', used_at = NULL WHERE id = ?", (ticket_id,))
    elif new_status == "ANULADA":
        c.execute("UPDATE tickets SET status = 'ANULADA' WHERE id = ?", (ticket_id,))
    conn.commit()
    conn.close()
    return True
