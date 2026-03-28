from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('radar', '0014_merge_20260327_0929'),
    ]

    operations = [
        migrations.CreateModel(
            name='FundamentalSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pe_ratio', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('pb_ratio', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('market_cap', models.BigIntegerField(null=True)),
                ('roe', models.DecimalField(decimal_places=2, max_digits=8, null=True)),
                ('roa', models.DecimalField(decimal_places=2, max_digits=8, null=True)),
                ('net_margin', models.DecimalField(decimal_places=2, max_digits=8, null=True)),
                ('revenue_growth', models.DecimalField(decimal_places=2, max_digits=8, null=True)),
                ('earnings_growth', models.DecimalField(decimal_places=2, max_digits=8, null=True)),
                ('debt_to_equity', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('current_ratio', models.DecimalField(decimal_places=2, max_digits=8, null=True)),
                ('dividend_yield', models.DecimalField(decimal_places=2, max_digits=8, null=True)),
                ('vi_score', models.DecimalField(decimal_places=2, max_digits=6, null=True)),
                ('vi_grade', models.CharField(max_length=2, null=True)),
                ('fetched_at', models.DateTimeField(auto_now=True)),
                ('symbol', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='fundamental_snapshot',
                    to='radar.symbol',
                )),
            ],
            options={
                'verbose_name': 'Fundamental Snapshot',
                'verbose_name_plural': 'Fundamental Snapshots',
            },
        ),
    ]
