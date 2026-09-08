#!/usr/bin/env python
import os
import sys

# Ensure Django environment is configured
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django
django.setup()

from apps.core.management.commands.it_domain_demo_data import Command

if __name__ == "__main__":
    Command().handle()
