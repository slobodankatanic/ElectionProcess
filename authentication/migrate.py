from flask import Flask;
from configuration import Configuration;
from flask_migrate import Migrate, init, migrate, upgrade, stamp;
from models import database, Role, UserRole, User;
from sqlalchemy_utils import create_database, database_exists;
import os;

application = Flask(__name__);
application.config.from_object(Configuration);

migrateObject = Migrate(application, database);

done = False;
while (not done):
    try:
        if (not database_exists(application.config["SQLALCHEMY_DATABASE_URI"])):
            create_database(application.config["SQLALCHEMY_DATABASE_URI"]);

        database.init_app(application);

        with application.app_context() as context:
            try:
                if (not os.path.isdir("migrations")):
                    init();
            except Exception as exception:
                print(exception);

            stamp();
            migrate(message="First migration");
            upgrade();

            adminRoleExists = Role.query.filter(Role.name == "admin").first();
            userRoleExists = Role.query.filter(Role.name == "official").first();

            if (not adminRoleExists):
                adminRole = Role(name = "admin");
                database.session.add(adminRole);
                database.session.commit();

            if (not userRoleExists):
                userRole = Role(name = "official");
                database.session.add(userRole);
                database.session.commit();

            adminExists = User.query.filter(User.email == "admin@admin.com").first();

            if (not adminExists):
                admin = User(
                    jmbg = "0000000000000",
                    email = "admin@admin.com",
                    password = "1",
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

            done = True;
    except Exception as exception:
        print(exception);