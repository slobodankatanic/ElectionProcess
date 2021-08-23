from flask import Flask;
from configuration import Configuration;
from flask_migrate import Migrate, init, migrate, upgrade;
from models import database, Role, UserRole, User;
from sqlalchemy_utils import create_database, database_exists;

application = Flask(__name__);
application.config.from_object(Configuration);

migrateObject = Migrate(application, database);

if (not database_exists(application.config["SQLALCHEMY_DATABASE_URI"])):
    create_database(application.config["SQLALCHEMY_DATABASE_URI"]);

database.init_app(application);

with application.app_context() as context:
    init();
    migrate(message = "First migration");
    upgrade();

    adminRole = Role(name = "admin");
    userRole = Role(name = "official");

    database.session.add(adminRole);
    database.session.add(userRole);
    database.session.commit();

    admin = User(
        jmbg = "2204999773615",
        email = "admin@admin.com",
        password = "123456Aa",
        forename = "admin",
        surname = "admin"
    );

    database.session.add(admin);
    database.session.commit();

    userRole = UserRole(
        userId = admin.id,
        roleId = adminRole.id
    );

    database.session.add(userRole);
    database.session.commit();