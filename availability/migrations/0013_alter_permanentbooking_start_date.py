# Generated by Django 5.0.6 on 2025-01-21 11:04

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('availability', '0012_archivedbooking_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='permanentbooking',
            name='start_date',
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]