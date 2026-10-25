import logging
from datetime import date, datetime, time, timedelta

from django.contrib import messages
from django.core.files.storage import default_storage
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from App_usuarios.decorators import role_required
from App_usuarios.models import Cliente, Estilista
from App_servicios.models import Servicio
from .forms import (
    ReservarCitaForm,
    _estilista_disponible,
    obtener_horarios_disponibles,
)
from .models import Cita, CitaArchivo, Mensaje

logger = logging.getLogger(__name__)
ALLOWED_UPLOAD_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.pdf', '.mp4', '.webm'}
ALLOWED_UPLOAD_MIME_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'application/pdf',
    'video/mp4',
    'video/webm',
}


def _estado_normalizado(estado):
    mapping = {'ACEPTADA': 'CONFIRMADA', 'APROBADA': 'CONFIRMADA', 'FINALIZADA': 'FINALIZADA'}
    return mapping.get(str(estado).upper(), str(estado).upper())


def _estado_visual(cita):
    if cita.estado == 'CONFIRMADA' and cita.fecha < timezone.localdate():
        return 'FINALIZADA'
    return cita.estado


def _validar_adjuntos(archivos):
    for archivo in archivos or []:
        if archivo is None or getattr(archivo, 'size', 0) == 0:
            continue
        nombre = archivo.name or 'adjunto'
        extension = ''
        if '.' in nombre:
            extension = nombre.rsplit('.', 1)[1].lower()
        if extension not in {ext.lstrip('.') for ext in ALLOWED_UPLOAD_EXTENSIONS}:
            raise ValueError('Tipo de archivo no permitido.')
        if archivo.size > 10 * 1024 * 1024:
            raise ValueError('El archivo supera el tamaño máximo permitido (10 MB).')
        if archivo.content_type not in ALLOWED_UPLOAD_MIME_TYPES:
            mime_type = archivo.content_type or ''
            if mime_type.split('/')[0] not in ('image', 'video', 'application'):
                raise ValueError('Tipo de archivo no permitido.')


def _guardar_adjuntos(cita, archivos):
    _validar_adjuntos(archivos)
    for archivo in archivos or []:
        if archivo is None or getattr(archivo, 'size', 0) == 0:
            continue
        nombre = archivo.name or 'adjunto'
        extension = nombre.rsplit('.', 1)[-1].lower() if '.' in nombre else ''
        safe_name = default_storage.get_valid_name(nombre)
        safe_name = default_storage.get_available_name(safe_name)
        saved_name = default_storage.save(safe_name, archivo)
        CitaArchivo.objects.create(
            cita=cita,
            archivo=saved_name,
            nombre_original=nombre,
            tipo=(archivo.content_type or '').split('/')[-1] or extension,
        )

