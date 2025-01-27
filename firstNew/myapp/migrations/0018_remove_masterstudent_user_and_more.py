# Generated by Django 4.2.17 on 2025-01-16 15:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0017_masterstudent_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='masterstudent',
            name='user',
        ),
        migrations.AddField(
            model_name='masterstudent',
            name='user_username',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, to_field='username'),
        ),
    ]
