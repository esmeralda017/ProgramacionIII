from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib import parse
port = 3000
class miServidor(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "/index.html"
            return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        logitud = int(self.headers['Content-Length'])
        datos = self.rfile.read(logitud)

        datos = datos.decode("utf-8")
        datos = parse.unquote(datos)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(datos.encode("utf-8"))
     
print("Iniciando servidor en el puerto 3000")
server = HTTPServer(("localhost", 3000), miServidor)
server.serve_forever()