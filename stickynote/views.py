
from django.contrib.auth.models import User #the user DB table
from .models import Stickynote, Colour, Group, SortingPreference #DB tables
from friends.models import Friend, Collaborator, FriendRequest #DB tables
from django.utils import timezone #timezone-data

from .utility_functions import UsersAreFriends, CanEditStickynote, CanOpenStickynote, GetRandomColour #utility functions

from django.db.models import Count    #Count
from django.shortcuts import render, redirect #rendering
from django.db.models.functions import Lower #to transform to lowercase in a .filter


from random import randint #random number generator
from django.http import JsonResponse #for AJAX requessts
from django.http import HttpResponseRedirect #redirection for POST-requests
from django.contrib.auth import authenticate, login, logout #authenticate, login, and logout users
from django.contrib.auth.decorators import login_required # to require users to log in

import json #for decoding JSON strings

#REST API:
from django.shortcuts import get_object_or_404 #Nice responses
from rest_framework.views import APIView #Lets normal view return API data
from rest_framework.response import Response #Handles JSON,... responses
from rest_framework import status
from .serializers import ColourSerializer, StickynoteSerializer, UserSerializer
from rest_framework import permissions #User permissions (I.e. extra admin priviliges)

#Initial page load
@login_required
def page_load(request):
    stickies = [];
    groups = [];
    colours = [];
    sp = SortingPreference.objects.get(user=request.user)

    iGroupHeaderColourModifier = 0.75;

    if request.user.is_authenticated:
        print('!!!!!!!!!!!!!!!!NEW PAGE LOAD!!!!!!!!!!!!!!!!!!!')
        print(sp.sorting_pref)
        if sp.sorting_pref == "TITLE":
            stickies = Stickynote.objects.filter(group_id__author_id=request.user.id).order_by(Lower('title'));
            print(stickies)
            groups = Group.objects.filter(author_id=request.user.id).order_by('-cannotBeDeleted', Lower('title'));

        elif sp.sorting_pref == "DATE_CREATED":
            stickies = Stickynote.objects.filter(group_id__author_id=request.user.id).order_by('created_date');
            print(stickies)
            groups = Group.objects.filter(author_id=request.user.id).order_by('-cannotBeDeleted', '-created_date');

        elif sp.sorting_pref == "DATE_EDITED":
            stickies = Stickynote.objects.filter(group_id__author_id=request.user.id).order_by('-last_edit_date');
            print(stickies)
            groups = Group.objects.filter(author_id=request.user.id).order_by('-cannotBeDeleted', '-last_edit_date');

        #TODO: remove the if and change the first elif to if. This will have the same functionality.
        else:
            stickies = Stickynote.objects.filter(group_id__author_id=request.user.id).order_by(Lower('title'));
            print(stickies)
            groups = Group.objects.filter(author_id=request.user.id).order_by('-cannotBeDeleted', Lower('title'));

        #Get&Set the colour that most stickies in a group have.
        for group in groups:
            groupStickies = Stickynote.objects.filter(group_id=group.id);
            majorityColour = groupStickies.values("colour_id").annotate(Count("id")).order_by('-id__count');
            majorityColour = majorityColour[0] if majorityColour.count() > 0 else {'colour_id': GetRandomColour().id,'id__count': 0};

            #majorityColour = Colour.objects.get(id=majorityColour.colour_id);
            majorityColour['r'] = round(Colour.objects.get(id=majorityColour['colour_id']).r*iGroupHeaderColourModifier);
            majorityColour['g'] = round(Colour.objects.get(id=majorityColour['colour_id']).b*iGroupHeaderColourModifier);
            majorityColour['b'] = round(Colour.objects.get(id=majorityColour['colour_id']).g*iGroupHeaderColourModifier);
            majorityColour['a'] = Colour.objects.get(id=majorityColour['colour_id']).a;
            majorityColour['colour'] = Colour.objects.get(id=majorityColour['colour_id']);
            group.majorityColour = majorityColour;
        print(groups)
        colours = Colour.objects.all().order_by('name');
        print(colours)
    return render(request, 'stickynote/index.html', {'stickies': stickies, 'groups': groups, 'colours': colours, 'author_id': request.user.id})

