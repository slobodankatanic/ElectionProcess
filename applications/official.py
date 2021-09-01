from flask import Flask, request, Response, jsonify;
from configuration import Configuration;
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, get_jwt_identity;
from models import database, Vote;
from rightAccess import roleCheck;
import csv;
import io;
from redis import Redis;

application = Flask(__name__)
application.config.from_object(Configuration);
jwt = JWTManager(application);

@application.route("/vote", methods = ["POST"])
@roleCheck(role = "official")
def vote():
    try:
        file = request.files["file"];
    except KeyError:
        return jsonify(message = "Field file is missing."), 400;

    content = file.stream.read().decode("utf-8")
    stream = io.StringIO(content);
    reader = csv.reader(stream);

    votes = [];
    rowNumber = 0;

    for row in reader:
        try:
            if (len(row) != 2):
                return jsonify(message = f"Incorrect number of values on line {rowNumber}."), 400;

            GUID = row[0];
            pollNumber = int(row[1]);

            if (pollNumber <= 0):
                return jsonify(message = f"Incorrect poll number on line {rowNumber}."), 400;

            refreshClaims = get_jwt();
            JMBG = refreshClaims["jmbg"];

            votes.append({
                "GUID": GUID,
                "JMBG": JMBG,
                "pollNumber": str(pollNumber)
            });

            rowNumber += 1;
        except Exception:
            return jsonify(message = f"Incorrect poll number on line {rowNumber}."), 400;

    with Redis(host = Configuration.REDIS_HOST) as redis:
        redis.publish(Configuration.REDIS_VOTES_CHANNEL, str(votes));

    return Response(status = 200);

if (__name__ == "__main__"):
    database.init_app(application);
    application.run(debug = True, host = "0.0.0.0", port = 5001);