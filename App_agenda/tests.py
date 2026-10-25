import tempfile
from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from App_servicios.models import Servicio
from App_usuarios.models import Cliente, Estilista, Persona

from .models import Cita, Horario, Mensaje


class CitaWorkflowTests(TestCase):
	def setUp(self):
		self.cliente_persona = Persona.objects.create_user(
			username='client', password='MakeupTest2026!abc', rol='cliente'
		)
		self.cliente = Cliente.objects.create(persona=self.cliente_persona)
		self.estilista_persona = Persona.objects.create_user(
			username='stylist', password='MakeupTest2026!abc', rol='estilista'
		)
		self.estilista = Estilista.objects.create(persona=self.estilista_persona)
		self.servicio = Servicio.objects.create(
			nombre='Maquillaje social',
			categoria='Maquillaje',
			precio='65000.00',
			duracion=60,
		)

	def test_root_redirects_to_login(self):
		response = self.client.get('/')
		self.assertRedirects(response, reverse('App_usuarios:login'))

	def test_root_with_an_existing_client_session_does_not_loop(self):
		self.client.force_login(self.cliente_persona)
		response = self.client.get('/', follow=True)

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'App_agenda/C_inicio.html')
		self.assertEqual(
			response.redirect_chain,
			[
				(reverse('App_usuarios:login'), 302),
				(reverse('App_agenda:c_inicio'), 302),
			],
		)

	def test_client_login_redirects_to_client_home(self):
		response = self.client.post(
			reverse('App_usuarios:login'),
			{
				'username': self.cliente_persona.username,
				'password': 'MakeupTest2026!abc',
				'rol': 'cliente',
			},
		)
		self.assertRedirects(response, reverse('App_agenda:c_inicio'))

	def test_stylist_login_redirects_to_stylist_home(self):
		response = self.client.post(
			reverse('App_usuarios:login'),
			{
				'username': self.estilista_persona.username,
				'password': 'MakeupTest2026!abc',
				'rol': 'estilista',
			},
		)

		self.assertRedirects(response, reverse('App_agenda:e_inicio'))

	def test_client_can_navigate_to_other_authorized_pages(self):
		self.client.force_login(self.cliente_persona)
		for route_name, template in (
			('App_agenda:c_mis_citas', 'App_agenda/C_mis_citas.html'),
			('App_agenda:c_reservar', 'App_agenda/C_reservar_cita.html'),
			('App_agenda:c_mensajes', 'App_agenda/C_mensajes.html'),
			('App_usuarios:perfil', 'App_usuarios/C_perfil.html'),
			('App_servicios:lista', 'App_servicios/C_servicios.html'),
		):
			with self.subTest(route=route_name):
				response = self.client.get(reverse(route_name))
				self.assertEqual(response.status_code, 200)
				self.assertTemplateUsed(response, template)

	def test_unauthenticated_user_is_redirected_to_login_and_then_to_requested_page(self):
		protected_url = reverse('App_agenda:c_mis_citas')
		response = self.client.get(protected_url)
		self.assertRedirects(
			response,
			f'{reverse("App_usuarios:login")}?next={protected_url}',
		)

		login_page = self.client.get(response['Location'])
		self.assertContains(login_page, f'name="next" value="{protected_url}"')
		response = self.client.post(
			reverse('App_usuarios:login'),
			{
				'username': self.cliente_persona.username,
				'password': 'MakeupTest2026!abc',
				'rol': 'cliente',
				'next': protected_url,
			},
		)
		self.assertRedirects(response, protected_url)

	def test_authenticated_user_without_required_role_gets_forbidden_without_redirect_loop(self):
		self.client.force_login(self.cliente_persona)
		response = self.client.get(reverse('App_agenda:e_inicio'), follow=True)

		self.assertEqual(response.status_code, 403)
		self.assertEqual(response.redirect_chain, [])

	def test_unknown_route_returns_404_without_redirecting(self):
		response = self.client.get('/not-a-real-route/', follow=True)

		self.assertEqual(response.status_code, 404)
		self.assertEqual(response.redirect_chain, [])

	def test_stylist_sees_stylist_service_management_page(self):
		self.client.force_login(self.estilista_persona)

		response = self.client.get(reverse('App_servicios:lista'))

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'App_servicios/E_servicios.html')

	def test_staff_login_redirects_to_stylist_home(self):
		administrador = Persona.objects.create_user(
			username='admin',
			password='MakeupTest2026!abc',
			is_staff=True,
		)
		response = self.client.post(
			reverse('App_usuarios:login'),
			{
				'username': administrador.username,
				'password': 'MakeupTest2026!abc',
				'rol': 'cliente',
			},
		)
		self.assertRedirects(response, reverse('App_agenda:e_inicio'))
		self.assertEqual(self.client.session['rol'], 'estilista')

	def test_logout_clears_session_and_redirects_to_login(self):
		self.client.force_login(self.cliente_persona)
		session = self.client.session
		session['rol'] = 'cliente'
		session['custom_value'] = 'temporary'
		session.save()

		response = self.client.post(reverse('App_usuarios:logout'))

		self.assertRedirects(response, reverse('App_usuarios:login'))
		self.assertNotIn('_auth_user_id', self.client.session)
		self.assertNotIn('custom_value', self.client.session)

	def test_booking_shows_services_from_the_database(self):
		self.client.force_login(self.cliente_persona)
		response = self.client.get(reverse('App_agenda:c_reservar'))

		self.assertEqual(response.status_code, 200)
		self.assertIn(self.servicio, response.context['servicios'])
		self.assertEqual(
			str(response.context['servicios'].get(pk=self.servicio.pk).precio),
			self.servicio.precio,
		)
		self.assertContains(response, 'Maquillaje social')
		self.assertContains(response, 'Maquillaje')
		self.assertContains(response, '60 min')
		self.assertContains(response, 'id="dias-calendario"')
		self.assertNotContains(response, '2026-10-23')
		self.assertNotContains(response, 'Peinado para eventos')

	def test_booking_shows_empty_state_when_there_are_no_active_services(self):
		self.servicio.activo = False
		self.servicio.save(update_fields=['activo'])
		self.client.force_login(self.cliente_persona)

		response = self.client.get(reverse('App_agenda:c_reservar'))

		self.assertContains(
			response,
			'No hay servicios disponibles para reservar en este momento.',
		)
		self.assertNotContains(response, 'Keratina')

	def test_booking_accepts_the_existing_template_payload(self):
		self.client.force_login(self.cliente_persona)
		fecha = timezone.localdate() + timedelta(days=2)
		response = self.client.post(
			reverse('App_agenda:c_reservar'),
			{
				'servicio_id': str(self.servicio.pk),
				'fecha': fecha.isoformat(),
				'hora': '10:30 AM',
				'mensaje': 'Referencia de prueba',
			},
		)
		self.assertRedirects(response, reverse('App_agenda:c_mis_citas'))
		cita = Cita.objects.get(cliente=self.cliente)
		self.assertEqual(cita.estilista, self.estilista)
		self.assertEqual(cita.hora_inicio.strftime('%H:%M'), '10:30')
		self.assertEqual(cita.hora_fin.strftime('%H:%M'), '11:30')
		self.assertEqual(cita.mensaje, 'Referencia de prueba')
		self.assertEqual(cita.estado, 'PENDIENTE')

	def test_booking_accepts_24_hour_time_and_persists_uploaded_files(self):
		self.client.force_login(self.cliente_persona)
		fecha = timezone.localdate() + timedelta(days=2)
		archivo = SimpleUploadedFile(
			'referencia.png',
			b'\x89PNG\r\n\x1a\n',
			content_type='image/png',
		)
		with tempfile.TemporaryDirectory() as media_root:
			with override_settings(MEDIA_ROOT=media_root):
				response = self.client.post(
					reverse('App_agenda:c_reservar'),
					{
						'servicio_id': str(self.servicio.pk),
						'fecha': fecha.isoformat(),
						'hora': '10:30',
						'mensaje': 'Conservar este mensaje',
						'adjuntos': [archivo],
					},
				)

		self.assertRedirects(response, reverse('App_agenda:c_mis_citas'))
		cita = Cita.objects.get(cliente=self.cliente)
		self.assertEqual(cita.hora_inicio, time(10, 30))
		self.assertEqual(cita.fecha_solicitada, fecha)
		self.assertEqual(cita.hora_solicitada, time(10, 30))
		self.assertEqual(cita.mensaje, 'Conservar este mensaje')
		self.assertEqual(cita.archivos.count(), 1)
		self.assertContains(
			self.client.get(reverse('App_agenda:c_mis_citas')),
			'Maquillaje social',
		)
		self.client.force_login(self.estilista_persona)
		solicitudes = self.client.get(reverse('App_agenda:e_solicitudes'))
		self.assertContains(solicitudes, 'En espera')
		self.assertContains(solicitudes, 'Maquillaje social')
		self.assertContains(solicitudes, 'Conservar este mensaje')

	def test_booking_rejects_a_past_date_and_preserves_the_message(self):
		self.client.force_login(self.cliente_persona)
		fecha = timezone.localdate() - timedelta(days=1)
		response = self.client.post(
			reverse('App_agenda:c_reservar'),
			{
				'servicio_id': str(self.servicio.pk),
				'fecha': fecha.isoformat(),
				'hora': '10:30',
				'mensaje': 'Texto que debe conservarse',
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Cita.objects.count(), 0)
		self.assertContains(response, 'La fecha de la cita no puede estar en el pasado.')
		self.assertContains(response, 'Texto que debe conservarse')
		self.assertEqual(response.context['form'].data['fecha'], fecha.isoformat())

	def test_booking_rejects_past_time_today_and_accepts_a_future_time(self):
		self.client.force_login(self.cliente_persona)
		fecha = timezone.localdate()
		hora_fijada = timezone.make_aware(datetime.combine(fecha, time(9, 0)))
		post_data = {
			'servicio_id': str(self.servicio.pk),
			'fecha': fecha.isoformat(),
			'mensaje': '',
		}
		with patch('App_agenda.forms.timezone.localtime', return_value=hora_fijada):
			response = self.client.post(
				reverse('App_agenda:c_reservar'),
				{**post_data, 'hora': '08:30'},
			)
			self.assertEqual(response.status_code, 200)
			self.assertEqual(Cita.objects.count(), 0)
			self.assertFormError(
				response.context['form'],
				'hora_inicio',
				'La hora seleccionada ya pasó.',
			)

			response = self.client.post(
				reverse('App_agenda:c_reservar'),
				{**post_data, 'hora': '10:30'},
			)

		self.assertRedirects(response, reverse('App_agenda:c_mis_citas'))
		self.assertEqual(Cita.objects.get(cliente=self.cliente).hora_inicio, time(10, 30))

	def test_booking_availability_api_returns_future_iso_times(self):
		self.client.force_login(self.cliente_persona)
		fecha = timezone.localdate() + timedelta(days=2)

		response = self.client.get(
			reverse('App_agenda:horarios_disponibles'),
			{'fecha': fecha.isoformat(), 'servicio_id': self.servicio.pk},
		)

		self.assertEqual(response.status_code, 200)
		self.assertIn(
			{'value': '10:30', 'display': '10:30 AM'},
			response.json()['horarios'],
		)

	def test_booking_availability_respects_configured_working_hours_and_duration(self):
		fecha = timezone.localdate() + timedelta(days=2)
		Horario.objects.create(
			estilista=self.estilista,
			dia_semana=fecha.weekday(),
			hora_inicio=time(9, 0),
			hora_fin=time(11, 0),
		)
		self.client.force_login(self.cliente_persona)

		response = self.client.get(
			reverse('App_agenda:horarios_disponibles'),
			{'fecha': fecha.isoformat(), 'servicio_id': self.servicio.pk},
		)

		self.assertEqual(
			[item['value'] for item in response.json()['horarios']],
			['09:00', '09:30', '10:00'],
		)

	def test_booking_rejects_overlapping_times(self):
		fecha = timezone.localdate() + timedelta(days=2)
		Cita.objects.create(
			cliente=self.cliente,
			estilista=self.estilista,
			servicio=self.servicio,
			fecha=fecha,
			hora_inicio=time(11, 0),
		)
		self.client.force_login(self.cliente_persona)
		response = self.client.post(
			reverse('App_agenda:c_reservar'),
			{
				'servicio_id': str(self.servicio.pk),
				'fecha': fecha.isoformat(),
				'hora': '11:30 AM',
				'mensaje': '',
			},
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Cita.objects.count(), 1)
		self.assertFormError(
			response.context['form'],
			'hora_inicio',
			'No hay estilistas disponibles en ese horario.',
		)

	def test_stylist_dashboard_and_client_breakdown_are_scoped(self):
		fecha_hoy = timezone.localdate()
		Cita.objects.create(
			cliente=self.cliente,
			estilista=self.estilista,
			servicio=self.servicio,
			fecha=fecha_hoy,
			hora_inicio=time(9, 0),
			estado='PENDIENTE',
		)
		Cita.objects.create(
			cliente=self.cliente,
			estilista=self.estilista,
			servicio=self.servicio,
			fecha=fecha_hoy,
			hora_inicio=time(11, 0),
			estado='CONFIRMADA',
		)
		self.client.force_login(self.estilista_persona)

		dashboard = self.client.get(reverse('App_agenda:e_inicio'))
		self.assertEqual(dashboard.context['total_pendientes'], 1)
		self.assertEqual(dashboard.context['total_confirmadas'], 1)
		self.assertEqual(dashboard.context['citas_hoy_count'], 1)
		self.assertEqual(dashboard.context['citas_hoy'].count(), 1)
		self.assertEqual(dashboard.context['horarios_ocupados'], '1 h 0 min')
		self.assertContains(dashboard, '$65000,00')

		clientes = self.client.get(reverse('App_agenda:e_clientes'))
		cliente_contexto = clientes.context['clientes'].get(pk=self.cliente.pk)
		self.assertEqual(cliente_contexto.total_citas, 2)
		self.assertEqual(cliente_contexto.citas_pendientes, 1)
		self.assertEqual(cliente_contexto.citas_confirmadas, 1)

	def test_dashboard_sums_confirmed_service_duration_and_all_time_confirmations(self):
		fecha_hoy = timezone.localdate()
		servicio_largo = Servicio.objects.create(
			nombre='Maquillaje de evento',
			precio='90000.00',
			duracion=90,
		)
		for servicio, fecha, estado, hora in (
			(self.servicio, fecha_hoy, 'CONFIRMADA', time(9, 0)),
			(servicio_largo, fecha_hoy, 'CONFIRMADA', time(11, 0)),
			(self.servicio, fecha_hoy, 'PENDIENTE', time(14, 0)),
			(self.servicio, fecha_hoy - timedelta(days=1), 'CONFIRMADA', time(9, 0)),
		):
			Cita.objects.create(
				cliente=self.cliente,
				estilista=self.estilista,
				servicio=servicio,
				fecha=fecha,
				hora_inicio=hora,
				estado=estado,
			)
		self.client.force_login(self.estilista_persona)

		response = self.client.get(reverse('App_agenda:e_inicio'))

		self.assertEqual(response.context['total_pendientes'], 1)
		self.assertEqual(response.context['citas_hoy_count'], 2)
		self.assertEqual(response.context['total_confirmadas'], 3)
		self.assertEqual(response.context['horarios_ocupados'], '2 h 30 min')
		self.assertEqual(
			[cita.servicio.nombre for cita in response.context['citas_hoy']],
			['Maquillaje social', 'Maquillaje de evento'],
		)

	def test_requests_and_calendar_are_scoped_to_the_logged_in_stylist(self):
		fecha = timezone.localdate() + timedelta(days=2)
		propia = Cita.objects.create(
			cliente=self.cliente,
			estilista=self.estilista,
			servicio=self.servicio,
			fecha=fecha,
			hora_inicio=time(10, 0),
			estado='PENDIENTE',
		)

		otra_persona = Persona.objects.create_user(
			username='other-stylist', password='MakeupTest2026!abc', rol='estilista'
		)

		otra_estilista = Estilista.objects.create(persona=otra_persona)
		Cita.objects.create(
			cliente=self.cliente,
			estilista=otra_estilista,
			servicio=self.servicio,
			fecha=fecha,
			hora_inicio=time(12, 0),
			estado='PENDIENTE',
		)
		self.client.force_login(self.estilista_persona)

		solicitudes = self.client.get(
			reverse('App_agenda:e_solicitudes'),
			{'estado': 'PENDIENTE'},
		)
		self.assertEqual(list(solicitudes.context['citas']), [propia])

		calendario = self.client.get(
			reverse('App_agenda:e_calendario'),
			{'fecha': fecha.isoformat()},
		)
		self.assertEqual(calendario.status_code, 200)
		self.assertEqual(
			[item['id'] for item in calendario.context['citas_dia']],
			[propia.pk],
		)

	def test_calendar_api_navigates_month_week_day_and_includes_leap_day(self):
		for fecha, hora in (
			(date(2024, 2, 29), time(10, 0)),
			(date(2024, 3, 1), time(11, 0)),
		):
			Cita.objects.create(
				cliente=self.cliente,
				estilista=self.estilista,
				servicio=self.servicio,
				fecha=fecha,
				hora_inicio=hora,
				estado='CONFIRMADA',
			)
		self.client.force_login(self.estilista_persona)
		url = reverse('App_agenda:e_calendario')

		mes = self.client.get(
			url,
			{'formato': 'json', 'fecha': '2024-02-29', 'vista': 'mes'},
		).json()
		self.assertEqual(mes['inicio_periodo'], '2024-02-01')
		self.assertEqual(mes['fin_periodo'], '2024-02-29')
		self.assertEqual([cita['fecha'] for cita in mes['citas']], ['2024-02-29'])
		self.assertEqual(mes['citas_dia'][0]['categoria'], 'Maquillaje')
		self.assertEqual(mes['citas_dia'][0]['precio'], '65000.00')
		self.assertEqual(mes['citas_dia'][0]['fin'], '11:00')
		self.assertEqual(mes['resumen']['CONFIRMADA'], 1)

		semana = self.client.get(
			url,
			{'formato': 'json', 'fecha': '2024-02-29', 'vista': 'semana'},
		).json()
		self.assertEqual(semana['inicio_periodo'], '2024-02-26')
		self.assertEqual(semana['fin_periodo'], '2024-03-03')
		self.assertEqual(len(semana['citas']), 2)

		dia = self.client.get(
			url,
			{'formato': 'json', 'fecha': '2024-02-29', 'vista': 'dia'},
		).json()
		self.assertEqual(dia['inicio_periodo'], '2024-02-29')
		self.assertEqual(dia['fin_periodo'], '2024-02-29')

	def test_calendar_search_status_and_date_filters_use_real_appointments(self):
		servicio2 = Servicio.objects.create(
			nombre='Peinado de fiesta',
			categoria='Cabello',
			precio='50000.00',
			duracion=45,
		)
		cita = Cita.objects.create(
			cliente=self.cliente,
			estilista=self.estilista,
			servicio=servicio2,
			fecha=date(2026, 10, 12),
			hora_inicio=time(10, 0),
			estado='PENDIENTE',
		)
		self.cliente_persona.first_name = 'María'
		self.cliente_persona.last_name = 'Rodríguez'
		self.cliente_persona.save(update_fields=['first_name', 'last_name'])
		self.client.force_login(self.estilista_persona)
		url = reverse('App_agenda:e_calendario')
		self.assertEqual(
			Cita.objects.filter(
				estilista=self.estilista,
				cliente__persona__last_name__icontains='rodr',
			).count(),
			1,
		)
		parameters = {
			'formato': 'json',
			'fecha': '2026-10-12',
			'vista': 'mes',
			'desde': '2026-10-01',
			'hasta': '2026-10-31',
			'estado': 'PENDIENTE',
		}

		por_nombre = self.client.get(url, {**parameters, 'q': 'rodr'}).json()
		self.assertEqual(
			[item['id'] for item in por_nombre['citas']],
			[cita.pk],
			por_nombre,
		)
		por_servicio = self.client.get(url, {**parameters, 'q': 'fiesta'}).json()
		self.assertEqual([item['id'] for item in por_servicio['citas']], [cita.pk])
		self.assertEqual(por_servicio['resumen']['PENDIENTE'], 1)
		por_horario = self.client.get(
			url,
			{**parameters, 'hora_desde': '09:30', 'hora_hasta': '10:30'},
		).json()
		self.assertEqual([item['id'] for item in por_horario['citas']], [cita.pk])
		hora_invalida = self.client.get(
			url,
			{**parameters, 'hora_desde': '11:00', 'hora_hasta': '09:00'},
		).json()
		self.assertIn('horario no es válido', hora_invalida['error'])
		self.assertEqual(hora_invalida['citas'], [])
		sin_resultados = self.client.get(
			url,
			{**parameters, 'q': 'inexistente'},
		).json()
		self.assertEqual(sin_resultados['citas'], [])
		invalido = self.client.get(
			url,
			{**parameters, 'desde': '2026-11-01', 'hasta': '2026-10-01'},
		).json()
		self.assertIn('posterior', invalido['error'])
		self.assertEqual(invalido['citas'], [])
		fecha_invalida = self.client.get(
			url,
			{'formato': 'json', 'fecha': 'no-es-fecha', 'vista': 'mes'},
		).json()
		self.assertIn('no es válida', fecha_invalida['error'])

	def test_client_calendar_only_exposes_the_logged_in_clients_appointments(self):
		propia = Cita.objects.create(
			cliente=self.cliente,
			estilista=self.estilista,
			servicio=self.servicio,
			fecha=date(2026, 10, 15),
			hora_inicio=time(10, 0),
			estado='FINALIZADA',
		)
		otra_persona = Persona.objects.create_user(
			username='calendar-other',
			password='MakeupTest2026!abc',
			first_name='Otra',
			last_name='Clienta',
			rol='cliente',
		)
		otro_cliente = Cliente.objects.create(persona=otra_persona)
		Cita.objects.create(
			cliente=otro_cliente,
			estilista=self.estilista,
			servicio=self.servicio,
			fecha=date(2026, 10, 15),
			hora_inicio=time(12, 0),
			estado='CONFIRMADA',
		)
		self.client.force_login(self.cliente_persona)

		response = self.client.get(
			reverse('App_agenda:c_calendario'),
			{'formato': 'json', 'fecha': '2026-10-15', 'vista': 'dia'},
		)

		self.assertEqual([item['id'] for item in response.json()['citas']], [propia.pk])
		self.assertNotContains(
			self.client.get(reverse('App_agenda:c_calendario')),
			'Otra Clienta',
		)

	def test_only_stylist_can_complete_confirmed_appointments(self):
		cita = Cita.objects.create(
			cliente=self.cliente,
			estilista=self.estilista,
			servicio=self.servicio,
			fecha=timezone.localdate() - timedelta(days=1),
			hora_inicio=time(10, 0),
			estado='CONFIRMADA',
		)
		url = reverse('App_agenda:completar_cita', args=[cita.pk])
		self.client.force_login(self.estilista_persona)
		self.assertEqual(self.client.get(url).status_code, 405)
		response = self.client.post(url)
		self.assertRedirects(
			response,
			f'{reverse("App_agenda:e_calendario")}?fecha={cita.fecha.isoformat()}',
		)
		cita.refresh_from_db()
		self.assertEqual(cita.estado, 'FINALIZADA')
		calendar_response = self.client.get(
			reverse('App_agenda:e_calendario'),
			{'fecha': cita.fecha.isoformat(), 'vista': 'dia'},
		)
		self.assertContains(calendar_response, 'line-through')
		self.assertContains(calendar_response, 'Hecho')
		self.assertContains(calendar_response, "cita.estado === 'CONFIRMADA'")
		self.assertContains(calendar_response, 'Marcar Hecho')

		otra_persona = Persona.objects.create_user(
			username='unrelated-stylist',
			password='MakeupTest2026!abc',
			rol='estilista',
		)
		Estilista.objects.create(persona=otra_persona)
		otra_cita = Cita.objects.create(
			cliente=self.cliente,
			estilista=self.estilista,
			servicio=self.servicio,
			fecha=timezone.localdate(),
			hora_inicio=time(12, 0),
			estado='CONFIRMADA',
		)
		self.client.force_login(otra_persona)
		self.assertEqual(
			self.client.post(
				reverse('App_agenda:completar_cita', args=[otra_cita.pk])
			).status_code,
			404,
		)
		self.client.force_login(self.cliente_persona)
		self.assertEqual(self.client.post(url).status_code, 403)

	def test_solicitud_changes_require_post_and_are_scoped_to_stylist(self):
		cita = Cita.objects.create(
			cliente=self.cliente,
			estilista=self.estilista,
			servicio=self.servicio,
			fecha=timezone.localdate() + timedelta(days=1),
			hora_inicio=time(10, 0),
		)
		url = reverse(
			'App_agenda:actualizar_solicitud',
			args=[cita.pk, 'CONFIRMADA'],
		)
		self.client.force_login(self.estilista_persona)

		self.assertEqual(self.client.get(url).status_code, 405)
		response = self.client.post(url)
		self.assertRedirects(response, reverse('App_agenda:e_solicitudes'))
		cita.refresh_from_db()
		self.assertEqual(cita.estado, 'CONFIRMADA')

		self.client.force_login(self.cliente_persona)
		self.assertEqual(self.client.post(url).status_code, 403)

	def test_client_messages_use_safe_recipient_and_read_notifications(self):
		self.cliente_persona.first_name = 'Ana'
		self.cliente_persona.last_name = 'Ríos'
		self.cliente_persona.save(update_fields=['first_name', 'last_name'])
		self.client.force_login(self.cliente_persona)

		inicio = self.client.get(reverse('App_agenda:c_inicio'))
		self.assertContains(inicio, 'Hola, Ana')
		self.assertContains(inicio, 'Ana Ríos')
		self.assertNotContains(inicio, 'sin leer')

		response = self.client.post(
			reverse('App_agenda:c_mensajes'),
			{'contenido': 'Hola', 'destinatario_id': '99999'},
		)
		self.assertRedirects(response, reverse('App_agenda:c_mensajes'))
		mensaje = Mensaje.objects.get()
		self.assertEqual(mensaje.destinatario, self.estilista_persona)

		otro_usuario = Persona.objects.create_user(
			username='other-client',
			password='MakeupTest2026!abc',
			rol='cliente',
		)
		historial = self.client.get(reverse('App_agenda:c_mensajes'))
		self.assertContains(historial, 'Pendiente')
		Mensaje.objects.create(
			remitente=self.estilista_persona,
			destinatario=self.cliente_persona,
			contenido='Respuesta',
		)
		otro_mensaje = Mensaje.objects.create(
			remitente=self.estilista_persona,
			destinatario=otro_usuario,
			contenido='Mensaje para otra persona',
		)

		inicio = self.client.get(reverse('App_agenda:c_inicio'))
		self.assertContains(inicio, '1 notificación sin leer')
		historial = self.client.get(reverse('App_agenda:c_mensajes'))
		self.assertContains(historial, 'Respondido por la estilista')
		self.assertTrue(
			Mensaje.objects.get(
				destinatario=self.cliente_persona,
				contenido='Respuesta',
			).leido
		)
		inicio = self.client.get(reverse('App_agenda:c_inicio'))
		self.assertNotContains(inicio, 'sin leer')
		otro_mensaje.refresh_from_db()
		self.assertFalse(otro_mensaje.leido)

	def test_client_cannot_send_when_stylist_recipient_is_ambiguous(self):
		otra_persona = Persona.objects.create_user(
			username='another-stylist',
			password='MakeupTest2026!abc',
			rol='estilista',
		)
		Estilista.objects.create(persona=otra_persona)
		self.client.force_login(self.cliente_persona)

		response = self.client.post(
			reverse('App_agenda:c_mensajes'),
			{'contenido': 'No debe llegar a destinatario incorrecto'},
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(Mensaje.objects.exists())
		self.assertContains(response, 'No se pudo determinar')

	def test_sidebar_highlights_the_current_stylist_section(self):
		self.client.force_login(self.estilista_persona)

		response = self.client.get(reverse('App_agenda:e_solicitudes'))

		self.assertContains(
			response,
			'href="/agenda/estilista/solicitudes/" class="flex items-center gap-3 px-4 py-2.5 bg-[#d6336c] text-white',
		)

	def test_sidebar_highlights_only_the_current_client_section(self):
		self.client.force_login(self.cliente_persona)

		response = self.client.get(reverse('App_agenda:c_mis_citas'))

		self.assertContains(
			response,
			'href="/agenda/mis-citas/" class="flex items-center gap-3 px-4 py-3 rounded-xl transition-colors text-xs font-medium bg-[#d6336c] text-white',
		)
		self.assertContains(
			response,
			'href="/agenda/inicio/" class="flex items-center gap-3 px-4 py-3 rounded-xl transition-colors text-xs font-medium text-gray-600 hover:bg-gray-50',
		)

# Create your tests here.
