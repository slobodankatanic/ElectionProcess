from flask import Flask, request, Response, jsonify;
from applications.configuration import Configuration;
from email.utils import parseaddr;
from sqlalchemy import and_;
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, get_jwt_identity;
from applications.models import database, Participant;
from rightAccess import roleCheck;
from datetime import datetime;

application = Flask(__name__);
application.config.from_object(Configuration);
jwt = JWTManager(application);

@application.route("/createParticipant", models = ["POST"])
@roleCheck(role = "admin")
def createParticipant():
    name = request.json.get("name", "");
    individual = request.json.get("name", "");

    nameEmpty = len(name) == 0;
    individualInvalid = isinstance(individual, bool);

    if (nameEmpty):
        return jsonify(message = "Field name is missing."), 400;
    if (individualInvalid):
        return jsonify(message = "Field individual is missing."), 400;

    type = 0;
    if (individual):
        type = 1;

    participant = Participant(name = name, type = type);
    database.session.add(participant);
    database.session.commit();

    return jsonify(id = participant.id);

@application.route("/getParticipant", models = ["GET"])
@roleCheck(role = "admin")
def getParticipant():
    participants = [];
    allParticipants = Participant.query.all();

    for participant in allParticipants:
        participants.append({
            "id": participant.id,
            "name": participant.name,
            "individual": participant.type == 1
        });

    return jsonify(participants = participants);

@application.route("/createElection", models = ["POST"])
@roleCheck(role = "admin")
def createElection():
    return False;

if (__name__ == "__main__"):
    database.init_app(application);
    application.run(debug = True, port = 5001);

