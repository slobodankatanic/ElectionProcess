from flask import Flask;
from redis import Redis;
from applications.configuration import Configuration;
from applications.models import database, Election, ElectionParticipant, Vote, Participant;
from datetime import datetime;
import json;

application = Flask(__name__);
application.config.from_object(Configuration);
database.init_app(application);

def getElectionOngoing():
    elections = Election.query.all();

    for election in elections:
        if (election.start <= datetime.now() and election.end > datetime.now()):
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
        channel = redis.pubsub();
        channel.subscribe(Configuration.REDIS_VOTES_CHANNEL);

        while (True):
            message = channel.get_message(True);

            if (message is None):
                continue;

            print("malo preee")

            data = str(message["data"])[2:-1];
            votes = json.loads(data.replace("'", '"'));

            print(votes);

            print("pre")

            election = getElectionOngoing()
            if (election == None):
                print("nema tren")
                continue;

            print("pocelo glasanje")

            votesForInsertion = [];
            allVotes = Vote.query.all();
            electionParticipants = ElectionParticipant.query.filter(ElectionParticipant.electionId == election.id).all();

            for vote in votes:
                GUID = vote["GUID"];
                JMBG = vote["JMBG"];
                pollNumber = int(vote["pollNumber"]);
                reasonForInvalidity = "";
                # participantId = Configuration.PARTICIPANT_FOR_VOTING_ID;

                if (not checkVote(GUID, votesForInsertion, allVotes)):
                    reasonForInvalidity = "Duplicate ballot.";
                elif (not checkPollNumber(pollNumber, electionParticipants)):
                    reasonForInvalidity = "Invalid poll number.";
                # else:
                #     participantId = getParticipantId(pollNumber, election.id, electionParticipants);

                newVote = Vote(guid = GUID, officialJmbg = JMBG, electionId = election.id,
                               pollNumber = pollNumber, reasonForInvalidity = reasonForInvalidity);

                votesForInsertion.append(newVote);

            database.session.add_all(votesForInsertion);
            database.session.commit();