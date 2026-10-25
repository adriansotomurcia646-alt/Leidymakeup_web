from django import forms

from .models import Servicio


class ServicioForm(forms.ModelForm):
	class Meta:
		model = Servicio
		fields = ('nombre', 'categoria', 'descripcion', 'precio', 'duracion')

	def __init__(self, *args, **kwargs):
		data = kwargs.get('data', args[0] if args else None)
		if data is not None and 'duracion' not in data and 'duracion_minutos' in data:
			data = data.copy()
			data['duracion'] = data['duracion_minutos']
			if 'data' in kwargs:
				kwargs['data'] = data
			else:
				args = (data, *args[1:])
		super().__init__(*args, **kwargs)
