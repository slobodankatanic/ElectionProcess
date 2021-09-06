from flask import Flask, request, Response, jsonify;
from configuration import Configuration;
from sqlalchemy import and_;
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, get_jwt_identity;
from models import database, Participant, Election, ElectionParticipant, Vote;
from rightAccess import roleCheck;
from datetime import datetime, timedelta;
from dateutil import parser;
import copy;

application = Flask(__name__)
application.config.from_object(Configuration);
jwt = JWTManager(application);

@application.route("/createParticipant", methods = ["POST"])
@roleCheck(role = "admin")
def createParticipant():
    name = request.json.get("name", "");
    individual = request.json.get("individual", "");

    nameEmpty = len(name) == 0;
    individualInvalid = not isinstance(individual, bool);

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

@application.route("/getParticipants", methods = ["GET"])
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
    # if (start >= end or start < datetime.now()):
    if (start >= end):
        return False;

    elections = Election.query.all();

    for election in elections:
        if (not (start >= election.end or end <= election.start)):
            return False;

    return True;

@application.route("/createElection", methods = ["POST"])
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

    # startValid = checkISODateTime(start);
    # endValid = checkISODateTime(end);

    # if ((not startValid) or (not endValid)):
    #     return jsonify(message = "Invalid date and time."), 400;

    # if (not checkDateTimeRange(datetime.strptime(start, "%Y-%m-%dT%H:%M"),
    #                            datetime.strptime(end, "%Y-%m-%dT%H:%M"))):
    #     return jsonify(message="Invalid date and time."), 400;

    try:
        # if (not checkDateTimeRange(datetime.fromisoformat(start),
        #                            datetime.fromisoformat(end))):
        #     return jsonify(message = "Invalid date and time."), 400;
        if (not checkDateTimeRange(parser.parse(start),
                                   parser.parse(end))):
            return jsonify(message = "Invalid date and time."), 400;
    except Exception:
        return jsonify(message = "Invalid date and time."), 400;

    if (not isinstance(participants, list)):
        return jsonify(message = "Invalid participants."), 400;

    if (len(participants) < 2):
        return jsonify(message = "Invalid participants."), 400;

    type = 0;
    if (individual):
        type = 1;

    for participantId in participants:
        participantObject = Participant.query.filter(Participant.id == participantId).first();
        if ((not participantObject) or (type != participantObject.type)):
            return jsonify(message = "Invalid participants."), 400;

    election = Election(start = start, end = end, type = type);
    database.session.add(election);
    database.session.commit();

    for participantId, pollNumber in zip(participants, range(1, len(participants) + 1)):
        electionParticipant = ElectionParticipant(electionId = election.id, participantId = participantId, pollNumber = pollNumber);
        database.session.add(electionParticipant);

    database.session.commit();

    pollNumbers = [];
    for i in range(1, len(participants) + 1):
        pollNumbers.append(i);

    return jsonify(pollNumbers = pollNumbers);

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

        individual = False;
        if (election.type == 1):
            individual = True;

        elections.append({
           "id": election.id,
           "start": election.start.isoformat(),
           "end": election.end.isoformat(),
           "individual": individual,
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

def getParticipantId(pollNumber, electionParticipants):
    for electionParticipant in electionParticipants:
        if (electionParticipant.pollNumber == pollNumber):
            return electionParticipant.participantId;

def presidentialElection(election):
    votes = election.votes;
    participants = election.participants;
    electionParticipants = ElectionParticipant.query.filter(ElectionParticipant.electionId == election.id).all();

    results = {};
    invalidVotes = [];
    totalVotes = 0;

    for vote in votes:
        if (len(vote.reasonForInvalidity) != 0):
            invalidVotes.append({
               "electionOfficialJmbg": vote.officialJmbg,
               "ballotGuid": vote.guid,
               # "pollNumber": getParticipantPollNumber(vote.participantId, electionParticipants),
                "pollNumber": vote.pollNumber,
               "reason": vote.reasonForInvalidity
            });
        else:
            totalVotes += 1;

            # if (not (str(vote.participant.id) in results)):
            #     results[str(vote.participant.id)] = 1;
            # else:
            #     results[str(vote.participant.id)] += 1;

            participantString = str(getParticipantId(vote.pollNumber, electionParticipants));

            if (not (participantString in results)):
                results[participantString] = 1;
            else:
                results[participantString] += 1;


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

    return jsonify(participants = participantsResult, invalidVotes = invalidVotes);

def partyElection(election):
    votes = election.votes;
    participants = election.participants;
    electionParticipants = ElectionParticipant.query.filter(ElectionParticipant.electionId == election.id).all();

    results = {};
    invalidVotes = [];
    totalVotes = 0;

    for vote in votes:
        if (len(vote.reasonForInvalidity) != 0):
            invalidVotes.append({
                "electionOfficialJmbg": vote.officialJmbg,
                "ballotGuid": vote.guid,
                # "pollNumber": getParticipantPollNumber(vote.participantId, electionParticipants),
                "pollNumber": vote.pollNumber,
                "reason": vote.reasonForInvalidity
            });
        else:
            totalVotes += 1;

            participantString = str(getParticipantId(vote.pollNumber, electionParticipants));

            if (not (participantString in results)):
                results[participantString] = 1;
            else:
                results[participantString] += 1;

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
            # if ((quotients[participantId] > currentMaxValue) or
            #     ((quotients[participantId] == currentMaxValue) and (results[currentMaxId] <= results[participantId]))):
            if (quotients[participantId] > currentMaxValue):
                currentMaxValue = quotients[participantId];
                currentMaxId = participantId;

        availableSeats -= 1;
        seatsAllocated[currentMaxId] += 1;
        quotients[currentMaxId] = results[currentMaxId] / (seatsAllocated[currentMaxId] + 1);

    participantsResult = [];
    for participantObject in participants:
        seats = 0;
        if (str(participantObject.id) in seatsAllocated):
            seats = seatsAllocated[str(participantObject.id)];

        participantsResult.append({
            "pollNumber": getParticipantPollNumber(participantObject.id, electionParticipants),
            "name": getParticipantName(participantObject.id, participants),
            "result": seats
        });

    return jsonify(participants = participantsResult, invalidVotes = invalidVotes);

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

    if ((datetime.now().replace(microsecond = 0) + timedelta(hours = 2, seconds = 5)) < election.end):
        return jsonify(message = "Election is ongoing."), 400;
        # now = datetime.now() + timedelta(hours = 2);
        # endara = election.end;
        # return jsonify(participants = [now, endara], invalidVotes = []);

    if (election.type == 1):
        return presidentialElection(election);
    else:
        return partyElection(election);

@application.route("/emptyDatabase", methods = ["GET"])
def emptyDatabase():
    ElectionParticipant.query.delete();
    Vote.query.delete();
    Election.query.delete();
    Participant.query.delete();

    database.session.commit();

    return Response(status = 200);

if (__name__ == "__main__"):
    database.init_app(application);
    application.run(debug = True, host = "0.0.0.0", port = 5003);

