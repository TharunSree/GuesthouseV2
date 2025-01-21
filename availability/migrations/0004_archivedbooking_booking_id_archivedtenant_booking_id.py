# Generated by Django 5.0.6 on 2024-06-18 21:22

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('availability', '0003_archivedtenant'),
    ]

    operations = [
        migrations.AddField(
            model_name='archivedbooking',
            name='booking_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AddField(
            model_name='archivedtenant',
            name='booking_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
