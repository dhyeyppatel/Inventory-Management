from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # If the user typed an '@' symbol, treat it as an email
        if username and '@' in username:
            kwargs = {'email': username}
        else:
            kwargs = {'username': username}
        
        try:
            user = User.objects.get(**kwargs)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        return None