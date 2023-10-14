from asyncio.log import logger
import os
import logging
import requests
import redis
import helpers
import datetime
from flask import Flask, request, jsonify


application = Flask(__name__)
application.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

VERSION = '0.0.1'

TARGET_URL = os.environ.get('TARGET_URL')
TARGET_PORT = os.environ.get('TARGET_PORT')
API_TOKEN = os.environ.get('IGH_TOKEN')

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

units_db = redis.StrictRedis(
    host=os.environ.get('REDIS_HOST'),
    port=os.environ.get('REDIS_PORT'),
    db=0,
    decode_responses=True
)


@application.route('/unit/details/<unit_id>', methods=['GET', 'POST', 'DELETE', 'PATCH'])
def unit_details(unit_id=None):
    if request.method == 'GET':
        if not helpers.is_unit_exists(units_db, unit_id):
            return jsonify({"message": "unit not found"}), 404

        unit_info = helpers.get_unit_info(units_db, unit_id)
        logger.info("This is the unit from db = {}".format(unit_info))
        unit = helpers.transform_unit_data(unit_info)
        logger.info("This is the unit after transform = {}".format(unit))
        return jsonify(unit), 200

    if request.method == 'POST':
        if not helpers.is_unit_exists(units_db, unit_id):
            name = request.get_json().get('name')

            data_set = {
                "is_active": "false",
                "name": name,
                "last_changed": str(datetime.datetime.now()),
                "trigger": "none"
            }

            helpers.add_content(units_db, unit_id, data_set)

            return jsonify(unit_id), 200

        return jsonify("unit already exists"), 500

    if request.method == 'DELETE':
        if not helpers.is_unit_exists(units_db, unit_id):
            return jsonify({"message": "unit not found"}), 404

        helpers.delete_unit(units_db, unit_id)
        
        return jsonify("deleted", unit_id), 200

    if request.method == 'PATCH':
        if helpers.is_unit_exists(units_db, unit_id):
            content = request.get_json(silent=False)
            helpers.add_content(units_db, unit_id,
                                content)
            return jsonify({"unit_id": unit_id, "update_status": "ok"}), 200

        return jsonify({"message": "unit not found"}), 404


@application.route('/unit/<unit_id>', methods=['GET', 'POST'])
def unit(unit_id=None):
    if (unit_id == "None"): 
        return jsonify({"message": "missing unit id"}), 500

    if not helpers.is_unit_exists(units_db, unit_id):
        return jsonify({"message": "unit not found"}), 404
    
    if request.method == 'GET':
        unit_state = helpers.get_unit_info(units_db, unit_id)
        logger.info("This is the state of {unit} in DB {status}".format(status=unit_state["is_active"], unit=unit_id))
        data_set = {
                "is_active": unit_state["is_active"]
            }
        return data_set, 200
        # return get_unit_state(TARGET_URL, TARGET_PORT, unit_id, API_TOKEN), 200

    if request.method == 'POST':
        # Handle cover type units
        if request.get_json().get('type') == "cover":
            logger.info("Unit type is cover - handling cover state")
            action = request.get_json().get('action')
            if action == "stop":
                last_action = helpers.get_unit_info(units_db, unit_id)
                response = set_unit_state(TARGET_URL, TARGET_PORT, unit_id, "", API_TOKEN, "cover", last_action['action']), 200
                if not response[0]:
                    logging.info("Returned status from IGH is {}".format(response[0]))
                    return jsonify(data_set), 200
                
                return jsonify({'action': last_action['action']}), 200

            response = set_unit_state(TARGET_URL, TARGET_PORT, unit_id, "", API_TOKEN, "cover", action), 200
            data_set = {
                    "action": action,
                    "last_changed": str(datetime.datetime.now())
                }
            if not response[0]:
                logging.info("Returned status from IGH is {}".format(response[0]))
                return jsonify(data_set), 200

            helpers.add_content(units_db, unit_id, data_set)
            return jsonify({'action': action}), 200
            
        logger.info("Request to set active state to {state} by REST on unit - {unit}".format(state=request.get_json().get('is_active'), unit=unit_id))
        is_active = request.get_json().get('is_active')
        response = set_unit_state(TARGET_URL, TARGET_PORT, unit_id, is_active, API_TOKEN), 200
        logger.info("This is the response {}".format(response[0]))
        data_set = {
                "is_active": is_active,
                "trigger": "rest",
                "last_changed": str(datetime.datetime.now())
            }
        if not response[0]:
            logging.info("Returned status from IGH is {}".format(response[0]))
            return jsonify(data_set)
        helpers.add_content(units_db, unit_id, data_set)
        helpers.set_unit_db_state(units_db, unit_id, is_active)
        return jsonify({'is_active': is_active}), 200

def set_unit_state(target, port, unit_id, is_active, api_token, type='switch', action='open'):
    time_limit = 3

    if type == "cover":
        logger.info("Setting action state to {} on IGH gateway".format(action))
    else:
        logger.info("Setting is_active state to {} on IGH gateway".format(is_active))    
    
    if (is_active == "true" or action == "open"):
        url = "http://" + target + ":" + port + "/unit/" + unit_id + "?on=100"
    else:
        url = "http://" + target + ":" + port + "/unit/" + unit_id + "?on=0"
    
    resp = requests.post(url, headers={"Authorization": "{}".format(api_token)}, json="{}", 
                        timeout=time_limit)
    
    if not resp.status_code == 200:
        logging.info("Target - {target_url} returned - {status} code".format(target_url=target, status=resp.status_code))
        return jsonify("something wrong")

    logging.info("This is the status code - {}".format(resp.status_code))
    
    if resp.status_code == 200:
        return True
    else:
        return False



if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", True)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5000)
    application.run(host='0.0.0.0', port=ENVIRONMENT_PORT,
                    debug=ENVIRONMENT_DEBUG)

