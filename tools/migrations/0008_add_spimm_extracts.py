# Generated by Django 3.2.16 on 2023-11-28 13:44

from django.db import migrations
from django.db.migrations import RunPython

from core.utils import insert_role_right_for_system, remove_role_right_for_system


SYSTEM_ROLE = 64
SPIMM_RIGHT = 131011


def add_rights(apps, schema_editor):
    insert_role_right_for_system(SYSTEM_ROLE, SPIMM_RIGHT)


def remove_rights(apps, schema_editor):
    remove_role_right_for_system(SYSTEM_ROLE, SPIMM_RIGHT)


class Migration(migrations.Migration):

    dependencies = [
        ('tools', '0007_set_managed_to_true'),
    ]

    operations = [
        migrations.RunPython(add_rights, remove_rights),
    ]
