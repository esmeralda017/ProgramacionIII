import mysql.connector

class crud:
    def __init__(self):
        self.conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="tu_contraseña", 
            database="db_academica"
        )
        self.cursor = self.conexion.cursor(dictionary=True)

    def consultar(self, sql):
        try:
            self.cursor.execute(sql)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error al consultar: {e}")
            return []

    def ejecutar(self, sql, valores):
        try:
            self.cursor.execute(sql, valores)
            self.conexion.commit()
            return "ok"
        except Exception as e:
            self.conexion.rollback()
            print(f"Error al ejecutar: {e}")
            return f"Error: {e}"