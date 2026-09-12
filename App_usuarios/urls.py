from django.urls import path
from django.http import HttpResponse


def usuarios_index(request):
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Usuarios - Leidy Make Up</title>
        <style>
            body { font-family: Arial; background: #fce4ec; text-align: center; padding: 50px; }
            h1 { color: #d81b60; }
            .card { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            a { display: block; margin-top: 20px; color: #d81b60; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>👤 Módulo de Usuarios</h1>
            <p>Aquí se gestionan los Clientes y Estilistas.</p>
            <p><strong>Modelos:</strong> Persona, Estilista, Cliente</p>
            <a href="/">← Volver al Login</a>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)


urlpatterns = [
    path('', usuarios_index, name='usuarios_index'),
]