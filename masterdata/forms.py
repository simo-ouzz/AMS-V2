from django import forms
from django.core.exceptions import ValidationError
from .models import tagEmplacement

class TagEmplacementForm(forms.ModelForm):
    class Meta:
        model = tagEmplacement
        fields = '__all__'

    def clean_reference(self):
        reference = self.cleaned_data.get('reference')
        if not reference.startswith('4C4F43'):
            raise ValidationError("La référence doit commencer par '4C4F43'.")
        return reference
