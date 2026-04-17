from django.db import models
import uuid

# Create your models here.

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    gender = models.CharField(max_length=50)
    gender_probability = models.FloatField()
    sample_size = models.IntegerField()
    age = models.IntegerField()
    age_group = models.CharField(max_length=50)
    country_id = models.CharField(max_length=10)
    country_probability = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'profiles'

    def to_dict(self, full=True):
        data = {
            'id': str(self.id),
            'name': self.name,
            'gender': self.gender,
            'age': self.age,
            'age_group': self.age_group,
            'country_id': self.country_id,
        }
        if full:
            data.update({
                'gender_probability': self.gender_probability,
                'sample_size': self.sample_size,
                'country_probability': self.country_probability,
                'created_at': self.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
            })
        return data