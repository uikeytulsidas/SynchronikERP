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
    path('register_student/', views.admin_register_student, name='admin_register_student'),
    path('register_employee/', views.admin_register_employee, name='admin_register_employee'),
    path('register_user/', views.admin_register_user, name='admin_register_user'),
    path('view_student/<int:student_id>/', views.view_student, name='view_student'),
    path('view_employee/<int:employee_id>/', views.view_employee, name='view_employee'),
    path('profile/', views.profile_view, name='profile'),
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
]
