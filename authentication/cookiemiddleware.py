from authentication.services import jwt_login, refresh_access_cookies


class CookieMiddleware:
    """This class makes sure there is an access cookie present set at login.
    It also gets deleted at logout. This cookie is used by Neuroglancer and the angular
    front end for authentication.
    TODO: User is logged in at the admin portal area, but not in Neuroglancer.
    The id, and access cookies are missing. The session cookies were there
    but the ones with an expiration date were not.
    Maybe set them for longer?
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        """The first if statement is for when people login with username and password.
        In this case, there is no cookie so we set it there.
        The 2nd if statement is when they logout so we delete the cookie.
        """

        response = self.get_response(request)
        access = request.COOKIES.get('id')
        if access is not None:
            access = True
        else :
            access = False

        isAuthenticated = request.user.is_authenticated

        if isAuthenticated and not access:
            response = jwt_login(response=response, user=request.user, request=request)
        elif isAuthenticated and access:
            refresh_access_cookies(response=response, request=request)
        elif not isAuthenticated and access:
            response.delete_cookie('id')
            response.delete_cookie('username')
            response.delete_cookie('access')
            response.delete_cookie('lab')
            response.delete_cookie('sessionid')
        else:
            pass
        

        return response