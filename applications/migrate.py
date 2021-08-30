from flask import Flask
from flask_migrate import Migrate, migrate, init, upgrade;
from applications.configuration import Configuration
from applications.models import database, Participant;
from sqlalchemy_utils import database_exists, create_database;

application = Flask(__name__);
application.config.from_object(Configuration);

migrateObject = Migrate(application, database);

if (not database_exists(Configuration.SQLALCHEMY_DATABASE_URI)):
    create_database(Configuration.SQLALCHEMY_DATABASE_URI);

database.init_app(application);

with application.app_context() as context:
    init();
    migrate(message = "First migration");
    upgrade();

    participant = Participant(id = 1000, name = "__participant_for_invalid_votes__", type = 1);
    database.session.add(participant);
    database.session.commit();
