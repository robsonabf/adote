# Generated by Django 5.0.1 on 2024-02-07 18:07

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('arvore', '0011_userprofile_email'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='cidade',
            field=models.CharField(default=1, max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='userprofile',
            name='estado',
            field=models.CharField(default=1, max_length=100),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='DoacaoAvulso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome_completo', models.CharField(max_length=150)),
                ('endereco', models.CharField(max_length=300)),
                ('cidade', models.CharField(max_length=100)),
                ('estado', models.CharField(max_length=100)),
                ('telefone', models.CharField(max_length=20)),
                ('quantidade_total', models.IntegerField()),
                ('data_plantio', models.DateTimeField(blank=True, null=True)),
                ('data_adocao', models.DateTimeField(blank=True, null=True)),
                ('local_de_plantio', models.CharField(max_length=200)),
                ('observacoes', models.CharField(blank=True, max_length=200, null=True)),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EspecieQuantidade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('especie', models.TextField()),
                ('quantidade', models.IntegerField()),
                ('doacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='arvore.doacaoavulso')),
            ],
        ),
    ]