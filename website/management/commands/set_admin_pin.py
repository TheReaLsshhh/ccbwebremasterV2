from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from website.models import StaffSecurityProfile


class Command(BaseCommand):
    help = "Set or reset the 6-digit admin PIN for a staff user."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Django username (superuser/staff account)")
        parser.add_argument("pin", help="New 6-digit PIN")

    def handle(self, *args, **options):
        username = options["username"].strip()
        pin = options["pin"].strip()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f'User "{username}" does not exist.') from exc

        if not user.is_staff:
            raise CommandError(f'User "{username}" is not a staff account.')

        is_valid, result = StaffSecurityProfile.validate_pin_format(pin)
        if not is_valid:
            raise CommandError(result)

        profile, _ = StaffSecurityProfile.objects.get_or_create(user=user)
        profile.set_pin(result)
        self.stdout.write(self.style.SUCCESS(f'Admin PIN updated for "{username}".'))
