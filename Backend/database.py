import sqlite3

DATABASE = 'context_chatter.db'

def create_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents(
            document_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            path TEXT NOT NULL
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def insert_document(document_id,filename,path):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO documents(document_id,filename,path)
        VALUES(?,?,?)
        """,
        (document_id,filename,path)
    )
    conn.commit()
    cursor.close()
    conn.close()


def delete_document(document_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM documents 
        WHERE document_id = ?
        """,
        (document_id,)
    )
    deleted = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    return deleted>0

def get_document(document_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT document_id,filename,path FROM documents
        WHERE document_id = ?
        """,
        (document_id,)
    )
    row = cursor.fetchone()

    cursor.close()
    conn.close()
    if row is None:
        return None
    return{
        "document_id": row[0],
        "filename": row[1],
        "path": row[2]
    } 

def get_all_documents():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT document_id,filename,path FROM documents
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    documents = []
    for row in rows:
        documents.append({
            "document_id":row[0],
            "filename":row[1],
            "path":row[2]
        })
    return documents