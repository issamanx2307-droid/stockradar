from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("radar", "0016_profile_can_use_portfolio"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(verbose_name="ข้อความ")),
                ("is_read", models.BooleanField(db_index=True, default=False, verbose_name="อ่านแล้ว")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("sender", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="sent_chat_msgs",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="ผู้ส่ง",
                )),
                ("receiver", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="recv_chat_msgs",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="ผู้รับ",
                )),
            ],
            options={
                "verbose_name": "ข้อความแชท",
                "verbose_name_plural": "ข้อความแชท",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="chatmessage",
            index=models.Index(
                fields=["sender", "receiver", "created_at"],
                name="idx_chat_convo",
            ),
        ),
    ]
