# Generated by Django 5.0.6 on 2024-06-18 21:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('availability', '0005_alter_archivedbooking_booking_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archivedbooking',
            name='tenant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='availability.archivedtenant'),
        ),
    ]
