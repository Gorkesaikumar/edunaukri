import os
import sys

# Ensure Django environment is configured
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django
django.setup()

from apps.core.management.commands.faculty_domain_demo_data_delete import Command

if __name__ == "__main__":
    cmd = Command()
    cmd.handle()
