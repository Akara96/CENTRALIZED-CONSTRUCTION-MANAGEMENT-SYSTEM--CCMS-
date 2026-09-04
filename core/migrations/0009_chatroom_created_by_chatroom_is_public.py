# Generated manually for chat room fields used by the chat views.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0008_chatroom_chatmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatroom',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_chat_rooms',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='chatroom',
            name='is_public',
            field=models.BooleanField(default=False),
        ),
    ]
