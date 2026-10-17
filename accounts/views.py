from django.shortcuts import render
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from .models import Profile, send_profile_verification_email
import logging


logger = logging.getLogger(__name__)

def login_page(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_obj = User.objects.filter(username=email)

        if not user_obj.exists():
            messages.error(request, 'User does not exist.')
            return HttpResponseRedirect(request.path_info)

        authenticated_user = authenticate(request, username=email, password=password)
        if authenticated_user is None:
            messages.error(request, 'Invalid email or password.')
            return HttpResponseRedirect(request.path_info)

        profile, _ = Profile.objects.get_or_create(user=authenticated_user)
        if not profile.is_email_verified:
            try:
                send_profile_verification_email(profile)
            except Exception:
                logger.exception('Unable to send verification email for user id %s', authenticated_user.pk)
                messages.error(request, 'Unable to send the verification email. Check the SMTP settings and try again.')
                return HttpResponseRedirect(request.path_info)
            messages.info(request, 'A new verification email has been sent. Please check your inbox.')
            return HttpResponseRedirect(request.path_info)

        login(request, authenticated_user)
        messages.success(request, 'Logged in successfully.')
        return HttpResponseRedirect(request.path_info)
        
    return render(request, 'accounts/login.html')


def register_page(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        user_obj = User.objects.filter(username = email)

        if user_obj.exists():
            messages.warning(request, 'User with this email already exists.')
            return HttpResponseRedirect(request.path_info)
        
        user_obj = User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=email,
            password=password
        )
        user_obj.set_password(password)
        user_obj.save()
        messages.success(request, 'User created successfully.')
        return HttpResponseRedirect(request.path_info)

    return render(request, 'accounts/register.html')


def activate_account(request, email_token):
    profile = Profile.objects.filter(email_token=email_token).first()
    if profile is None:
        messages.error(request, 'This verification link is invalid or has expired.')
        return HttpResponseRedirect('/accounts/login/')

    profile.is_email_verified = True
    profile.email_token = None
    profile.save(update_fields=['is_email_verified', 'email_token'])
    messages.success(request, 'Email verified. You can now log in.')
    return HttpResponseRedirect('/accounts/login/')