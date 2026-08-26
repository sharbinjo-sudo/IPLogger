from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0002_dedupe_unique_visitor_ip"),
    ]

    operations = [
        migrations.AddField(
            model_name="visitor",
            name="connection_ip",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
    ]
