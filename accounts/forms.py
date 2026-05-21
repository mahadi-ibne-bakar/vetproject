from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, VetProfile
from core.widgets import ImageUploadWidget

# Helper: minimal attrs for all inputs — styling is handled by base.html CSS
def input_attrs(placeholder=""):
    return {'placeholder': ' ', 'autocomplete': 'off'}

def password_attrs():
    return {'placeholder': ' '}

def textarea_attrs(rows=4):
    return {'placeholder': ' ', 'rows': rows}


class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True,
        widget=forms.TextInput(attrs=input_attrs()))
    last_name = forms.CharField(max_length=50, required=True,
        widget=forms.TextInput(attrs=input_attrs()))
    email = forms.EmailField(required=True,
        widget=forms.EmailInput(attrs=input_attrs()))
    phone_number = forms.CharField(max_length=20, required=True,
        widget=forms.TextInput(attrs=input_attrs()))

    class Meta:
        model = User
        fields = ['phone_number', 'address', 'profile_photo']
        widgets = {
            'phone_number':  forms.TextInput(attrs={'placeholder': ' '}),
            'address':       forms.Textarea(attrs={'placeholder': ' ', 'rows': 3}),
            'profile_photo': ImageUploadWidget(),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs=password_attrs())
        self.fields['password2'].widget = forms.PasswordInput(attrs=password_attrs())
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        pass

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data['phone_number']
        user.role = User.Role.USER
        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email',
        widget=forms.EmailInput(attrs={**input_attrs(), 'autofocus': True}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs=password_attrs()))

class UserProfileForm(forms.ModelForm):
    """Allows pet owners to edit their own profile details."""

    first_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'placeholder': ' '})
    )
    last_name = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'placeholder': ' '})
    )

    class Meta:
        model = User
        fields = ['phone_number', 'address', 'profile_photo']
        widgets = {
            'phone_number': forms.TextInput(attrs={'placeholder': ' '}),
            'address':      forms.Textarea(attrs={'placeholder': ' ', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['first_name'].initial = self.instance.first_name
            self.fields['last_name'].initial  = self.instance.last_name

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name  = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user

class VetLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email',
        widget=forms.EmailInput(attrs={**input_attrs(), 'autofocus': True}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs=password_attrs()))


class VetApplicationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True,
        widget=forms.TextInput(attrs=input_attrs()))
    last_name = forms.CharField(max_length=50, required=True,
        widget=forms.TextInput(attrs=input_attrs()))
    email = forms.EmailField(required=True,
        widget=forms.EmailInput(attrs=input_attrs()))
    phone_number = forms.CharField(max_length=20, required=True,
        widget=forms.TextInput(attrs=input_attrs()))
    password1 = forms.CharField(label='Password',
        widget=forms.PasswordInput(attrs=password_attrs()))
    password2 = forms.CharField(label='Confirm Password',
        widget=forms.PasswordInput(attrs=password_attrs()))

    class Meta:
        model = VetProfile
        fields = ['bio', 'bvc_registration_number', 'education',
                  'years_of_experience', 'specializations']
        widgets = {
            'bio': forms.Textarea(attrs=textarea_attrs(4)),
            'bvc_registration_number': forms.TextInput(attrs=input_attrs()),
            'education': forms.Textarea(attrs=textarea_attrs(3)),
            'years_of_experience': forms.NumberInput(attrs={**input_attrs(), 'min': 0}),
            'specializations': forms.TextInput(attrs=input_attrs()),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        return cleaned_data


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs=input_attrs()))


class SetNewPasswordForm(forms.Form):
    password1 = forms.CharField(label='New Password',
        widget=forms.PasswordInput(attrs=password_attrs()))
    password2 = forms.CharField(label='Confirm New Password',
        widget=forms.PasswordInput(attrs=password_attrs()))

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        return cleaned_data