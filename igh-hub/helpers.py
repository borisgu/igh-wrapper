
def get_all_units(db):
    query = db.keys()
    return query


def is_unit_exists(db, unit_id):
    entity_state = db.exists(unit_id)
    return entity_state


def get_unit_info(db, unit_id):
    unit_info = db.hgetall(unit_id)
    unit_info["unit_id"] = unit_id
    return unit_info


def add_content(db, unit_id, content):
    content["unit_id"] = unit_id
    for key, value in content.items():
        print("Setting key {k} to val {v}".format(k=str(key),v=str(value)))
        db.hset(unit_id, key, value)
    return unit_id


def delete_unit(db, unit_id):
    q = db.delete(str(unit_id))
    return q


def update_admin_state(db, unit_id, state):
    query = db.hset(unit_id, "admin_state", state)
    return query

def set_unit_db_state(db, unit_id, is_active):
    q = db.hset(unit_id, "is_active", is_active)
    return q

def transform_unit_data(unit_info):
    
    return {
        "unit_id": unit_info["unit_id"],
        "is_active": unit_info["is_active"],
        "name": unit_info["name"],
        "last_changed": unit_info["last_changed"],
        "trigger": unit_info["trigger"]
    }