from django.test import TestCase
from django.urls import reverse

from App_usuarios.models import Cliente, Estilista, Persona

from .models import Servicio


class ServicioWorkflowTests(TestCase):
	def setUp(self):
		self.estilista_persona = Persona.objects.create_user(
			username='stylist', password='MakeupTest2026!abc', rol='estilista'
		)
		Estilista.objects.create(persona=self.estilista_persona)
		self.cliente_persona = Persona.objects.create_user(
			username='client', password='MakeupTest2026!abc', rol='cliente'
		)
		Cliente.objects.create(persona=self.cliente_persona)

	def test_stylist_crud_updates_the_customer_catalog(self):
		self.client.force_login(self.estilista_persona)
		create_response = self.client.post(
			reverse('App_servicios:crear'),
			{
				'nombre': 'Maquillaje social',
				'categoria': 'Maquillaje',
				'descripcion': 'Servicio de prueba',
				'precio': '65000.00',
				'duracion': '60',
			},
		)
		self.assertRedirects(create_response, reverse('App_servicios:lista'))
		servicio = Servicio.objects.get(nombre='Maquillaje social')

		self.client.post(
			reverse('App_servicios:editar', kwargs={'pk': servicio.pk}),
			{
				'nombre': 'Maquillaje de noche',
				'categoria': 'Maquillaje',
				'descripcion': 'Actualizado',
				'precio': '75000.00',
				'duracion': '90',
			},
		)
		servicio.refresh_from_db()
		self.assertEqual(servicio.nombre, 'Maquillaje de noche')
		self.assertEqual(servicio.duracion, 90)

		self.client.post(
			reverse('App_servicios:eliminar', kwargs={'pk': servicio.pk})
		)
		servicio.refresh_from_db()
		self.assertFalse(servicio.activo)

		self.client.force_login(self.cliente_persona)
		catalogo = self.client.get(reverse('App_servicios:lista'))
		self.assertEqual(catalogo.status_code, 200)
		self.assertNotContains(catalogo, 'Maquillaje de noche')

	def test_stylist_service_form_routes_render_existing_template(self):
		self.client.force_login(self.estilista_persona)
		create_page = self.client.get(reverse('App_servicios:crear'))
		self.assertEqual(create_page.status_code, 200)
		self.assertTemplateUsed(create_page, 'E_servicio_form.html')

		servicio = Servicio.objects.create(
			nombre='Peinado',
			categoria='Cabello',
			precio='40000.00',
			duracion=45,
		)
		edit_page = self.client.get(
			reverse('App_servicios:editar', kwargs={'pk': servicio.pk})
		)
		self.assertEqual(edit_page.status_code, 200)
		self.assertTemplateUsed(edit_page, 'E_servicio_form.html')
