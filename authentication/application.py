from flask import Flask, request, Response, jsonify;
from models import User, database, UserRole;
from configuration import Configuration;
from email.utils import parseaddr;
from sqlalchemy import and_;
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, get_jwt_identity;
from rightAccess import roleCheck;
import re;

application = Flask(__name__);
application.config.from_object(Configuration);
jwt = JWTManager(application);

def checkJMBG(jmbg):
    if ((len(jmbg) != 13)):
        return False;

    day = int(jmbg[0:2]);
    if (day > 31 or day < 1):
        return False;

    month = int(jmbg[2:4]);
    if (month > 31 or month < 1):
        return False;

    region = int(jmbg[7:9]);
    if (region > 99 or region < 70):
        return False;

    # control = int(jmbg[12]);
    # realControl = (7 * (int(jmbg[0]) + int(jmbg[6])) + 6 * (int(jmbg[1]) + int(jmbg[7])) +
    #                5 * (int(jmbg[2]) + int(jmbg[8])) + 4 * (int(jmbg[3]) + int(jmbg[9])) +
    #                3 * (int(jmbg[4]) + int(jmbg[10])) + 2 * (int(jmbg[5]) + int(jmbg[11]))) % 11;
    # if (realControl <= 9):
    #     if (control != realControl):
    #         return False;
    # else:
    #     if (realControl != 0):
    #         return False;

    return True;

def checkPassword(password):
    if (len(password) < 8):
        return False;

    if ((re.search("[0-9]", password) is None) or (re.search("[A-Z]", password) is None) or
        (re.search("[a-z]",password) is None)):
        return False;

    return True;

@application.route("/register", methods = ["POST"])
def register():
    jmbg = request.json.get("jmbg", "");
    email = request.json.get("email", "");
    password = request.json.get("password", "");
    forename = request.json.get("forename", "");
    surname = request.json.get("surname", "");

    jmbgEmpty = len(jmbg) == 0;
    emailEmpty = len(email) == 0;
    passwordEmpty = len(password) == 0;
    foreameEmpty = len(forename) == 0;
    surnameEmpty = len(surname) == 0;

    if (jmbgEmpty):
        return jsonify(message = "Field jmbg is missing."), 400;
    if (foreameEmpty):
        return jsonify(message = "Field forename is missing."), 400;
    if (surnameEmpty):
        return jsonify(message = "Field surname is missing."), 400;
    if (emailEmpty):
        return jsonify(message = "Field email is missing."), 400;
    if (passwordEmpty):
        return jsonify(message = "Field password is missing."), 400;

    if (not checkJMBG(jmbg)):
        return jsonify(message = "Invalid jmbg."), 400;

    emailRegex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b';
    if (not re.fullmatch(emailRegex, email)):
        return jsonify(message = "Invalid email."), 400;

    if (not checkPassword(password)):
        return jsonify(message = "Invalid password."), 400;

    user = User.query.filter(User.email == email).first();
    if (user):
        return jsonify(message = "Email already exists."), 400;

    user = User(jmbg = jmbg, email = email, password = password, forename = forename, surname = surname);
    database.session.add(user);
    database.session.commit();

    userRole = UserRole(userId = user.id, roleId = 2);
    database.session.add(userRole);
    database.session.commit();

    return Response(status = 200);

@application.route("/login", methods = ["POST"])
def login():
    email = request.json.get("email", "");
    password = request.json.get("password", "");

    emailEmpty = len(email) == 0;
    passwordEmpty = len(password) == 0;

    if (emailEmpty):
        return jsonify(message = "Field email is missing."), 400;
    if (passwordEmpty):
        return jsonify(message = "Field password is missing."), 400;

    emailRegex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b';
    if (not re.fullmatch(emailRegex, email)):
        return jsonify(message="Invalid email."), 400;

    user = User.query.filter(and_(User.email == email, User.password == password)).first();

    if (not user):
        return jsonify(message = "Invalid credentials."), 400;

    additionalClaims = {
        "jmbg": user.jmbg,
        "email": user.email,
        "password": user.password,
        "forename": user.forename,
        "surname": user.surname,
        "roles": [str(role) for role in user.roles]
    };

    accessToken = create_access_token(identity = user.email, additional_claims = additionalClaims);
    refreshToken = create_refresh_token(identity = user.email, additional_claims = additionalClaims);

    return jsonify(accessToken = accessToken, refreshToken = refreshToken);

@application.route("/check", methods = ["POST"])
@jwt_required()
def check():
    return "Token is valid";

@application.route("/refresh", methods = ["POST"])
@jwt_required(refresh = True)
def refresh():
    identity = get_jwt_identity();
    refreshClaims = get_jwt();

    additionalClaims = {
        "jmbg": refreshClaims["jmbg"],
        "email": refreshClaims["email"],
        "password": refreshClaims["password"],
        "forename": refreshClaims["forename"],
        "surname": refreshClaims["surname"],
        "roles": refreshClaims["roles"]
    };

    return Response(create_access_token(identity = identity, additional_claims = additionalClaims), status = 200);

@application.route("/", methods = ["GET"])
def index():
    return "Helov";

@application.route("/delete", methods = ["POST"])
@roleCheck(role = "admin")
def deleteUser():
    email = request.json.get("email", "");

    emailEmpty = len(email) == 0;

    if (emailEmpty):
        return jsonify(message = "Field email is missing."), 400;

    emailRegex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b';
    if (not re.fullmatch(emailRegex, email)):
        return jsonify(message="Invalid email."), 400;

    user = User.query.filter(and_(User.email == email)).first();

    if (not user):
        return jsonify(message = "Unknown user."), 400;

    UserRole.query.filter(UserRole.userId == user.id).delete();
    User.query.filter(User.email == email).delete();

    database.session.commit();

    return Response(status = 200);

if (__name__ == "__main__"):
    database.init_app(application);
    application.run(debug = True, host = "0.0.0.0", port = 5002);