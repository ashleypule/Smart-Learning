# Generated by Django 4.2.16 on 2024-10-14 06:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0008_content_quizquestion'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='performance',
            name='user',
        ),
        migrations.RemoveField(
            model_name='quiz',
            name='question',
        ),
        migrations.RemoveField(
            model_name='quizquestion',
            name='content',
        ),
        migrations.DeleteModel(
            name='Content',
        ),
        migrations.DeleteModel(
            name='Performance',
        ),
        migrations.DeleteModel(
            name='Quiz',
        ),
        migrations.DeleteModel(
            name='QuizQuestion',
        ),
    ]
