import mysql.connector
from mysql.connector import Error

class crud:
    def __init__(self):
        print("Intentando conectar a la base de datos...")
        self.conexion = None
        try:
            self.conexion = mysql.connector.connect(
                host='localhost',
                user='root',
                # ¡CONFIRMA ESTA CONTRASEÑA! Si tu root no tiene, déjala vacía.
                password='', 
                database='db_academica' # Asegúrate que el nombre sea EXACTO
            )
            if self.conexion.is_connected():
                print("Conexión exitosa a la base de datos.")
            else:
                print("Conexión falló, pero sin excepción.")
                self.conexion = None
        except Error as e:
            # Captura cualquier error fatal de conexión (credenciales, servidor apagado)
            print(f"Error FATAL en la conexión: {e}")
            self.conexion = e # Almacenamos el objeto de error para que otros métodos lo vean

    def consultar(self, sql):
        # Verifica si el objeto de conexión es un error
        if isinstance(self.conexion, Error):
            return [{"msg": str(self.conexion)}] # Devuelve el error de conexión como JSON
        
        try:
            cursor = self.conexion.cursor(dictionary=True)
            cursor.execute(sql)
            resultados = cursor.fetchall()
            cursor.close()
            return resultados
        except Error as e:
            return [{"msg": f"Error al consultar SQL: {str(e)}"}]
    
    def ejecutar(self, sql, datos):
        # Verifica si el objeto de conexión es un error
        if isinstance(self.conexion, Error):
            return str(self.conexion) # Devuelve el error de conexión como string
        
        try:
            cursor = self.conexion.cursor()
            cursor.execute(sql, datos)
            self.conexion.commit()
            cursor.close()
            return "ok"
        except Error as e:
            return f"Error al ejecutar SQL: {str(e)}"