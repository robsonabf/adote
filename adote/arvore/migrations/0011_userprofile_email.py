# Generated by Django 5.0.1 on 2024-01-12 20:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('arvore', '0010_userprofile_delete_perfilusuario'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email',
            field=models.EmailField(default=1, max_length=254),
            preserve_default=False,
        ),
    ]