from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm as BaseUserChangeForm
from myapp.models import User  # Import the custom User model
from django.contrib.auth import get_user_model
from .models import masterStudent, masterEmployee, StudentContact, StudentAcademic, StudentBank, StudentParent, Department, EmployeeDepartment, EmployeeContact, EmployeeAcademic, EmployeeBank, Institute, University, Program, Branch

# LoginForm: A simple form for logging in users
class LoginForm(forms.Form):
    # Username field with a maximum length of 150 characters
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',  # Adds Bootstrap styling
            'placeholder': 'Username',  # Placeholder text displayed in the input field
        })
    )
    # Password field with hidden input for security
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',  # Adds Bootstrap styling
            'placeholder': 'Password',  # Placeholder text displayed in the input field
        })
    )

User = get_user_model()

# AdminUserCreationForm: Form for admin to create a new user
class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'user_type')

# AdminUserRegistrationForm: Form for admin to register users with additional fields
class AdminUserRegistrationForm(forms.ModelForm):
    user_type = forms.ChoiceField(choices=User.USER_TYPE_CHOICES, required=True)
    mobile_number = forms.CharField(max_length=15, required=True)
    aadhar_card_number = forms.CharField(max_length=12, required=True)

    class Meta:
        model = User
        fields = ['email', 'mobile_number', 'aadhar_card_number', 'user_type']

# StudentInfoForm: Form for student information
class StudentInfoForm(forms.ModelForm):
    class Meta:
        model = masterStudent
        fields = '__all__'

