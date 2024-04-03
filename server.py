# Standard library imports
import os
import json
from datetime import datetime, timedelta

# Third-party imports
import socketserver
from pymongo import MongoClient
from bson.objectid import ObjectId

# Local imports
from util.request import Request
from util.auth import (
    extract_credentials,
    generate_hash,
    validate_password,
    generate_salted_hash,
    validate_salted_hash,
)
from util.router import Router


mongo_client = MongoClient("mongo", 27017)
db = mongo_client["cse312"]
chat_collection = db["chat"]
users_collection = db["users"]
auth_collection = db["auth"]
xsrf_collection = db["xsrf"]


class MyTCPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        
        received_data = self.request.recv(2048)

        # print(self.client_address)
        # print("--- received data ---")
        # print(received_data)
        # print("--- end of data ---\n\n")
        
        request = Request(received_data)

        router = Router()
        router.add_route("GET", "^/$", self.home_page_endpoint)
        router.add_route("GET", "^/public", self.assets_endpoint)
        router.add_route("POST", "/login", self.login_endpoint)
        router.add_route("POST", "^/register", self.registration_endpoint)
        router.add_route("GET", "^/logout", self.logout_endpoint)
        # router.add_route("GET", "^/spotify", self.spotify_endpoint)
        router.add_route("POST", "/chat-messages", self.add_message_endpoint)
        router.add_route("GET", "/chat-messages", self.get_messages_endpoint)
        router.add_route("PUT", "/chat-messages/[0-9a-fA-F]{24}", self.update_message_endpoint)
        router.add_route("DELETE", "/chat-messages/[0-9a-fA-F]{24}", self.delete_message_endpoint)
        router.route_request(request)


    def route_request(self, request: Request):
        # This method is called to route the request to the correct handler
        matched = False
        for route in self.routes:
            method, path, function = route
            if method == request.method and re.match(path, request.path):
                function(request)
                matched = True
                break

        if not matched:
            self.response_404()

    def home_page_endpoint(self, request: Request):
        root_path = "public/index.html"
        visits = int(request.cookies.get("visits", "0")) + 1
        expires = (datetime.utcnow() + timedelta(hours=1)).strftime("%a, %d-%b-%Y %H:%M:%S GMT")
        xsrf_token = None

        if self.is_logged_in(request):
            xsrf_token = self.generate_xsrf_token(request)

        if os.path.isfile(root_path):
            with open(root_path, "r", encoding="utf-8") as file:
                HTML_file = file.read()
                HTML_file = HTML_file.replace("{{visits}}", str(visits))
                HTML_file = HTML_file.replace("{{xsrf_token}}", str(xsrf_token))
                HTML_file = (
                    HTML_file.replace(
                        "{{logout_button}}", str('<button onclick="logout()">Logout</button>')
                    )
                    if self.is_logged_in(request)
                    else HTML_file.replace("{{logout_button}}", str(""))
                )
                content = HTML_file.encode("utf-8")

            cookie_headers = f"Set-Cookie: visits={visits}; Expires={expires}; Path=/; HttpOnly\r\n"

            self.send_response(content, "text/html; charset=utf-8", cookie_headers)
        else:
            self.response_404()

    # TODO move those methods to the auth file
    def generate_xsrf_token(self, request):
        user_data = self.is_logged_in(request)
        if user_data:
            token = generate_hash(user_data.get("username"))
            xsrf_collection.insert_one(
                {"token": token, "username": user_data.get("username")}
            )
            return token

    def delete_user_session(self, user_data):
        auth_collection.delete_one({"auth_token": user_data["auth_token"]})

    def is_user_session_expired(self, user_data):
        expires = datetime.strptime(user_data["expires"], "%a, %d-%b-%Y %H:%M:%S GMT")
        if expires < datetime.utcnow():
            try:
                self.delete_user_session(user_data)
                self.logout_endpoint(None)
            except KeyError:
                pass
            return True
        return False

    def is_logged_in(self, request: Request):
        logged = request.cookies.get("auth_token")
        if logged:
            user_data = auth_collection.find_one({"auth_token": logged})
            if user_data:
                return user_data
        return False

    def logout_endpoint(self, request: Request):
        if self.is_logged_in(request):
            cookie_headers = "Set-Cookie: session_id=None; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; HttpOnly\r\n"
            self.send_response(
                "successfully logged out".encode("utf-8"),
                "text/plain",
                cookie_headers=cookie_headers,
            )

    def registration_endpoint(self, request: Request):
    username, password = extract_credentials(request)
    is_valid = validate_password(password)
    if is_valid:
        salt = generate_salt()  # Generate a unique salt for each user
        hashed_password = generate_salted_hash(password, salt)
        result = users_collection.insert_one(
            {"username": username, "password": hashed_password, "salt": salt}  # Store the salt in the database
        )
        if result.inserted_id:
            message = f"User {username} created successfully"
            data = {"message": message}

            self.send_response(
                json.dumps(data).encode("utf-8"), "application/json", status_code="201 Created"
            )
        return
    self.send_response("Password not validated".encode("utf-8"), "text/plain")


    # def login_spotify_endpoint(self, request: Request):
    #     client_id = ""
    #     client_secret = ""
    #     redirect_uri = "http://localhost:8080/spotify"
    #     scope = ["user-read-private", "user-read-email"]  # Define scopes as per your requirements

    #     authorization_base_url = "https://accounts.spotify.com/authorize"
    #     token_url = "https://accounts.spotify.com/api/token"

    #     spotify = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    #     # oauthlib.oauth2.rfc6749.errors.InsecureTransportError: (insecure_transport) OAuth 2 MUST utilize https.
    #     self.send_response(b"", "application/json", status_code="302 Found")


    # def spotify_endpoint(self, request: Request):
    #     return pass

    def login_endpoint(self, request: Request):
    username, password = extract_credentials(request)
    query_user = users_collection.find_one({"username": username})
    if query_user:
        if validate_salted_hash(password, query_user["salt"], query_user["password"]):
            message = f"User {username} logged in successfully"
            data = {"message": message}
            expires = (datetime.utcnow() + timedelta(hours=1)).strftime(
                "%a, %d-%b-%Y %H:%M:%S GMT"
            )
            cookie_hash = generate_hash(username)

            cookie_headers = (
                f"Set-Cookie: auth_token={cookie_hash}; Expires={expires}; Path=/; HttpOnly\r\n"
            )

            auth_collection.insert_one(
                {"username": username, "auth_token": cookie_hash, "expires": expires}
            )

            self.send_response(
                json.dumps(data).encode("utf-8"),
                "application/json",
                status_code="200 OK",
                cookie_headers=cookie_headers,
            )
            return  # Exit the function after successful login
    self.send_response("User or Password incorrect".encode("utf-8"), "application/json")

    def assets_endpoint(self, request: Request):
        path = request.path
        if path.endswith(".html"):
            content_type = "text/html; charset=utf-8"
        elif path.endswith(".css"):
            content_type = "text/css; charset=utf-8"
        elif path.endswith(".js"):
            content_type = "text/javascript; charset=utf-8"
        elif path.endswith(".jpg"):
            content_type = "image/jpeg"
        elif path.endswith(".jpeg"):
            content_type = "image/jpeg"
        elif path.endswith(".png"):
            content_type = "image/png"
        elif path.endswith(".mp4"):
            content_type = "video/mp4"
        elif path.endswith(".txt"):
            content_type = "text/plain; charset=utf-8"
        elif path.endswith(".json"):
            content_type = "application/json; charset=utf-8"
        elif path.endswith(".ico"):
            content_type = "image/x-icon"
        else:
            content_type = "application/octet-stream"

        path_file = request.path[1:]
        if os.path.isfile(path_file):
            with open(path_file, "rb") as file:
                content = file.read()
            self.send_response(content, content_type)
        else:
            self.response_404()

    # TODO: fix the status code here and review the places that uses it
    def send_response(self, content, content_type, cookie_headers="", status_code="200 OK"):

        HTTP_headers = (
            f"HTTP/1.1 {status_code}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"X-Content-Type-Options: nosniff\r\n"
            f"{cookie_headers}"
            f"Content-Length: {len(content)}\r\n\r\n"
        )

        self.request.sendall(HTTP_headers.encode("utf-8") + content)

    def response_404(self):

        content = "Content was not found.\r\n".encode("utf-8")

        response = (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            f"Content-Length: {len(content)}\r\n\r\n"
            f"X-Content-Type-Options: nosniff\r\n"
            "\r\n"
        ).encode("utf-8") + content

        self.request.sendall(response)

    def add_message_endpoint(self, request):

        data = json.loads(request.body.decode("utf-8"))
        # username = "Guest"
        user_data = self.is_logged_in(request)
        xsrf_token = data.get("xsrf-token")

        if xsrf_token and user_data:
            xsrf = xsrf_collection.find_one(
                {"token": xsrf_token, "username": user_data.get("username")}
            )

            if "message" in data and xsrf:
                username = user_data["username"]
                message = html.escape(data["message"])
                result = chat_collection.insert_one({"username": username, "message": message})
                id = str(result.inserted_id)
                data = {"message": message, "username": username, "id": id}
                self.send_response(
                    json.dumps(data).encode("utf-8"), "application/json", status_code="201 Created"
                )
        else:
            self.send_response(
                "XSRF token not valid".encode("utf-8"),
                "application/json",
                status_code="403 Forbidden",
            )


    def update_message_endpoint(self, request):
        if "chat-messages" in request.path:
            id = request.path.split("/")[-1]
            if id:
                message_obj_id = ObjectId(id)
                data = json.loads(request.body.decode("utf-8"))
                result = chat_collection.update_one({"_id": message_obj_id}, {"$set": data})
                if result.modified_count == 1:
                    print("data updated")
                    self.send_response(b"", "application/json", status_code="204 No Content")
                else:
                    self.response_404()

    def delete_message_endpoint(self, request):

        id = request.path.split("/")[-1]
        if "chat-messages" in request.path and id:
            message_obj_id = ObjectId(id)

            user = self.is_logged_in(request)
            if user:
                message = chat_collection.find_one({"_id": message_obj_id})
                if user.get("username") == message.get("username"):
                    result = chat_collection.delete_one({"_id": message_obj_id})

                    if result.deleted_count == 1:
                        self.send_response(b"", "application/json", status_code="204 No Content")
                else:
                    self.send_response(
                        "unable to delete message, not the owner".encode("utf-8"),
                        "application/json",
                        status_code="404 Not Found",
                    )

    def get_messages_endpoint(self, request):
        messages = []
        for message in chat_collection.find({}):
            try:
                message.append = ({
                    "id": str(message["_id"]),
                    "username": message["username"],
                    "message": html.escape(message["message"])
                })
                # messages.append(message)
            except KeyError:
                continue

        # messages_json = json.dumps(messages)
        self.send_response(json.dumps(messages).encode("utf-8"), "application/json")


def main():
    host = "0.0.0.0"
    port = 8080
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer((host, port), MyTCPHandler)

    print("Listening on port " + str(port))

    server.serve_forever()


if __name__ == "__main__":
    main()
