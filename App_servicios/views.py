from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from App_usuarios.decorators import role_required

from .forms import ServicioForm
from .models import Servicio


def lista_servicios_view(request):
    # Obtenemos todos los servicios registrados por la estilista
    servicios = Servicio.objects.all().order_by('id')
    
    # Si es la estilista, va al CRUD de estilista. Si es cliente, va al catálogo general.
    if (
        request.user.is_staff
        or request.user.is_superuser
        or getattr(request.user, 'rol', None) == 'estilista'
    ):
        return render(request, 'App_servicios/E_servicios.html', {'servicios': servicios})
    else:
        return render(
            request,
            'App_servicios/C_servicios.html',
            {'servicios': servicios.filter(activo=True)},
        )

@role_required('estilista')
def crear_servicio_view(request):
    if request.method != 'POST':
        return render(
            request,
            'E_servicio_form.html',
            {'accion': 'Crear', 'servicio': None},
        )

    form = ServicioForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, 'El servicio fue creado correctamente.')
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect('App_servicios:lista')


@role_required('estilista')
def editar_servicio_view(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    if request.method != 'POST':
        return render(
            request,
            'E_servicio_form.html',
            {'accion': 'Editar', 'servicio': servicio},
        )

    form = ServicioForm(request.POST, instance=servicio)
    if form.is_valid():
        form.save()
        messages.success(request, 'El servicio fue actualizado correctamente.')
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect('App_servicios:lista')


@role_required('estilista')
@require_POST
def eliminar_servicio_view(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    servicio.activo = False
    servicio.save(update_fields=['activo'])
    messages.success(request, 'El servicio fue retirado del catálogo.')
    return redirect('App_servicios:lista')