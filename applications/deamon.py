from flask import Flask;
from redis import Redis;
from configuration import Configuration;
from models import database, Election, ElectionParticipant, Vote, Participant;
from datetime import datetime, timedelta;
import json;
from sqlalchemy import and_;
import time;

application = Flask(__name__);
application.config.from_object(Configuration);
database.init_app(application);

def getElectionOngoing():
    elections = Election.query.all();
    for election in elections:
        if (election.start <= (datetime.now().replace(microsecond = 0) + timedelta(hours = 2, seconds = 1)) and election.end >= (datetime.now().replace(microsecond = 0) + timedelta(hours = 2, seconds = 1))):
            return election;

    return None;

def checkVote(GUID, votesForInsertion, allVotes):
    for vote in votesForInsertion:
        if (vote.guid == GUID):
            return False;

    for vote in allVotes:
        if (vote.guid == GUID):
            return False;

    return True;

def checkPollNumber(pollNumber, electionParticipants):
    for electionPartcipant in electionParticipants:
        if (electionPartcipant.pollNumber == pollNumber):
            return True;

    return False;

def getParticipantId(pollNumber, electionId, electionParticipants):
    for electionParticipant in electionParticipants:
        if (electionParticipant.pollNumber == pollNumber and electionParticipant.electionId == electionId):
            return electionParticipant.participantId;

with application.app_context() as context:
    with Redis(host = Configuration.REDIS_HOST) as redis:
        # channel = redis.pubsub();
        # channel.subscribe(Configuration.REDIS_VOTES_CHANNEL);

        while (True):
            message = redis.rpop(Configuration.REDIS_VOTES_CHANNEL);
            # message = channel.get_message(True);

            if (message is None):
                continue;

            # data = str(message["data"])[2:-1];
            # votes = json.loads(data.replace("'", '"'));
            message = message.decode("utf-8");
            # vote = json.loads(message.replace("'", '"'));
            votes = json.loads(message.replace("'", '"'));
            print(len(votes));
            print(datetime.now());

            election = getElectionOngoing()
            if (election == None):
                # print(datetime.now() + timedelta(hours = 2));
                continue;
            # print(vote);
            # print(election.id);
            # print(datetime.now() + timedelta(hours=2));

            # votesForInsertion = [];
            # allVotes = Vote.query.all();
            # electionParticipants = ElectionParticipant.query.filter(ElectionParticipant.electionId == election.id).all();

            for vote in votes:
                GUID = vote["GUID"];
                JMBG = vote["JMBG"];
                pollNumber = int(vote["pollNumber"]);
                reasonForInvalidity = "";

                # added
                duplicateVote = Vote.query.filter(Vote.guid == GUID).first();
                pollNumberExists = ElectionParticipant.query.filter(and_(ElectionParticipant.electionId == election.id, ElectionParticipant.pollNumber == pollNumber)).first();

                if (duplicateVote):
                    reasonForInvalidity = "Duplicate ballot.";
                # elif (not checkPollNumber(pollNumber, electionParticipants)):
                elif (not pollNumberExists):
                    reasonForInvalidity = "Invalid poll number.";
                # added

                # if (not checkVote(GUID, votesForInsertion, allVotes)):
                #     reasonForInvalidity = "Duplicate ballot.";
                # elif (not checkPollNumber(pollNumber, electionParticipants)):
                #     reasonForInvalidity = "Invalid poll number.";

                newVote = Vote(guid = GUID, officialJmbg = JMBG, electionId = election.id,
                               pollNumber = pollNumber, reasonForInvalidity = reasonForInvalidity);

                # votesForInsertion.append(newVote);

                # database.session.add_all(votesForInsertion);
                database.session.add(newVote);
                database.session.commit();