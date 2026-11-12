from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("heat_empire", "0009_seed_heat_pump_catalog")]

    operations = [migrations.RenameModel(old_name="HeatPump", new_name="HeatingProduct")]
