from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Visitor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ip_address", models.GenericIPAddressField(db_index=True)),
                ("user_agent", models.TextField(blank=True)),
                ("visited_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"ordering": ["-visited_at"]},
        ),
    ]
