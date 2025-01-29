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

        # Check if user exists (by username or email)
        try:
            user = User.objects.get(username=username) if '@' not in username else User.objects.get(email=username)
        except User.DoesNotExist:
            messages.error(request, "No account found with the provided username.")
            captcha_value = generate_captcha()
            request.session['captcha_value'] = captcha_value
            return render(request, 'myapp/login.html', {'captcha': captcha_value})

        # Check password
        password = request.POST.get('password')
        myapp_user = authenticate(request, username=username, password=password)

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
    user_id = request.user.id
    user_type = request.user.user_type
    user_data = None
    students = []
    employees = []

    if user_type == 'student':
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
            """, [user_id])
            user_data = cursor.fetchone()
    elif user_type == 'teacher':
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT me.id, me.name, me.date_of_birth, me.gender, me.hire_date,
                       ec.phone_number, ec.email, ec.address,
                       ea.highest_degree, ea.institution, ea.year_of_passing,
                       eb.bank_account, eb.ifsc_code, eb.bank_name,
                       ed.subject, d.name as department_name
                FROM myapp_masteremployee me
                LEFT JOIN myapp_employeecontact ec ON me.id = ec.employee_id
                LEFT JOIN myapp_employeeacademic ea ON me.id = ea.employee_id
                LEFT JOIN myapp_employeebank eb ON me.id = eb.employee_id
                LEFT JOIN myapp_employeedepartment ed ON me.id = ed.employee_id
                LEFT JOIN myapp_department d ON ed.department_id = d.id
                WHERE me.user_id = %s
            """, [request.user.username])
            user_data = cursor.fetchone()
    elif user_type == 'admin':
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.username, u.email, ms.name, ms.date_of_birth, 
                       ms.gender, ms.admission_date
                FROM myapp_user u
                JOIN myapp_masterstudent ms ON u.id = ms.user_id
                WHERE NOT u.is_staff AND u.id != %s
            """, [user_id])
            students = cursor.fetchall()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.username, u.email, me.name, me.date_of_birth, 
                       me.gender, me.hire_date
                FROM myapp_user u
                JOIN myapp_masteremployee me ON u.id = me.user_id
                WHERE u.is_staff AND u.id != %s
            """, [user_id])
            employees = cursor.fetchall()

    return render(request, 'myapp/home.html', {'user_data': user_data, 'students': students, 'employees': employees})

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
                return redirect('admin_register_user')
            else:
                return redirect('custom-admin:custom_admin_login')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'myapp/custom_admin_login.html')


@user_passes_test(lambda u: u.is_staff)
def admin_register_student(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            mobile_number = form.cleaned_data['mobile_number']
            aadhar_card_number = form.cleaned_data['aadhar_card_number']
            student_id = form.cleaned_data['student_id']
            university = form.cleaned_data['university']
            institute = form.cleaned_data['institute']
            program = form.cleaned_data['program']
            branch = form.cleaned_data['branch']
            admission_year = form.cleaned_data['admission_year']
            semester = form.cleaned_data['semester']
            username = generate_username(email)
            password = get_random_string(length=8)

            try:
                with transaction.atomic():
                    user = get_user_model().objects.create_user(
                        username=username,
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
                            'aadhar_card_number': aadhar_card_number
                        }
                    )
                    if not created:
                        profile.mobile_number = mobile_number
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
                        semester=semester
                    )
                    logger.debug(f"Master student created: {master_student}")

                    send_registration_email(user, password)
                    messages.success(request, f"Student {user.email} created successfully!")
                    return redirect('home')  # Ensure this redirect is executed
            except IntegrityError as e:
                logger.error(f"IntegrityError: {e}")
                messages.error(request, "There was an error creating the student. Please try again.")
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

