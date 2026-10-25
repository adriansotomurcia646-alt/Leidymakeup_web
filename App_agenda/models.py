from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from App_usuarios.models import Cliente, Estilista
from App_servicios.models import Servicio


class Horario(models.Model):
	estilista = models.ForeignKey(Estilista, on_delete=models.CASCADE, related_name='horarios')
	dia_semana = models.PositiveSmallIntegerField(help_text='0 lunes, 6 domingo')
	hora_inicio = models.TimeField()
	hora_fin = models.TimeField()
	activo = models.BooleanField(default=True)

	def __str__(self):
		return f'{self.estilista} - día {self.dia_semana}'


class Cita(models.Model):
	ESTADOS = (
		('PENDIENTE', 'En espera'),
		('CONFIRMADA', 'Aceptada'),
		('FINALIZADA', 'Hecho'),
		('RECHAZADA', 'Rechazada'),
		('CANCELADA', 'Cancelada'),
	)

	cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='citas')
	estilista = models.ForeignKey(Estilista, on_delete=models.CASCADE, related_name='citas')
	servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name='citas')
	fecha = models.DateField()
	hora_inicio = models.TimeField()
	hora_fin = models.TimeField()
	estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
	mensaje = models.TextField(blank=True)
	notas = models.TextField(blank=True)
	fecha_solicitud = models.DateTimeField(auto_now_add=True)
	fecha_aceptacion = models.DateTimeField(null=True, blank=True)
	fecha_finalizacion = models.DateTimeField(null=True, blank=True)
	fecha_solicitada = models.DateField(null=True, blank=True)
	hora_solicitada = models.TimeField(null=True, blank=True)
	duracion_aprobada = models.PositiveIntegerField(null=True, blank=True)

	@property
	def hora(self):
		return self.hora_inicio

	@hora.setter
	def hora(self, value):
		self.hora_inicio = value

	@property
	def nota(self):
		return self.mensaje or self.notas

	@property
	def es_historica(self):
		return self.estado == 'CONFIRMADA' and self.fecha < timezone.localdate()

	@property
	def estado_visual(self):
		if self.es_historica:
			return 'FINALIZADA'
		return self.estado

	def save(self, *args, **kwargs):
		if self.fecha and self.hora_inicio and self.servicio_id:
			inicio = datetime.combine(self.fecha, self.hora_inicio)
			self.hora_fin = (
				inicio + timedelta(minutes=self.servicio.duracion)
			).time()
		if self.estado == 'CONFIRMADA' and not self.fecha_aceptacion:
			self.fecha_aceptacion = timezone.now()
		if self.estado == 'FINALIZADA' and not self.fecha_finalizacion:
			self.fecha_finalizacion = timezone.now()
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.servicio} - {self.fecha} {self.hora_inicio}'


class CitaArchivo(models.Model):
	cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='archivos')
	archivo = models.FileField(upload_to='citas/archivos/%Y/%m/%d/', max_length=500)
	nombre_original = models.CharField(max_length=255, blank=True)
	tipo = models.CharField(max_length=30, blank=True)
	creado_en = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('creado_en',)

	def __str__(self):
		return self.nombre_original or self.archivo.name


class Mensaje(models.Model):
	remitente = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='mensajes_enviados',
	)
	destinatario = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='mensajes_recibidos',
	)
	contenido = models.CharField(max_length=2000)
	creado_en = models.DateTimeField(auto_now_add=True)
	leido = models.BooleanField(default=False)

	class Meta:
		ordering = ('creado_en',)

	def __str__(self):
		return f'Mensaje de {self.remitente} para {self.destinatario}'