@login_required
def reservar_cita_view(request):
	servicios = Servicio.objects.filter(activo=True).order_by('nombre')
	form = ReservarCitaForm(
		request.POST if request.method == 'POST' else None
	)
	error = ''
	paso_actual = 1

	if request.method == 'POST':
		try:
			_validar_adjuntos(request.FILES.getlist('adjuntos'))
		except ValueError as exc:
			error = str(exc)

		if not error and form.is_valid():
			cliente, _ = Cliente.objects.get_or_create(persona=request.user)
			estilista = form.cleaned_data['estilista']
			servicio = form.cleaned_data['servicio']
			fecha = form.cleaned_data['fecha']
			hora_inicio = form.cleaned_data['hora_inicio']
			try:
				with transaction.atomic():
					estilista = Estilista.objects.select_for_update().get(
						pk=estilista.pk
					)
					duplicada = Cita.objects.filter(
						cliente=cliente,
						servicio=servicio,
						fecha=fecha,
						hora_inicio=hora_inicio,
						estado__in=('PENDIENTE', 'CONFIRMADA'),
					).exists()
					if duplicada:
						form.add_error(
							'hora_inicio',
							'Ya tienes una solicitud para ese servicio, fecha y hora.',
						)
					elif not _estilista_disponible(
						estilista, fecha, hora_inicio, servicio, cliente=cliente
					):
						form.add_error(
							'hora_inicio',
							'Ese horario acaba de dejar de estar disponible. '
							'Selecciona otro horario.',
						)
					else:
						cita = form.save(commit=False)
						cita.cliente = cliente
						cita.estilista = estilista
						cita.estado = 'PENDIENTE'
						cita.fecha_solicitada = fecha
						cita.hora_solicitada = hora_inicio
						cita.save()
						_guardar_adjuntos(
							cita, request.FILES.getlist('adjuntos')
						)
				if not form.errors:
					messages.success(
						request, 'Tu solicitud de cita fue enviada correctamente.'
					)
					return redirect('App_agenda:c_mis_citas')
			except (IntegrityError, OperationalError):
				logger.exception(
					'No se pudo guardar una solicitud de cita por un conflicto '
					'de concurrencia o integridad.'
				)
				form.add_error(
					'hora_inicio',
					'No fue posible reservar ese horario porque cambió su '
					'disponibilidad. Actualiza la página e inténtalo de nuevo.',
				)
		elif not error:
			error = 'Revisa los datos señalados antes de enviar la solicitud.'

		if form.errors or error:
			paso_actual = 3 if request.POST.get('servicio_id') else 1
			if not request.POST.get('fecha') or not request.POST.get('hora'):
				paso_actual = 2 if request.POST.get('servicio_id') else 1

	return render(
		request,
		'App_agenda/C_reservar_cita.html',
		{
			'servicios': servicios,
			'form': form,
			'error': error,
			'paso_actual': paso_actual,
			'hoy': timezone.localdate().isoformat(),
		},
	)


@role_required('cliente')
def horarios_disponibles_view(request):
	fecha_texto = request.GET.get('fecha', '')
	servicio_id = request.GET.get('servicio_id', '')
	try:
		fecha = date.fromisoformat(fecha_texto)
		servicio = Servicio.objects.get(pk=servicio_id, activo=True)
	except (ValueError, TypeError, Servicio.DoesNotExist):
		return JsonResponse(
			{'error': 'Selecciona una fecha y un servicio válidos.'},
			status=400,
		)

	if fecha < timezone.localdate():
		return JsonResponse(
			{'error': 'No se pueden consultar horarios de fechas pasadas.'},
			status=400,
		)

	horarios = obtener_horarios_disponibles(fecha, servicio)
	return JsonResponse({
		'horarios': [
			{
				'value': horario.strftime('%H:%M'),
				'display': datetime.combine(fecha, horario).strftime('%I:%M %p').lstrip('0'),
			}
			for horario in horarios
		],
	})

@role_required('cliente')
def mis_citas_view(request):
	cliente, _ = Cliente.objects.get_or_create(persona=request.user)
	citas = Cita.objects.filter(cliente=cliente).select_related(
		'servicio', 'estilista__persona'
	).order_by('-fecha', '-hora_inicio')
	return render(request, 'App_agenda/C_mis_citas.html', {'citas': citas})


@role_required('cliente')
@require_POST
def cancelar_cita_view(request, cita_id):
	cliente, _ = Cliente.objects.get_or_create(persona=request.user)
	cita = get_object_or_404(
		Cita,
		pk=cita_id,
		cliente=cliente,
		estado__in=('PENDIENTE', 'CONFIRMADA'),
	)
	cita.estado = 'CANCELADA'
	cita.save(update_fields=['estado'])
	messages.success(request, 'La cita fue cancelada.')
	return redirect('App_agenda:c_mis_citas')


