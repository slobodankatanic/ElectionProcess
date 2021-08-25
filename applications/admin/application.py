from flask import Flask, request, Response, jsonify;
from applications.configuration import Configuration;
from email.utils import parseaddr;
from sqlalchemy import and_;
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, get_jwt_identity;
from applications.models import database, Participant, Election, ElectionParticipant;
from rightAccess import roleCheck;
from datetime import datetime;
import copy;

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

def checkISODateTime(dateTime):
    if (not isinstance(dateTime, str)):
        return False;

    try:
        datetimeObject = datetime.strptime(dateTime, "%Y-%m-%dT%H:%M");
    except ValueError:
        return False;

    return True;

def checkDateTimeRange(start, end):
    if (start >= end or start < datetime.now()):
        return False;

    elections = Election.query.all();

    for election in elections:
        if (not (start >= election.end or end <= election.start)):
            return False;

    return True;

@application.route("/createElection", models = ["POST"])
@roleCheck(role = "admin")
def createElection():
    start = request.json.get("start", "");
    end = request.json.get("end", "");
    individual = request.json.get("individual", "");
    participants = request.json.get("participants", "");

    startEmpty = isinstance(start, str) and len(start) == 0;
    endEmpty = isinstance(end, str) and len(end) == 0;
    individualEmpty = (not isinstance(individual, bool)) or (isinstance(individual, str) and len(individual) == 0);
    participantsEmpty = isinstance(participants, str) and len(participants) == 0;

    if (startEmpty):
        return jsonify(message = "Field start is missing."), 400;
    if (endEmpty):
        return jsonify(message = "Field end is missing."), 400;
    if (individualEmpty):
        return jsonify(message = "Field individual is missing."), 400;
    if (participantsEmpty):
        return jsonify(message = "Field participants is missing."), 400;

    startValid = checkISODateTime(start);
    endValid = checkISODateTime(end);

    if ((not startValid) or (not endValid)):
        return jsonify(message = "Invalid date and time."), 400;

    if (not checkDateTimeRange(datetime.strptime(start, "%Y-%m-%dT%H:%M"),
                               datetime.strptime(end, "%Y-%m-%dT%H:%M"))):
        return jsonify(message = "Invalid date and time."), 400;

    if (not isinstance(participants, list)):
        return jsonify(message = "Invalid participant."), 400;

    if (len(participants) < 2):
        return jsonify(message = "Invalid participant."), 400;

    type = 0;
    if (individual):
        type = 1;

    for participantId in participants:
        participantObject = Participant.query.filter(Participant.id == participantId).first();
        if ((not participantObject) or (type != participantObject.type)):
            return jsonify(message = "Invalid participant."), 400;

    # add election, add electionpart, return poll numbers
    election = Election(start = start, end = end, type = type);
    database.session.add(election);
    database.session.commit();

    pollNumber = 0;
    for participantId, pollNumber in zip(participants, range(1, len(participants) + 1)):
        electionParticipant = ElectionParticipant(electionId = election.id, participantId = participantId, pollNumber = pollNumber);
        database.session.add(electionParticipant);

    database.session.commit();

    return jsonify(pollNumbers = range(1, len(participants) + 1));

@application.route("/getElections", methods = ["GET"])
@roleCheck(role = "admin")
def getElections():
    allElections = Election.query.all();

    elections = [];
    for election in allElections:
        participants = [];
        for participant in election.participants:
            participants.append({
                "id": participant.id,
                "name": participant.name
            });

        elections.append({
           "id": election.id,
           "start": election.start,
           "end": election.end,
           "individual": election.type == 1,
           "participants": participants
        });

    return jsonify(elections = elections);

def getParticipantPollNumber(participantId, electionParticipants):
    for participant in electionParticipants:
        if (participant.participantId == participantId):
            return participant.pollNumber;

def getParticipantName(participantId, participants):
    for participant in participants:
        if (participant.id == participantId):
            return participant.name;

def presidentialElection(election):
    votes = election.votes;
    participants = election.participants;
    electionParticipants = ElectionParticipant.query.filter(ElectionParticipant.electionId == election.id).all();

    results = {};
    invalidVotes = [];
    totalVotes = 0;

    for vote in votes:
        if (len(vote.reasonForInvalidity) == 0):
            invalidVotes.append({
               "electionOfficialJmbg": vote.officialJmbg,
               "ballotGuid": vote.id,
               "pollNumber": getParticipantPollNumber(vote.participantId, electionParticipants),
               "reason": vote.reasonForInvalidity
            });
        else:
            totalVotes += 1;

            if (not (str(vote.participant.id) in results)):
                results[str(vote.participant.id)] = 1;
            else:
                results[str(vote.participant.id)] += 1;


    participantsResult = [];
    for participantObject in participants:
        result = 0.00;
        if (str(participantObject.id) in results):
            result = round((float(results[str(participantObject.id)])) / (float (totalVotes)), 2);

        participantsResult.append({
            "pollNumber": getParticipantPollNumber(int(participantObject.id), electionParticipants),
            "name": getParticipantName(int(participantObject.id), participants),
            "result": result
        });

    return jsonify(participans = participantsResult, invalidVotes = invalidVotes);

def partyElection(election):
    votes = election.votes;
    participants = election.participants;
    electionParticipants = ElectionParticipant.query.filter(ElectionParticipant.electionId == election.id).all();

    results = {};
    invalidVotes = [];
    totalVotes = 0;

    for vote in votes:
        if (len(vote.reasonForInvalidity) == 0):
            invalidVotes.append({
                "electionOfficialJmbg": vote.officialJmbg,
                "ballotGuid": vote.id,
                "pollNumber": getParticipantPollNumber(vote.participantId, electionParticipants),
                "reason": vote.reasonForInvalidity
            });
        else:
            totalVotes += 1;

            if (not (str(vote.participant.id) in results)):
                results[str(vote.participant.id)] = 1;
            else:
                results[str(vote.participant.id)] += 1;

    seatsAllocated = {};
    treshold = 0.05 * float(totalVotes);
    for participantObject in participants:
        if (str(participantObject.id) in results):
            if (results[str(participantObject.id)] < treshold):
                results.pop(str(participantObject.id));
            else:
                seatsAllocated[str(participantObject.id)] = 0;

    availableSeats = 250;
    quotients = copy.deepcopy(results);
    while (availableSeats > 0):
        currentMaxValue = -1;
        currentMaxId = "";
        for participantId in quotients:
            if (quotients[participantId] > currentMaxValue):
                currentMaxValue = quotients[participantId];
                currentMaxId = participantId;
            elif (quotients[participantId] == currentMaxValue):
                if (len(currentMaxId) != 0 and results[currentMaxId] > results[participantId]):
                    return False;

@application.route("/getResults", methods = ["GET"])
@roleCheck(role = "admin")
def getResults():
    try:
        electionId = request.args["id"];
    except KeyError:
        return jsonify(message = "Field id is missing."), 400;

    election = Election.query.filter(Election.id == electionId).first();

    if (not election):
        return jsonify(message = "Election does not exist."), 400;

    if (datetime.now() < election.end):
        return jsonify(message = "Election is ongoing."), 400;

    if (election.type == 1):
        return presidentialElection(election);
    else:
        return partyElection(election);

@application.route("/vote", methods = ["POST"])
@roleCheck(role = "official")
def vote():
    return False;

if (__name__ == "__main__"):
    database.init_app(application);
    application.run(debug = True, port = 5001);