@user_passes_test(lambda u: u.is_staff)
def admin_register_employee(request):
    if request.method == "POST":
        form = EmployeeRegistrationForm(request.POST)
        if form.is_valid():
            try:
                email = form.cleaned_data['email']
                hire_date = form.cleaned_data['hire_date']
                position = form.cleaned_data['position']
                mobile_number = form.cleaned_data['mobile_number']
                aadhar_card_number = form.cleaned_data['aadhar_card_number']
                employee_id = form.cleaned_data['employee_id']
                employee_type = form.cleaned_data['employee_type']
                university = form.cleaned_data['university']
                institute = form.cleaned_data['institute']
                program = form.cleaned_data['program'] if employee_type in ['teacher', 'hod'] else None
                branch = form.cleaned_data['branch'] if employee_type == 'teacher' else None
                username = generate_username(email)
                password = get_random_string(length=8)

                with transaction.atomic():
                    user = get_user_model().objects.create_user(
                        username=username,
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
            logger.error(f"Form errors: {form.errors}")
            messages.error(request, "Please correct the errors in the form.")
    if request.method == "POST":
        form = AdminUserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            mobile_number = form.cleaned_data['mobile_number']
            aadhar_card_number = form.cleaned_data['aadhar_card_number']
            user_type = form.cleaned_data['user_type']
            username = generate_username(email)
            password = get_random_string(length=8)

            user = get_user_model().objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type=user_type
            )
            user.save()

            # Save additional user details
            Profile.objects.create(
                user=user,
                mobile_number=mobile_number,
                aadhar_card_number=aadhar_card_number
            )

            send_registration_email(user, password)
            messages.success(request, f"User {user.email} created successfully!")
            return redirect('home')
    else:
        form = AdminUserRegistrationForm()

    return render(request, 'myapp/admin_register_user.html', {'form': form})

@user_passes_test(lambda u: u.is_staff)
def admin_register_user(request):
    if request.method == "POST":
        form = AdminUserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            mobile_number = form.cleaned_data['mobile_number']
            aadhar_card_number = form.cleaned_data['aadhar_card_number']
            user_type = form.cleaned_data['user_type']
            username = generate_username(email)
            password = get_random_string(length=8)

            try:
                with transaction.atomic():
                    user = get_user_model().objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        user_type=user_type
                    )
                    user.save()
                    logger.debug(f"User created: {user}")

                    # Save additional user details
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

                    send_registration_email(user, password)
                    messages.success(request, f"User {user.email} created successfully!")
                    return redirect('home')
            except IntegrityError as e:
                logger.error(f"IntegrityError: {e}")
                messages.error(request, "There was an error creating the user. Please try again.")
        else:
            logger.error(f"Form errors: {form.errors}")
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = AdminUserRegistrationForm()

    return render(request, 'myapp/admin_register_user.html', {'form': form})