#Gets the data of a stickynote with the given ID.
#Returns an error if no such stickynote exists
def get_sticky_by_id(request):
    if request.user.is_authenticated:
        iStickyID = request.GET.get('iStickyID',None)
        #Sticky must exist and only the author of the sticky can retrieve it
        if iStickyID == None or not CanOpenStickynote(iStickyID, request.user.id):
            return JsonResponse({'status':'false','message':"ERROR: Invalid StickynoteID passed or access denied"}, status=404)
        pSticky = Stickynote.objects.get(id=iStickyID);

        data = {
            'title':            pSticky.title,
            'contents':         pSticky.contents,
            'created_date':     pSticky.created_date,
            'last_edit_date':   pSticky.last_edit_date,
            'shared':           pSticky.shared,
            'colour_id':        pSticky.colour_id,
            'group_id':         pSticky.group_id,
            'group_is_shared':  Group.objects.get(id=pSticky.group_id).shared if Group.objects.filter(id=pSticky.group_id).exists() else False,
            'can_edit':         CanEditStickynote(iStickyID, request.user.id),
        }
        return JsonResponse(data)
    return JsonResponse({'status':'false','message':"ERROR: Not Logged in, so nothing to retrieve"}, status=401)

#Gets the data of a Colour with the given ID.
#Returns an error if no such colour exists
def get_colour_by_id(request):
    iColourID = request.GET.get('iColourID',None)
    if iColourID == None or not Colour.objects.filter(id=iColourID).exists():
        return JsonResponse({'status':'false','message':"ERROR: Invalid ColourID passed"}, status=404)

    pColour = Colour.objects.get(id=iColourID);

    data = {
        'name':     pColour.name,
        'r':        pColour.r,
        'g':        pColour.g,
        'b':        pColour.b,
        'a':        pColour.a,
        'filename': pColour.filename,
    }
    return JsonResponse(data)

#
#
def set_or_create_sticky_by_id(request, *args, **kwargs):
    #Must be logged in (otherwise there's nowhere to save to)
    if request.user.is_authenticated:
        sTitle = request.POST.get('title', '');
        sContents = request.POST.get('contents', '');
        iColour = request.POST.get('colour', -1);
        iColour = Colour.objects.get(id=iColour).id if Colour.objects.filter(id=iColour).exists() else Colour.objects.order_by('id')[0].id

        iGroup = request.POST.get('group', -1);
        iGroup = Group.objects.get(id=iGroup).id if Group.objects.filter(id=iGroup).exists() else Group.objects.filter(cannotBeDeleted=True,author_id=request.user.id).order_by('id')[0].id
        bShared = request.POST.get('shared', False) == 'true';

        iID = request.POST.get('id', -1)
        if Stickynote.objects.filter(id=iID).exists():
            #Already Exists: so we update it
            pSticky = Stickynote.objects.get(id=iID)

            #Sanity check. No wiping other user's stickies (this should never happen)
            if Stickynote.objects.filter(id=iID, group_id__author_id=request.user.id).count() <= 0: return HttpResponseRedirect('') #FAILED

            pSticky.title = sTitle;
            pSticky.contents = sContents;
            pSticky.colour = Colour.objects.get(id=iColour);
            pSticky.group = Group.objects.get(id=iGroup);
            pSticky.shared = bShared;
            pSticky.last_edit_date = timezone.now()

            pSticky.save()
        else:
            #Does not yet exist: so we create a new one
            Stickynote.objects.create(title=sTitle, contents=sContents, created_date=timezone.now(), shared=bShared, colour_id=iColour, group_id=iGroup);
        return HttpResponseRedirect('/'); #SUCCESSFUL
    return HttpResponseRedirect('') #FAILED


#Delete a single sticky from the DB (with a given id)
def delete_sticky_by_id(request, *args, **kwargs):
    if request.user.is_authenticated:
        iID = request.POST.get('id', -1)
        #the given ID should actually exist and MUST be of the currently logged in user (no wiping other's stickies!)
        if Stickynote.objects.filter(id=iID,group_id__author_id=request.user.id).exists():
            Stickynote.objects.get(id=iID,group_id__author_id=request.user.id).delete();
            return HttpResponseRedirect('/'); #SUCCESSFUL
    return HttpResponseRedirect('') #FAILED


