from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.contrib.auth.views import PasswordResetView
from django.core.mail import send_mail
from django.db import connection, IntegrityError, transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.crypto import get_random_string
from django.utils.timezone import now, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib import messages
from random import randint, choices
import logging
import random
import re
import string
from django.utils import timezone

from .models import User, UserOTP, Profile, masterStudent, masterEmployee, EmployeeBank, EmployeeAcademic, EmployeeContact, Institute, Program, Branch
from .forms import StudentInfoForm, StudentParent, StudentBank, StudentAcademic, StudentContact, AdminUserCreationForm, EmployeeInfoForm, UserChangeForm, AdminUserRegistrationForm, EmployeeRegistrationForm, StudentRegistrationForm

# Configure logger
logger = logging.getLogger(__name__)

@login_required
def change_password_view(request):
    """
    Allow the user to change their password after logging in with a system-generated password.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            new_password = form.cleaned_data.get('new_password1')
            if validate_password_strength(new_password):
                form.save()
                messages.success(request, "Your password has been updated successfully.")
            else:
                messages.error(request, "Password does not meet the required strength criteria.")
        else:
            messages.error(request, "There was an error with your form. Please try again.")
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'myapp/change_password.html', {'form': form})

def generate_captcha():
    """
    Generate a simple CAPTCHA string.
    """
    return ''.join(choices(string.ascii_uppercase + string.digits, k=6))

def generate_otp():
    """
    Generate a 6-digit OTP.
    """
    return str(randint(100000, 999999))

def generate_student_id(course_code, admission_year, year_type):
    """
    Generate a student ID in the format: COURSE_YEAR_TYPE_NUMBER
    Example: BT2023F001
    """
    last_student = masterStudent.objects.filter(
        student_id__startswith=f"{course_code}{admission_year}{year_type}"
    ).order_by('student_id').last()
    
    if last_student:
        last_id_number = int(last_student.student_id[-3:])
        new_id_number = last_id_number + 1
    else:
        new_id_number = 1

    return f"{course_code}{admission_year}{year_type}{new_id_number:03d}"

def generate_employee_id(employee_type, hire_year):
    """
    Generate an employee ID in the format: EM_YEAR_TYPE_NUMBER
    Example: EM2023T001
    """
    type_code = {
        'teacher': 'T',
        'hod': 'H',
        'scholarship_officer': 'S',
        'fee_collector': 'F',
        'admin': 'A'
    }.get(employee_type, 'O')  # Default to 'O' for other types

    last_employee = masterEmployee.objects.filter(
        employee_id__startswith=f"EM{hire_year}{type_code}"
    ).order_by('employee_id').last()
    
    if last_employee:
        last_id_number = int(last_employee.employee_id[-3:])
        new_id_number = last_id_number + 1
    else:
        new_id_number = 1

    return f"EM{hire_year}{type_code}{new_id_number:03d}"

@csrf_exempt
def login_view(request):
    """
    Handle user login with CAPTCHA, OTP authentication, and first-time login password change.
    """
    if request.method == 'GET':
        request.session.flush()  # Clear the session data
        
    if request.method == 'POST':
        username = request.POST.get('username')
        user_captcha = request.POST.get('captcha-input')
        session_captcha = request.session.get('captcha_value')

        # Validate CAPTCHA
        if user_captcha != session_captcha:
            messages.error(request, "Invalid CAPTCHA. Please try again.")
            captcha_value = generate_captcha()
            request.session['captcha_value'] = captcha_value
            return render(request, 'myapp/login.html', {'captcha': captcha_value})

        # Check if user exists (by student_id or employee_id)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "No account found with the provided ID.")
            captcha_value = generate_captcha()
            request.session['captcha_value'] = captcha_value
            return render(request, 'myapp/login.html', {'captcha': captcha_value})

        # Check password
        password = request.POST.get('password')
        myapp_user = authenticate(request, username=username, password=password)
        if user is not None:
            username = user.username
        if myapp_user is not None:
            if myapp_user.last_login is None:  # First time login check
                login(request, myapp_user)  # Log the user in
                return redirect('change_password')  # Redirect to password change page
            else:
                login(request, myapp_user)  # Log the user in

            # Ensure the Profile exists
            if not hasattr(myapp_user, 'profile'):
                Profile.objects.create(user=myapp_user)

            # Check if the user has filled the student info form
            if not myapp_user.is_staff and not masterStudent.objects.filter(user=myapp_user).exists():
                return redirect('student_info_form')

            # Check if the user has filled the employee info form
            if myapp_user.is_staff and not masterEmployee.objects.filter(user=myapp_user).exists():
                return redirect('employee_info_form')

            # Generate and save OTP for the user's registered email
            otp = generate_otp()
            UserOTP.objects.update_or_create(email=user.email, defaults={'otp': otp, 'created_at': now()})

            # Send OTP to the user's registered email
            send_mail(
                subject="Your Login OTP",
                message=f"Your OTP for login is {otp}. It is valid for 5 minutes.",
                from_email="your_email@example.com",
                recipient_list=[user.email],
            )

            return redirect('verify_otp', email=user.email)
        else:
            messages.error(request, "Invalid credentials")
            captcha_value = generate_captcha()
            request.session['captcha_value'] = captcha_value
            return render(request, 'myapp/login.html', {'captcha': captcha_value})

    captcha_value = generate_captcha()
    request.session['captcha_value'] = captcha_value
    return render(request, 'myapp/login.html', {'captcha': captcha_value})

def verify_otp_view(request, email):
    if request.method == 'POST':
        otp = request.POST.get('otp')

        try:
            user_otp = UserOTP.objects.get(email=email)
            if user_otp.otp == otp and now() - user_otp.created_at < timedelta(minutes=5):
                user = User.objects.get(email=email)
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, "Invalid or expired OTP.")
        except UserOTP.DoesNotExist:
            messages.error(request, "No OTP found. Please try logging in again.")

    return render(request, 'myapp/verify_otp.html', {'email': email})

@login_required
def home_view(request):
    user = request.user
    user_type = user.user_type
    students = []
    employees = []
    sidebar_icons = []

    if user_type == 'admin':
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.username, u.email, ms.name, ms.date_of_birth, 
                       ms.gender, ms.admission_date
                FROM myapp_user u
                JOIN myapp_masterstudent ms ON u.id = ms.user_id
                WHERE NOT u.is_staff
            """)
            students = cursor.fetchall()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.username, u.email, me.name, me.date_of_birth, 
                       me.gender, me.hire_date
                FROM myapp_user u
                JOIN myapp_masteremployee me ON u.id = me.user_id
                WHERE u.is_staff
            """)
            employees = cursor.fetchall()
        # Add sidebar icons based on admin permissions
        sidebar_icons = [
            {'icon': 'fas fa-tachometer-alt', 'label': 'Dashboard', 'url': 'home'},
            {'icon': 'fas fa-user-plus', 'label': 'Admin Register Student', 'url': 'admin_register_student'},
            {'icon': 'fas fa-user-plus', 'label': 'Admin Register Employee', 'url': 'admin_register_employee'},
            # ...other admin icons...
        ]
    elif user_type == 'student':
        try:
            student = masterStudent.objects.get(user=user)
            # Add sidebar icons based on student permissions
            sidebar_icons = [
                {'icon': 'fas fa-tachometer-alt', 'label': 'Dashboard', 'url': 'home'},
                # ...other student icons...
            ]
        except masterStudent.DoesNotExist:
            messages.error(request, "Student record not found.")
            return redirect('home')
    elif user_type == 'teacher':
        try:
            employee = masterEmployee.objects.get(user=user)
            # Add sidebar icons based on teacher permissions
            sidebar_icons = [
                {'icon': 'fas fa-tachometer-alt', 'label': 'Dashboard', 'url': 'home'},
                # ...other teacher icons...
            ]
        except masterEmployee.DoesNotExist:
            messages.error(request, "Employee record not found.")
            return redirect('home')

    return render(request, 'myapp/home.html', {
        'students': students,
        'employees': employees,
        'sidebar_icons': sidebar_icons,
    })

class CustomPasswordResetView(PasswordResetView):
    """
    Customized password reset view with specific templates and success URL.
    """
    template_name = 'myapp/password_reset_form.html'
    email_template_name = 'myapp/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')

def logout_view(request):
    """
    Log out the user and redirect to the home page.
    """
    logout(request)
    return redirect('home')

def validate_password_strength(password):
    """
    Check if the password meets the following criteria:
    - At least 8 characters long
    - Contains both uppercase and lowercase letters
    - Includes at least one number
    - Includes at least one special character
    """
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

def custom_admin_login_view(request):
    """
    Handle the login for admin users.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_staff:
                return redirect('admin_register')
            else:
                return redirect('custom_admin_login')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'myapp/custom_admin_login.html')

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_register(request):
    form_type = request.GET.get('form', 'student')
    student_form = StudentRegistrationForm()
    employee_form = EmployeeRegistrationForm()
    universities = University.objects.all()

    if request.method == "POST":
        if 'student_form' in request.POST:
            student_form = StudentRegistrationForm(request.POST)
            if student_form.is_valid():
                email = student_form.cleaned_data['email']
                aadhar_card_number = student_form.cleaned_data['aadhar_card_number']
                university = student_form.cleaned_data['university']
                institute = student_form.cleaned_data['institute']
                program = student_form.cleaned_data['program']
                branch = student_form.cleaned_data['branch']
                admission_year = student_form.cleaned_data['admission_year']
                semester = student_form.cleaned_data['semester']
                year_type = 'F' if admission_year == 1 else 'S'
                course_code = 'BT'  # Assuming course code is BT for B-Tech
                student_id = generate_student_id(course_code, admission_year, year_type)
                password = get_random_string(length=8)

                try:
                    with transaction.atomic():
                        user = get_user_model().objects.create_user(
                            username=student_id,
                            email=email,
                            password=password,
                            user_type='student'
                        )
                        user.save()
                        logger.debug(f"User created: {user}")

                        # Save additional student details
                        profile, created = Profile.objects.get_or_create(
                            user=user,
                            defaults={
                                'aadhar_card_number': aadhar_card_number
                            }
                        )
                        if not created:
                            profile.aadhar_card_number = aadhar_card_number
                            profile.save()
                        logger.debug(f"Profile created or updated: {profile}")

                        # Create masterStudent instance with required fields
                        master_student = masterStudent.objects.create(
                            user=user,
                            student_id=student_id,
                            university=university,
                            institute=institute,
                            program=program,
                            branch=branch,
                            admission_year=admission_year,
                            semester=semester,
                            name=None,
                            date_of_birth=None,
                            gender=None,
                            admission_date=None,
                            abc_id=None,
                            aadhar_number=None,
                            mobile_number=None,
                            email=None
                        )
                        logger.debug(f"Master student created: {master_student}")

                        send_registration_email(user, password)
                        messages.success(request, f"Student {user.email} created successfully!")
                        return redirect('home')
                except IntegrityError as e:
                    logger.error(f"IntegrityError: {e}")
                    messages.error(request, "There was an error creating the student. Please try again.")
            else:
                logger.error(f"Form errors: {student_form.errors}")
                messages.error(request, "Please correct the errors in the form.")
        elif 'employee_form' in request.POST:
            employee_form = EmployeeRegistrationForm(request.POST)
            if employee_form.is_valid():
                email = employee_form.cleaned_data['email']
                hire_date = employee_form.cleaned_data['hire_date']
                position = employee_form.cleaned_data['position']
                mobile_number = employee_form.cleaned_data['mobile_number']
                aadhar_card_number = employee_form.cleaned_data['aadhar_card_number']
                department_code = 'CS'  # Assuming department code is CS for Computer Science
                hire_year = hire_date.year
                employee_id = generate_employee_id(department_code, hire_year)
                employee_type = employee_form.cleaned_data['employee_type']
                university = employee_form.cleaned_data['university']
                institute = employee_form.cleaned_data['institute']
                program = employee_form.cleaned_data['program'] if employee_type in ['teacher', 'hod'] else None
                branch = employee_form.cleaned_data['branch'] if employee_type == 'teacher' else None
                password = get_random_string(length=8)

                try:
                    with transaction.atomic():
                        user = get_user_model().objects.create_user(
                            username=employee_id,
                            email=email,
                            password=password,
                            user_type='teacher' if employee_type == 'teacher' else 'staff'
                        )
                        user.is_staff = True
                        user.save()

                        # Save additional employee details
                        profile, created = Profile.objects.get_or_create(
                            user=user,
                            defaults={
                                'mobile_number': mobile_number,
                                'aadhar_card_number': aadhar_card_number
                            }
                        )
                        if not created:
                            profile.mobile_number = mobile_number
                            profile.aadhar_card_number = aadhar_card_number
                            profile.save()
                        logger.debug(f"Profile created or updated: {profile}")

                        masterEmployee.objects.create(
                            user=user,
                            hire_date=hire_date,
                            position=position,
                            employee_id=employee_id,
                            employee_type=employee_type,
                            program=program,
                            branch=branch,
                            university=university,
                            institute=institute
                        )

                        send_registration_email(user, password)
                        messages.success(request, f"Employee {user.email} created successfully!")
                        return redirect('home')
                except IntegrityError as e:
                    logger.error(f"IntegrityError: {e}")
                    messages.error(request, "There was an error creating the employee. Please try again.")
            else:
                logger.error(f"Form errors: {employee_form.errors}")
                messages.error(request, "Please correct the errors in the form.")

    return render(request, 'myapp/admin_register.html', {
        'student_form': student_form,
        'employee_form': employee_form,
        'form_type': form_type,
        'universities': universities
    })

