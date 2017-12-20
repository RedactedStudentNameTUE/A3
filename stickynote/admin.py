from django.contrib import admin
from .models import Stickynote, Colour

#The model registered in admin.site.register(..) can be either a single
#model or an iteratble list

myModels = [Stickynote,Colour]
admin.site.register(myModels)
