from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Client


@receiver(post_save, sender=User)
def create_default_client_profile(sender, instance, created, **kwargs):
    if not created:
        return

    client_group, _ = Group.objects.get_or_create(name="Client")
    instance.groups.add(client_group)

    Client.objects.get_or_create(
        user=instance,
        defaults={
            "full_name": instance.get_full_name() or instance.username,
            "first_name": instance.first_name or "",
            "last_name": instance.last_name or "",
            "timezone": "Europe/Minsk",
        },
    )


@receiver(post_save, sender=User)
def save_related_profile(sender, instance, **kwargs):
    if hasattr(instance, "client_profile"):
        instance.client_profile.save()
    if hasattr(instance, "employee_profile"):
        instance.employee_profile.save()
