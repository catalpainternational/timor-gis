from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("timor_locations", "0008_recode_pcode_to_intl"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProviderCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scheme", models.CharField(choices=[("estrada", "Estrada (legacy integer codes)"), ("intl2024", "INTL / PNDS 2024 (New*Cod)")], max_length=32)),
                ("code", models.CharField(max_length=16)),
                ("name", models.CharField(blank=True, max_length=100)),
                ("relation", models.CharField(choices=[("matched", "Same entity, re-coded"), ("rename", "Same entity, renamed"), ("new", "Introduced by this scheme; no prior code"), ("removed", "In a prior scheme; gone here"), ("split", "One prior entity became several"), ("merge", "Several prior entities became one")], default="matched", max_length=12)),
                ("score", models.FloatField(blank=True, null=True)),
                ("note", models.CharField(blank=True, max_length=200)),
                ("object_id", models.CharField(max_length=12)),
                ("content_type", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="contenttypes.contenttype")),
            ],
        ),
        migrations.AddIndex(
            model_name="providercode",
            index=models.Index(fields=["content_type", "object_id"], name="timor_loc_content_obj_idx"),
        ),
        migrations.AddIndex(
            model_name="providercode",
            index=models.Index(fields=["scheme", "code"], name="timor_loc_scheme_code_idx"),
        ),
        migrations.AddConstraint(
            model_name="providercode",
            constraint=models.UniqueConstraint(
                condition=models.Q(relation__in=["matched", "rename", "new"]),
                fields=["scheme", "code"],
                name="uniq_scheme_code_1to1",
            ),
        ),
    ]
