from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse


def login_view(request):
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Leidy Make Up - Login</title>
        <style>
            body { font-family: Arial, sans-serif; background: #fce4ec; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .login-box { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 350px; text-align: center; }
            h1 { color: #d81b60; margin-bottom: 10px; }
            p { color: #666; font-size: 14px; }
            .role-select { display: flex; justify-content: center; gap: 15px; margin: 20px 0; }
            .role-select button { padding: 10px 20px; border: 1px solid #d81b60; background: white; color: #d81b60; border-radius: 5px; cursor: pointer; }
            .role-select button.active { background: #d81b60; color: white; }
            input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            .btn-login { width: 100%; padding: 12px; background: #d81b60; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; margin-top: 10px; }
            .btn-login:hover { background: #ad1457; }
            .register-link { margin-top: 15px; display: block; color: #d81b60; text-decoration: none; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1>Leidy Make Up</h1>
            <p>Gestión de citas para tu salón de belleza</p>
            <div class="role-select">
                <button class="active">Cliente</button>
                <button>Estilista</button>
            </div>
            <form method="POST" action="/usuarios/">
                <input type="email" placeholder="Correo electrónico" required>
                <input type="password" placeholder="Contraseña" required>
                <button type="submit" class="btn-login">Iniciar sesión</button>
            </form>
            <a href="#" class="register-link">¿No tienes cuenta? Regístrate</a>
            <p style="margin-top: 20px; font-size: 12px; color: #999;">Beta educativa · Leidy Make Up</p>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),
    path('usuarios/', include('App_usuarios.urls')),
    path('servicios/', include('App_servicios.urls')),
    path('agenda/', include('App_agenda.urls')),
    path('facturacion/', include('App_facturacion.urls')),
]