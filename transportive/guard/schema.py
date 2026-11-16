"""guard/schema.py: guards as a Django migration."""
OPS = {   # a CHECK can start NOT VALID, a unique index cannot
    "check": "        AddConstraintNotValid(model_name=\"{model}\", constraint=models.CheckConstraint(\n"
             "            condition=models.Q({q}), name=\"{name}\")),\n",
    "unique": "        migrations.AddConstraint(model_name=\"{model}\", constraint=models.UniqueConstraint(\n"
              "            fields={fields!r}, condition=models.Q({q}), name=\"{name}\")),\n",
}


def name(rule):
    return f"guard_{rule.id.replace('.', '_').replace('-', '_').lower()}"


def migration(rules, after):
    # NOT VALID: new writes checked, old rows later
    ops = "".join(OPS[r.db["guard"]].format(name=name(r), **r.db) for r in rules if r.db)
    return ("from django.contrib.postgres.operations import AddConstraintNotValid\nfrom django.db import migrations, models"
            f"\n\n\nclass Migration(migrations.Migration):\n    dependencies = [(\"payment\", \"{after}\")]\n"
            f"    operations = [\n{ops}    ]\n")
