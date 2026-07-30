from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
# Create your views here.
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.core.mail import send_mail
from .models import PasswordResetCode
from .forms import RequestResetCodeForm, PasswordResetCodeForm
# from django.contrib.auth.models import User
from customers.models import Customer
import uuid
import re
import phonenumbers

import re

from django.contrib.auth import get_user_model

User = get_user_model()

def format_kenyan_phone_number(phone_raw: str) -> str:
    """
    Normalizes a phone number into international digits-only format.

    Rules:
    - If number already has a country code (starts with 1-9 and length >= 11),
      keep it as-is.
    - If number starts with 0 (e.g 0712...), replace 0 with 254.
    - If number starts with 7 and has 9 digits, add 254.
    - Removes spaces, +, dashes, brackets.
    
    Returns:
        str: formatted phone number like 254712345678, 255712345678, 245740675645
    """

    if not phone_raw:
        raise ValueError("Phone number is required.")

    # Remove everything except digits
    phone = re.sub(r"\D", "", phone_raw.strip())

    if not phone:
        raise ValueError("Phone number is required.")

    # Convert 00 prefix to normal country code style
    if phone.startswith("00"):
        phone = phone[2:]

    # Kenyan local formats
    if phone.startswith("0") and len(phone) >= 10:
        phone = "254" + phone[1:]

    elif phone.startswith("7") and len(phone) == 9:
        phone = "254" + phone

    # If it already looks like an international number, keep it
    elif len(phone) >= 11 and phone[0] != "0":
        # already has country code, do nothing
        pass

    else:
        raise ValueError("Invalid phone number format.")

    # Basic validation: must be between 11 and 15 digits (E.164 max is 15)
    if len(phone) < 11 or len(phone) > 15:
        raise ValueError("Invalid phone number length.")

    return phone

def generate_unique_refferal_code():
    while True:
        refferal_code = uuid.uuid4().hex[:4]
        if not Customer.objects.filter(refferal_code=refferal_code).exists():
            return refferal_code
        



def request_reset_code(request):
    if request.method == 'POST':
        email = "".join(request.POST['email'].split())
        try:
            user = User.objects.get(email__iexact=email)      
            # Generate or update the reset code
            reset_code, created = PasswordResetCode.objects.get_or_create(user=user)
            reset_code.code = str(uuid.uuid4().hex[:6])
            reset_code.is_valid = True
            reset_code.save()
            
            # Send email
            send_mail(
                'GARANTII MALL PASSWORD RESET CODE',
                f'Your reset code is: {reset_code.code}',
                'noreply@example.com',
                [email],
            )
            messages.success(request, 'A reset code has been sent to your email and expires in ten minutes.')
            messages.success(request, 'if not seeing the email countercheck from the spam folder.')
            return redirect('verify_reset_code')
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email.')
            messages.error(request, 'create new account or contact admin 0706420043')
    else:
        form = RequestResetCodeForm()
    return render(request, 'home/request_reset_code.html')


def verify_reset_code(request):
    if request.method == 'POST':
        form = PasswordResetCodeForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Error assessing your data counter check and try again')
            return redirect('verify_reset_code')
        code = form.cleaned_data['code']
        try:
            reset_code = PasswordResetCode.objects.filter(code=code, is_valid=True).order_by('created_at').last()
            if reset_code is None:
                messages.error(request, 'Counter check your code seems its incorrect')
                return redirect('verify_reset_code')
            if reset_code.is_expired():
                reset_code.is_valid = False
                reset_code.save()
                messages.error(request, 'This code has expired.')
                return redirect('request_reset_code')
            else:
                # Invalidate the code
                reset_code.is_valid = False
                reset_code.save()
                # Redirect to password reset form
                request.session['password_reset_user_id'] = reset_code.user.id
                return redirect('reset_password')
        except PasswordResetCode.DoesNotExist:
            messages.error(request, 'Counter check your code seems its incorrect')
            return redirect('verify_reset_code')
    form = PasswordResetCodeForm()
    return render(request, 'home/verify_reset_code.html', {'form': form} )

