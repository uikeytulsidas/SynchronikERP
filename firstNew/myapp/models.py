import logging

logger = logging.getLogger(__name__)

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.mail import send_mail
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .middleware import get_current_user

# Custom user manager for handling user creation
class CustomUserManager(BaseUserManager):
    """
    Manager class for creating users and superusers.
    """
    def create_user(self, username, email, password=None, user_type='student'):
        """
        Creates and saves a user with the given username, email, password, and user_type.
        """
        if not email:
            raise ValueError("Users must have an email address")
        if not username:
            raise ValueError("Users must have a username")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, user_type=user_type)
        
        # Generate a temporary password if not provided
        if not password:
            password = get_random_string(length=8)  # Random password generation
        user.set_password(password)  # Hash the password
        user.save(using=self._db)
        
        # Send email with credentials
        self.send_welcome_email(user, password)

        return user

    def send_welcome_email(self, user, password):
        """
        Sends an email to the user with their username, temporary password, and instructions to change the password.
        """
        subject = "Welcome to Our Platform"
        message = (
            f"Hi {user.username},\n\n"
            f"Your account has been created successfully. Your temporary password is: {password}\n\n"
            f"Please log in and change your password as soon as possible.\n\n"
            f"Best Regards,\nYour Platform"
        )
        send_mail(
            subject,
            message,
            'from@example.com',  # Change to your email address
            [user.email],
            fail_silently=False,
        )

    def create_superuser(self, username, email, password):
        """
        Creates and saves a superuser with the given username, email, and password.
        """
        user = self.create_user(username=username, email=email, password=password, user_type='admin')
        user.is_staff = True  # Grant staff privileges
        user.is_superuser = True  # Grant superuser privileges
        user.save(using=self._db)
        return user

