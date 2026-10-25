from datetime import datetime, timedelta

from django.db import migrations, models


def populate_hora_fin(apps, schema_editor):
    Cita = apps.get_model('App_agenda', 'Cita')
    for cita in Cita.objects.select_related('servicio').iterator():
        inicio = datetime.combine(cita.fecha, cita.hora_inicio)
        cita.hora_fin = (
            inicio + timedelta(minutes=cita.servicio.duracion)
        ).time()
        cita.save(update_fields=['hora_fin'])


def normalize_estados(apps, schema_editor):
    Cita = apps.get_model('App_agenda', 'Cita')
    for estado in ('pendiente', 'confirmada', 'rechazada', 'cancelada'):
        Cita.objects.filter(estado=estado).update(estado=estado.upper())


class Migration(migrations.Migration):

    dependencies = [
        ('App_agenda', '0003_mensaje'),
        ('App_servicios', '0002_service_fields'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cita',
            old_name='hora',
            new_name='hora_inicio',
        ),
        migrations.AddField(
            model_name='cita',
            name='hora_fin',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cita',
            name='mensaje',
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(populate_hora_fin, migrations.RunPython.noop),
        migrations.RunPython(normalize_estados, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cita',
            name='hora_fin',
            field=models.TimeField(),
        ),
        migrations.AlterField(
            model_name='cita',
            name='estado',
            field=models.CharField(
                choices=[
                    ('PENDIENTE', 'Pendiente'),
                    ('CONFIRMADA', 'Confirmada'),
                    ('RECHAZADA', 'Rechazada'),
                    ('CANCELADA', 'Cancelada'),
                ],
                default='PENDIENTE',
                max_length=20,
            ),
        ),
    ]