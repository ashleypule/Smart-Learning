# Generated by Django 4.2.16 on 2024-09-19 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0003_alter_grade_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='subject',
            name='topic',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
