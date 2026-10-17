from django.conf import settings
from django.core.mail import send_mail

def send_account_verification_email(email, email_token):
  subject = 'Your account needs to be verified'
  email_from = settings.DEFAULT_FROM_EMAIL
  message = f'Please click the following link to verify your account: {settings.SITE_URL}/accounts/activate/{email_token}'

  send_mail(subject, message, email_from, [email])