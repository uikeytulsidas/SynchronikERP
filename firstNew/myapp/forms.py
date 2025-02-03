from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm as BaseUserChangeForm
from myapp.models import User  # Import the custom User model
from django.contrib.auth import get_user_model
from .models import masterStudent, masterEmployee, StudentContact, StudentAcademic, StudentBank, StudentParent, EmployeeContact, EmployeeAcademic, EmployeeBank, Institute, University, Program, Branch

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
    contact_phone_number = forms.CharField(max_length=15, required=False)
    contact_email = forms.EmailField(required=False)
    contact_address = forms.CharField(widget=forms.Textarea, required=False)
    class_10_score = forms.DecimalField(max_digits=5, decimal_places=2, required=False)
    class_12_score = forms.DecimalField(max_digits=5, decimal_places=2, required=False)
    graduation_score = forms.DecimalField(max_digits=5, decimal_places=2, required=False)
    bank_account = forms.CharField(max_length=20, required=False)
    ifsc_code = forms.CharField(max_length=11, required=False)
    bank_name = forms.CharField(max_length=100, required=False)
    parent_name = forms.CharField(max_length=100, required=False)
    parent_relationship = forms.CharField(max_length=50, required=False)
    parent_contact_number = forms.CharField(max_length=15, required=False)

    class Meta:
        model = masterStudent
        fields = [
            'name', 'date_of_birth', 'gender', 'aadhar_number', 'mobile_number', 'email',
            'contact_phone_number', 'contact_email', 'contact_address',
            'class_10_score', 'class_12_score', 'graduation_score',
            'bank_account', 'ifsc_code', 'bank_name',
            'parent_name', 'parent_relationship', 'parent_contact_number'
        ]

    def __init__(self, *args, **kwargs):
        super(StudentInfoForm, self).__init__(*args, **kwargs)
        if self.instance:
            try:
                contact = self.instance.contact
                self.fields['contact_phone_number'].initial = contact.phone_number
                self.fields['contact_email'].initial = contact.email
                self.fields['contact_address'].initial = contact.address
            except StudentContact.DoesNotExist:
                pass

            try:
                academic = self.instance.academic
                self.fields['class_10_score'].initial = academic.class_10_score
                self.fields['class_12_score'].initial = academic.class_12_score
                self.fields['graduation_score'].initial = academic.graduation_score
            except StudentAcademic.DoesNotExist:
                pass

            try:
                bank = self.instance.bank_details
                self.fields['bank_account'].initial = bank.bank_account
                self.fields['ifsc_code'].initial = bank.ifsc_code
                self.fields['bank_name'].initial = bank.bank_name
            except StudentBank.DoesNotExist:
                pass

            parent = self.instance.parents.first()
            if parent:
                self.fields['parent_name'].initial = parent.parent_name
                self.fields['parent_relationship'].initial = parent.relationship
                self.fields['parent_contact_number'].initial = parent.contact_number

    def make_fields_editable(self, fields):
        for field in fields:
            if field in self.fields:
                self.fields[field].widget.attrs.pop('readonly', None)