def reset_password(request):
    user_id = request.session.get('password_reset_user_id')
    if not user_id:
        messages.error(request, 'There was an error proccessing your application, try again')
        return redirect('request_reset_code')
    
    user = User.objects.get(id=user_id)
    try:
        reset_code = PasswordResetCode.objects.filter(user=user).order_by('-created_at').first()
        if reset_code is None:
            messages.error(request, 'There was an error proccessing your application, try again')
            return redirect('request_reset_code')
        if reset_code.is_expired():
            # If the code is expired or invalid, redirect to request a new one
            reset_code.is_valid = False
            reset_code.save()
            messages.error(request, 'Your reset code has expired. Please request a new code.')
            return redirect('request_reset_code')
    except (User.DoesNotExist, PasswordResetCode.DoesNotExist):
        # If the user or reset code is not found, redirect to the request page
        messages.error(request, 'Invalid reset request. Please try again.')
        return redirect('request_reset_code')
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            # Keep the user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been successfully reset.')
            return redirect('login_user')
    else:
        form = SetPasswordForm(user)
    return render(request, 'home/reset_password.html', {'form': form})

# Create your views here.
def register_user(request):
    next_url = request.GET.get('next', '')
    refferal_code = request.GET.get('refferal_code') or ''
    wholesaler = request.GET.get('wholesaler', '')
    seller = request.GET.get('seller', '')
    shop_patner = request.GET.get('shop_patner', '') # customer/shops we are patnering with to help get customers
    stored_refferal_code= request.session.get('stored_refferal_code') or '' #  we get both refferal code plus business slug         
    context = {
        'next_url': next_url,
        'shop_patner' : shop_patner,
    }
    if wholesaler !='':
        request.session['wholesaler'] = wholesaler
        
    if shop_patner !='':
        request.session['shop_patner'] = shop_patner

    if refferal_code !='':
        request.session['stored_refferal_code'] = refferal_code

    if stored_refferal_code !='':
        refferal_code = stored_refferal_code

    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')  # will install phonenumber and check if number is valid and convert it to international format
        password = request.POST.get('password')
        try:
            username = format_kenyan_phone_number(phone_number)
        except ValueError as e:
            messages.success(request, 'Invalid Phone number.')
            return render(request, 'home/register.html', context)
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            messages.success(request, 'Phone Number already exists.')
            messages.success(request, 'Please login and if forgot password click forgot password')
            return render(request, 'home/register.html', context)
        
        # Create user
        user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name, email=email, password=password)
        customer = Customer.objects.filter(phone_number=username).first()
        if  customer is None:
            customer = Customer.objects.create(
                phone_number=username,# username is the phone number
                total_loyalty_points = int(50), # 50 point welcome points
                refferal_code = generate_unique_refferal_code()
                )
            
            messages.success(request, 'Congrats You have Received 50 points ***Welcome Bonus *** ')

            if refferal_code != '':
                refferer = Customer.objects.filter(refferal_code=refferal_code).first()
                if refferer:
                    customer.reffered_by = refferer.user
                    customer.save()
        
        customer.user = user
        customer.save()
        
        if seller != '':
            user = authenticate(username=username, password=password)
            login(request, user)
            url = f'/business/add-business/?seller={seller}'
            return redirect(url)

        # Handle redirect for "next_url" parameter
        if next_url != '':
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect(next_url)

        # Default redirect after registration
        user = authenticate(username=username, password=password)
        login(request, user)
        return redirect('all_Wholesale_products')
    
    
    
    return render(request, 'home/register.html', context)

from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
def login_user(request):
    next_url = request.GET.get('next', '')
    
    if request.method == 'POST':
        phone_number = request.POST['phone_number'] # will install phonenumber and check if number is valid and convert it to international format
        password = request.POST['password']
        
        try:
            username = format_kenyan_phone_number(phone_number)
        except ValueError as e:
            messages.success(request, 'Invalid Phone number.')
            return render(request, 'home/login.html', {'next': next_url})
        
        if not User.objects.filter(username=username).exists():
            messages.success(request, 'Phone Number does not exists.')
            messages.success(request, 'Please create new account.')
            messages.success(request, "and if you've already  created the account countercheck your phone number")
            return render(request, 'home/login.html', {'next': next_url})
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            print(request.user.is_authenticated)  # Should be True
            messages.success(request, 'Welcome, you have been logged in!')
            return redirect(next_url or 'index')
     
        messages.error(request, "your password is incorrect")
        messages.success(request, "if you don't remember click forget password to reset")
        return redirect('login_user')

    return render(request, 'home/login.html', {'next': next_url})

def logout_user(request):
    logout(request)
    messages.success(request, "You Have Been Logged Out...")
    return redirect('login_user')