def send_registration_email(user, password):
    """
    Send an email to the user with their login credentials (username and password).
    """
    subject = "Your Registration Details"
    message = f"Hello {user.username},\n\nYour account has been created successfully.\nYour temporary password is: {password}\nPlease log in and change your password immediately."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

def reset_password_view(request):
    """
    View for the user to reset their password upon first login.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)

            user_profile = Profile.objects.get(user=request.user)
            user_profile.has_reset_password = True
            user_profile.save()

            messages.success(request, "Your password has been successfully reset!")
            return redirect('home')
        else:
            messages.error(request, "There was an error resetting your password. Please try again.")
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'myapp/firstPass.html', {'form': form})

@csrf_exempt
def student_info_form_view(request):
    """
    Display and handle the student information form.
    """
    try:
        student = masterStudent.objects.get(user=request.user)
    except masterStudent.DoesNotExist:
        messages.error(request, "Student record not found.")
        return redirect('home')

    if request.method == 'POST':
        form = StudentInfoForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save(commit=False)
            student.user = request.user
            student.save()

            StudentContact.objects.update_or_create(
                student=student,
                defaults={
                    'phone_number': form.cleaned_data['contact_phone_number'],
                    'email': form.cleaned_data['contact_email'],
                    'address': form.cleaned_data['contact_address'],
                }
            )
            StudentAcademic.objects.update_or_create(
                student=student,
                defaults={
                    'class_10_score': form.cleaned_data['class_10_score'],
                    'class_12_score': form.cleaned_data['class_12_score'],
                    'graduation_score': form.cleaned_data['graduation_score'],
                }
            )
            StudentBank.objects.update_or_create(
                student=student,
                defaults={
                    'bank_account': form.cleaned_data['bank_account'],
                    'ifsc_code': form.cleaned_data['ifsc_code'],
                    'bank_name': form.cleaned_data['bank_name'],
                }
            )
            StudentParent.objects.update_or_create(
                student=student,
                defaults={
                    'parent_name': form.cleaned_data['parent_name'],
                    'relationship': form.cleaned_data['parent_relationship'],
                    'contact_number': form.cleaned_data['parent_contact_number'],
                }
            )

            messages.success(request, "Your information has been updated successfully!")
            return redirect('home')
    else:
        form = StudentInfoForm(instance=student)

    return render(request, 'myapp/student_info_form.html', {'form': form, 'student': student})

@login_required
def employee_info_form_view(request):
    """
    Display and handle the employee information form.
    """
    is_admin = request.user.is_staff

    if request.method == 'POST':
        form = EmployeeInfoForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the masterEmployee data first
            employee = form.save(commit=False)
            employee.user = request.user
            employee.user_id = request.user.id  # Correctly set the user_id to the numeric ID
            employee.save()

            # Save the contact, academic, and bank information
            EmployeeContact.objects.create(
                employee=employee,
                phone_number=form.cleaned_data['contact_number'],
                email=form.cleaned_data['email_address'],
                address=form.cleaned_data['address'],
            )

            EmployeeAcademic.objects.create(
                employee=employee,
                highest_degree=form.cleaned_data['highest_degree'],
                institution=form.cleaned_data['institution'],
                year_of_passing=form.cleaned_data['year_of_passing'],
            )

            EmployeeBank.objects.create(
                employee=employee,
                bank_account=form.cleaned_data['bank_account'],
                ifsc_code=form.cleaned_data['ifsc_code'],
                bank_name=form.cleaned_data['bank_name'],
            )

            # Save role-specific fields
            if employee.employee_type == 'admin':
                employee.assigned_responsibilities = form.cleaned_data['assigned_responsibilities']
                employee.work_schedule_shift_details = form.cleaned_data['work_schedule_shift_details']
            elif employee.employee_type == 'teacher':
                employee.subjects_taught = form.cleaned_data['subjects_taught']
                employee.classes_grades_assigned = form.cleaned_data['classes_grades_assigned']
                employee.qualifications = form.cleaned_data['qualifications']
                employee.teaching_experience = form.cleaned_data['teaching_experience']
                employee.special_skills_certifications = form.cleaned_data['special_skills_certifications']
            elif employee.employee_type == 'hod':
                employee.years_of_experience_in_institution = form.cleaned_data['years_of_experience_in_institution']
                employee.staff_supervised = form.cleaned_data['staff_supervised']
                employee.key_responsibilities = form.cleaned_data['key_responsibilities']
            elif employee.employee_type == 'scholarship_officer':
                employee.scholarship_programs_managed = form.cleaned_data['scholarship_programs_managed']
                employee.approval_authority = form.cleaned_data['approval_authority']
                employee.coordinating_departments = form.cleaned_data['coordinating_departments']
            elif employee.employee_type == 'fee_collector':
                employee.assigned_counters = form.cleaned_data['assigned_counters']
                employee.handled_payment_modes = form.cleaned_data['handled_payment_modes']
                employee.software_tools_used = form.cleaned_data['software_tools_used']
            else:
                employee.job_specific_responsibilities = form.cleaned_data['job_specific_responsibilities']
                employee.safety_training = form.cleaned_data['safety_training']

            employee.save()

            # Show success message and redirect
            messages.success(request, "Your information has been saved successfully!")
            return redirect('home')
        else:
            # Log form errors
            logger.error(f"Form errors: {form.errors}")
            messages.error(request, "Please correct the errors in the form.")

    else:
        form = EmployeeInfoForm()

    return render(request, 'myapp/employee_info_form.html', {'form': form, 'is_admin': is_admin})

@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def view_student(request, student_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT u.id, u.username, u.email, ms.name, ms.date_of_birth, ms.gender, ms.admission_date,
                   sc.phone_number, sc.email AS contact_email, sc.address,
                   sa.class_10_score, sa.class_12_score, sa.graduation_score,
                   sb.bank_account, sb.ifsc_code, sb.bank_name,
                   sp.parent_name, sp.relationship, sp.contact_number
            FROM myapp_user u
            LEFT JOIN myapp_masterstudent ms ON u.id = ms.user_id
            LEFT JOIN myapp_studentcontact sc ON ms.id = sc.student_id
            LEFT JOIN myapp_studentacademic sa ON ms.id = sa.student_id
            LEFT JOIN myapp_studentbank sb ON ms.id = sb.student_id
            LEFT JOIN myapp_studentparent sp ON ms.id = sp.student_id
            WHERE u.id = %s
        """, [student_id])
        student_data = cursor.fetchone()

    return render(request, 'myapp/view_student.html', {'student_data': student_data})

