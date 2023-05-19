
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
        db.hset(unit_id, key, value)
    db.save()
    return unit_id


def del_content(db, unit_id):
    q = db.delete(str(unit_id))
    return q