#get a random sticky colour from those in the DB and send it back via AJAX
def get_random_colour(request):
    pRandomColour = GetRandomColour();

    data = {
        'id':       pRandomColour.id,
        'name':     pRandomColour.name,
        'r':        pRandomColour.r,
        'g':        pRandomColour.g,
        'b':        pRandomColour.b,
        'a':        pRandomColour.a,
        'filename': pRandomColour.filename,
    }
    print(data)
    return JsonResponse(data)

'''
#Get all stickynote colours (and their RGB-values from the DB)
def retrieve_sticky_colours(request):
    #create an empty array
    colourlist = [];
    #populate it with the colournames
    for colour in Colour.objects.all().order_by('name'):
        colourlist.append([colour.id, colour.name.lower(), colour.r, colour.g, colour.b, colour.a/255]);
    print(colourlist)
    return JsonResponse({"colourlist": colourlist})
'''

#Check if the entered password and username are correct. If yes, login
def user_login(request, *args, **kwargs):
    username = request.POST.get('username', None)
    password = request.POST.get('password', None)

    if username and password and User.objects.filter(username__iexact=username).exists():
        user = User.objects.get(username=username)

        user = authenticate(username=username, password=password)
        login(request, user)
        print(str(username) + " just logged in!");
        return HttpResponseRedirect('/') #redirect to nothing (but we still need to return something in order to fire the success() function)
    else:
        return HttpResponseRedirect('') #redirect to nothing (ajax fail function fires too)

#Log the current user out
def user_logout(request):
    print('someone just logged out')
    logout(request);
    return HttpResponseRedirect('/');

#returns true if the client is authenticated (I.e. logged in). returns false otherwise
def user_is_authenticated(request):
    if request.user.is_authenticated:
        return JsonResponse({'authenticated': True})
    return JsonResponse({'authenticated': False})

################################################################################
#Groups:

#Gets the data of a Group with the given ID.
#Returns an error if no such group exists
def get_group_by_id(request):
    iGroupID = request.GET.get('iGroupID',None)
    if iGroupID == None or not Group.objects.filter(id=iGroupID, author_id=request.user.id).exists():
        return JsonResponse({'status':'false','message':"ERROR: Invalid GroupID passed or no access to group data"}, status=404)

    pGroup = Group.objects.get(id=iGroupID);

    data = {
        'title':            pGroup.title,
        'shared':           pGroup.shared,
        'created_date':     pGroup.created_date,
        'last_edit_date':   pGroup.last_edit_date,
        'cannotBeDeleted':  pGroup.cannotBeDeleted,
    }
    return JsonResponse(data)

#
#
def set_or_create_group_by_id(request, *args, **kwargs):
    #Must be logged in (otherwise there's nowhere to save to)
    if request.user.is_authenticated:
        sTitle = request.POST.get('title', None);
        bShared = request.POST.get('shared', None);

        iID = request.POST.get('id', -1)
        if Group.objects.filter(id=iID).exists():
            #Already Exists: so we update it
            pGroup = Group.objects.get(id=iID)

            #Sanity check. No wiping other user's groups (this should never happen)
            if Group.objects.filter(id=iID, author_id=request.user.id).count() <= 0: return HttpResponseRedirect('') #FAILED

            pGroup.title = sTitle if sTitle != None else pGroup.title; #only update if we can update
            pGroup.shared = bShared == 'true' if bShared else pGroup.shared;
            pGroup.last_edit_date = timezone.now();

            pGroup.save()
        else:
            #Does not yet exist: so we create a new one
            Group.objects.create(title=sTitle, created_date=timezone.now(), shared=bShared=='true', author_id=request.user.id, cannotBeDeleted=False);
        return HttpResponseRedirect('/'); #SUCCESSFUL
    return HttpResponseRedirect('') #FAILED


