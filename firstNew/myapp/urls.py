from django.urls import path
from django.contrib import admin
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from . import views
from myapp.admin import admin_site

DEFAULT_DOMAIN = '127.0.0.1:8000'

# Check if the user is a staff member before granting access to the admin page
def staff_only(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            return redirect('home')  # Redirect to a non-admin page if the user is not staff
        return view_func(request, *args, **kwargs)
    return _wrapped_view

urlpatterns = [
    path('custom-admin/', views.custom_admin_login_view, name='custom_admin_login'),
    path('change_password/', views.change_password_view, name='change_password'),
    path('student_info_form/', views.student_info_form_view, name='student_info_form'),
    path('employee_info_form/', views.employee_info_form_view, name='employee_info_form'),
    path('view_student/<int:student_id>/', views.view_student, name='view_student'),
    path('view_employee/<int:employee_id>/', views.view_employee, name='view_employee'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/', views.profile_view, name='profile_view'),
    path('', views.home_view, name='home'),
    path('employee_home/', views.home_view, name='employee_home'),
    path('login/', views.login_view, name='login'),
    path('verify-otp/<str:email>/', views.verify_otp_view, name='verify_otp'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='myapp/password_reset_form.html',
        email_template_name='myapp/password_reset_email.html',
        subject_template_name='myapp/password_reset_subject.txt',
        success_url='/password-reset/done/'
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='myapp/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='myapp/password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='myapp/password_reset_complete.html'
    ), name='password_reset_complete'),

    path('load-institutes/', views.load_institutes, name='load_institutes'),
    path('load-programs/', views.load_programs, name='load_programs'),
    path('load-branches/', views.load_branches, name='load_branches'),
    path('admin_register/', views.admin_register, name='admin_register'),

    # AJAX URLs for dynamic dropdowns
    path('ajax/load-institutes/', views.load_institutes, name='load_institutes'),
    path('ajax/load-programs/', views.load_programs, name='load_programs'),
    path('ajax/load-branches/', views.load_branches, name='load_branches'),

    # New URLs for admin register student and employee
    path('admin_register_student/', views.admin_register_student, name='admin_register_student'),
    path('admin_register_employee/', views.admin_register_employee, name='admin_register_employee'),

    # New URLs for AJAX requests
    path('viewProfile/', views.load_profile, name='load_profile'),
    path('changePassword/', views.load_change_password, name='load_change_password'),
    path('adminRegisterStudent/', views.load_admin_register_student, name='load_admin_register_student'),
    path('adminRegisterEmployee/', views.load_admin_register_employee, name='load_admin_register_employee'),

    # New URLs for student section
    path('student_section/', views.student_section_view, name='student_section'),
    path('edit_student_permissions/<int:student_id>/', views.edit_student_permissions, name='edit_student_permissions'),
    path('student_home/', views.student_home_view, name='student_home'),

    # New URL for student management
    path('student_management/', views.student_management_view, name='student_management'),
]