class EmployeeInfoForm(forms.ModelForm):
    # General Fields
    full_name = forms.CharField(max_length=100, required=True)
    date_of_birth = forms.DateField(required=True)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], required=True)
    contact_number = forms.CharField(max_length=15, required=True)
    email_address = forms.EmailField(required=True)
    address = forms.CharField(widget=forms.Textarea, required=True)
    emergency_contact_name = forms.CharField(max_length=100, required=True)
    emergency_contact_relationship = forms.CharField(max_length=50, required=True)
    emergency_contact_number = forms.CharField(max_length=15, required=True)
    employee_id = forms.CharField(max_length=20, required=True)
    joining_date = forms.DateField(required=True)
    hire_date = forms.DateField(required=True)
    university = forms.ModelChoiceField(queryset=University.objects.all(), required=True)
    institute = forms.ModelChoiceField(queryset=Institute.objects.all(), required=True)
    program = forms.ModelChoiceField(queryset=Program.objects.none(), required=False)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)

    # Role-Specific Fields
    subjects_taught = forms.CharField(widget=forms.Textarea, required=False)
    classes_grades_assigned = forms.CharField(widget=forms.Textarea, required=False)
    qualifications = forms.CharField(widget=forms.Textarea, required=False)
    teaching_experience = forms.IntegerField(required=False)
    special_skills_certifications = forms.CharField(widget=forms.Textarea, required=False)
    department_name = forms.CharField(max_length=100, required=False)
    years_of_experience_in_institution = forms.IntegerField(required=False)
    staff_supervised = forms.IntegerField(required=False)
    key_responsibilities = forms.CharField(widget=forms.Textarea, required=False)
    scholarship_programs_managed = forms.CharField(widget=forms.Textarea, required=False)
    approval_authority = forms.ChoiceField(choices=[('yes', 'Yes'), ('no', 'No')], required=False)
    coordinating_departments = forms.CharField(widget=forms.Textarea, required=False)
    assigned_counters = forms.CharField(widget=forms.Textarea, required=False)
    handled_payment_modes = forms.CharField(widget=forms.Textarea, required=False)
    software_tools_used = forms.CharField(widget=forms.Textarea, required=False)
    assigned_responsibilities = forms.CharField(widget=forms.Textarea, required=False)
    work_schedule_shift_details = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = masterEmployee
        fields = [
            'full_name', 'date_of_birth', 'gender', 'contact_number', 'email_address', 'address',
            'emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_number',
            'employee_id', 'joining_date', 'hire_date', 'university', 'institute', 'program', 'department', 'subjects_taught', 'classes_grades_assigned',
            'qualifications', 'teaching_experience', 'special_skills_certifications', 'department_name',
            'years_of_experience_in_institution', 'staff_supervised', 'key_responsibilities',
            'scholarship_programs_managed', 'approval_authority', 'coordinating_departments',
            'assigned_counters', 'handled_payment_modes', 'software_tools_used', 'assigned_responsibilities',
            'work_schedule_shift_details'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['institute'].queryset = Institute.objects.none()
        self.fields['program'].queryset = Program.objects.none()

        if 'university' in self.data:
            try:
                university_id = int(self.data.get('university'))
                self.fields['institute'].queryset = Institute.objects.filter(university_id=university_id).order_by('name')
                self.fields['program'].queryset = Program.objects.filter(institute__university_id=university_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['institute'].queryset = self.instance.university.institute_set.order_by('name')
            self.fields['program'].queryset = Program.objects.filter(institute__university=self.instance.university).order_by('name')

        if 'program' in self.data:
            try:
                program_id = int(self.data.get('program'))
                self.fields['subject'].queryset = Department.objects.filter(program_id=program_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['subject'].queryset = Department.objects.filter(program=self.instance.program).order_by('name')

class UserChangeForm(BaseUserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'user_type')

class StudentRegistrationForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    mobile_number = forms.CharField(max_length=15, required=True)
    aadhar_card_number = forms.CharField(max_length=12, required=True)
    student_id = forms.CharField(max_length=20, required=True)
    university = forms.ModelChoiceField(queryset=University.objects.all(), required=True)
    institute = forms.ModelChoiceField(queryset=Institute.objects.all(), required=True)
    program = forms.ModelChoiceField(queryset=Program.objects.all(), required=True)
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)
    branch = forms.ModelChoiceField(queryset=Branch.objects.all(), required=True)
    admission_year = forms.ChoiceField(choices=[(year, year) for year in range(1, 5)], required=True)
    semester = forms.ChoiceField(choices=[(sem, sem) for sem in range(1, 9)], required=True)

    class Meta:
        model = masterStudent
        fields = ['mobile_number', 'aadhar_card_number', 'student_id', 'university', 'institute', 'program', 'department', 'branch', 'admission_year', 'semester']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['institute'].queryset = Institute.objects.none()
        self.fields['program'].queryset = Program.objects.none()
        self.fields['department'].queryset = Department.objects.none()
        self.fields['branch'].queryset = Branch.objects.none()

        if 'university' in self.data:
            try:
                university_id = int(self.data.get('university'))
                self.fields['institute'].queryset = Institute.objects.filter(university_id=university_id).order_by('name')
                self.fields['program'].queryset = Program.objects.filter(institute__university_id=university_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['institute'].queryset = self.instance.university.institute_set.order_by('name')
            self.fields['program'].queryset = Program.objects.filter(institute__university=self.instance.university).order_by('name')

        if 'program' in self.data:
            try:
                program_id = int(self.data.get('program'))
                self.fields['department'].queryset = Department.objects.filter(program_id=program_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['department'].queryset = Department.objects.filter(program=self.instance.program).order_by('name')

        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['branch'].queryset = Branch.objects.filter(department_id=department_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['branch'].queryset = Branch.objects.filter(department=self.instance.department).order_by('name')

class EmployeeRegistrationForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    hire_date = forms.DateField(required=True)
    mobile_number = forms.CharField(max_length=15, required=True)
    aadhar_card_number = forms.CharField(max_length=12, required=True)
    employee_id = forms.CharField(max_length=20, required=True)
    employee_type = forms.ChoiceField(choices=[
        ('teacher', 'Teacher'),
        ('hod', 'Head of Department'),
        ('scholarship_officer', 'Scholarship Officer'),
        ('fee_collector', 'Fee Collector'),
        ('admin', 'Admin'),  # Added admin option
        # Add other employee types as needed
    ], required=True)
    university = forms.ModelChoiceField(queryset=University.objects.all(), required=True)
    institute = forms.ModelChoiceField(queryset=Institute.objects.none(), required=True)
    program = forms.ModelChoiceField(queryset=Program.objects.none(), required=False)
    department = forms.ModelChoiceField(queryset=Department.objects.none(), required=False)
    position = forms.CharField(max_length=100, required=False)  # Position not required for teacher and hod
    teaching_subject = forms.CharField(max_length=100, required=False)  # Teaching subject not required for teacher and hod

    class Meta:
        model = masterEmployee
        fields = [
            'email', 'hire_date', 'mobile_number', 'aadhar_card_number', 'employee_id', 'employee_type',
            'university', 'institute', 'program', 'department', 'position', 'teaching_subject'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['institute'].queryset = Institute.objects.none()
        self.fields['program'].queryset = Program.objects.none()
        self.fields['department'].queryset = Department.objects.none()

        if 'university' in self.data:
            try:
                university_id = int(self.data.get('university'))
                self.fields['institute'].queryset = Institute.objects.filter(university_id=university_id).order_by('name')
                print(f"Filtered institutes for university_id {university_id}")  # Debug log
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['institute'].queryset = self.instance.university.institute_set.order_by('name')

        if 'institute' in self.data:
            try:
                institute_id = int(self.data.get('institute'))
                self.fields['program'].queryset = Program.objects.filter(institute_id=institute_id).order_by('name')
                print(f"Filtered programs for institute_id {institute_id}")  # Debug log
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['program'].queryset = Program.objects.filter(institute=self.instance.institute).order_by('name')

        if 'program' in self.data:
            try:
                program_id = int(self.data.get('program'))
                self.fields['department'].queryset = Department.objects.filter(program_id=program_id).order_by('name')
                print(f"Filtered departments for program_id {program_id}")  # Debug log
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['department'].queryset = Department.objects.filter(program=self.instance.program).order_by('name')

        # Set initial values if instance exists
        if self.instance.pk:
            self.fields['institute'].queryset = Institute.objects.filter(university=self.instance.university).order_by('name')
            self.fields['program'].queryset = Program.objects.filter(institute=self.instance.institute).order_by('name')
            self.fields['department'].queryset = Department.objects.filter(program=self.instance.program).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        employee_type = cleaned_data.get('employee_type')

        if employee_type in ['teacher', 'hod']:
            cleaned_data['position'] = None
            cleaned_data['teaching_subject'] = None
        elif employee_type in ['scholarship_officer', 'fee_collector', 'admin']:
            cleaned_data['program'] = None
            cleaned_data['department'] = None
            cleaned_data['position'] = None
            cleaned_data['teaching_subject'] = None

        return cleaned_data
