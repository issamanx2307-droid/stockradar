from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("radar", "0018_sitesetting_chatmessage_is_ai_response"),
    ]

    operations = [
        migrations.CreateModel(
            name="AlpacaOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("symbol", models.CharField(max_length=20, verbose_name="หุ้น")),
                ("side", models.CharField(choices=[("buy", "Buy"), ("sell", "Sell")], max_length=4, verbose_name="ทิศทาง")),
                ("qty", models.DecimalField(decimal_places=4, max_digits=12, verbose_name="จำนวนหุ้น")),
                ("order_type", models.CharField(choices=[("market", "Market"), ("limit", "Limit")], default="market", max_length=10, verbose_name="ประเภท Order")),
                ("limit_price", models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True, verbose_name="ราคา Limit")),
                ("status", models.CharField(choices=[("pending_confirm", "รอยืนยัน"), ("submitted", "ส่งแล้ว"), ("filled", "สำเร็จ"), ("cancelled", "ยกเลิก"), ("rejected", "ถูกปฏิเสธ")], default="pending_confirm", max_length=20, verbose_name="สถานะ")),
                ("alpaca_order_id", models.CharField(blank=True, max_length=100, verbose_name="Alpaca Order ID")),
                ("ai_reasoning", models.TextField(blank=True, verbose_name="เหตุผลที่ AI เสนอ")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="สร้างเมื่อ")),
                ("confirmed_at", models.DateTimeField(blank=True, null=True, verbose_name="ยืนยันเมื่อ")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alpaca_orders", to=settings.AUTH_USER_MODEL, verbose_name="ผู้ใช้")),
            ],
            options={
                "verbose_name": "Alpaca Order",
                "verbose_name_plural": "Alpaca Orders",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["user", "status"], name="radar_alpac_user_id_idx"),
                    models.Index(fields=["alpaca_order_id"], name="radar_alpac_alpaca__idx"),
                ],
            },
        ),
    ]
