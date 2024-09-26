import os
import time
import requests
import pandas as pd
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from .forms import UnicastSMSForm, BulkSMSForm
from .models import SMSLog
from django.contrib.auth.decorators import login_required

@login_required
# Unicast SMS
def send_unicast_sms(request):
    if request.method == 'POST':
        form = UnicastSMSForm(request.POST)
        if form.is_valid():
            mobile_number = form.cleaned_data['mobile_number']
            message = form.cleaned_data['message']
            # API call to send SMS
            url = (
                f"http://{os.getenv('SMS_API_IP')}/http.aspx?"
                f"guid={os.getenv('SMS_API_GUID')}&"
                f"username={os.getenv('SMS_API_USERNAME')}&"
                f"password={os.getenv('SMS_API_PASSWORD')}&"
                f"countryCode=np&"
                f"mobileNumber=%2b977{mobile_number}&"
                f"message={message}"
            )

            response = requests.get(url)
            response_text = response.text

            # Determine status based on response
            if "Message received" in response_text:
                status = 'Sent'
            elif "Invalid SMS123Go username or password" in response_text:
                status = 'Failed: Invalid credentials'
            elif "Failed sending message" in response_text:
                status = 'Failed: Invalid mobile number'
            else:
                status = 'Failed: Unknown error'

            # Log the SMS
            SMSLog.objects.create(
                mobile_number=mobile_number,
                message=message,
                status=status,
                response=response_text
            )
            return redirect('sms_report')  # Redirect to reporting page after sending
    else:
        form = UnicastSMSForm()

    return render(request, 'send_unicast_sms.html', {'form': form})


# Bulk SMS
@login_required
def send_bulk_sms(request):
    if request.method == 'POST':
        form = BulkSMSForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            df = pd.read_excel(excel_file)
            for index, row in df.iterrows():
                mobile_number = row['mobile_number']
                message = row['message']

                # Construct the URL using environment variables
                url = (
                    f"http://{os.getenv('SMS_API_IP')}/http.aspx?"
                    f"guid={os.getenv('SMS_API_GUID')}&"
                    f"username={os.getenv('SMS_API_USERNAME')}&"
                    f"password={os.getenv('SMS_API_PASSWORD')}&"
                    f"countryCode=np&"
                    f"mobileNumber=%2b977{mobile_number}&"
                    f"message={message}"
                )
                response = requests.get(url)
                print(url)
                response_text = response.text

                # Determine status based on response
                if "Message received" in response_text:
                    status = 'Sent'
                elif "Invalid SMS123Go username or password" in response_text:
                    status = 'Failed: Invalid credentials'
                elif "Failed sending message" in response_text:
                    status = 'Failed: Invalid mobile number'
                else:
                    status = 'Failed: Unknown error'

                # Log the SMS
                SMSLog.objects.create(
                    mobile_number=mobile_number,
                    message=message,
                    status=status,
                    response=response_text
                )

                # Introduce a 1-second delay before sending the next SMS
                time.sleep(1)

            return redirect('sms_report')  # Redirect to reporting page after bulk SMS
    else:
        form = BulkSMSForm()

    return render(request, 'send_bulk_sms.html', {'form': form})


@login_required
def sms_report(request):
    logs_list = SMSLog.objects.all().order_by('-sent_at')
    paginator = Paginator(logs_list, 20)  # Show 20 logs per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'sms_report.html', {'page_obj': page_obj})