class EmployeeInfoForm(forms.ModelForm):
    # General Fields
    name = forms.CharField(max_length=100, required=True)
    date_of_birth = forms.DateField(required=True)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], required=True)
    mobile_number = forms.CharField(max_length=15, required=True)
    email = forms.EmailField(required=True)
    aadhar_number = forms.CharField(max_length=12, required=True)
    hire_date = forms.DateField(required=True)
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
    branch = forms.ModelChoiceField(queryset=Branch.objects.none(), required=False)
    position = forms.CharField(max_length=100, required=False)  # Position not required for teacher and hod
    teaching_subject = forms.CharField(max_length=100, required=False)  # Teaching subject not required for teacher and hod

    class Meta:
        model = masterEmployee
        fields = [
            'name', 'date_of_birth', 'gender', 'mobile_number', 'email', 'aadhar_number', 'hire_date',
            'employee_id', 'employee_type', 'university', 'institute', 'program', 'branch', 'position', 'teaching_subject'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['institute'].queryset = Institute.objects.none()
        self.fields['program'].queryset = Program.objects.none()
        self.fields['branch'].queryset = Branch.objects.none()

        if 'university' in self.data:
            try:
                university_id = int(self.data.get('university'))
                self.fields['institute'].queryset = Institute.objects.filter(university_id=university_id).order_by('name')
                print(f"Filtered institutes for university_id {university_id}")  # Debug log
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['institute'].queryset = self.instance.university.institutes.order_by('name')

        if 'institute' in self.data:
            try:
                institute_id = int(self.data.get('institute'))
                self.fields['program'].queryset = Program.objects.filter(institute_id=institute_id).order_by('name')
                print(f"Filtered programs for institute_id {institute_id}")  # Debug log
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk and hasattr(self.instance, 'institute'):
            self.fields['program'].queryset = Program.objects.filter(institute=self.instance.institute).order_by('name')

        if 'program' in self.data:
            try:
                program_id = int(self.data.get('program'))
                self.fields['branch'].queryset = Branch.objects.filter(program_id=program_id).order_by('name')
                print(f"Filtered branches for program_id {program_id}")  # Debug log
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk and hasattr(self.instance, 'program'):
            self.fields['branch'].queryset = Branch.objects.filter(program=self.instance.program).order_by('name')

        # Set initial values if instance exists
        if self.instance.pk:
            self.fields['institute'].queryset = Institute.objects.filter(university=self.instance.university).order_by('name')
            if hasattr(self.instance, 'institute'):
                self.fields['program'].queryset = Program.objects.filter(institute=self.instance.institute).order_by('name')
            if hasattr(self.instance, 'program'):
                self.fields['branch'].queryset = Branch.objects.filter(program=self.instance.program).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        employee_type = cleaned_data.get('employee_type')

        if employee_type in ['teacher', 'hod']:
            cleaned_data['position'] = None
            cleaned_data['teaching_subject'] = None
        elif employee_type in ['scholarship_officer', 'fee_collector', 'admin']:
            cleaned_data['program'] = None
            cleaned_data['branch'] = None
            cleaned_data['position'] = None
            cleaned_data['teaching_subject'] = None

        return cleaned_data

class UserChangeForm(BaseUserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'user_type')

class StudentRegistrationForm(forms.ModelForm):
    admission_year = forms.ChoiceField(
        choices=[
            ('1', 'First Year'),
            ('2', 'Second Year'),
            ('3', 'Third Year'),
            ('4', 'Fourth Year')
        ],
        required=True
    )
    semester = forms.ChoiceField(
        choices=[
            ('1', 'Semester 1'),
            ('2', 'Semester 2'),
            ('3', 'Semester 3'),
            ('4', 'Semester 4'),
            ('5', 'Semester 5'),
            ('6', 'Semester 6'),
            ('7', 'Semester 7'),
            ('8', 'Semester 8')
        ],
        required=True
    )
    admission_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)

    class Meta:
        model = masterStudent
        fields = ['name', 'email', 'mobile_number', 'aadhar_number', 'university', 'institute', 'program', 'branch', 'admission_year', 'semester', 'admission_date', 'abc_id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['institute'].queryset = Institute.objects.none()
        self.fields['program'].queryset = Program.objects.none()
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
                self.fields['branch'].queryset = Branch.objects.filter(program_id=program_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['branch'].queryset = Branch.objects.filter(program=self.instance.program).order_by('name')

class EmployeeRegistrationForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    mobile_number = forms.CharField(max_length=15, required=True)
    aadhar_number = forms.CharField(max_length=12, required=True)
    hire_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    # Removed date_of_birth field
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
    highest_qualification = forms.CharField(max_length=100, required=True)  # Corrected field name

    class Meta:
        model = masterEmployee
        fields = ['name', 'email', 'mobile_number', 'aadhar_number', 'hire_date', 'employee_type', 'university', 'institute', 'highest_qualification']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['institute'].queryset = Institute.objects.none()

        if 'university' in self.data:
            try:
                university_id = int(self.data.get('university'))
                self.fields['institute'].queryset = Institute.objects.filter(university_id=university_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            self.fields['institute'].queryset = self.instance.university.institute_set.order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        employee_type = cleaned_data.get('employee_type')

        # Clear fields that are not required for the selected employee type
        if employee_type in ['scholarship_officer', 'fee_collector', 'admin']:
            cleaned_data['program'] = None
            cleaned_data['branch'] = None

        return cleaned_data
