# -*- coding: utf-8 -*-
"""
Created on Fri Apr 10 21:13:23 2026

@author: tarfu
"""

import sqlite3

conn = sqlite3.connect("main_db.db")
cur = conn.cursor()

cur.execute("""
SELECT names.names_names, threshold.Value_threshold, threshold.Timestamp_threshold
FROM threshold
JOIN names ON threshold.ID_Name = names.ID_names
""")

for name, value, timestamp in cur.fetchall():
    print(f"{name} | {value:.3f} | {timestamp}")

conn.close()