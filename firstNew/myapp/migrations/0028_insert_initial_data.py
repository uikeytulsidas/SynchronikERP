from django.db import migrations

def insert_initial_data(apps, schema_editor):
    University = apps.get_model('myapp', 'University')
    Institute = apps.get_model('myapp', 'Institute')
    Program = apps.get_model('myapp', 'Program')
    Branch = apps.get_model('myapp', 'Branch')

    # Insert data into University table
    university1 = University.objects.create(id=1, name='Example University')
    university2 = University.objects.create(id=2, name='Tech University')

    # Insert data into Institute table
    institute1 = Institute.objects.create(id=1, name='Engineering Institute', university=university1)
    institute2 = Institute.objects.create(id=2, name='Management Institute', university=university1)
    institute3 = Institute.objects.create(id=3, name='Tech School of AI', university=university2)

    # Insert data into Program table
    program1 = Program.objects.create(id=1, name='B.Tech in Computer Science', institute=institute1)
    program2 = Program.objects.create(id=2, name='MBA in Marketing', institute=institute2)
    program3 = Program.objects.create(id=3, name='M.Tech in AI', institute=institute3)

    # Insert data into Branch table
    branch1 = Branch.objects.create(id=1, name='Artificial Intelligence', program=program1)
    branch2 = Branch.objects.create(id=2, name='Data Science', program=program1)
    branch3 = Branch.objects.create(id=3, name='Digital Marketing', program=program2)
    branch4 = Branch.objects.create(id=4, name='Machine Learning', program=program3)

    # Ensure that any other data referencing Branch is inserted after the Branch data

class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0027_set_default_branch'),  # Adjust the dependency to your last migration file
    ]

    operations = [
        migrations.RunPython(insert_initial_data),
    ]
