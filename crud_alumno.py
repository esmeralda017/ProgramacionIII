import crud_academico

# Se asume que db es una instancia de la clase 'crud' de crud_academico
db = crud_academico.crud() 

class crud_alumno:
    def consultar(self, buscar):
        # Esta función usa el método consultar de crud_academico para traer los datos
        return db.consultar("SELECT * FROM alumnos WHERE nombre like '%"+ buscar +"%'")
    
    def administrar(self, datos):
        sql = None
        valores = None
        
        # Usamos if/elif/else para asegurar que las variables se definan
        if datos['accion'] == "nuevo":
            sql = """
                INSERT INTO alumnos (codigo, nombre, direccion, telefono, email)
                VALUES (%s, %s, %s, %s, %s)
            """
            valores = (datos['codigo'], datos['nombre'], datos['direccion'], datos['telefono'], datos['email'])
            
        elif datos['accion'] == "modificar":
            sql = """
                UPDATE alumnos SET codigo=%s, nombre=%s, direccion=%s, telefono=%s, email=%s
                WHERE idAlumno=%s
            """
            valores = (datos['codigo'], datos['nombre'], datos['direccion'], datos['telefono'], datos['email'], datos['idAlumno'])
            
        elif datos['accion'] == "eliminar":
            sql = "DELETE FROM alumnos WHERE idAlumno=%s"
            valores = (datos['idAlumno'],)
            
        else:
            # Si la acción no es reconocida, devuelve un error
            return "Error: Acción no válida."

        # Ejecutamos la consulta solo si sql y valores fueron definidos
        if sql and valores is not None:
            # El método ejecutar de crud_academico.py ya maneja los errores
            return db.ejecutar(sql, valores)
        
        return "Error desconocido: Faltan datos para la acción."