from django.db import models
from App_usuarios.models import Cliente
from App_agenda.models import Cita
from decimal import Decimal


class RegistroCobro(models.Model):
	cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='registros_cobro')
	cita = models.OneToOneField(Cita, on_delete=models.PROTECT, related_name='registro_cobro')
	monto_total = models.DecimalField(max_digits=10, decimal_places=2)
	monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	saldo_pendiente = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	fecha = models.DateField(auto_now_add=True)

	def __str__(self):
		return f'Cobro {self.cliente} - {self.fecha}'
