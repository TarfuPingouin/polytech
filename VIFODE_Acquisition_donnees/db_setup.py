import sqlite3

# Connexion à la base
conn = sqlite3.connect("main_db.db")
cur = conn.cursor()

# Active les clés étrangères
cur.execute("PRAGMA foreign_keys = ON")

# Drop des tables existantes
cur.execute("DROP TABLE IF EXISTS threshold")
cur.execute("DROP TABLE IF EXISTS names")

# Recréation de la table names
cur.execute("""
CREATE TABLE names (
    ID_names INTEGER PRIMARY KEY,
    names_names TEXT NOT NULL
)
""")

# Recréation de la table threshold
cur.execute("""
CREATE TABLE threshold (
    ID_threshold INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_Name INTEGER NOT NULL,
    Value_threshold REAL NOT NULL,
    Timestamp_threshold REAL NOT NULL,
    FOREIGN KEY (ID_Name) REFERENCES names(ID_names)
)
""")

# Remplissage de la table names
cur.executemany("""
INSERT INTO names (ID_names, names_names)
VALUES (?, ?)
""", [
    (1, "AccX"),
    (2, "AccY"),
    (3, "AccZ"),
    (4, "RotX"),
    (5, "RotY"),
    (6, "RotZ"),
    (7, "Temp")
])

# Validation des changements
conn.commit()

print("Base recréée correctement.")

# Fermeture
conn.close()