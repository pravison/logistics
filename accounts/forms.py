from django import forms 
from django.forms import ModelForm

class RequestResetCodeForm(forms.Form):
    email = forms.EmailField()

class PasswordResetCodeForm(forms.Form):
    code = forms.CharField(max_length=1000)
