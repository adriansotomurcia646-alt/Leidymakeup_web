import json
from datetime import datetime
from decimal import Decimal

from django.db.models import Count, Sum
from django.shortcuts import render
from django.db.models.functions import TruncMonth

from App_agenda.models import Cita
from App_usuarios.decorators import role_required

from .models import RegistroCobro


@role_required('estilista')
def inventario_view(request):
	registros = RegistroCobro.objects.filter(
		cita__estilista__persona=request.user,
	).select_related(
		'cliente__persona', 'cita__servicio'
	).order_by('-fecha')
	return render(
		request,
		'App_facturacion/E_inventario.html',
		{
			'registros': registros,
			'total_clientes': registros.values('cliente_id').distinct().count(),
			'total_pendiente': registros.aggregate(
				total=Sum('saldo_pendiente')
			)['total'] or 0,
			'registros_json': json.dumps([
				{
					'cliente': str(registro.cliente),
					'servicio': registro.cita.servicio.nombre,
					'fecha': registro.fecha.isoformat(),
					'monto': float(registro.monto_total),
					'atendido': registro.saldo_pendiente == 0,
				}
				for registro in registros
			]),
		},
	)


@role_required('estilista')
def reportes_view(request):
	registros = RegistroCobro.objects.filter(
		cita__estilista__persona=request.user,
		cita__estado='CONFIRMADA',
		monto_pagado__gt=0,
	).select_related(
		'cliente__persona', 'cita__servicio'
	).order_by('-fecha')
	totales = registros.aggregate(
		ingresos=Sum('monto_pagado'),
		saldos_pendientes=Sum('saldo_pendiente'),
	)
	ingresos_mensuales = registros.annotate(
		mes=TruncMonth('fecha'),
	).values('mes').annotate(
		ingresos=Sum('monto_pagado'),
	).order_by('mes')

	fecha_inicio = request.GET.get('fecha_inicio', '').strip()
	fecha_fin = request.GET.get('fecha_fin', '').strip()
	error_fechas = ''
	total_periodo = None
	if fecha_inicio or fecha_fin:
		try:
			if not fecha_inicio or not fecha_fin:
				raise ValueError
			inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
			fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
			if inicio > fin:
				error_fechas = 'La fecha inicial no puede ser posterior a la fecha final.'
			else:
				total_periodo = registros.filter(
					fecha__gte=inicio,
					fecha__lte=fin,
				).aggregate(total=Sum('monto_pagado'))['total'] or Decimal('0.00')
		except ValueError:
			error_fechas = 'Ingresa un rango válido con fecha inicial y fecha final.'

	servicios_populares = Cita.objects.filter(
		estilista__persona=request.user,
		estado__in=('PENDIENTE', 'CONFIRMADA'),
	).values('servicio__nombre').annotate(
		total=Count('pk', distinct=True),
	).order_by('-total', 'servicio__nombre')[:5]
	servicio_mas_popular = servicios_populares[0] if servicios_populares else None
	total_citas = Cita.objects.filter(
		estilista__persona=request.user,
		estado__in=('PENDIENTE', 'CONFIRMADA'),
	).count()
	return render(
		request,
		'App_facturacion/E_reportes.html',
		{
			'registros': registros,
			'total_ingresos': totales['ingresos'] or Decimal('0.00'),
			'total_pendiente': totales['saldos_pendientes'] or 0,
			'total_citas': total_citas,
			'servicios_populares': servicios_populares,
			'servicio_mas_popular': servicio_mas_popular,
			'ingresos_mensuales': ingresos_mensuales,
			'fecha_inicio': fecha_inicio,
			'fecha_fin': fecha_fin,
			'error_fechas': error_fechas,
			'total_periodo': total_periodo,
		},
	)
