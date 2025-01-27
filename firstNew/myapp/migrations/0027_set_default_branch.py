from django.db import migrations, models

def set_default_branch(apps, schema_editor):
    MasterStudent = apps.get_model('myapp', 'MasterStudent')
    Branch = apps.get_model('myapp', 'Branch')
    default_branch = Branch.objects.first()
    for student in MasterStudent.objects.all():
        student.branch = default_branch
        student.save()

class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0026_institute_university_masteremployee_department_and_more'),
    ]

    operations = [
        migrations.RunPython(set_default_branch, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='masterstudent',
            name='branch',
            field=models.ForeignKey(on_delete=models.CASCADE, to='myapp.Branch', default=1),
        ),
    ]
