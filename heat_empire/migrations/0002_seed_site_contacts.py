from django.db import migrations


def seed_site_contacts(apps, schema_editor):
    site_contacts = apps.get_model("heat_empire", "SiteContacts")
    site_contacts.objects.using(schema_editor.connection.alias).get_or_create(
        pk=1,
        defaults={
            "phone": "+7 (924) 131-71-30",
            "address": "г. Санкт-Петербург, г. Колпино,\nул. Анисимова, 5 корпус 2, лит. А, пом. 6Н",
        },
    )


class Migration(migrations.Migration):
    dependencies = [("heat_empire", "0001_initial")]
    operations = [migrations.RunPython(seed_site_contacts, migrations.RunPython.noop)]
