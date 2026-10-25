from django.db import models

class Servicio(models.Model):
    nombre = models.CharField(max_length=150)
    categoria = models.CharField(max_length=100, blank=True, default='General')
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(decimal_places=2, max_digits=10)
    duracion = models.PositiveIntegerField(help_text='Duración en minutos')
    es_demo = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"