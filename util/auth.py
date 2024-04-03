import hashlib
import random
import string
import urllib.parse

# Define a dictionary to store user credentials (username, salt, hashed password) and XSRF tokens
user_credentials = {}
user_xsrf_tokens = {}

def extract_credentials(request):
    body = request.body.decode("utf-8")
    parsed_body = urllib.parse.parse_qs(body)
    username = parsed_body.get("username_reg", [""])[0] or parsed_body.get("username_login", [""])[0]
    password = parsed_body.get("password_reg", [""])[0] or parsed_body.get("password_login", [""])[0]

    # URL decode the password
    password = urllib.parse.unquote(password)

    return [username, password]

def validate_password(password):
    if len(password) < 8:
        return False
    if not any(char.islower() for char in password):
        return False
    if not any(char.isupper() for char in password):
        return False
    if not any(char.isdigit() for char in password):
        return False
    special_characters = "!@#$%^&()-_="
    if not any(char in special_characters for char in password):
        return False
    valid_characters = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" + special_characters)
    if not all(char in valid_characters for char in password):
        return False
    return True

def generate_salt():
    # Generate a random salt
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def generate_salted_hash(password, salt):
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

def validate_salted_hash(password, salt, hashed_password):
    """
    Validate if the given password matches the hashed password using the provided salt.
    """
    # Hash the provided password with the given salt
    input_hash = generate_salted_hash(password, salt)
    # Compare the input hash with the stored hashed password
    return input_hash == hashed_password

# Other utility functions...

def generate_hash(data):
    # Generate a SHA-256 hash for the provided data
    return hashlib.sha256(data.encode()).hexdigest()

