from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('radar', '0015_fundamentalsnapshot'),
    ]
    operations = [
        migrations.AddField(
            model_name='profile',
            name='can_use_portfolio',
            field=models.BooleanField(default=False, verbose_name='เข้าใช้ Portfolio ได้'),
        ),
    ]
