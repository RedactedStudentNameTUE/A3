# Generated by Django 2.0 on 2018-01-14 21:26

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('stickynote', '0009_sortingpreference'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='last_edit_date',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True),
        ),
        migrations.AlterField(
            model_name='stickynote',
            name='last_edit_date',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True),
        ),
    ]