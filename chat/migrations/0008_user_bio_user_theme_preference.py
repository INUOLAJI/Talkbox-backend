from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('chat', '0007_room_profile_picture_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='bio',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='user',
            name='theme_preference',
            field=models.CharField(choices=[('light', 'Light'), ('dark', 'Dark')], default='light', max_length=20),
        ),
    ]
