from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("radar", "0013_latestsnapshot"),
    ]

    operations = [
        migrations.AlterField(
            model_name="newsitem",
            name="url",
            field=models.URLField(max_length=2048, unique=True, verbose_name="ลิงก์ข่าว"),
        ),
    ]
