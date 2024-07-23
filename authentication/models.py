from django.db import models
from django.contrib.auth.models import AbstractUser

class Lab(models.Model):
    id = models.AutoField(primary_key=True)
    lab_name = models.CharField(max_length=100, blank=False, null=False)
    lab_url = models.CharField(max_length=250, blank=False, null=False)
    active = models.BooleanField(default = True)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = False
        db_table = 'auth_lab'
        verbose_name = 'Laboratory'
        verbose_name_plural = 'Labs'
        ordering = ['lab_name']
        
    def __str__(self):
        return f"{self.lab_name}"

class User(AbstractUser):
    lab = models.ForeignKey(Lab, models.CASCADE, null=True, blank=True, db_column="FK_lab_id", verbose_name="Primary lab")
    labs = models.ManyToManyField(Lab, related_name="labs", verbose_name="Viewable labs")

    class Meta:
        managed = False
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    
    
    