@role_required('cliente')
def mensajes_cliente_view(request):
	cliente = Cliente.objects.filter(persona=request.user).first()
	estilistas_asociadas = Estilista.objects.none()
	if cliente:
		estilistas_asociadas = Estilista.objects.filter(
			citas__cliente=cliente
		).distinct()

	conversacion = Mensaje.objects.filter(
		Q(remitente=request.user, destinatario__rol='estilista')
		| Q(remitente=request.user, destinatario__is_staff=True)
		| Q(remitente=request.user, destinatario__is_superuser=True)
		| Q(destinatario=request.user, remitente__rol='estilista')
		| Q(destinatario=request.user, remitente__is_staff=True)
		| Q(destinatario=request.user, remitente__is_superuser=True)
	).order_by('-creado_en').first()
	contacto = None
	if conversacion:
		destinatario_id = (
			conversacion.destinatario_id
			if conversacion.remitente_id == request.user.pk
			else conversacion.remitente_id
		)
		contacto = Estilista.objects.filter(persona_id=destinatario_id).select_related(
			'persona'
		).first()
	elif estilistas_asociadas.count() == 1:
		contacto = estilistas_asociadas.select_related('persona').first()
	else:
		estilistas = Estilista.objects.filter(
			persona__rol='estilista'
		).select_related('persona')
		if estilistas.count() == 1:
			contacto = estilistas.first()

	if request.method == 'POST' and contacto:
		contenido = request.POST.get('contenido', '').strip()
		if not contenido or len(contenido) > 2000:
			messages.error(request, 'El mensaje debe tener entre 1 y 2000 caracteres.')
		else:
			Mensaje.objects.create(
				remitente=request.user,
				destinatario=contacto.persona,
				contenido=contenido,
			)
			return redirect('App_agenda:c_mensajes')
	elif request.method == 'POST':
		messages.error(
			request,
			'No se pudo determinar una estilista destinataria para tu mensaje.',
		)

	mensajes = Mensaje.objects.none()
	if contacto:
		respuesta_posterior = Mensaje.objects.filter(
			remitente=contacto.persona,
			destinatario=request.user,
			creado_en__gt=OuterRef('creado_en'),
		)
		mensajes = Mensaje.objects.filter(
			Q(remitente=request.user, destinatario=contacto.persona)
			| Q(remitente=contacto.persona, destinatario=request.user)
		).annotate(
			tiene_respuesta=Exists(respuesta_posterior),
		).select_related('remitente', 'destinatario')
		mensajes.filter(destinatario=request.user, leido=False).update(leido=True)
	return render(
		request,
		'App_agenda/C_mensajes.html',
		{'contacto': contacto, 'mensajes': mensajes},
	)


@role_required('estilista')
def inicio_estilista_view(request):
	estilista, _ = Estilista.objects.get_or_create(persona=request.user)
	citas = Cita.objects.filter(estilista=estilista)
	citas_hoy = citas.filter(
		fecha=timezone.localdate(),
		estado='CONFIRMADA',
	).select_related(
		'cliente__persona', 'servicio'
	).order_by('hora_inicio')
	duracion_minutos = citas_hoy.aggregate(
		total=Sum('servicio__duracion'),
	)['total'] or 0
	horas, minutos = divmod(duracion_minutos, 60)
	context = {
		'total_pendientes': citas.filter(estado='PENDIENTE').count(),
		'total_confirmadas': citas.filter(estado='CONFIRMADA').count(),
		'citas_hoy': citas_hoy,
		'citas_hoy_count': citas_hoy.count(),
		'horarios_ocupados': f'{horas} h {minutos} min',
	}
	return render(request, 'App_agenda/E_inicio.html', context)


@role_required('estilista')
def solicitudes_view(request):
	estilista, _ = Estilista.objects.get_or_create(persona=request.user)
	estado = request.GET.get('estado', 'PENDIENTE').upper()
	solicitudes = Cita.objects.filter(estilista=estilista)
	if estado in dict(Cita.ESTADOS):
		solicitudes = solicitudes.filter(estado=estado)
	elif estado != 'TODAS':
		estado = 'PENDIENTE'
		solicitudes = solicitudes.filter(estado=estado)
	solicitudes = solicitudes.select_related(
		'cliente__persona', 'servicio'
	).order_by('fecha', 'hora_inicio')
	return render(
		request,
		'App_agenda/E_solicitudes.html',
		{'citas': solicitudes, 'solicitudes': solicitudes, 'estado_seleccionado': estado},
	)


