# Generated by Django 5.0.1 on 2024-02-07 19:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('arvore', '0012_userprofile_cidade_userprofile_estado_doacaoavulso_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='doacaoavulso',
            name='quantidade_total',
        ),
    ]
