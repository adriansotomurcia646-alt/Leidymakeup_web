from django.db import models
from django.contrib.auth.models import AbstractUser


class Persona(AbstractUser):
	ROLES = (
		('cliente', 'Cliente'),
		('estilista', 'Estilista'),
	)

	rol = models.CharField(max_length=20, choices=ROLES, default='cliente')

	def __str__(self):
		return self.get_full_name() or self.username

	def es_cliente(self):
		return hasattr(self, 'cliente')

	def es_estilista(self):
		return hasattr(self, 'estilista')


class Estilista(models.Model):
	persona = models.OneToOneField(Persona, on_delete=models.CASCADE, related_name='estilista')
	especialidad = models.CharField(max_length=120, blank=True)

	def __str__(self):
		return str(self.persona)


class Cliente(models.Model):
	persona = models.OneToOneField(Persona, on_delete=models.CASCADE, related_name='cliente')
	telefono = models.CharField(max_length=30, blank=True)

	@property
	def username(self):
		return self.persona.username

	def get_full_name(self):
		return self.persona.get_full_name()

	@property
	def profile(self):
		return self

	def __str__(self):
		return str(self.persona)
