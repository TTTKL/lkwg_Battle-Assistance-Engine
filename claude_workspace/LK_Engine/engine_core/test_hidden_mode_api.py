import unittest

import api


class HiddenModeApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pet_name = None
        cls.learnable_skills = []
        for name, template in api.engine.data_loader.pets.items():
            skills = api._normalize_skill_names(getattr(template, "learnable_skills", []))
            if len(skills) >= 5:
                cls.pet_name = name
                cls.learnable_skills = skills
                break
        if cls.pet_name is None:
            raise RuntimeError("未找到可用于隐藏模式测试的精灵样本")

    def test_hidden_projection_keeps_observed_skill_and_drops_nature(self):
        observed_skill = self.learnable_skills[4]
        payload = {
            "name": self.pet_name,
            "skills": [{"name": skill_name} for skill_name in self.learnable_skills[:4]],
            "hp_percent": 1.0,
            "energy": 6,
            "nature": "保守",
            "iv": {"生命": 10, "物攻": 10, "魔攻": 10, "物防": 10, "魔防": 10, "速度": 10},
        }
        projected, meta = api._project_hidden_pet_payload(
            payload,
            {
                "observed_skills": [observed_skill],
                "iv_constraints": {
                    "speedIvMin": 1,
                    "speedIvMax": 3,
                },
            },
        )

        projected_skill_names = [item["name"] for item in projected["skills"]]
        self.assertIn(observed_skill, projected_skill_names)
        self.assertLessEqual(len(projected_skill_names), 4)
        self.assertNotIn("nature", projected)
        self.assertEqual(meta["observed_skill_count"], 1)
        self.assertGreaterEqual(meta["predicted_skill_count"], 0)
        self.assertTrue(meta["skills"])
        self.assertIn("prediction_source", meta["skills"][0])
        self.assertIn("estimated_stats", meta)
        self.assertIn("stat_ranges", meta)

    def test_hidden_projection_respects_iv_constraints(self):
        payload = {
            "name": self.pet_name,
            "skills": [{"name": skill_name} for skill_name in self.learnable_skills[:4]],
            "hp_percent": 1.0,
            "energy": 10,
            "iv": {"生命": 10, "物攻": 10, "魔攻": 10, "物防": 10, "魔防": 10, "速度": 10},
        }
        projected, meta = api._project_hidden_pet_payload(
            payload,
            {
                "observed_skills": [],
                "iv_constraints": {
                    "atkIvMin": 0,
                    "atkIvMax": 2,
                    "speedIvMin": 4,
                    "speedIvMax": 6,
                },
            },
        )

        self.assertGreaterEqual(projected["iv"]["物攻"], 0)
        self.assertLessEqual(projected["iv"]["物攻"], 2)
        self.assertGreaterEqual(projected["iv"]["速度"], 4)
        self.assertLessEqual(projected["iv"]["速度"], 6)
        self.assertLessEqual(meta["iv_profile"]["min"], meta["iv_profile"]["max"])


if __name__ == "__main__":
    unittest.main()