@role_required('estilista')
@require_POST
def actualizar_solicitud_view(request, cita_id, estado):
	estado = _estado_normalizado(estado)
	if estado not in ('CONFIRMADA', 'RECHAZADA'):
		messages.error(request, 'El estado solicitado no es válido.')
		return redirect('App_agenda:e_solicitudes')

	estilista, _ = Estilista.objects.get_or_create(persona=request.user)
	with transaction.atomic():
		cita = get_object_or_404(
			Cita.objects.select_for_update(),
			pk=cita_id,
			estilista=estilista,
			estado='PENDIENTE',
		)
		if estado == 'CONFIRMADA':
			overlap = Cita.objects.filter(
				estilista=estilista,
				fecha=cita.fecha,
				estado__in=('PENDIENTE', 'CONFIRMADA'),
				hora_inicio__lt=cita.hora_fin,
				hora_fin__gt=cita.hora_inicio,
			).exclude(pk=cita.pk).exists()
			if overlap:
				messages.error(request, 'Ese horario ya fue reservado por otra solicitud activa.')
				return redirect('App_agenda:e_solicitudes')
		cita.estado = estado
		cita.duracion_aprobada = cita.servicio.duracion
		if estado == 'CONFIRMADA':
			cita.fecha_aceptacion = timezone.now()
			if cita.fecha_solicitada is None:
				cita.fecha_solicitada = cita.fecha
			if cita.hora_solicitada is None:
				cita.hora_solicitada = cita.hora_inicio
		cita.save(update_fields=['estado', 'duracion_aprobada', 'fecha_aceptacion', 'fecha_solicitada', 'hora_solicitada'])
	messages.success(request, f'La solicitud fue {"aceptada" if estado == "CONFIRMADA" else "rechazada"}.')
	return redirect('App_agenda:e_solicitudes')


def _calendar_date(value, fallback):
	if not value:
		return fallback, ''
	try:
		return date.fromisoformat(value), ''
	except (TypeError, ValueError):
		return fallback, 'La fecha indicada no es válida.'


def _calendar_range(fecha, vista):
	if vista == 'dia':
		return fecha, fecha
	if vista == 'semana':
		inicio = fecha - timedelta(days=fecha.weekday())
		return inicio, inicio + timedelta(days=6)
	inicio = fecha.replace(day=1)
	siguiente_mes = (
		date(inicio.year + 1, 1, 1)
		if inicio.month == 12
		else date(inicio.year, inicio.month + 1, 1)
	)
	return inicio, siguiente_mes - timedelta(days=1)


