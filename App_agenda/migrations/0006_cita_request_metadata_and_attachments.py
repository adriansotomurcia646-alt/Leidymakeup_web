from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('App_agenda', '0005_alter_cita_estado'),
    ]

    operations = [
        migrations.AddField(
            model_name='cita',
            name='duracion_aprobada',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cita',
            name='fecha_aceptacion',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cita',
            name='fecha_finalizacion',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cita',
            name='fecha_solicitada',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cita',
            name='fecha_solicitud',
            field=models.DateTimeField(auto_now_add=True, default='2024-01-01T00:00:00Z'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='cita',
            name='hora_solicitada',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='CitaArchivo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('archivo', models.FileField(max_length=500, upload_to='citas/archivos/%Y/%m/%d/')),
                ('nombre_original', models.CharField(blank=True, max_length=255)),
                ('tipo', models.CharField(blank=True, max_length=30)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('cita', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='archivos', to='App_agenda.cita')),
            ],
            options={
                'ordering': ('creado_en',),
            },
        ),
    ]
