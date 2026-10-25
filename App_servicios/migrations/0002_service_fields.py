from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('App_servicios', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='servicio',
            old_name='duracion_minutos',
            new_name='duracion',
        ),
        migrations.AlterField(
            model_name='servicio',
            name='duracion',
            field=models.PositiveIntegerField(help_text='Duración en minutos'),
        ),
        migrations.AddField(
            model_name='servicio',
            name='categoria',
            field=models.CharField(blank=True, default='General', max_length=100),
        ),
        migrations.AddField(
            model_name='servicio',
            name='es_demo',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='servicio',
            name='nombre',
            field=models.CharField(max_length=150),
        ),
    ]