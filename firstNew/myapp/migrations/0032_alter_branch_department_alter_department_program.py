# Generated by Django 4.2.17 on 2025-01-25 02:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0031_alter_masteremployee_department_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='branch',
            name='department',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='branches', to='myapp.department'),
        ),
        migrations.AlterField(
            model_name='department',
            name='program',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='departments', to='myapp.program'),
        ),
    ]
