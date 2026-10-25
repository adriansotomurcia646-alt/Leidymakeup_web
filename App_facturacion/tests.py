from datetime import date, time
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from App_agenda.models import Cita
from App_servicios.models import Servicio
from App_usuarios.models import Cliente, Estilista, Persona

from .models import RegistroCobro


class ReportesTests(TestCase):
	def setUp(self):
		self.cliente_persona = Persona.objects.create_user(
			username='report-client',
			password='MakeupTest2026!abc',
			rol='cliente',
		)
		self.cliente = Cliente.objects.create(persona=self.cliente_persona)
		self.estilista_persona = Persona.objects.create_user(
			username='report-stylist',
			password='MakeupTest2026!abc',
			rol='estilista',
		)
		self.estilista = Estilista.objects.create(persona=self.estilista_persona)
		self.servicio = Servicio.objects.create(
			nombre='Maquillaje social',
			categoria='Maquillaje',
			precio=Decimal('65000.00'),
			duracion=60,
		)
		self.client.force_login(self.estilista_persona)

	def crear_cobro(self, fecha, monto_pagado, estado='CONFIRMADA'):
		cita = Cita.objects.create(
			cliente=self.cliente,
			estilista=self.estilista,
			servicio=self.servicio,
			fecha=timezone.localdate(),
			hora_inicio=time(10, 0),
			estado=estado,
		)
		cobro = RegistroCobro.objects.create(
			cliente=self.cliente,
			cita=cita,
			monto_total=Decimal('65000.00'),
			monto_pagado=Decimal(monto_pagado),
			saldo_pendiente=Decimal('0.00'),
		)
		RegistroCobro.objects.filter(pk=cobro.pk).update(fecha=fecha)
		return cobro

	def test_report_uses_received_payments_and_groups_months_by_year(self):
		self.crear_cobro(date(2025, 1, 15), '10.25')
		self.crear_cobro(date(2026, 1, 20), '12.50')
		self.crear_cobro(
			date(2026, 2, 1),
			'65000.00',
			estado='CANCELADA',
		)

		response = self.client.get(reverse('App_facturacion:reportes'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['total_ingresos'], Decimal('22.75'))
		meses = list(response.context['ingresos_mensuales'])
		self.assertEqual(len(meses), 2)
		self.assertEqual(
			[(item['mes'].year, item['mes'].month) for item in meses],
			[(2025, 1), (2026, 1)],
		)
		self.assertEqual(
			[item['ingresos'] for item in meses],
			[Decimal('10.25'), Decimal('12.50')],
		)
		self.assertContains(response, 'Ingresos recibidos')

	def test_report_date_filter_includes_both_limits_and_handles_invalid_ranges(self):
		self.crear_cobro(date(2026, 1, 1), '5.00')
		self.crear_cobro(date(2026, 1, 31), '7.00')
		self.crear_cobro(date(2025, 12, 31), '99.00')

		response = self.client.get(
			reverse('App_facturacion:reportes'),
			{'fecha_inicio': '2026-01-01', 'fecha_fin': '2026-01-31'},
		)
		self.assertEqual(response.context['total_periodo'], Decimal('12.00'))

		for inicio, fin in (
			('invalid', '2026-01-31'),
			('2026-02-01', '2026-01-31'),
			('2026-01-01', ''),
		):
			with self.subTest(inicio=inicio, fin=fin):
				response = self.client.get(
					reverse('App_facturacion:reportes'),
					{'fecha_inicio': inicio, 'fecha_fin': fin},
				)
				self.assertEqual(response.status_code, 200)
				self.assertIsNone(response.context['total_periodo'])
				self.assertTrue(response.context['error_fechas'])

	def test_popular_services_excludes_rejected_and_cancelled_appointments(self):
		for estado in ('PENDIENTE', 'CONFIRMADA', 'RECHAZADA', 'CANCELADA'):
			Cita.objects.create(
				cliente=self.cliente,
				estilista=self.estilista,
				servicio=self.servicio,
				fecha=timezone.localdate(),
				hora_inicio=time(10, 0),
				estado=estado,
			)

		response = self.client.get(reverse('App_facturacion:reportes'))

		self.assertEqual(response.context['total_citas'], 2)
		self.assertEqual(
			response.context['servicios_populares'][0]['total'],
			2,
		)
