# Generated by Django 4.2.14 on 2025-02-16 20:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viewmaster', '0004_alter_movie_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movie',
            name='cost',
            field=models.DecimalField(decimal_places=2, help_text='In USD.', max_digits=5),
        ),
    ]
