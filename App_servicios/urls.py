from django.urls import path
from django.http import HttpResponse


def servicios_index(request):
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Servicios - Leidy Make Up</title>
        <style>
            body { font-family: Arial; background: #fce4ec; text-align: center; padding: 50px; }
            h1 { color: #d81b60; }
            .card { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            a { display: block; margin-top: 20px; color: #d81b60; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>💅 Módulo de Servicios</h1>
            <p>Aquí se gestiona el catálogo de servicios.</p>
            <p><strong>Modelo:</strong> Servicios</p>
            <a href="/">← Volver al Login</a>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)


urlpatterns = [
    path('', servicios_index, name='servicios_index'),
]