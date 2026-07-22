from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse

from .models import Customer
from accounts.views import generate_unique_refferal_code
from accounts.views import format_kenyan_phone_number
# Create your views here.

def add_customer(request):
    refferal_code = request.GET.get('refferal_code') or ''
    reffered_customer_number = request.GET.get('reffered_customer_number') or ''
    bussiness_slug = request.GET.get('bussiness_slug') or ''

    if request.method == 'POST':
        name = request.POST['name'] # will install phonenumber and check if number is valid and convert it to international format
        phone_number = request.POST['phone_number'] 
        refferal_code = request.POST['refferal_code'] or ''
        
        #lets get customer with the above reffral code 
        user_who_reffered = None
        if refferal_code !='':
            customer_with_the_code = Customer.objects.filter(refferal_code=refferal_code).first()
            if customer_with_the_code:
                # lets check if customer object has user field 
                if customer_with_the_code.user:
                    user_who_reffered = customer_with_the_code.user

        # lets save neigbor record to the database
        # first check if customer with the number already exists
        # lets create loyalty points record for the welcome bonus to the customer
        url = f'/customers/invite-a-neighbor/?refferal_code={refferal_code}&bussiness_slug={bussiness_slug}'
        phone_number = format_kenyan_phone_number(str(phone_number))
        customer = Customer.objects.filter(phone_number=phone_number).first()
        if  customer:
            if bussiness_slug !='':
                messages.success(request, 'Unfoortunately customer with that phone number already exists')
            else:
                messages.success(request, 'Unfoortunately Neighbor already been added by someone else')
            return redirect(url)
        else:
            customer = Customer.objects.create(
                name = name,
                phone_number=phone_number,
                total_loyalty_points = int(50), # 50 point welcome points
                refferal_code = generate_unique_refferal_code(),
                reffered_by = user_who_reffered
                )
            
            # lets add customer to a business that added him
            notify1="Congrats Your Neighbor has Received 50 points ***Welcome Bonus *** "
            notify2="Neighbor added succesfuly to your lists of refferals"
            messages.success(request, notify1)
            messages.success(request, notify2)
            url = f'/customers/invite-a-neighbor/?refferal_code={refferal_code}&reffered_customer_number={phone_number}&bussiness_slug={bussiness_slug}'
            
            return redirect(url)
        
       
    context = {
        'refferal_code': refferal_code,
        'reffered_customer_number': reffered_customer_number,
        'bussiness_slug': bussiness_slug
    }
    return render(request, 'customers/add-customer.html', context)
    
def upload_profile_image(request):
    if request.method == 'POST':
        customer = request.user.customer
        profile_image = request.FILES.get('profile_image')

        if not profile_image:
            return JsonResponse({'success': False, 'error': 'No image uploaded.'})

        customer.profile_image = profile_image
        customer.save()
        return JsonResponse({'pofile image uploaded successfully': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})