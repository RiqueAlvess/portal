# Generated by Django 5.2 on 2025-04-16 13:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('convocacao', '0003_alter_convocacao_codigoexame_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='convocacao',
            options={'verbose_name': 'Convocação', 'verbose_name_plural': 'Convocações'},
        ),
        migrations.AlterField(
            model_name='convocacao',
            name='MATRICULA',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
