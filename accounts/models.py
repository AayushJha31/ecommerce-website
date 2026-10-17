from django.db import models
from django.contrib.auth.models import User
from base.models import BaseModel
from django.db.models.signals import post_save
from django.dispatch import receiver
from base.emails import send_account_verification_email
import uuid
import logging


logger = logging.getLogger(__name__)


class Profile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_email_verified = models.BooleanField(default=False)
    email_token = models.CharField(max_length=100, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile')


def send_profile_verification_email(profile):
    email_token = str(uuid.uuid4())
    profile.email_token = email_token
    profile.save(update_fields=['email_token'])
    try:
        send_account_verification_email(profile.user.email, email_token)
    except Exception:
        profile.email_token = None
        profile.save(update_fields=['email_token'])
        raise


@receiver(post_save, sender=User)
def send_email_token(sender, instance, created, **kwargs):
    try:
        if created:
            profile, _ = Profile.objects.get_or_create(user=instance)
            send_profile_verification_email(profile)

    except Exception as e:
        logger.exception('Unable to send account verification email: %s', e)