#Delete a single group from the DB (with a given id).
#WARNING: Also deletes ALL stickies associated with this Group!
def delete_group_by_id(request, *args, **kwargs):
    if request.user.is_authenticated:
        iID = request.POST.get('id', -1)
        #the given ID should actually exist and MUST be of the currently logged in user (no wiping other's groups/stickies!)
        if Group.objects.filter(id=iID,author_id=request.user.id).exists():
            pGroup = Group.objects.get(id=iID,author_id=request.user.id);
            #Non-deletable groups cannot be deleted (outside of the admin-panel)
            if not pGroup.cannotBeDeleted:
                #Delete all stickies in this group first
                tStickies = Stickynote.objects.filter(group_id=iID);

                for sticky in tStickies:
                    sticky.delete();

                #Actually Delete the Group
                pGroup.delete();

                return HttpResponseRedirect('/'); #SUCCESSFUL
    return HttpResponseRedirect('') #FAILED
################################################################################
#REST API

#host/stickies/
class StickynoteList(APIView):
    '''Lists all Stickynotes'''
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get(self, request): #GET requessts
        stickies = Stickynote.objects.all()
        serializer = StickynoteSerializer(stickies, many=True)
        return Response(serializer.data)

#host/stickies/id
class StickynoteDetails(APIView):
    '''Data of a specific Stickynote'''
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get_object(self, id):
        try:
            return Stickynote.objects.get(id=id)
        except Stickynote.DoesNotExist:
            raise Http404

    def get(self, request, id, format=None):
        stickynote = self.get_object(id)
        serializer = StickynoteSerializer(stickynote)
        return Response(serializer.data)

#host/stickies/user/author_id
class StickynoteAuthorList(APIView):
    '''Lists all stickynotes of a specific User'''
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get(self, request, author_id, format=None): #GET requessts
        stickies = Stickynote.objects.filter(author_id=author_id)
        serializer = StickynoteSerializer(stickies, many=True)
        return Response(serializer.data)

#host/colours/
class ColourList(APIView):
    '''Lists all Colours'''
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get(self, request, format=None): #GET requessts
        colours = Colour.objects.all()
        serializer = ColourSerializer(colours, many=True)
        return Response(serializer.data)

#host/colours/id/
class ColourDetails(APIView):
    '''Data of a specific Colour'''
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get_object(self, id):
        try:
            return Colour.objects.get(id=id)
        except Colour.DoesNotExist:
            raise Http404

    def get(self, request, id, format=None):
        colour = self.get_object(id)
        serializer = ColourSerializer(colour)
        return Response(serializer.data)

#host/colours/
class UserList(APIView):
    '''Lists all Users'''
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get(self, request, format=None): #GET requessts
        colours = User.objects.all()
        serializer = UserSerializer(colours, many=True)
        return Response(serializer.data)

#host/user/id/
class UserDetails(APIView):
    '''Data of a specific User'''
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get_object(self, id):
        try:
            return User.objects.get(id=id)
        except User.DoesNotExist:
            raise Http404

    def get(self, request, id, format=None):
        user = self.get_object(id)
        serializer = UserSerializer(user)
        return Response(serializer.data)

################################################################################
#Sorting Preference

#Set sorting preference to TITLE
def set_sorting_pref_to_title(request):
    sp = SortingPreference.objects.get(user=request.user)
    if request.method == "POST":
        sp.sorting_pref = "TITLE"
        sp.save()
        return redirect('stickynote:page_load')

#Set sorting preference to DATE_EDITED
def set_sorting_pref_to_edited(request):
    sp = SortingPreference.objects.get(user=request.user)
    if request.method == "POST":
        sp.sorting_pref = "DATE_EDITED"
        sp.save()
        return redirect('stickynote:page_load')

#Set sorting preference to DATE_CREATED
def set_sorting_pref_to_created(request):
    sp = SortingPreference.objects.get(user=request.user)
    if request.method == "POST":
        sp.sorting_pref = "DATE_CREATED"
        sp.save()
        return redirect('stickynote:page_load')



#there's a comment here as atom keeps removing empty lines at the end of a file
