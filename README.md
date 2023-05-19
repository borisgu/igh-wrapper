# IGH Wrapper
After 3 years of waiting for proper actions from IGH (not so smart switches vendor for Smart Homes) and laziness from my side, I decided to wrap these switches (mostly the gateway that controls them).


## Motivation
The main motivation is to control the switches from HomeAssistant and get immediate indication about ths switch status.
The idea is to create `command_line` switch in HomeAssistant and wrap it with a light entity.
When I send the command directly the IGH Gateway, I don't get immediate status from the gateway. I needed to send another command to update the status of the switch.
In addition, in this `command_line` mode I needed (and still need) to scan all the switches every 10 seconds to get their status, because in case if someone changes the status of the switch manually, the HomeAssistant not notified.

## Architecture
The design is pretty simple, there are 2 services and one Redis for storing the switches info.
One service to get a REST commands and forward them to IGH Gateway and store the data into Redis and getting info from Redis once the HomeAssistant sends GET request.
The other service is a sheduler that runs every 10 seconds, gets all the status from all the switches and updates it once needed in Redis.
HomeAssistant configuration remains the same as today but, now doesn't interact with IGH Gateway but the IGH-HUB services.
Once there is a request from HomeAssistant, it's sent toward the IGH-HUB, this service sends the command to IGH Gateway and returns the status to HomeAssistant. In addition, the status in Redis, because when the HomeAssistant sends the GET status message we don't query the IGH Gateway anymore. We rely on the data from Redis.
The second scenario is when someone turns on/off the switch manually. In that case we still rely on data from Redis, because the state will always be updated by the IGH-Coordinator service (we get data every 10 seconds).

---
### Build and Use

First we need to povide some data in `docker-compose.yaml`.

To build and run the services, run:

IGH_TOKEN - api token from the IGH App.
TARGET_URL - usually the IP address of the IGH gateway
TARGET_PORT - the port of the IGH Gateway

This is the example `docker-compose.yaml`
```
---
version: "3.5"
services:
  redis-server:
    image: redis:alpine3.17
    container_name: redis-server
    restart: unless-stopped
    command: redis-server --save 20 1 --loglevel warning
    environment:
      TZ: Asia/Jerusalem
    ports:
      - "6379:6379"
    volumes:
      - ./redis/:/data

  igh-coordinator:
    image: igh-coordinator
    container_name: igh-coordinator
    build:
      context: igh-wrapper/igh-coordinator
      dockerfile: Dockerfile
    environment:
      TARGET_URL: "x.x.x.x"
      TARGET_PORT: "xxx"
      IGH_TOKEN: "get the token from the IGH app"
      REDIS_HOST: "redis-server"
      REDIS_PORT: "6379"
      TZ: Asia/Jerusalem
    restart: unless-stopped
    depends_on:
      - redis-server

  igh-hub:
    image: igh-hub
    container_name: igh-hub
    build:
      context: igh-wrapper/igh-hub
      dockerfile: Dockerfile
    ports:
      - "8081:5000"
    environment:
      TARGET_URL: "x.x.x.x"
      TARGET_PORT: "xxx"
      IGH_TOKEN: "get the token from the IGH app"
      REDIS_HOST: "redis-server"
      REDIS_PORT: "6379"
      TZ: Asia/Jerusalem
    restart: unless-stopped
    depends_on:
      - redis-server

```

Run the following command:
```
docker-compose up -d
```

---

### Current capabilities and commands:


1. Add new unit to DB: 

```
curl --location 'http://x.x.x.x:8081/unit/details/<unit_id>' \
--header 'Content-Type: application/json' \
--data '{
    "is_active": "false",
    "name": "Bathroom Light",
    "last_changed": "0",
    "trigger": "none"
```

Using this comman we can add all our units. The unit ID can me extracted from the IGH Gateway logs.
Use the IP of the machine you run the service on.

2. Update unit status:

```
curl --location 'http://x.x.x.x:8081/unit/<unit_id>' \
--header 'Content-Type: application/json' \
--data '{
    "is_active": "false"
}'
```

This is the command we are going to use in HomeAssistant to turn on/off the switches.

3. Get unit status:

```
curl --location 'hrrp://x.x.x.x:8081/unit/<unit_id>'
```

This command will be used in HomeAssistant switch as a `command_state`.

4. Get unit details:

```
curl --location 'http://x.x.x.x:8081/unit/details/<unit_id>'
```

Sometimes we want to see the the unit details, mostly for testing the HomeAssistant configuration.

---
## HomeAssistant Configuration

So now that we have all our switches in Redis, we are ready to connect our app to HomeAssistant.
The best approach I've found is wo use the `command_line` platform based switches and wrap them in light entities.

Let's start with the switch:

1. Create `switches.yaml` and inglude it in your `configuration.yaml` file. Now let's create some switch:

```
- platform: command_line
    scan_interval: 5
    switches:
      living_room:
        command_on: "curl --silent -X POST 'http://x.x.x.x:8081/unit/<unit_id>' --header 'Content-Type: application/json' --data '{\"is_active\": \"true\"}'  | jq -r .is_active"
        command_off: "curl --silent -X POST 'http://x.x.x.x:8081/unit/<unit_id>' --header 'Content-Type: application/json' --data '{\"is_active\": \"false\"}'  | jq -r .is_active"
        command_state: "curl --silent -X GET 'http://x.x.x.x:8081/unit/<unit_id>'  | jq -r .is_active"
        value_template: '{{ value }}'
        friendly_name: "Living Room"
```

I used `jq` to get only the value of `is_active` key.

2. Now we need to wrap it as a light entity. It's optional, we still can use it as a switch entity. I prefer the light entity. So it's very simple. Create `lights.yaml` file and include it in your `configuration.yaml` file. Now let's create a light entity:

```
  - platform: switch
    name: Living Room
    entity_id: switch.living_room
```

Now restart you HomeAssistant and you can create a button from the light entity.
