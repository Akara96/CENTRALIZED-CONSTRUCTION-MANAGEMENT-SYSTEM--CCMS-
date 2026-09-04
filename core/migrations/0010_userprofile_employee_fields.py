from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_chatroom_created_by_chatroom_is_public'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='employee_id',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='division',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='status',
            field=models.CharField(blank=True, default='Active', max_length=30, null=True),
        ),
    ]
