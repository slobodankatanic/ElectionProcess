
class Configuration:
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:root@localhost:3307/election_process";
    REDIS_HOST = "localhost";
    REDIS_VOTES_CHANNEL = "votes";
    JWT_SECRET_KEY = "MY_SECRET_KEY";
    PARTICIPANT_FOR_VOTING_ID = 1000;