class Request:
    def __init__(self, request: bytes):
        line = request.split(b'\r\n\r\n', 1)
        self.body = line[1] if len(line) > 1 else b""
        headers = line[0].decode('utf-8').split("\r\n")
        
        # Parse the request line
        request_line_parts = headers[0].split(' ')
        self.method = request_line_parts[0]
        self.path = request_line_parts[1]
        self.http_version = request_line_parts[2]

        self.headers = {}
        self.cookies = {}

        # Parse headers
        for header in headers[1:]:
            key, value = header.split(": ", 1)
            self.headers[key] = value.strip()
            if key.lower() == 'cookie':
                cookies = value.split(';')
                for cookie in cookies:
                    if '=' in cookie:
                        cookie_key, cookie_value = cookie.strip().split('=', 1)
                        self.cookies[cookie_key.strip()] = cookie_value.strip()

    def is_authenticated(self):
        # Check if the authentication token is present in the cookies
        return 'auth_token' in self.cookies

def test1():
    # Test case for a GET request without a body
    request_get = Request(b'GET / HTTP/1.1\r\nHost: localhost:8080\r\nConnection: keep-alive\r\n\r\n')
    assert request_get.method == "GET"
    assert "Host" in request_get.headers
    assert request_get.headers["Host"] == "localhost:8080"  # Note: The leading space in the header value must be removed
    assert request_get.body == b""  # There is no body for this request.
    assert not request_get.is_authenticated()  # No authentication token in cookies

    # Test case for a POST request with a body
    request_post = Request(b'POST /login HTTP/1.1\r\nHost: localhost:8080\r\nContent-Length: 21\r\n\r\nusername=user&password=pass')
    assert request_post.method == "POST"
    assert "Content-Length" in request_post.headers
    assert request_post.headers["Content-Length"] == "21"
    assert request_post.body == b"username=user&password=pass"
    assert not request_post.is_authenticated()  # No authentication token in cookies

    # Test case for a GET request with an authentication token in cookies
    request_auth = Request(b'GET /protected HTTP/1.1\r\nHost: localhost:8080\r\nConnection: keep-alive\r\nCookie: auth_token=abc123\r\n\r\n')
    assert request_auth.method == "GET"
    assert "Cookie" in request_auth.headers
    assert request_auth.cookies == {"auth_token": "abc123"}
    assert request_auth.is_authenticated()  # Authentication token present in cookies

    # Additional test cases can be added here to cover more scenarios


    # Additional tests can be added to cover more cases, including POST requests.

if __name__ == '__main__':
    test1()
