# Generated by Django 5.0.1 on 2024-01-12 19:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('arvore', '0007_efetivardoacao_data_efetivacao_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='efetivardoacao',
            name='observacoes',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]