def generate_username(email):
    """
    Generate a unique username based on the email address.
    """
    base_username = email.split('@')[0]
    random_string = get_random_string(length=4, allowed_chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")
    return f"{base_username}_{random_string}"

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
    if request.method == 'POST':
        form = StudentInfoForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.user = request.user
            student.save()

            StudentContact.objects.create(
                student=student,
                phone_number=form.cleaned_data['contact_phone_number'],
                email=form.cleaned_data['contact_email'],
                address=form.cleaned_data['contact_address'],
            )
            StudentAcademic.objects.create(
                student=student,
                class_10_score=form.cleaned_data['class_10_score'],
                class_12_score=form.cleaned_data['class_12_score'],
                graduation_score=form.cleaned_data['graduation_score'],
            )
            StudentBank.objects.create(
                student=student,
                bank_account=form.cleaned_data['bank_account'],
                ifsc_code=form.cleaned_data['ifsc_code'],
                bank_name=form.cleaned_data['bank_name'],
            )
            StudentParent.objects.create(
                student=student,
                parent_name=form.cleaned_data['parent_name'],
                relationship=form.cleaned_data['parent_relationship'],
                contact_number=form.cleaned_data['parent_contact_number'],
            )

            messages.success(request, "Your information has been saved successfully!")
            return redirect('home')
    else:
        form = StudentInfoForm()

    return render(request, 'myapp/student_info_form.html', {'form': form})

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

            # Save the contact, academic, bank, and department information
            EmployeeContact.objects.create(
                employee=employee,
                phone_number=form.cleaned_data['contact_number'],
                email=form.cleaned_data['email_address'],
                address=form.cleaned_data['address'],
            )

            EmployeeAcademic.objects.create(
                employee=employee,
                highest_degree=form.cleaned_data['qualifications'],
                institution=form.cleaned_data['institute'],  # Corrected field name
                year_of_passing=form.cleaned_data['year_of_passing'],
            )

            EmployeeBank.objects.create(
                employee=employee,
                bank_account=form.cleaned_data['account_number'],
                ifsc_code=form.cleaned_data['ifsc_code'],
                bank_name=form.cleaned_data['bank_name'],
            )

            # Create the department record
            EmployeeDepartment.objects.create(
                employee=employee,
                department=form.cleaned_data['department'],
                subject=form.cleaned_data['subjects_taught'],
            )

            # Save role-specific fields
            if employee.employee_type == 'admin':
                employee.areas_of_responsibility = form.cleaned_data['areas_of_responsibility']
                employee.access_privileges = form.cleaned_data['access_privileges']
                employee.work_hours_shift_details = form.cleaned_data['work_hours_shift_details']
            elif employee.employee_type == 'teacher':
                employee.subjects_taught = form.cleaned_data['subjects_taught']
                employee.class_grade_responsibility = form.cleaned_data['class_grade_responsibility']
                employee.qualifications = form.cleaned_data['qualifications']
                employee.past_teaching_experience = form.cleaned_data['past_teaching_experience']
                employee.timetable = form.cleaned_data['timetable']
                employee.special_skills = form.cleaned_data['special_skills']
            elif employee.employee_type == 'hod':
                employee.department_name = form.cleaned_data['department_name']
                employee.years_of_experience_in_department = form.cleaned_data['years_of_experience_in_department']
                employee.key_responsibilities = form.cleaned_data['key_responsibilities']
                employee.staff_managed = form.cleaned_data['staff_managed']
                employee.budget_handling = form.cleaned_data['budget_handling']
            elif employee.employee_type == 'scholarship_officer':
                employee.scholarship_programs_managed = form.cleaned_data['scholarship_programs_managed']
                employee.application_evaluation_criteria = form.cleaned_data['application_evaluation_criteria']
                employee.report_submission_frequency = form.cleaned_data['report_submission_frequency']
                employee.stakeholder_coordination = form.cleaned_data['stakeholder_coordination']
            elif employee.employee_type == 'fee_collector':
                employee.fee_collection_timings = form.cleaned_data['fee_collection_timings']
                employee.payment_modes_supported = form.cleaned_data['payment_modes_supported']
                employee.daily_weekly_collection_report_submission = form.cleaned_data['daily_weekly_collection_report_submission']
                employee.receipt_issuance_process = form.cleaned_data['receipt_issuance_process']
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

    departments = Department.objects.all()
    return render(request, 'myapp/employee_info_form.html', {'form': form, 'departments': departments, 'is_admin': is_admin})

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
    user_data = None

    if user.user_type == 'student':
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.username, u.email, ms.name, ms.date_of_birth, ms.gender, ms.admission_date,
                       sc.phone_number, sc.email AS contact_email, sc.address,
                       sa.class_10_score, sa.class_12_score, sa.graduation_score,
                       sb.bank_account, sb.ifsc_code, sb.bank_name,
                       sp.parent_name, sp.relationship, sp.contact_number
                FROM myapp_user u
                LEFT JOIN myapp_masterstudent ms ON u.username = ms.user_id
                LEFT JOIN myapp_studentcontact sc ON ms.id = sc.student_id
                LEFT JOIN myapp_studentacademic sa ON ms.id = sa.student_id
                LEFT JOIN myapp_studentbank sb ON ms.id = sb.student_id
                LEFT JOIN myapp_studentparent sp ON ms.id = sp.student_id
                WHERE u.id = %s
            """, [user.id])
            user_data = cursor.fetchone()
    elif user.user_type == 'teacher':
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT me.id, me.name, me.date_of_birth, me.gender, me.hire_date,
                       ec.phone_number, ec.email, ec.address,
                       ea.highest_degree, ea.institution, ea.year_of_passing,
                       eb.bank_account, eb.ifsc_code, eb.bank_name
                FROM myapp_masteremployee me
                LEFT JOIN myapp_employeecontact ec ON me.id = ec.employee_id
                LEFT JOIN myapp_employeeacademic ea ON me.id = ea.employee_id
                LEFT JOIN myapp_employeebank eb ON me.id = eb.employee_id
                WHERE me.user_id = %s
            """, [user.username])
            user_data = cursor.fetchone()

    if request.method == 'POST':
        field = request.POST.get('field')
        value = request.POST.get('value')
        if field and value:
            if field == 'user_type' and not request.user.is_staff:
                messages.error(request, "You do not have permission to change the user type.")
            else:
                setattr(user, field, value)
                user.save()
                messages.success(request, f"Your {field} has been updated successfully.")
                return redirect('profile')

    return render(request, 'myapp/profile.html', {'user_data': user_data})

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

# ...existing code...
