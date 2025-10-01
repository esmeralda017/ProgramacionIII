import pandas as pd
import mysql.connector

# Nombre del archivo Excel
EXCEL_FILE = "criterios.xlsx"

# Conectar a la BD
conn = mysql.connector.connect(
    host="localhost",
    user="root",   # cambia si tu mysql usa otra contraseña
    password="",
    database="feria_logros"
)
cur = conn.cursor()

# Leer archivo Excel
df = pd.read_excel(EXCEL_FILE, engine="openpyxl")

# Limpiar tabla antes de insertar (opcional, evita duplicados)
cur.execute("TRUNCATE TABLE criterios")

# Insertar criterios
for _, row in df.iterrows():
    descripcion = str(row["descripcion"]).strip()
    peso = float(row["peso"])
    cur.execute("INSERT INTO criterios (descripcion, peso) VALUES (%s, %s)", (descripcion, peso))

conn.commit()
cur.close()
conn.close()

print("✅ Criterios importados correctamente desde Excel.")
