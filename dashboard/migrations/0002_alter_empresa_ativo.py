# Generated by Django 5.2 on 2025-04-06 14:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='empresa',
            name='ATIVO',
            field=models.BooleanField(default=True),
        ),
    ]
