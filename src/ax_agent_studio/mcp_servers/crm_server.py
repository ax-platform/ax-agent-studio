import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("guerrilla-crm")

# Database setup
DB_PATH = Path("data/guerrilla_crm.db")

def get_db():
    """Get a database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database schema."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Leads table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT UNIQUE,
        source TEXT,
        status TEXT DEFAULT 'RAW', -- RAW, ENRICHED, DRAFTED, SENT, REPLIED
        email TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Activity Log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        action TEXT,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(lead_id) REFERENCES leads(id)
    )
    """)
    
    conn.commit()
    conn.close()

# Initialize on module load
init_db()

@mcp.tool()
def add_lead(name: str, url: str, source: str = "manual") -> str:
    """Add a new lead to the CRM."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO leads (name, url, source) VALUES (?, ?, ?)",
            (name, url, source)
        )
        lead_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return f"Lead added with ID: {lead_id}"
    except sqlite3.IntegrityError:
        return f"Error: Lead with URL {url} already exists."
    except Exception as e:
        return f"Error adding lead: {str(e)}"

@mcp.tool()
def update_lead(lead_id: int, data: str) -> str:
    """Update a lead's fields. Data should be a JSON string."""
    try:
        updates = json.loads(data)
        if not updates:
            return "No updates provided."
            
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values())
        values.append(lead_id)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE leads SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
        
        if cursor.rowcount == 0:
            conn.close()
            return f"Error: Lead ID {lead_id} not found."
            
        conn.commit()
        conn.close()
        return f"Lead {lead_id} updated successfully."
    except json.JSONDecodeError:
        return "Error: Data must be a valid JSON string."
    except Exception as e:
        return f"Error updating lead: {str(e)}"

@mcp.tool()
def get_leads_by_status(status: str, limit: int = 10) -> str:
    """Get leads with a specific status."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE status = ? ORDER BY updated_at DESC LIMIT ?", (status, limit))
    rows = cursor.fetchall()
    conn.close()
    
    leads = [dict(row) for row in rows]
    return json.dumps(leads, indent=2)

@mcp.tool()
def get_lead_details(lead_id: int) -> str:
    """Get full details for a specific lead."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.dumps(dict(row), indent=2)
    return "Lead not found."

@mcp.tool()
def log_activity(lead_id: int, action: str, details: str = "") -> str:
    """Log an activity for a lead."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO activity_log (lead_id, action, details) VALUES (?, ?, ?)",
        (lead_id, action, details)
    )
    conn.commit()
    conn.close()
    return "Activity logged."

if __name__ == "__main__":
    mcp.run()
