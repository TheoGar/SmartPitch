import os

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", 60))
MQTT_QOS = 1

MATCH_ID = os.getenv("MATCH_ID", "match_001")
TOPIC_PATTERN = "smartpitch/match/{match_id}/player/{player_id}"


def get_player_topic(match_id: str, player_id: int) -> str:
    return TOPIC_PATTERN.format(match_id=match_id, player_id=player_id)


def get_subscribe_pattern(match_id: str) -> str:
    return f"smartpitch/match/{match_id}/player/+"
