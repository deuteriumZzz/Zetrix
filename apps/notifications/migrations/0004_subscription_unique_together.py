from django.db import migrations


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('notifications', '0003_alter_subscription_options_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='subscription',
            unique_together={('user', 'country', 'region', 'market_type')},
        ),
    ]
