from django import forms
from accounts.models import VetProfile
from .models import Pet, VetAvailability, BlockedDate, Prescription
from core.widgets import ImageUploadWidget


def input_attrs():
    return {'placeholder': ' '}

def textarea_attrs(rows=4):
    return {'placeholder': ' ', 'rows': rows}


# ── Vet Profile Form ───────────────────────────────────────────────────────────

class VetProfileForm(forms.ModelForm):
    """
    Allows vets to edit their own profile details.
    Excludes admin-only fields like application_status,
    is_active, and consultation_fee.
    """
    first_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs=input_attrs())
    )
    last_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs=input_attrs())
    )
    phone_number = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs=input_attrs())
    )

    class Meta:
        model = VetProfile
        fields = [
            'bio',
            'bvc_registration_number',
            'education',
            'years_of_experience',
            'specializations',
            'profile_photo',
        ]
        widgets = {
            'bio': forms.Textarea(attrs=textarea_attrs(4)),
            'bvc_registration_number': forms.TextInput(attrs=input_attrs()),
            'education': forms.Textarea(attrs=textarea_attrs(3)),
            'years_of_experience': forms.NumberInput(
                attrs={**input_attrs(), 'min': 0}
            ),
            'specializations': forms.TextInput(attrs=input_attrs()),
            'profile_photo': ImageUploadWidget(),
        }

    def __init__(self, *args, **kwargs):
        # Pull the user instance so we can pre-fill name fields
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial  = self.user.last_name
            self.fields['phone_number'].initial = self.user.phone_number

        # Disable the fields to make them read-only
        self.fields['first_name'].disabled = True
        self.fields['last_name'].disabled = True
        self.fields['bvc_registration_number'].disabled = True

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            # We only save phone_number now, since first_name and last_name are read-only
            self.user.phone_number = self.cleaned_data.get('phone_number', '')
            self.user.save()
        if commit:
            profile.save()
        return profile


# ── Pet Form ───────────────────────────────────────────────────────────────────

class PetForm(forms.ModelForm):
    """Used by pet owners to add or edit their pet profiles."""

    class Meta:
        model = Pet
        fields = [
            'name', 'species', 'breed',
            'age_years', 'age_months',
            'weight_kg', 'photo',
        ]
        widgets = {
            'name':       forms.TextInput(attrs=input_attrs()),
            'species':    forms.Select(attrs=input_attrs()),
            'breed':      forms.TextInput(attrs=input_attrs()),
            'age_years':  forms.NumberInput(attrs={**input_attrs(), 'min': 0}),
            'age_months': forms.NumberInput(attrs={**input_attrs(), 'min': 0, 'max': 11}),
            'weight_kg':  forms.NumberInput(attrs={**input_attrs(), 'min': 0, 'step': '0.01'}),
            'photo': ImageUploadWidget(),
        }


# ── Availability Forms ─────────────────────────────────────────────────────────

DAYS_OF_WEEK = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]

TIME_CHOICES = []
from datetime import time as dt_time
for hour in range(0, 24):
    for minute in (0, 15, 30, 45):
        t = dt_time(hour, minute)
        label = t.strftime('%I:%M %p').lstrip('0')
        TIME_CHOICES.append((t.strftime('%H:%M'), label))


class RecurringAvailabilityForm(forms.Form):
    """
    Vet sets recurring weekly availability.
    Selects one or more days and adds up to 3 time windows.
    All selected days get the same windows.
    End date is optional.
    """
    days = forms.MultipleChoiceField(
        choices=DAYS_OF_WEEK,
        widget=forms.CheckboxSelectMultiple(),
        required=True,
        label='Repeat on these days',
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'placeholder': ' ',
        }),
        label='End date (optional)',
    )

    # Window 1 (required)
    window1_start = forms.ChoiceField(
        choices=TIME_CHOICES,
        label='Window 1 start',
        widget=forms.Select(attrs=input_attrs()),
    )
    window1_end = forms.ChoiceField(
        choices=TIME_CHOICES,
        label='Window 1 end',
        widget=forms.Select(attrs=input_attrs()),
    )

    # Window 2 (optional)
    window2_start = forms.ChoiceField(
        choices=[('', '—')] + TIME_CHOICES,
        required=False,
        label='Window 2 start',
        widget=forms.Select(attrs=input_attrs()),
    )
    window2_end = forms.ChoiceField(
        choices=[('', '—')] + TIME_CHOICES,
        required=False,
        label='Window 2 end',
        widget=forms.Select(attrs=input_attrs()),
    )

    # Window 3 (optional)
    window3_start = forms.ChoiceField(
        choices=[('', '—')] + TIME_CHOICES,
        required=False,
        label='Window 3 start',
        widget=forms.Select(attrs=input_attrs()),
    )
    window3_end = forms.ChoiceField(
        choices=[('', '—')] + TIME_CHOICES,
        required=False,
        label='Window 3 end',
        widget=forms.Select(attrs=input_attrs()),
    )

    def clean(self):
        cleaned = super().clean()
        # Validate window 1
        w1s = cleaned.get('window1_start')
        w1e = cleaned.get('window1_end')
        if w1s and w1e and w1s >= w1e:
            raise forms.ValidationError(
                "Window 1: end time must be after start time."
            )
        # Validate window 2 if provided
        w2s = cleaned.get('window2_start')
        w2e = cleaned.get('window2_end')
        if w2s and not w2e:
            raise forms.ValidationError("Window 2: please set an end time.")
        if w2e and not w2s:
            raise forms.ValidationError("Window 2: please set a start time.")
        if w2s and w2e and w2s >= w2e:
            raise forms.ValidationError(
                "Window 2: end time must be after start time."
            )
        # Validate window 3 if provided
        w3s = cleaned.get('window3_start')
        w3e = cleaned.get('window3_end')
        if w3s and not w3e:
            raise forms.ValidationError("Window 3: please set an end time.")
        if w3e and not w3s:
            raise forms.ValidationError("Window 3: please set a start time.")
        if w3s and w3e and w3s >= w3e:
            raise forms.ValidationError(
                "Window 3: end time must be after start time."
            )
        return cleaned


