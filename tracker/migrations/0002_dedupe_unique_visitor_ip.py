from django.db import migrations, models


def keep_latest_visit_per_ip(apps, schema_editor):
    Visitor = apps.get_model("tracker", "Visitor")
    duplicate_ips = (
        Visitor.objects.values_list("ip_address", flat=True)
        .order_by("ip_address")
        .distinct()
    )

    for ip_address in duplicate_ips:
        visits = Visitor.objects.filter(ip_address=ip_address).order_by("-visited_at", "-id")
        keep_id = visits.values_list("id", flat=True).first()
        if keep_id is not None:
            visits.exclude(id=keep_id).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(keep_latest_visit_per_ip, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="visitor",
            name="ip_address",
            field=models.GenericIPAddressField(db_index=True, unique=True),
        ),
    ]
