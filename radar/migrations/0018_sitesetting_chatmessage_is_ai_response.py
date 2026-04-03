from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("radar", "0017_chatmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="is_ai_response",
            field=models.BooleanField(default=False, verbose_name="ตอบโดย AI"),
        ),
        migrations.CreateModel(
            name="SiteSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ai_chat_enabled", models.BooleanField(
                    default=False,
                    verbose_name="เปิดใช้ AI ในแชท",
                    help_text="เมื่อเปิด ระบบจะตอบแชทผู้ใช้โดยอัตโนมัติด้วย Claude AI",
                )),
            ],
            options={
                "verbose_name": "ตั้งค่าระบบ",
                "verbose_name_plural": "ตั้งค่าระบบ",
            },
        ),
    ]
