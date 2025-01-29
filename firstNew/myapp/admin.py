# Import necessary modules
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import path
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
import random
import string

from .models import User, masterStudent, StudentContact, StudentAcademic, StudentBank, StudentParent, masterEmployee, EmployeeContact, EmployeeAcademic, EmployeeBank, Institute, Program, Branch
from .views import admin_register_student, admin_register_employee

# Custom admin page
class CustomAdminSite(admin.AdminSite):
    site_header = 'My Admin Dashboard'
    site_title = 'Admin Dashboard'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('register_student/', self.admin_view(admin_register_student), name='admin_register_student'),
            path('register_employee/', self.admin_view(admin_register_employee), name='admin_register_employee'),
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['admin_register_student_link'] = format_html('<a href="{}">Register New Student</a>', self.get_url('admin_register_student'))
        extra_context['admin_register_employee_link'] = format_html('<a href="{}">Register New Employee</a>', self.get_url('admin_register_employee'))
        return super().index(request, extra_context)

# Instantiate your custom admin site
admin_site = CustomAdminSite(name='custom_admin')

# Register your models with the custom admin site
admin_site.register(User)

# Function to generate a unique username
def generate_username(email):
    base_username = email.split('@')[0]  # Use the part before '@' as base
    random_string = get_random_string(length=4, allowed_chars=string.ascii_letters + string.digits)
    return f"{base_username}_{random_string}"

# Custom UserAdmin
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'is_active', 'is_staff']
    search_fields = ['username', 'email']

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # User is being created
            # Generate a unique username
            username = generate_username(obj.email)
            obj.username = username

            # Generate a temporary password
            password = get_random_string(length=8)
            obj.set_password(password)

            # Save the user object
            super().save_model(request, obj, form, change)

            # Send the email with credentials
            subject = "Your Registration Details"
            message = f"Hello {obj.username},\n\nYour account has been created successfully.\nYour temporary password is: {password}\nPlease log in and change your password."
            send_mail(subject, message, 'admin@yourdomain.com', [obj.email])
        else:
            super().save_model(request, obj, form, change)

# Register the custom User model with the custom UserAdmin
admin.site.register(User, CustomUserAdmin)

# Register other models
admin.site.register(masterStudent)
admin.site.register(StudentContact)
admin.site.register(StudentAcademic)
admin.site.register(StudentBank)
admin.site.register(StudentParent)

# Register the new models with the custom admin site
admin_site.register(Institute)
admin_site.register(Program)
admin_site.register(Branch)
admin_site.register(masterEmployee)
admin_site.register(EmployeeContact)
admin_site.register(EmployeeAcademic)
admin_site.register(EmployeeBank)
# Remove EmployeeDepartment registration
# admin_site.register(EmployeeDepartment)
