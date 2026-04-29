from flask import Flask

from api import engine_bp


def build_payload():
    return {
        "player_team": [
            {
                "name": "迪莫",
                "hp_percent": 1.0,
                "energy": 8,
                "bloodline": "leader",
                "skills": [
                    {"name": "猛烈撞击"},
                    {"name": "闪光"},
                    {"name": "防御"},
                    {"name": "魔法增效"},
                ],
            },
            {
                "name": "火花",
                "hp_percent": 1.0,
                "energy": 5,
                "skills": [
                    {"name": "热力爆弹"},
                    {"name": "烟幕"},
                    {"name": "鼓舞"},
                    {"name": "休息回复"},
                ],
            },
        ],
        "opponent_team": [
            {
                "name": "喵喵",
                "hp_percent": 1.0,
                "energy": 6,
                "skills": [
                    {"name": "抓挠"},
                    {"name": "休息回复"},
                    {"name": "棘突"},
                    {"name": "扫尾"},
                ],
            },
            {
                "name": "水蓝蓝",
                "hp_percent": 1.0,
                "energy": 4,
                "skills": [
                    {"name": "泡沫"},
                    {"name": "水疗"},
                    {"name": "护盾"},
                    {"name": "冰冻"},
                ],
            },
        ],
        "player_active": 0,
        "opponent_active": 0,
        "turn": 3,
        "turn_prepared": True,
    }


def build_client():
    app = Flask(__name__)
    app.register_blueprint(engine_bp)
    return app.test_client()


def test_analyze_returns_action_panels():
    client = build_client()
    response = client.post("/api/analyze", json=build_payload())
    assert response.status_code == 200, response.json

    data = response.json
    assert "action_panels" in data
    assert "player" in data["action_panels"]
    assert data["action_panels"]["player"]["can_leader_evolution"] is True
    assert data["action_panels"]["player"]["switch_targets"] == [1]

    skills = data["action_panels"]["player"]["skills"]
    assert len(skills) >= 4
    assert all("current_energy_cost" in skill for skill in skills)
    assert all("is_legal" in skill for skill in skills)


def test_resolve_returns_next_turn_action_panels():
    client = build_client()
    payload = build_payload()
    payload["player_action"] = {"type": "leader_evolution"}
    payload["opponent_action"] = {"type": "switch_pet", "target_index": 1}

    response = client.post("/api/resolve", json=payload)
    assert response.status_code == 200, response.json

    data = response.json
    assert data["state"]["turn"] == 4
    assert "action_panels" in data
    assert data["action_panels"]["player"]["switch_targets"] == [1]


if __name__ == "__main__":
    test_analyze_returns_action_panels()
    test_resolve_returns_next_turn_action_panels()
    print("api action panel tests passed")