# Custom User model
class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model that uses email instead of username for authentication.
    """
    username = models.CharField(max_length=150, unique=True)  # Unique username
    email = models.EmailField(unique=True)  # Unique email address
    is_active = models.BooleanField(default=True)  # User activation status
    is_staff = models.BooleanField(default=False)  # Staff privileges

    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
        ('other', 'Other'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')

    # Related fields for Django's permissions system
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
    )

    objects = CustomUserManager()  # Assign the custom manager

    USERNAME_FIELD = 'username'  # Field used for authentication
    REQUIRED_FIELDS = ['email']  # Required fields for creating a user

    def __str__(self):
        """
        String representation of the User model.
        """
        return self.username

# Profile model for additional user details
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)
    is_default_password = models.BooleanField(default=True)
    first_login = models.BooleanField(default=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    aadhar_card_number = models.CharField(max_length=12, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

class University(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, null=True, blank=True)
    contact_no = models.CharField(max_length=15, null=True, blank=True)
    website = models.CharField(max_length=255, null=True, blank=True)
    estd_year = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=8, choices=[('Active', 'Active'), ('Inactive', 'Inactive')], default='Active')
    uni_code = models.CharField(max_length=50, null=True, blank=True)
    affil_status = models.CharField(max_length=10, choices=[('Affiliated', 'Affiliated'), ('Autonomous', 'Autonomous')], default='Affiliated')
    accred_details = models.CharField(max_length=255, null=True, blank=True)
    uni_type = models.CharField(max_length=7, choices=[('Public', 'Public'), ('Private', 'Private'), ('Deemed', 'Deemed')], default='Public')
    addl_contact_no = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    chancellor_name = models.CharField(max_length=255, null=True, blank=True)
    entry_person = models.CharField(max_length=255, null=True, blank=True)
    entry_date = models.DateField(null=True, blank=True)
    edit_person = models.CharField(max_length=255, null=True, blank=True)
    edit_date = models.DateField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    sort_order = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user:
            if not self.pk:
                self.entry_person = user.username
                self.entry_date = timezone.now().date()
            self.edit_person = user.username
            self.edit_date = timezone.now().date()
            logger.info(f"User {user.username} made changes to University: {self.name}")
        else:
            logger.warning("No user found in thread-local storage")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Institute(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='institutes')
    name = models.CharField(max_length=255)
    inst_code = models.CharField(max_length=50)
    address = models.CharField(max_length=255, null=True, blank=True)
    website = models.CharField(max_length=255, null=True, blank=True)
    affil_year = models.IntegerField(null=True, blank=True)
    autonomy_status = models.CharField(max_length=3, choices=[('Yes', 'Yes'), ('No', 'No')], default='No')
    acad_autonomy_year = models.IntegerField(null=True, blank=True)
    curric_type = models.CharField(max_length=255, null=True, blank=True)
    exam_ctrl = models.CharField(max_length=255, null=True, blank=True)
    degree_auth = models.CharField(max_length=255, null=True, blank=True)
    accred_details = models.CharField(max_length=255, null=True, blank=True)
    contact_no = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    director_name = models.CharField(max_length=255, null=True, blank=True)
    entry_person = models.CharField(max_length=255, null=True, blank=True)
    entry_date = models.DateField(null=True, blank=True)
    edit_person = models.CharField(max_length=255, null=True, blank=True)
    edit_date = models.DateField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    sort_order = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user:
            if not self.pk:
                self.entry_person = user.username
                self.entry_date = timezone.now().date()
            self.edit_person = user.username
            self.edit_date = timezone.now().date()
            logger.info(f"User {user.username} made changes to Institute: {self.name}")
        else:
            logger.warning("No user found in thread-local storage")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Program(models.Model):
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='programs')
    name = models.CharField(max_length=255)
    program_code = models.CharField(max_length=50)
    duration = models.IntegerField()
    level = models.CharField(max_length=50)
    type = models.CharField(max_length=50)
    affil_status = models.CharField(max_length=10, choices=[('Affiliated', 'Affiliated'), ('Autonomous', 'Autonomous')], default='Affiliated')
    intake_capacity = models.IntegerField()
    program_outcome = models.TextField()
    entry_person = models.CharField(max_length=255, null=True, blank=True)
    entry_date = models.DateField(null=True, blank=True)
    edit_person = models.CharField(max_length=255, null=True, blank=True)
    edit_date = models.DateField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    sort_order = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user:
            if not self.pk:
                self.entry_person = user.username
                self.entry_date = timezone.now().date()
            self.edit_person = user.username
            self.edit_date = timezone.now().date()
            logger.info(f"User {user.username} made changes to Program: {self.name}")
        else:
            logger.warning("No user found in thread-local storage")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Branch(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    branch_code = models.CharField(max_length=50)
    total_years = models.IntegerField()
    intake_capacity = models.IntegerField()
    add_on_capacity = models.IntegerField()
    entry_person = models.CharField(max_length=255, null=True, blank=True)
    entry_date = models.DateField(null=True, blank=True)
    edit_person = models.CharField(max_length=255, null=True, blank=True)
    edit_date = models.DateField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    sort_order = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user:
            if not self.pk:
                self.entry_person = user.username
                self.entry_date = timezone.now().date()
            self.edit_person = user.username
            self.edit_date = timezone.now().date()
            logger.info(f"User {user.username} made changes to Branch: {self.name}")
        else:
            logger.warning("No user found in thread-local storage")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Year(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='years')
    year_of_study = models.IntegerField()
    total_semesters = models.IntegerField()
    intake_capacity = models.IntegerField()
    add_on_capacity = models.IntegerField(default=0)
    lateral_entry = models.BooleanField(default=False)
    entry_person = models.CharField(max_length=100, null=True, blank=True)
    entry_date = models.DateField(default=timezone.now)
    edit_person = models.CharField(max_length=100, null=True, blank=True)
    edit_date = models.DateField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    sort_order = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user:
            if not self.pk:
                self.entry_person = user.username
                self.entry_date = timezone.now().date()
            self.edit_person = user.username
            self.edit_date = timezone.now().date()
            logger.info(f"User {user.username} made changes to Year: {self.year_of_study}")
        else:
            logger.warning("No user found in thread-local storage")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Year {self.year_of_study} for Branch: {self.branch.name}"

class Semester(models.Model):
    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='semesters')
    semester_number = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    sem_type = models.CharField(max_length=10)
    entry_person = models.CharField(max_length=100, null=True, blank=True)
    entry_date = models.DateField(default=timezone.now)
    edit_person = models.CharField(max_length=100, null=True, blank=True)
    edit_date = models.DateField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    sort_order = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user:
            if not self.pk:
                self.entry_person = user.username
                self.entry_date = timezone.now().date()
            self.edit_person = user.username
            self.edit_date = timezone.now().date()
            logger.info(f"User {user.username} made changes to Semester: {self.semester_number}")
        else:
            logger.warning("No user found in thread-local storage")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Semester {self.semester_number} for Year: {self.year.year_of_study}"

# Master student model
class masterStudent(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, default="default_student_id")
    name = models.CharField(max_length=100, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    admission_date = models.DateField(null=True, blank=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    admission_year = models.IntegerField(default=2023)
    semester = models.IntegerField(default=1)

    def __str__(self):
        return self.name if self.name else f"Student ID: {self.student_id}"

# Student contact information model
class StudentContact(models.Model):
    student = models.ForeignKey(masterStudent, on_delete=models.CASCADE, related_name='contacts')
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.name} - Contact"

# Student academic information model
class StudentAcademic(models.Model):
    student = models.ForeignKey(masterStudent, on_delete=models.CASCADE, related_name='academics')
    class_10_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    class_12_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    graduation_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.student.name} - Academic"

# Student banking information model
class StudentBank(models.Model):
    student = models.ForeignKey(masterStudent, on_delete=models.CASCADE, related_name='bank_details')
    bank_account = models.CharField(max_length=20, null=True, blank=True)
    ifsc_code = models.CharField(max_length=11, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.student.name} - Bank Details"

# Student parent information model
class StudentParent(models.Model):
    student = models.ForeignKey(masterStudent, on_delete=models.CASCADE, related_name='parents')
    parent_name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.student.name} - Parent: {self.parent_name}"

# User OTP model
class UserOTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.email} - {self.otp}"

# Master employee model
class masterEmployee(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    employee_id = models.CharField(max_length=20, default="default_employee_id")
    name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    hire_date = models.DateField()
    employee_type = models.CharField(max_length=50, default='admin')
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    teaching_subject = models.CharField(max_length=100, null=True, blank=True)
    # New fields for role-specific information
    subjects_taught = models.TextField(null=True, blank=True)
    classes_grades_assigned = models.TextField(null=True, blank=True)
    qualifications = models.TextField(null=True, blank=True)
    teaching_experience = models.IntegerField(null=True, blank=True)
    special_skills_certifications = models.TextField(null=True, blank=True)
    years_of_experience_in_institution = models.IntegerField(null=True, blank=True)
    staff_supervised = models.IntegerField(null=True, blank=True)
    key_responsibilities = models.TextField(null=True, blank=True)
    scholarship_programs_managed = models.TextField(null=True, blank=True)
    approval_authority = models.CharField(max_length=3, null=True, blank=True)
    coordinating_departments = models.TextField(null=True, blank=True)
    assigned_counters = models.TextField(null=True, blank=True)
    handled_payment_modes = models.TextField(null=True, blank=True)
    software_tools_used = models.TextField(null=True, blank=True)
    assigned_responsibilities = models.TextField(null=True, blank=True)
    work_schedule_shift_details = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

# Employee contact information model
class EmployeeContact(models.Model):
    employee = models.ForeignKey(masterEmployee, on_delete=models.CASCADE, related_name='contacts')
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.name} - Contact"

# Employee academic information model
class EmployeeAcademic(models.Model):
    employee = models.ForeignKey(masterEmployee, on_delete=models.CASCADE, related_name='academics')
    highest_degree = models.CharField(max_length=100)
    institution = models.CharField(max_length=100)
    year_of_passing = models.IntegerField()

    def __str__(self):
        return f"{self.employee.name} - Academic"

# Employee banking information model
class EmployeeBank(models.Model):
    employee = models.ForeignKey(masterEmployee, on_delete=models.CASCADE, related_name='bank_details')
    bank_account = models.CharField(max_length=20, null=True, blank=True)
    ifsc_code = models.CharField(max_length=11, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.employee.name} - Bank Details"