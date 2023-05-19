import os
from datetime import datetime, timedelta
import helpers
import redis
import requests
import logging
from apscheduler.schedulers.blocking import BlockingScheduler

now = datetime.now()
run_at = now + timedelta(seconds=10)
delay = (run_at - now).total_seconds()

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

def get_unit_state(unit_id):
    time_limit = 3

    url = "http://" + TARGET_URL + ":" + TARGET_PORT + "/unit/" + unit_id
    resp = requests.get(url, headers={"Authorization": "{}".format(API_TOKEN)},
                        timeout=time_limit)
    
    if not resp.status_code == 200:
        logging.info("Target - {target_url} returned - {status} code".format(target_url=TARGET_URL, status=resp.status_code))
        return "something went wrong", 500
    
    logging.info("This is the returned status from IGH - {}".format(resp.json()['status']))

    return resp.json()['status']

def handle_unit_state(unit_id, is_active):
    resp = get_unit_state(unit_id )
    if resp == 1 and is_active == "true":
        data_set = {
            "is_active": "false",
            "trigger": "manual",
            "last_changed": str(datetime.now())
        }
        logging.debug("Updating status in DB to actual status - {}".format(resp))
        helpers.add_content(units_db, unit_id, data_set)
        return
    elif resp == 2 and is_active == "false":
        data_set = {
            "is_active": "true",
            "trigger": "manual",
            "last_changed": str(datetime.now())
        }
        logging.debug("Updating status in DB to actual status - {}".format(resp))
        helpers.add_content(units_db, unit_id, data_set)
        return
    else:
        logging.debug("Actual status is {astat} and wanted status is {wstat}".format(astat=resp, wstat=is_active))
        return

def job():
    units = helpers.get_all_units(units_db)
    if not units:
        logging.info("No units found")
        exit()

    for unit in units:
        unit_info = helpers.get_unit_info(units_db, unit)
        unit_status = unit_info['is_active']
        unit_name = unit_info['name']
        logging.info("Running on unit id - {id}, unit name - {name}".format(id=unit, name=unit_name))
        handle_unit_state(unit, unit_status)


scheduler = BlockingScheduler()
scheduler.add_job(job, 'interval', seconds=10)
scheduler.start()

