from django.http import JsonResponse
from django.views.generic import TemplateView
from django.conf import settings
from authentication.models import User


class SessionVarView(TemplateView):

    def get(self, request, *args, **kwargs):
        data = {'user_id':0, 'username': None}
        if request.user.is_authenticated:
            data = {'user_id':request.user.id, 'username': request.user.username}
        if settings.DEBUG:
            userid = 38 # Marissa
            browser = str(request.META['HTTP_USER_AGENT']).lower()
            if 'firefox' in browser:
                userid = 2
            user = User.objects.get(pk=userid) 
            data = {'user_id':user.id, 'username': user.username}

        return JsonResponse(data)