@login_required
@user_passes_test(lambda u: u.user_type == 'admin')
def view_employee(request, employee_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT u.id, u.username, u.email, me.name, me.date_of_birth, me.gender, me.hire_date,
                   ec.phone_number, ec.email, ec.address,
                   ea.highest_degree, ea.institution, ea.year_of_passing,
                   eb.bank_account, eb.ifsc_code, eb.bank_name
            FROM myapp_user u
            LEFT JOIN myapp_masteremployee me ON u.username = me.user_id
            LEFT JOIN myapp_employeecontact ec ON me.id = ec.employee_id
            LEFT JOIN myapp_employeeacademic ea ON me.id = ea.employee_id
            LEFT JOIN myapp_employeebank eb ON me.id = eb.employee_id
            WHERE me.id = %s
        """, [employee_id])
        employee_data = cursor.fetchone()

    return render(request, 'myapp/view_employee.html', {'employee_data': employee_data})

@login_required
def profile_view(request):
    user = request.user
    student = None
    contact = None
    academic = None
    bank = None
    parent = None

    if user.user_type == 'student':
        try:
            student = masterStudent.objects.get(user=user)
            contact = StudentContact.objects.get(student=student)
            academic = StudentAcademic.objects.get(student=student)
            bank = StudentBank.objects.get(student=student)
            parent = StudentParent.objects.get(student=student)
        except masterStudent.DoesNotExist:
            messages.error(request, "Student record not found.")
            return redirect('home')
        except StudentContact.DoesNotExist:
            contact = None
        except StudentAcademic.DoesNotExist:
            academic = None
        except StudentBank.DoesNotExist:
            bank = None
        except StudentParent.DoesNotExist:
            parent = None

        if request.method == 'POST':
            field_name = request.POST.get('field_name')
            field_value = request.POST.get('field_value')
            if field_name and field_value:
                if field_name in ['contact_phone_number', 'contact_email', 'contact_address']:
                    setattr(contact, field_name.split('_')[1], field_value)
                    contact.save()
                elif field_name in ['class_10_score', 'class_12_score', 'graduation_score']:
                    setattr(academic, field_name, field_value)
                    academic.save()
                elif field_name in ['bank_account', 'ifsc_code', 'bank_name']:
                    setattr(bank, field_name, field_value)
                    bank.save()
                elif field_name in ['parent_name', 'parent_relationship', 'parent_contact_number']:
                    setattr(parent, field_name.split('_')[1], field_value)
                    parent.save()
                else:
                    setattr(student, field_name, field_value)
                    student.save()
                messages.success(request, f"{field_name.replace('_', ' ').title()} updated successfully!")
                return redirect('profile')

        form = StudentInfoForm(instance=student)
        return render(request, 'myapp/profile.html', {
            'form': form,
            'student': student,
            'contact': contact,
            'academic': academic,
            'bank': bank,
            'parent': parent
        })

    return redirect('home')

from django.db.models import F
from .models import University

def create_university(request):
    if request.method == 'POST':
        university = University(
            name=request.POST['name'],
            # ...other fields...
        )
        university.save()
        return HttpResponse("University created successfully")
    return render(request, 'create_university.html')

def update_university(request, university_id):
    if request.method == 'POST':
        university = University.objects.get(id=university_id)
        university.name = request.POST['name']
        # ...other fields...
        university.save()
        return HttpResponse("University updated successfully")
    return render(request, 'update_university.html', {'university': University.objects.get(id=university_id)})

def bulk_update_universities(request):
    if request.method == 'POST':
        user = request.user
        University.objects.filter(status='Active').update(
            status='Inactive',
            edit_person=user.username,
            edit_date=timezone.now().date()
        )
        return HttpResponse("Universities updated successfully")
    return render(request, 'bulk_update_universities.html')

@user_passes_test(lambda u: u.is_staff)
def admin_register_student(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            mobile_number = form.cleaned_data['mobile_number']
            aadhar_number = form.cleaned_data['aadhar_number']
            university = form.cleaned_data['university']
            institute = form.cleaned_data['institute']
            program = form.cleaned_data['program']
            branch = form.cleaned_data['branch']
            admission_year = form.cleaned_data['admission_year']
            semester = form.cleaned_data['semester']
            admission_date = form.cleaned_data['admission_date']
            year_type = 'F' if admission_year == 1 else 'S'
            course_code = 'BT'  # Assuming course code is BT for B-Tech
            admission_year = admission_date.year  # Use the year from the admission date
            student_id = generate_student_id(course_code, admission_year, year_type)
            password = get_random_string(length=8)

            try:
                with transaction.atomic():
                    user = get_user_model().objects.create_user(
                        username=student_id,
                        email=email,
                        password=password,
                        user_type='student'
                    )
                    user.save()
                    logger.debug(f"User created: {user}")

                    # Save additional student details
                    profile, created = Profile.objects.get_or_create(
                        user=user,
                        defaults={
                            'mobile_number': mobile_number,
                            'aadhar_card_number': aadhar_number
                        }
                    )
                    if not created:
                        profile.mobile_number = mobile_number
                        profile.aadhar_card_number = aadhar_number
                        profile.save()
                    logger.debug(f"Profile created or updated: {profile}")

                    # Create masterStudent instance with required fields
                    master_student = masterStudent.objects.create(
                        user=user,
                        student_id=student_id,
                        name=name,
                        university=university,
                        institute=institute,
                        program=program,
                        branch=branch,
                        admission_year=admission_year,
                        semester=semester,
                        admission_date=admission_date,
                        abc_id=form.cleaned_data['abc_id']
                    )
                    logger.debug(f"Master student created: {master_student}")

                    send_registration_email(user, password)
                    messages.success(request, f"Student {user.email} created successfully!")
                    return redirect('admin_register_student')
            except IntegrityError as e:
                logger.error(f"IntegrityError: {e}")
                messages.error(request, "There was an error creating the student. Please try again.")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                messages.error(request, "An unexpected error occurred. Please try again.")
        else:
            logger.error(f"Form errors: {form.errors}")
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = StudentRegistrationForm()

    return render(request, 'myapp/admin_register_student.html', {'form': form})

@user_passes_test(lambda u: u.is_staff)
def load_institutes(request):
    university_id = request.GET.get('university_id')
    logger.debug(f"Fetching institutes for university_id: {university_id}")  # Debug log
    if university_id:
        institutes = Institute.objects.filter(university_id=university_id).order_by('name')
        logger.debug(f"Found institutes: {list(institutes.values('id', 'name'))}")  # Debug log
        return JsonResponse(list(institutes.values('id', 'name')), safe=False)
    else:
        logger.error("No university_id provided")
        return JsonResponse({'error': 'No university_id provided'}, status=400)

@user_passes_test(lambda u: u.is_staff)
def load_programs(request):
    institute_id = request.GET.get('institute_id')
    logger.debug(f"Fetching programs for institute_id: {institute_id}")  # Debug log
    if institute_id:
        programs = Program.objects.filter(institute_id=institute_id).order_by('name')
        logger.debug(f"Found programs: {list(programs.values('id', 'name'))}")  # Debug log
        return JsonResponse(list(programs.values('id', 'name')), safe=False)
    else:
        logger.error("No institute_id provided")
        return JsonResponse({'error': 'No institute_id provided'}, status=400)

@user_passes_test(lambda u: u.is_staff)
def load_branches(request):
    program_id = request.GET.get('program_id')
    logger.debug(f"Fetching branches for program_id: {program_id}")  # Debug log
    if program_id:
        branches = Branch.objects.filter(program_id=program_id).order_by('name')
        logger.debug(f"Found branches: {list(branches.values('id', 'name'))}")  # Debug log
        return JsonResponse(list(branches.values('id', 'name')), safe=False)
    else:
        logger.error("No program_id provided")
        return JsonResponse({'error': 'No program_id provided'}, status=400)

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction, IntegrityError
from .forms import EmployeeRegistrationForm
from .models import Profile, masterEmployee

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_register_employee(request):
    if request.method == "POST":
        form = EmployeeRegistrationForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            mobile_number = form.cleaned_data['mobile_number']
            aadhar_number = form.cleaned_data['aadhar_number']
            hire_date = form.cleaned_data['hire_date']
            employee_type = form.cleaned_data['employee_type']
            university = form.cleaned_data['university']
            institute = form.cleaned_data['institute']
            highest_qualification = form.cleaned_data['highest_qualification']  # Corrected field name
            hire_year = hire_date.year
            employee_id = generate_employee_id(employee_type, hire_year)
            password = get_random_string(length=8)
            # Removed date_of_birth handling

            try:
                with transaction.atomic():
                    user = get_user_model().objects.create_user(
                        username=employee_id,  # Set the username to the generated employee ID
                        email=email,
                        password=password,
                        user_type=employee_type
                    )
                    user.is_staff = True
                    user.save()

                    # Save additional employee details
                    profile, created = Profile.objects.get_or_create(
                        user=user,
                        defaults={
                            'mobile_number': mobile_number,
                            'aadhar_card_number': aadhar_number
                        }
                    )
                    if not created:
                        profile.mobile_number = mobile_number
                        profile.aadhar_card_number = aadhar_number
                        profile.save()
                    logger.debug(f"Profile created or updated: {profile}")

                    masterEmployee.objects.create(
                        user=user,
                        employee_id=employee_id,
                        name=name,
                        hire_date=hire_date,
                        employee_type=employee_type,
                        university=university,
                        institute=institute,
                        highest_qualification=highest_qualification,  # Corrected field name
                        # Removed date_of_birth field
                    )

                    send_registration_email(user, password)
                    messages.success(request, f"Employee {user.email} created successfully!")
                    return redirect('admin_register_employee')
            except IntegrityError as e:
                logger.error(f"IntegrityError: {e}")
                messages.error(request, "There was an error creating the employee. Please try again.")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                messages.error(request, "An unexpected error occurred. Please try again.")
        else:
            logger.error(f"Form errors: {form.errors}")
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = EmployeeRegistrationForm()

    return render(request, 'myapp/admin_register_employee.html', {'form': form})

@login_required
def load_profile(request):
    user = request.user
    student = None
    contact = None
    academic = None
    bank = None
    parent = None

    if user.user_type == 'student':
        try:
            student = masterStudent.objects.get(user=user)
            contact = StudentContact.objects.get(student=student)
            academic = StudentAcademic.objects.get(student=student)
            bank = StudentBank.objects.get(student=student)
            parent = StudentParent.objects.get(student=student)
        except masterStudent.DoesNotExist:
            messages.error(request, "Student record not found.")
            return redirect('home')
        except StudentContact.DoesNotExist:
            contact = None
        except StudentAcademic.DoesNotExist:
            academic = None
        except StudentBank.DoesNotExist:
            bank = None
        except StudentParent.DoesNotExist:
            parent = None

        form = StudentInfoForm(instance=student)
        return render(request, 'myapp/profile.html', {
            'form': form,
            'student': student,
            'contact': contact,
            'academic': academic,
            'bank': bank,
            'parent': parent
        })

    return redirect('home')

@login_required
def load_change_password(request):
    form = PasswordChangeForm(request.user)
    return render(request, 'myapp/change_password.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_staff)
def load_admin_register_student(request):
    form = StudentRegistrationForm()
    return render(request, 'myapp/admin_register_student.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_staff)
def load_admin_register_employee(request):
    form = EmployeeRegistrationForm()
    return render(request, 'myapp/admin_register_employee.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_staff)
def student_section_view(request):
    students = masterStudent.objects.all()
    return render(request, 'myapp/student_section.html', {'students': students})

@login_required
@user_passes_test(lambda u: u.is_staff)
def edit_student_permissions(request, student_id):
    student = masterStudent.objects.get(id=student_id)
    if request.method == 'POST':
        can_view_profile = request.POST.get('can_view_profile') == 'on'
        can_edit_profile = request.POST.get('can_edit_profile') == 'on'
        can_delete_profile = request.POST.get('can_delete_profile') == 'on'
        # Update or create permissions for the student
        StudentPermission.objects.update_or_create(
            student=student,
            defaults={
                'can_view_profile': can_view_profile,
                'can_edit_profile': can_edit_profile,
                'can_delete_profile': can_delete_profile,
            }
        )
        messages.success(request, f"Permissions updated for {student.name}")
        return redirect('student_section')
    else:
        permissions, created = StudentPermission.objects.get_or_create(student=student)
        return render(request, 'myapp/edit_student_permissions.html', {'student': student, 'permissions': permissions})

@login_required
def student_home_view(request):
    user = request.user
    if user.user_type == 'student':
        try:
            student = masterStudent.objects.get(user=user)
            permissions = student.permissions
            return render(request, 'myapp/student_home.html', {'student': student, 'permissions': permissions})
        except masterStudent.DoesNotExist:
            messages.error(request, "Student record not found.")
            return redirect('home')
    return redirect('home')

@login_required
@user_passes_test(lambda u: u.is_staff)
def student_management_view(request):
    students = masterStudent.objects.all()
    return render(request, 'myapp/student_management.html', {'students': students})