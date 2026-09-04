from django.apps import apps
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import UserProfile


EMPLOYEES = [
    {
        'employee_id': 'DL-EMP-001',
        'name': 'Lamberto Miranda',
        'position': 'Director/General Manager',
        'division': 'Executive',
        'phone': '67077247612',
        'email': 'dlekibo@gmail.com',
        'status': 'Active',
        'role': 'HQ_DIRECTOR',
        'is_staff': True,
        'is_superuser': True,
    },
    {
        'employee_id': 'DL-EMP-002',
        'name': 'Apolito Munuasa',
        'position': 'Lead Architect',
        'division': 'Consultant',
        'phone': '67075503195',
        'email': 'healerapolito@gmail.com',
        'status': 'Active',
        'role': 'CONSULTANT',
    },
    {
        'employee_id': 'DL-EMP-003',
        'name': 'Ricardo Amadeu',
        'position': 'General Admin/Finance',
        'division': 'Admin/Finance',
        'phone': '',
        'email': '',
        'status': 'Active',
        'role': 'FINANCE_HQ',
        'is_staff': True,
    },
    {
        'employee_id': 'DL-EMP-004',
        'name': 'Dony Martha, AMd.',
        'position': 'Project Manager',
        'division': 'Engineering',
        'phone': '',
        'email': '',
        'status': 'Active',
        'role': 'PROJECT_MANAGER',
    },
    {
        'employee_id': 'DL-EMP-005',
        'name': 'Lucio Belino Guterres',
        'position': 'Site Engineer',
        'division': 'Engineering',
        'phone': '',
        'email': '',
        'status': 'Active',
        'role': 'SITE_ENGINEER',
    },
    {
        'employee_id': 'DL-EMP-006',
        'name': 'Alu Yesus',
        'position': 'Plumber Technician',
        'division': 'Skill Worker',
        'phone': '',
        'email': '',
        'status': 'Active',
        'role': 'SUPERVISOR',
    },
    {
        'employee_id': 'DL-EMP-007',
        'name': 'Sumarto',
        'position': 'Foreman / Concrete Work',
        'division': 'Skill Worker',
        'phone': '',
        'email': '',
        'status': 'Active',
        'role': 'SUPERVISOR',
    },
    {
        'employee_id': 'DL-EMP-008',
        'name': 'Estevao da Costa',
        'position': 'Carpenter / Formwork',
        'division': 'Skill Worker',
        'phone': '',
        'email': '',
        'status': 'Active',
        'role': 'SUPERVISOR',
    },
    {
        'employee_id': 'DL-EMP-009',
        'name': 'Antonio T. Alves',
        'position': 'M&E Technician',
        'division': 'Skill Worker',
        'phone': '',
        'email': '',
        'status': 'Active',
        'role': 'SUPERVISOR',
    },
    {
        'employee_id': 'DL-EMP-010',
        'name': 'Sumantri Yuwno',
        'position': 'Welder / Fabrication',
        'division': 'Skill Worker',
        'phone': '',
        'email': '',
        'status': 'Active',
        'role': 'SUPERVISOR',
    },
    {
        'employee_id': 'DL-EMP-011',
        'name': 'Evangelito da Silva',
        'position': 'Welder/Fabrication',
        'division': 'Skill Worker',
        'phone': '',
        'email': '',
        'status': 'Active',
        'role': 'SUPERVISOR',
    },
    {
        'employee_id': 'DL-EMP-012',
        'name': 'Octaviano Calucho Soares',
        'position': 'Carpenter / Formwork',
        'division': 'Skill Worker',
        'phone': '',
        'email': '',
        'status': 'Active',
        'role': 'SUPERVISOR',
    },
]


class Command(BaseCommand):
    help = 'Replace old CCMS users with the employee user list.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default='CCMS@2026',
            help='Default password assigned to all imported users.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password']
        employee_ids = [employee['employee_id'] for employee in EMPLOYEES]

        created_users = {}
        for employee in EMPLOYEES:
            first_name, last_name = self._split_name(employee['name'])
            user, _ = User.objects.update_or_create(
                username=employee['employee_id'],
                defaults={
                    'email': employee['email'],
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_active': employee['status'].lower() == 'active',
                    'is_staff': employee.get('is_staff', False),
                    'is_superuser': employee.get('is_superuser', False),
                },
            )
            user.set_password(password)
            user.save()

            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'employee_id': employee['employee_id'],
                    'role': employee['role'],
                    'phone': employee['phone'],
                    'position': employee['position'],
                    'division': employee['division'],
                    'status': employee['status'],
                },
            )
            created_users[employee['employee_id']] = user

        fallback_user = created_users['DL-EMP-001']
        old_users = User.objects.exclude(username__in=employee_ids)
        old_user_ids = list(old_users.values_list('id', flat=True))

        reassigned = 0
        if old_user_ids:
            for model in apps.get_models():
                for field in model._meta.fields:
                    remote = getattr(field, 'remote_field', None)
                    if not remote or remote.model is not User:
                        continue
                    if model is UserProfile:
                        continue
                    updated = model.objects.filter(**{f'{field.name}_id__in': old_user_ids}).update(
                        **{field.name: fallback_user}
                    )
                    reassigned += updated

            for model in apps.get_models():
                for field in model._meta.many_to_many:
                    remote = getattr(field, 'remote_field', None)
                    if not remote or remote.model is not User:
                        continue
                    for obj in model.objects.filter(**{f'{field.name}__id__in': old_user_ids}).distinct():
                        getattr(obj, field.name).add(fallback_user)

        deleted_count, _ = old_users.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Imported {len(created_users)} employee users. "
            f"Reassigned {reassigned} user references. "
            f"Deleted {deleted_count} old related user records. "
            f"Default password: {password}"
        ))

    def _split_name(self, full_name):
        parts = full_name.split()
        if not parts:
            return '', ''
        if len(parts) == 1:
            return parts[0], ''
        return parts[0], ' '.join(parts[1:])
