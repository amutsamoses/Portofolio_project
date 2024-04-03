import re
from util.request import Request

class Router:
    def __init__(self):
        self.routes = []

    def add_route(self, method, path, function, auth_required=False, xsrf_required=False):
        # Prepend '^' to match the beginning of the path
        path = '^' + path
        self.routes.append((method, path, function, auth_required, xsrf_required))

    def route_request(self, request: Request):
        matched_route = None

        for route in self.routes:
            method, path, function, auth_required, xsrf_required = route
            # Use re.match instead of re.search to match from the beginning
            if method == request.method and re.match(path, request.path):
                # Select the first matched route
                matched_route = route
                break

        if matched_route:
            _, _, function, auth_required, xsrf_required = matched_route

            # Check if the route requires authentication
            if auth_required and not request.is_authenticated():
                return b"HTTP/1.1 401 Unauthorized\r\n\r\n"  # Unauthorized response

            # Check if XSRF token is required and validate it
            if xsrf_required and not request.is_valid_xsrf_token():
                return b"HTTP/1.1 403 Forbidden\r\n\r\n"  # Forbidden response due to invalid XSRF token

            return function(request)
        else:
            return b"HTTP/1.1 404 Not Found\r\n\r\n"