def _calendar_payload(request, stylist):
	hoy = timezone.localdate()
	fecha, error = _calendar_date(request.GET.get('fecha'), hoy)
	vista = request.GET.get('vista', 'mes')
	if vista not in ('mes', 'semana', 'dia'):
		vista = 'mes'
		error = error or 'La vista solicitada no es válida.'

	citas = Cita.objects.all()
	if stylist:
		citas = citas.filter(estilista=stylist)
	else:
		citas = citas.filter(cliente__persona=request.user)

	query = request.GET.get('q', '').strip()[:100]
	if query:
		citas = citas.filter(
			Q(cliente__persona__first_name__icontains=query)
			| Q(cliente__persona__last_name__icontains=query)
			| Q(cliente__persona__username__icontains=query)
			| Q(servicio__nombre__icontains=query)
		)

	estado = request.GET.get('estado', '').upper()
	estados_validos = dict(Cita.ESTADOS)
	if estado and estado not in estados_validos:
		error = error or 'El estado seleccionado no es válido.'
		citas = citas.none()
	elif estado:
		citas = citas.filter(estado=estado)

	fecha_inicio_raw = request.GET.get('desde', '').strip()
	fecha_fin_raw = request.GET.get('hasta', '').strip()
	fecha_inicio = fecha_fin = None
	if fecha_inicio_raw or fecha_fin_raw:
		fecha_inicio, error_inicio = _calendar_date(fecha_inicio_raw, None)
		fecha_fin, error_fin = _calendar_date(fecha_fin_raw, None)
		if error_inicio or error_fin or not fecha_inicio or not fecha_fin:
			error = error or 'El rango de fechas debe incluir dos fechas válidas.'
			citas = citas.none()
		elif fecha_inicio > fecha_fin:
			error = error or 'La fecha inicial no puede ser posterior a la final.'
			citas = citas.none()
		else:
			citas = citas.filter(fecha__gte=fecha_inicio, fecha__lte=fecha_fin)

	hora_inicio_raw = request.GET.get('hora_desde', '').strip()
	hora_fin_raw = request.GET.get('hora_hasta', '').strip()
	if hora_inicio_raw or hora_fin_raw:
		try:
			hora_inicio = time.fromisoformat(hora_inicio_raw) if hora_inicio_raw else None
			hora_fin = time.fromisoformat(hora_fin_raw) if hora_fin_raw else None
			if hora_inicio and hora_fin and hora_inicio > hora_fin:
				raise ValueError
		except ValueError:
			error = error or 'El rango horario no es válido.'
			citas = citas.none()
		else:
			if hora_inicio:
				citas = citas.filter(hora_inicio__gte=hora_inicio)
			if hora_fin:
				citas = citas.filter(hora_inicio__lte=hora_fin)

	inicio, fin = _calendar_range(fecha, vista)
	citas_periodo = citas.filter(
		fecha__gte=inicio,
		fecha__lte=fin,
	).select_related('cliente__persona', 'servicio').order_by('fecha', 'hora_inicio')
	citas_dia = citas.filter(fecha=fecha).select_related(
		'cliente__persona', 'servicio'
	).order_by('hora_inicio')
	estados = citas_dia.values('estado').annotate(total=Count('pk'))
	resumen = {estado: 0 for estado in estados_validos}
	resumen.update({fila['estado']: fila['total'] for fila in estados})
	duracion = citas_dia.exclude(
		estado__in=('RECHAZADA', 'CANCELADA')
	).aggregate(total=Sum('servicio__duracion'))['total'] or 0
	proximas = citas.filter(
		Q(fecha__gt=hoy)
		| Q(fecha=hoy, hora_inicio__gte=timezone.localtime().time()),
		estado__in=('PENDIENTE', 'CONFIRMADA'),
	).count()

	def serialize(cita):
		estado_visual = _estado_visual(cita)
		return {
			'id': cita.pk,
			'cliente': cita.cliente.get_full_name() or cita.cliente.username,
			'servicio': cita.servicio.nombre,
			'categoria': cita.servicio.categoria,
			'precio': str(cita.servicio.precio),
			'fecha': cita.fecha.isoformat(),
			'inicio': cita.hora_inicio.strftime('%H:%M'),
			'fin': cita.hora_fin.strftime('%H:%M'),
			'duracion': cita.servicio.duracion,
			'estado': cita.estado,
			'estado_visual': estado_visual,
			'mensaje': cita.mensaje or cita.notas,
		}

	dias_con_citas = list(
		citas_periodo.values_list('fecha', flat=True).distinct().order_by('fecha')
	)
	payload = {
		'fecha': fecha,
		'hoy': hoy,
		'vista': vista,
		'inicio_periodo': inicio,
		'fin_periodo': fin,
		'citas': [serialize(cita) for cita in citas_periodo],
		'citas_dia': [serialize(cita) for cita in citas_dia],
		'resumen': resumen,
		'proximas': proximas,
		'duracion_total': duracion,
		'dias_con_citas': [dia.isoformat() for dia in dias_con_citas],
		'error': error,
		'rol_calendario': 'estilista' if stylist else 'cliente',
	}
	return payload


def _calendar_view(request, stylist):
	payload = _calendar_payload(request, stylist)
	if request.GET.get('formato') == 'json' or request.GET.get('format') == 'json':
		return JsonResponse({
			key: value.isoformat() if isinstance(value, date) else value
			for key, value in payload.items()
			if key != 'calendar_json'
		})
	template = (
		'App_agenda/E_calendario.html'
		if stylist
		else 'App_agenda/C_calendario.html'
	)
	payload['estados_choices'] = Cita.ESTADOS
	payload['calendar_json'] = {
		key: value
		for key, value in payload.items()
		if key != 'estados_choices'
	}
	return render(request, template, payload)


