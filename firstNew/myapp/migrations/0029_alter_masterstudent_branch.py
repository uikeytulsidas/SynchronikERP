# Generated by Django 4.2.17 on 2025-01-25 01:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0028_insert_initial_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='masterstudent',
            name='branch',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='students', to='myapp.branch'),
        ),
    ]
