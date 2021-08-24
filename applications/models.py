from flask_sqlalchemy import SQLAlchemy

database = SQLAlchemy();

class Election (database.Model):
    __tablename__ = "elections";

    id = database.Column(database.Integer, primary_key = True);
    start = database.Column(database.DateTime, nullable = False);
    end = database.Column(database.DateTime, nullable = False);
    type = database.Column(database.Integer, nullable = False); # 0 - parlam. 1 - presid.

    votes = database.relationship("Vote", back_populates = "elections");

class Participant (database.Model):
    __tablename__ = "participants";

    id = database.Column(database.Integer, primary_key = True);
    name = database.Column(database.String(256), nullable = False);
    type = database.Column(database.Integer, nullable = False);  # 0 - party 1 - indiv.

    votes = database.relationship("Vote", back_populates = "participant");

class Vote (database.Model):
    __tablename__ = "votes";

    id = database.Column(database.Integer, primary_key = True);
    officialJmbg = database.Column(database.String(13), nullable = False);
    electionId = database.Column(database.Integer, database.ForeignKey("elections.id"), nullable = False);
    participantId = database.Column(database.Integer, database.ForeignKey("participants.id"), nullable = False);

    election = database.relationship("Election", back_populates = "votes");
    participant = database.relationship("Participant", back_populates = "votes");