class SpecificDateAvailabilityForm(forms.Form):
    """
    Vet sets availability for a specific one-off date.
    Same multi-window structure as recurring.
    """
    specific_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': ' '}),
        label='Date',
    )
    window1_start = forms.ChoiceField(
        choices=TIME_CHOICES,
        label='Window 1 start',
        widget=forms.Select(attrs=input_attrs()),
    )
    window1_end = forms.ChoiceField(
        choices=TIME_CHOICES,
        label='Window 1 end',
        widget=forms.Select(attrs=input_attrs()),
    )
    window2_start = forms.ChoiceField(
        choices=[('', '—')] + TIME_CHOICES,
        required=False,
        label='Window 2 start',
        widget=forms.Select(attrs=input_attrs()),
    )
    window2_end = forms.ChoiceField(
        choices=[('', '—')] + TIME_CHOICES,
        required=False,
        label='Window 2 end',
        widget=forms.Select(attrs=input_attrs()),
    )
    window3_start = forms.ChoiceField(
        choices=[('', '—')] + TIME_CHOICES,
        required=False,
        label='Window 3 start',
        widget=forms.Select(attrs=input_attrs()),
    )
    window3_end = forms.ChoiceField(
        choices=[('', '—')] + TIME_CHOICES,
        required=False,
        label='Window 3 end',
        widget=forms.Select(attrs=input_attrs()),
    )

    def clean(self):
        cleaned = super().clean()
        w1s = cleaned.get('window1_start')
        w1e = cleaned.get('window1_end')
        if w1s and w1e and w1s >= w1e:
            raise forms.ValidationError(
                "Window 1: end time must be after start time."
            )
        w2s = cleaned.get('window2_start')
        w2e = cleaned.get('window2_end')
        if w2s and not w2e:
            raise forms.ValidationError("Window 2: please set an end time.")
        if w2e and not w2s:
            raise forms.ValidationError("Window 2: please set a start time.")
        if w2s and w2e and w2s >= w2e:
            raise forms.ValidationError(
                "Window 2: end time must be after start time."
            )
        w3s = cleaned.get('window3_start')
        w3e = cleaned.get('window3_end')
        if w3s and not w3e:
            raise forms.ValidationError("Window 3: please set an end time.")
        if w3e and not w3s:
            raise forms.ValidationError("Window 3: please set a start time.")
        if w3s and w3e and w3s >= w3e:
            raise forms.ValidationError(
                "Window 3: end time must be after start time."
            )
        return cleaned


class BlockedDateForm(forms.ModelForm):
    """Vet blocks a specific date — overrides all availability for that day."""

    class Meta:
        model = BlockedDate
        fields = ['date', 'reason']
        widgets = {
            'date':   forms.DateInput(attrs={'type': 'date', 'placeholder': ' '}),
            'reason': forms.TextInput(attrs=input_attrs()),
        }


# ── Prescription Form ──────────────────────────────────────────────────────────

class PrescriptionForm(forms.ModelForm):
    """Filled by vet during or after consultation."""

    class Meta:
        model = Prescription
        fields = [
            'medications',
            'dosage_instructions',
            'follow_up_advice',
            'additional_notes',
        ]
        widgets = {
            'medications':       forms.Textarea(attrs={**textarea_attrs(4), 'placeholder': ' '}),
            'dosage_instructions': forms.Textarea(attrs={**textarea_attrs(4), 'placeholder': ' '}),
            'follow_up_advice':  forms.Textarea(attrs={**textarea_attrs(3), 'placeholder': ' '}),
            'additional_notes':  forms.Textarea(attrs={**textarea_attrs(2), 'placeholder': ' '}),
        }