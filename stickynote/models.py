from django.db import models
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator

#to save user preference of sorting stickies
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

#Stickynote entry (yes, most of this is unused (or not displayed to the user), though it could be used in A3)
class Stickynote(models.Model):
    #1-to-many relation with a Group (which has an author field), so it's not neccesary here
    '''
    author = models.ForeignKey(
            'auth.User',
            on_delete=models.CASCADE,
            )
    '''
    title = models.CharField(max_length=200)
    contents = models.TextField()
    created_date = models.DateTimeField(
            default=timezone.now)
    last_edit_date = models.DateTimeField(
            blank=True, null=True, default=timezone.now)
    colour = models.ForeignKey(
            'Colour',
            on_delete=models.CASCADE,
            )
    group = models.ForeignKey(
            'Group',
            on_delete=models.CASCADE,
            default = 1,
    )
    shared = models.BooleanField()

    def create(self):
        self.created_date = timezone.now()
        self.save()

    def save_edits(self):
        self.last_edit_date = timezone.now()
        self.save()

    def __str__(self):
        return self.title

#Colour entry
class Colour(models.Model):
    name = models.CharField(max_length=20)
    r = models.IntegerField(
            default=0,
            validators=[MaxValueValidator(255), MinValueValidator(0)],
    )
    g = models.IntegerField(
            default=0,
            validators=[MaxValueValidator(255), MinValueValidator(0)],
    )
    b = models.IntegerField(
            default=0,
            validators=[MaxValueValidator(255), MinValueValidator(0)],
    )
    a = models.IntegerField(
            default=255,
            validators=[MaxValueValidator(255), MinValueValidator(0)],
    )
    filename = models.CharField(
            default = "stickynote_yellow.png", #files must be locaeted in STATIC/Images/
            max_length = 40,
    )

    def __str__(self):
        return self.name

#Stickynote Group Entry
class Group(models.Model):
    author = models.ForeignKey(
            'auth.User',
            on_delete=models.CASCADE,
            )
    title = models.CharField(max_length=200)
    created_date = models.DateTimeField( #Creation Date
            default=timezone.now)
    last_edit_date = models.DateTimeField( #Last date something was added/removed from this group
            blank=True, null=True, default=timezone.now)
    shared = models.BooleanField()
    cannotBeDeleted = models.BooleanField(default=False)

    def create(self):
        self.created_date = timezone.now()
        self.save()

    def save_edits(self):
        self.last_edit_date = timezone.now()
        self.save()

    def __str__(self):
        return (self.title + " (" + self.author.username + ")")


#to save user preference of sorting stickies
class SortingPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    sorting_pref = models.CharField(max_length=30, default="TITLE")

@receiver(post_save, sender=User)
def create_sorting_pref(sender, instance, created, **kwargs):
    if created:
        SortingPreference.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_sorting_pref(sender, instance, **kwargs):
    instance.sortingpreference.save()