@role_required('estilista')
def calendario_view(request):
	estilista, _ = Estilista.objects.get_or_create(persona=request.user)
	return _calendar_view(request, estilista)


@role_required('cliente')
def calendario_cliente_view(request):
	return _calendar_view(request, None)


@role_required('estilista')
@require_POST
def completar_cita_view(request, cita_id):
	estilista, _ = Estilista.objects.get_or_create(persona=request.user)
	cita = get_object_or_404(
		Cita,
		pk=cita_id,
		estilista=estilista,
		estado='CONFIRMADA',
	)
	cita.estado = 'FINALIZADA'
	cita.fecha_finalizacion = timezone.now()
	cita.save(update_fields=['estado', 'fecha_finalizacion'])
	messages.success(request, 'La cita fue marcada como Hecho.')
	return redirect(f'{reverse("App_agenda:e_calendario")}?fecha={cita.fecha.isoformat()}')


@role_required('estilista')
def clientes_view(request):
	estilista, _ = Estilista.objects.get_or_create(persona=request.user)
	clientes = Cliente.objects.filter(citas__estilista=estilista).annotate(
		total_citas=Count('citas', filter=Q(citas__estilista=estilista), distinct=True),
		citas_pendientes=Count(
			'citas',
			filter=Q(citas__estilista=estilista, citas__estado='PENDIENTE'),
			distinct=True,
		),
		citas_confirmadas=Count(
			'citas',
			filter=Q(citas__estilista=estilista, citas__estado='CONFIRMADA'),
			distinct=True,
		),
	).select_related('persona').distinct().order_by(
		'persona__last_name', 'persona__first_name'
	)
	return render(request, 'App_agenda/E_clientes.html', {'clientes': clientes})


@role_required('estilista')
def mensajes_estilista_view(request):
	estilista, _ = Estilista.objects.get_or_create(persona=request.user)
	contactos = Cliente.objects.filter(citas__estilista=estilista).distinct(
	).select_related('persona').order_by('persona__last_name', 'persona__first_name')
	contacto = None
	contacto_id = request.POST.get('destinatario_id') or request.GET.get('con')
	if contacto_id:
		contacto = contactos.filter(pk=contacto_id).first()
		if contacto is None:
			messages.error(request, 'La clienta seleccionada no está en tu directorio.')

	if request.method == 'POST' and contacto:
		contenido = request.POST.get('contenido', '').strip()
		if not contenido or len(contenido) > 2000:
			messages.error(request, 'El mensaje debe tener entre 1 y 2000 caracteres.')
		else:
			Mensaje.objects.create(
				remitente=request.user,
				destinatario=contacto.persona,
				contenido=contenido,
			)
			return redirect(f'{reverse("App_agenda:e_mensajes")}?con={contacto.pk}')

	mensajes = Mensaje.objects.none()
	if contacto:
		mensajes = Mensaje.objects.filter(
			Q(remitente=request.user, destinatario=contacto.persona)
			| Q(remitente=contacto.persona, destinatario=request.user)
		).select_related('remitente', 'destinatario')
		mensajes.filter(destinatario=request.user, leido=False).update(leido=True)
	return render(
		request,
		'App_agenda/E_mensajes.html',
		{'contactos': contactos, 'contacto': contacto, 'mensajes': mensajes},
	)


@role_required('cliente')
def c_inicio_view(request):
	notificaciones_mensajes = Mensaje.objects.filter(
		destinatario=request.user,
		leido=False,
	).filter(
		Q(remitente__rol='estilista')
		| Q(remitente__is_staff=True)
		| Q(remitente__is_superuser=True)
	).count()
	return render(
		request,
		'App_agenda/C_inicio.html',
		{'notificaciones_mensajes': notificaciones_mensajes},
	)