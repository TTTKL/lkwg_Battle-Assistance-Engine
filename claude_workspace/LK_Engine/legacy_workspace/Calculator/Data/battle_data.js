var _BATTLE_RAW={
  "rules": {
    "version": "1.0",
    "initial_energy": 10,
    "priority_rules": [
      "1. 先手等级高的先行动",
      "2. 先手等级相同或均为0：速度快的先行动",
      "3. 速度一致：随机先手"
    ],
    "damage_formula": {
      "simple": "进攻方攻击 / 防御方防御 × 0.9 × 显示威力 × 不稳定加成 × 连击数 × (1 - 减伤)",
      "detailed": "进攻方攻击 / 防御方防御 × 0.9 × (技能威力 × 应对倍率 + 威力加成) × 能力等级 × 威力提升buff × 本系加成 × 克制关系 × 天气影响 × (1 - 减伤)",
      "ability_level": "(1 + 我方攻击提升 + 敌方防御降低) / (1 + 我方攻击降低 + 敌方防御提升)",
      "notes": [
        "显示威力 = 技能右下角威力，已自动计算各种加成",
        "不稳定触发的效果不自动计入显示威力（应对成功的倍率提升、风起印记等）",
        "多个减伤效果互相之间乘算",
        "本系加成：技能属性与精灵属性相同时×1.5"
      ]
    },
    "buff_rules": {
      "definition": "增加属性、技能威力、连击数，以及降低能耗、吸血、过载等效果（不包括印记、特性、其他类效果）",
      "stack_rule": "获得魔攻+70%代表获得10%魔攻buff×7层",
      "clear_on_switch": true,
      "clear_on_battle_end": true,
      "buff_per_layer": 0.1
    },
    "counter_system": {
      "应对防御": {
        "trigger": "敌方使用防御技能",
        "effect": "本次行动必定先手，且触发应对效果"
      },
      "应对攻击": {
        "trigger": "敌方使用攻击技能",
        "effect": "本次行动必定先手，且触发应对效果",
        "side_effect": "使用后，携带的防御技能进入1回合冷却"
      },
      "应对状态": {
        "trigger": "敌方使用状态技能",
        "effect": "本次行动必定先手，且触发应对效果"
      }
    },
    "defense_rules": {
      "duration": "当回合",
      "note": "防御类技能的减伤效果仅在当回合生效"
    }
  },
  "skills": {
    "冰锋横扫": {
      "damage_type": "magical",
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "dynamic_power",
          "desc": "造成魔伤，本技能威力等于敌方精灵技能总能耗的10倍。",
          "note": "Runtime calculation needed"
        }
      ],
      "counters": [],
      "element": "冰",
      "category": "魔攻"
    },
    "抓挠": {
      "damage_type": "physical",
      "base_power": 35,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 1
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "猛烈撞击": {
      "damage_type": "physical",
      "base_power": 65,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "飞踢": {
      "damage_type": "physical",
      "base_power": 110,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "扫尾": {
      "damage_type": "physical",
      "base_power": 90,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "迫近攻击": {
      "damage_type": "physical",
      "base_power": 90,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 45
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "音爆": {
      "damage_type": "magical",
      "base_power": 130,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "冲撞": {
      "damage_type": "physical",
      "base_power": 135,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": -1
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "见招拆招": {
      "damage_type": "physical",
      "base_power": 65,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 55,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "触底强击": {
      "damage_type": "magical",
      "base_power": 65,
      "energy_cost": 110,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 110,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "突袭": {
      "damage_type": "magical",
      "base_power": 70,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_multiply",
          "value": 3,
          "conditional": true
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力变为3倍",
          "effects": [
            {
              "type": "power_multiply",
              "value": 3
            }
          ]
        }
      ],
      "element": "普通",
      "category": "魔攻"
    },
    "连续爪击": {
      "damage_type": "physical",
      "base_power": 30,
      "energy_cost": 2,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能连击数翻倍",
          "effects": [
            {
              "type": "hits_multiply",
              "value": 2
            }
          ]
        }
      ],
      "element": "普通",
      "category": "物攻"
    },
    "追打": {
      "damage_type": "magical",
      "base_power": 75,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本技能变为3连击",
          "effects": [
            {
              "type": "hits_set",
              "value": 3
            }
          ]
        }
      ],
      "element": "普通",
      "category": "魔攻"
    },
    "旋转突击": {
      "damage_type": "physical",
      "base_power": 35,
      "energy_cost": 3,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "偷袭": {
      "damage_type": "physical",
      "base_power": 85,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_multiply",
          "value": 3,
          "conditional": true
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力变为3倍",
          "effects": [
            {
              "type": "power_multiply",
              "value": 3
            }
          ]
        }
      ],
      "element": "普通",
      "category": "物攻"
    },
    "乱打": {
      "damage_type": "magical",
      "base_power": 25,
      "energy_cost": 4,
      "hits": 5,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "乘胜追击": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "阻断": {
      "damage_type": "magical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "额外打断被应对技能",
          "effects": []
        }
      ],
      "element": "普通",
      "category": "魔攻"
    },
    "穿膛": {
      "damage_type": "physical",
      "base_power": 65,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "重击": {
      "damage_type": "physical",
      "base_power": 110,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": 1
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "魔能爆": {
      "damage_type": "magical",
      "base_power": 1,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "consume_all_energy",
          "power_per_energy": 21,
          "note": "Power = 1 + consumed energy × 21"
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "垂死反击": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "power_scaling": {
        "type": "self_hp_lost",
        "per_5_percent": 5
      },
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "能量刃": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 90
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "气势一击": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 180,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "吞噬": {
      "damage_type": "physical",
      "base_power": 150,
      "energy_cost": 6,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 6
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "蓄能轰击": {
      "damage_type": "magical",
      "base_power": 130,
      "energy_cost": 6,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": -2
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "力量增效": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 10,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "魔法增效": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 7,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "休息回复": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "heal",
          "target": "self",
          "percent": 0.3
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "聒噪": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "激怒": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "咆哮": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "atk",
          "layers": 13,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "锐利眼神": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "def",
          "layers": 12,
          "per_layer": 0.1
        },
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "mdef",
          "layers": 12,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "快速移动": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff_flat",
          "target": "self",
          "stat": "spd",
          "value": 80
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为速度+160",
          "effects": [
            {
              "type": "buff_flat",
              "target": "self",
              "stat": "spd",
              "value": 160
            }
          ]
        }
      ],
      "element": "普通",
      "category": "状态"
    },
    "伺机而动": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "主场优势": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "操控": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "应激反应": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "heal",
          "target": "self",
          "percent": 0.25
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为回复50%生命",
          "effects": [
            {
              "type": "heal",
              "target": "self",
              "percent": 0.5
            }
          ]
        }
      ],
      "element": "普通",
      "category": "状态"
    },
    "棘刺": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "精神扰乱": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为能耗+3",
          "effects": []
        }
      ],
      "element": "普通",
      "category": "状态"
    },
    "退化": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "防反": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.6,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 4,
          "per_layer": 0.1
        },
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 4,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己获得物攻和魔攻+40%",
          "effects": [
            {
              "type": "buff",
              "target": "self",
              "stat": "atk",
              "layers": 4,
              "per_layer": 0.1
            },
            {
              "type": "buff",
              "target": "self",
              "stat": "matk",
              "layers": 4,
              "per_layer": 0.1
            }
          ]
        }
      ],
      "element": "普通",
      "category": "防御"
    },
    "血气": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.6,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "本回合受到致命伤害时",
          "effects": []
        }
      ],
      "element": "普通",
      "category": "防御"
    },
    "无畏之心": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 1.0,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": 2
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "减免的伤害变为回复自己生命",
          "effects": []
        }
      ],
      "element": "普通",
      "category": "防御"
    },
    "借用": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "取念": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "复写": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "落星": {
      "damage_type": "physical",
      "base_power": 45,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "拍击": {
      "damage_type": "magical",
      "base_power": 65,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "音波弹": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "许愿星": {
      "damage_type": "magical",
      "base_power": 110,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "星星撞击": {
      "damage_type": "magical",
      "base_power": 90,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "能量炮": {
      "damage_type": "magical",
      "base_power": 50,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "压扁": {
      "damage_type": "physical",
      "base_power": 155,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "践踏": {
      "damage_type": "physical",
      "base_power": 130,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "湮灭": {
      "damage_type": "magical",
      "base_power": 155,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "打鼾": {
      "damage_type": "magical",
      "base_power": 165,
      "energy_cost": 6,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "先发制人": {
      "damage_type": "physical",
      "base_power": 55,
      "energy_cost": 2,
      "hits": 1,
      "priority": 1,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "天旋地转": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 3,
      "hits": 1,
      "priority": 1,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 30,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "吨位压制": {
      "damage_type": "physical",
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "以重制重": {
      "damage_type": "physical",
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "当头棒喝": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 100,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "后发制人": {
      "damage_type": "physical",
      "base_power": 155,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "加固": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "def",
          "layers": 14,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "鼓劲": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "mdef",
          "layers": 17,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "耀眼": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "彗星": {
      "damage_type": "magical",
      "base_power": 240,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "power_scaling": {
        "type": "self_hp_lost",
        "per_5_percent": -10
      },
      "effects": [
        {
          "type": "self_damage",
          "target": "self",
          "value": 9999
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "消毒法": {
      "damage_type": "magical",
      "base_power": 115,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "三连破": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 3,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "热身运动": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "晒太阳": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "有效预防": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 1,
      "damage_reduction": 0.5,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "下一次行动获得先手+1",
          "effects": [
            {
              "type": "priority_bonus",
              "value": 1
            }
          ]
        }
      ],
      "element": "普通",
      "category": "防御"
    },
    "嗜痛": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 4,
          "per_layer": 0.1
        },
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 4,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "期间自己每次受到伤害",
          "effects": []
        }
      ],
      "element": "普通",
      "category": "防御"
    },
    "吓退": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.6,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "敌方脱离",
          "effects": [
            {
              "type": "force_switch"
            }
          ]
        }
      ],
      "element": "普通",
      "category": "防御"
    },
    "埋伏": {
      "damage_type": "magical",
      "base_power": 30,
      "energy_cost": 4,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "逆袭": {
      "damage_type": "physical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "摇篮曲": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "stun",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "额外造成打断",
          "effects": []
        }
      ],
      "element": "普通",
      "category": "状态"
    },
    "倾泻": {
      "damage_type": "magical",
      "base_power": 70,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "魔攻"
    },
    "种子弹": {
      "damage_type": "physical",
      "base_power": 30,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 1
        }
      ],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "荆棘爪": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "仙人掌刺击": {
      "damage_type": "physical",
      "base_power": 150,
      "energy_cost": 6,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "刺藤": {
      "damage_type": "physical",
      "base_power": 45,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "藤绞": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 5
        }
      ],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "光能聚集": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 60
        }
      ],
      "counters": [],
      "element": "草",
      "category": "魔攻"
    },
    "徒长": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 10,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 10
        }
      ],
      "counters": [],
      "element": "草",
      "category": "状态"
    },
    "盛开": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为威力+60",
          "effects": []
        }
      ],
      "element": "草",
      "category": "状态"
    },
    "根吸收": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 15,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "heal",
          "target": "self",
          "percent": 0.15
        }
      ],
      "counters": [],
      "element": "草",
      "category": "状态"
    },
    "氧输送": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 7,
          "per_layer": 0.1
        },
        {
          "type": "energy_restore",
          "target": "self",
          "value": 4
        }
      ],
      "counters": [],
      "element": "草",
      "category": "状态"
    },
    "孢子": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "状态"
    },
    "芳香诱引": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "stun",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "额外造成打断",
          "effects": []
        }
      ],
      "element": "草",
      "category": "状态"
    },
    "丰饶": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 14,
          "per_layer": 0.1
        },
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 14,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "草",
      "category": "状态"
    },
    "移花接木": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "heal",
          "target": "self",
          "percent": 0.15
        }
      ],
      "counters": [],
      "element": "草",
      "category": "状态"
    },
    "光合作用": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "状态"
    },
    "酶浓度调整": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [
        {
          "type": "heal",
          "target": "self",
          "percent": 0.2
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己回复20%生命",
          "effects": [
            {
              "type": "heal",
              "target": "self",
              "percent": 0.2
            }
          ]
        }
      ],
      "element": "草",
      "category": "防御"
    },
    "蜡质膜": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 80,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 3
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "回复3能量",
          "effects": [
            {
              "type": "energy_restore",
              "target": "self",
              "value": 3
            }
          ]
        }
      ],
      "element": "草",
      "category": "防御"
    },
    "汲取": {
      "damage_type": "magical",
      "base_power": 30,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "魔攻"
    },
    "飞叶": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "种皮爆裂": {
      "damage_type": "physical",
      "base_power": 25,
      "energy_cost": 1,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "花香": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "魔攻"
    },
    "棘突": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "魔攻"
    },
    "孢子爆散": {
      "damage_type": "physical",
      "base_power": 30,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "叶绿光束": {
      "damage_type": "magical",
      "base_power": 120,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "魔攻"
    },
    "顶端优势": {
      "damage_type": "physical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "筛管奔流": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 75,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "花炮": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 6,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "草",
      "category": "状态"
    },
    "聚盐": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "heal",
          "target": "self",
          "percent": 0.05
        }
      ],
      "counters": [],
      "element": "草",
      "category": "状态"
    },
    "富养化": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 3
        }
      ],
      "counters": [],
      "element": "草",
      "category": "状态"
    },
    "纤维化": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "def",
          "layers": 7,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己获得物防+70%",
          "effects": [
            {
              "type": "buff",
              "target": "self",
              "stat": "def",
              "layers": 7,
              "per_layer": 0.1
            }
          ]
        }
      ],
      "element": "草",
      "category": "防御"
    },
    "抽枝": {
      "damage_type": "physical",
      "base_power": 90,
      "energy_cost": 50,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "heal",
          "target": "self",
          "percent": 0.5
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "自己回复50%生命和5能量",
          "effects": [
            {
              "type": "heal",
              "target": "self",
              "percent": 0.5
            }
          ]
        }
      ],
      "element": "草",
      "category": "物攻"
    },
    "针刺射击": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "火焰冲锋": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "物攻"
    },
    "炎枪": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "火苗": {
      "damage_type": "physical",
      "base_power": 30,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 1
        }
      ],
      "counters": [],
      "element": "火",
      "category": "物攻"
    },
    "闪燃": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_multiply",
          "value": 4,
          "conditional": true
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力变为4倍",
          "effects": [
            {
              "type": "power_multiply",
              "value": 4
            }
          ]
        }
      ],
      "element": "火",
      "category": "物攻"
    },
    "双响炮": {
      "damage_type": "physical",
      "base_power": 25,
      "energy_cost": 1,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "物攻"
    },
    "吹火": {
      "damage_type": "physical",
      "base_power": 50,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 20
        }
      ],
      "counters": [],
      "element": "火",
      "category": "物攻"
    },
    "流星火雨": {
      "damage_type": "physical",
      "base_power": 75,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 75
        }
      ],
      "counters": [],
      "element": "火",
      "category": "物攻"
    },
    "持续高温": {
      "damage_type": "magical",
      "base_power": 70,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "下次攻击技能威力翻倍",
          "effects": []
        }
      ],
      "element": "火",
      "category": "魔攻"
    },
    "易燃物质": {
      "damage_type": "magical",
      "base_power": 30,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "burn",
          "layers": 2,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "高温回火": {
      "damage_type": "magical",
      "base_power": 40,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "山火": {
      "damage_type": "physical",
      "base_power": 15,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "物攻"
    },
    "引燃": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "burn",
          "layers": 10,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "火",
      "category": "状态"
    },
    "热身": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_multiply",
          "value": 4,
          "conditional": true
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为威力变为4倍",
          "effects": [
            {
              "type": "power_multiply",
              "value": 4
            }
          ]
        }
      ],
      "element": "火",
      "category": "状态"
    },
    "充分燃烧": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "burn",
          "layers": 1,
          "target": "enemy"
        }
      ],
      "counters": [],
      "element": "火",
      "category": "状态"
    },
    "天火": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "burn",
          "layers": 10,
          "target": "self"
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为获得30层",
          "effects": []
        }
      ],
      "element": "火",
      "category": "状态"
    },
    "火焰护盾": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.7,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "burn",
          "layers": 6,
          "target": "self"
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "敌方获得6层灼烧",
          "effects": []
        }
      ],
      "element": "火",
      "category": "防御"
    },
    "火云车": {
      "damage_type": "physical",
      "base_power": 140,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "物攻"
    },
    "爆裂飞弹": {
      "damage_type": "magical",
      "base_power": 160,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "热气": {
      "damage_type": "magical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "流火": {
      "damage_type": "magical",
      "base_power": 15,
      "energy_cost": 1,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "火爪": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "火焰箭": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "物攻"
    },
    "炙热波动": {
      "damage_type": "magical",
      "base_power": 55,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "burn",
          "layers": 4,
          "target": "self"
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力和赋予灼烧翻倍",
          "effects": []
        }
      ],
      "element": "火",
      "category": "魔攻"
    },
    "火焰切割": {
      "damage_type": "physical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "物攻"
    },
    "烈焰风暴": {
      "damage_type": "magical",
      "base_power": 75,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "burn",
          "layers": 6,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "炎息": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "物攻"
    },
    "灼伤": {
      "damage_type": "physical",
      "base_power": 120,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "物攻"
    },
    "炎打": {
      "damage_type": "magical",
      "base_power": 95,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "怒火": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 12,
          "per_layer": 0.1
        },
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 12,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "火",
      "category": "状态"
    },
    "淬火": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "下次攻击技能威力翻倍",
          "effects": []
        }
      ],
      "element": "火",
      "category": "防御"
    },
    "燃尽": {
      "damage_type": "magical",
      "base_power": 155,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "power_scaling": {
        "type": "enemy_hp_lost",
        "per_5_percent": -5
      },
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "焚毁": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "焚烧烙印": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "burn",
          "layers": 5,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "火",
      "category": "状态"
    },
    "除厄": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "阳火增辉": {
      "damage_type": "magical",
      "base_power": 75,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "火",
      "category": "魔攻"
    },
    "甩水": {
      "damage_type": "magical",
      "base_power": 30,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 1
        }
      ],
      "counters": [],
      "element": "水",
      "category": "魔攻"
    },
    "水弹枪": {
      "damage_type": "magical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "魔攻"
    },
    "气泡": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "魔攻"
    },
    "水炮": {
      "damage_type": "magical",
      "base_power": 110,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": -1
        }
      ],
      "counters": [],
      "element": "水",
      "category": "魔攻"
    },
    "水刃": {
      "damage_type": "physical",
      "base_power": 115,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": -4
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本技能能耗永久-4",
          "effects": []
        }
      ],
      "element": "水",
      "category": "物攻"
    },
    "天洪": {
      "damage_type": "magical",
      "base_power": 150,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": -6
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本技能能耗永久-6",
          "effects": []
        }
      ],
      "element": "水",
      "category": "魔攻"
    },
    "润泽": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 19,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "水",
      "category": "状态"
    },
    "蓄水": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "状态"
    },
    "打湿": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "状态"
    },
    "落雨": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "状态"
    },
    "泡沫幻影": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己脱离",
          "effects": []
        }
      ],
      "element": "水",
      "category": "防御"
    },
    "水泡盾": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 7,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己获得魔攻+70%",
          "effects": [
            {
              "type": "buff",
              "target": "self",
              "stat": "matk",
              "layers": 7,
              "per_layer": 0.1
            }
          ]
        }
      ],
      "element": "水",
      "category": "防御"
    },
    "水环": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.6,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己获得全技能能耗-2",
          "effects": []
        }
      ],
      "element": "水",
      "category": "防御"
    },
    "水光冲击": {
      "damage_type": "magical",
      "base_power": 140,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "魔攻"
    },
    "水波术": {
      "damage_type": "magical",
      "base_power": 90,
      "energy_cost": 6,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 20
        }
      ],
      "counters": [],
      "element": "水",
      "category": "魔攻"
    },
    "水弹": {
      "damage_type": "magical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "魔攻"
    },
    "泡沫": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "物攻"
    },
    "肥皂泡": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "魔攻"
    },
    "水花四溅": {
      "damage_type": "magical",
      "base_power": 20,
      "energy_cost": 3,
      "hits": 4,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "魔攻"
    },
    "潮涌": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "物攻"
    },
    "水幕冲击": {
      "damage_type": "physical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "物攻"
    },
    "激流": {
      "damage_type": "magical",
      "base_power": 120,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "魔攻"
    },
    "涌泉": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 6,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "魔攻"
    },
    "洗礼": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "状态"
    },
    "盐水浴": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为技能能耗-3",
          "effects": []
        }
      ],
      "element": "水",
      "category": "状态"
    },
    "潮汐": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.6,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己获得1层湿润印记",
          "effects": [
            {
              "type": "add_mark",
              "target": "self",
              "mark_name": "湿润印记",
              "stacks": 1
            }
          ]
        }
      ],
      "element": "水",
      "category": "防御"
    },
    "闪光": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "魔攻"
    },
    "闪光冲击": {
      "damage_type": "physical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "物攻"
    },
    "过曝": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 30
        }
      ],
      "counters": [],
      "element": "光",
      "category": "魔攻"
    },
    "折射": {
      "damage_type": "magical",
      "base_power": 50,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "魔攻"
    },
    "漫反射": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "状态"
    },
    "镜像反射": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.7,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "本技能变为被应对的技能",
          "effects": []
        }
      ],
      "element": "光",
      "category": "防御"
    },
    "光球": {
      "damage_type": "magical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "魔攻"
    },
    "光之矛": {
      "damage_type": "physical",
      "base_power": 30,
      "energy_cost": 3,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "物攻"
    },
    "光刃": {
      "damage_type": "physical",
      "base_power": 120,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "物攻"
    },
    "脉冲光线": {
      "damage_type": "magical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "魔攻"
    },
    "虹光冲击": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "魔攻"
    },
    "折线冲击": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "物攻"
    },
    "天光": {
      "damage_type": "magical",
      "base_power": 95,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "魔攻"
    },
    "透射": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "光",
      "category": "物攻"
    },
    "放晴": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 50
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为永久+100%",
          "effects": []
        }
      ],
      "element": "光",
      "category": "状态"
    },
    "械斗": {
      "damage_type": "physical",
      "base_power": 45,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "机械",
      "category": "物攻"
    },
    "齿轮扭矩": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 20
        }
      ],
      "counters": [],
      "element": "机械",
      "category": "物攻"
    },
    "钢钻": {
      "damage_type": "physical",
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "机械",
      "category": "物攻"
    },
    "钢铁洪流": {
      "damage_type": "physical",
      "base_power": 70,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "机械",
      "category": "物攻"
    },
    "杠杆置换": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 2
        }
      ],
      "counters": [],
      "element": "机械",
      "category": "状态"
    },
    "轴承支撑": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "机械",
      "category": "状态"
    },
    "联动装置": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 20
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "变为威力永久+30",
          "effects": []
        }
      ],
      "element": "机械",
      "category": "状态"
    },
    "能量守恒": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": -1
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "两侧技能能耗永久-1",
          "effects": []
        }
      ],
      "element": "机械",
      "category": "防御"
    },
    "拆卸": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "机械",
      "category": "物攻"
    },
    "离子震荡": {
      "damage_type": "magical",
      "base_power": 90,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "机械",
      "category": "魔攻"
    },
    "传感器": {
      "damage_type": "physical",
      "base_power": 20,
      "energy_cost": 1,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "机械",
      "category": "物攻"
    },
    "金属噪音": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "机械",
      "category": "魔攻"
    },
    "磁暴": {
      "damage_type": "magical",
      "base_power": 70,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "机械",
      "category": "魔攻"
    },
    "齿轮切开": {
      "damage_type": "physical",
      "base_power": 130,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "机械",
      "category": "物攻"
    },
    "主轴": {
      "damage_type": "physical",
      "base_power": 75,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "机械",
      "category": "物攻"
    },
    "啮合传递": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff_flat",
          "target": "self",
          "stat": "spd",
          "value": 80
        },
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 6,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "机械",
      "category": "状态"
    },
    "扬沙": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "物攻"
    },
    "跺地": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "物攻"
    },
    "地刺": {
      "damage_type": "physical",
      "base_power": 95,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "额外打断被应对技能",
          "effects": []
        }
      ],
      "element": "土",
      "category": "物攻"
    },
    "岩土暴击": {
      "damage_type": "physical",
      "base_power": 140,
      "energy_cost": 8,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": -1
        }
      ],
      "counters": [],
      "element": "土",
      "category": "物攻"
    },
    "石锁": {
      "damage_type": "physical",
      "base_power": 50,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "物攻"
    },
    "裂石": {
      "damage_type": "physical",
      "base_power": 95,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "def",
          "layers": 8,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "敌方获得物防-80%",
          "effects": [
            {
              "type": "debuff",
              "target": "enemy",
              "stat": "def",
              "layers": 8,
              "per_layer": 0.1
            }
          ]
        }
      ],
      "element": "土",
      "category": "物攻"
    },
    "抛石": {
      "damage_type": "physical",
      "base_power": 30,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": -5
        }
      ],
      "counters": [],
      "element": "土",
      "category": "物攻"
    },
    "地震": {
      "damage_type": "physical",
      "base_power": 190,
      "energy_cost": 10,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "物攻"
    },
    "流沙": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "敌方获得双防-60%",
          "effects": []
        }
      ],
      "element": "土",
      "category": "状态"
    },
    "泥浆铠甲": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "额外使自己的增益翻倍",
          "effects": []
        }
      ],
      "element": "土",
      "category": "状态"
    },
    "沙涌": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "状态"
    },
    "刺盾": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.7,
      "effects": [
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "atk",
          "layers": 7,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "敌方获得物攻-70%",
          "effects": [
            {
              "type": "debuff",
              "target": "enemy",
              "stat": "atk",
              "layers": 7,
              "per_layer": 0.1
            }
          ]
        }
      ],
      "element": "土",
      "category": "防御"
    },
    "硬化": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.9,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "",
          "effects": []
        }
      ],
      "element": "土",
      "category": "防御"
    },
    "壁垒": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.9,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "防御技能冷却-1",
          "effects": []
        }
      ],
      "element": "土",
      "category": "防御"
    },
    "遁地": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.5,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "",
          "effects": []
        }
      ],
      "element": "土",
      "category": "防御"
    },
    "泥浆": {
      "damage_type": "magical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "魔攻"
    },
    "泥巴喷射": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "魔攻"
    },
    "落石": {
      "damage_type": "physical",
      "base_power": 55,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "物攻"
    },
    "热砂": {
      "damage_type": "magical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "魔攻"
    },
    "陨石": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "魔攻"
    },
    "鸣沙陷阱": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "物攻"
    },
    "地陷": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "def",
          "layers": 7,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力翻倍",
          "effects": []
        }
      ],
      "element": "土",
      "category": "物攻"
    },
    "岩脉崩毁": {
      "damage_type": "physical",
      "base_power": 120,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "物攻"
    },
    "震击": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "物攻"
    },
    "石肤术": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "def",
          "layers": 16,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "土",
      "category": "状态"
    },
    "钧势": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "def",
          "layers": 14,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "土",
      "category": "状态"
    },
    "蓄势待发": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "土",
      "category": "状态"
    },
    "淤泥表皮": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "敌方获得连击数-3",
          "effects": []
        }
      ],
      "element": "土",
      "category": "防御"
    },
    "不动如山": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.9,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "",
          "effects": []
        }
      ],
      "element": "土",
      "category": "防御"
    },
    "砂石冲撞": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "def",
          "layers": 10,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "土",
      "category": "物攻"
    },
    "风吹雪": {
      "damage_type": "magical",
      "base_power": 30,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 1
        }
      ],
      "counters": [],
      "element": "冰",
      "category": "魔攻"
    },
    "暴风雪": {
      "damage_type": "physical",
      "base_power": 85,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "物攻"
    },
    "冰晶坠": {
      "damage_type": "physical",
      "base_power": 90,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "物攻"
    },
    "冰雹": {
      "damage_type": "physical",
      "base_power": 105,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "额外使敌方获得全技能能耗+3",
          "effects": []
        }
      ],
      "element": "冰",
      "category": "物攻"
    },
    "极寒领域": {
      "damage_type": "magical",
      "base_power": 105,
      "energy_cost": 6,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 60,
          "conditional": true
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "使冻结翻倍",
          "effects": []
        }
      ],
      "element": "冰",
      "category": "魔攻"
    },
    "冰冻光线": {
      "damage_type": "magical",
      "base_power": 90,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "魔攻"
    },
    "霜降": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "状态"
    },
    "瞬间零度": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为全技能能耗+3",
          "effects": []
        }
      ],
      "element": "冰",
      "category": "状态"
    },
    "雾气环绕": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "状态"
    },
    "霜天": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "状态"
    },
    "冰天雪地": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "被应对技能能耗+3",
          "effects": []
        }
      ],
      "element": "冰",
      "category": "防御"
    },
    "冰墙": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "敌方获得2层冻结",
          "effects": []
        }
      ],
      "element": "冰",
      "category": "防御"
    },
    "冰锥": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "物攻"
    },
    "冷风": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "魔攻"
    },
    "冰爪": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "物攻"
    },
    "打雪仗": {
      "damage_type": "magical",
      "base_power": 45,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "魔攻"
    },
    "滚雪球": {
      "damage_type": "physical",
      "base_power": 55,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "额外获得2层",
          "effects": []
        }
      ],
      "element": "冰",
      "category": "物攻"
    },
    "丢冰块": {
      "damage_type": "physical",
      "base_power": 90,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "物攻"
    },
    "寒风吹": {
      "damage_type": "magical",
      "base_power": 70,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "mdef",
          "layers": 5,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "冰",
      "category": "魔攻"
    },
    "雪球": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "状态"
    },
    "碎冰冰": {
      "damage_type": "magical",
      "base_power": 40,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 20,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "冰",
      "category": "魔攻"
    },
    "冰捆缚": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "状态"
    },
    "速冻": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "状态"
    },
    "冰蛋壳": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.6,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "敌方获得2层减速印记",
          "effects": [
            {
              "type": "add_mark",
              "target": "enemy",
              "mark_name": "减速印记",
              "stacks": 2
            }
          ]
        }
      ],
      "element": "冰",
      "category": "防御"
    },
    "雪替身": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 70,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.7,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "回复能量",
          "effects": []
        }
      ],
      "element": "冰",
      "category": "防御"
    },
    "冬至": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "状态"
    },
    "霜冻": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "mdef",
          "layers": 10,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "冰",
      "category": "状态"
    },
    "冰点": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "额外获得5层",
          "effects": []
        }
      ],
      "element": "冰",
      "category": "状态"
    },
    "龙吼": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "龙",
      "category": "物攻"
    },
    "吹炎": {
      "damage_type": "physical",
      "base_power": 170,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力翻倍",
          "effects": []
        }
      ],
      "element": "龙",
      "category": "物攻"
    },
    "怨力打击": {
      "damage_type": "magical",
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "龙",
      "category": "魔攻"
    },
    "升龙咆哮": {
      "damage_type": "magical",
      "base_power": 200,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "龙",
      "category": "魔攻"
    },
    "龙之利爪": {
      "damage_type": "physical",
      "base_power": 130,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "龙",
      "category": "物攻"
    },
    "龙吟": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 10,
          "per_layer": 0.1
        },
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 10,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "龙",
      "category": "状态"
    },
    "架势": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "heal",
          "target": "self",
          "percent": 0.2
        }
      ],
      "counters": [],
      "element": "龙",
      "category": "状态"
    },
    "龙爪": {
      "damage_type": "physical",
      "base_power": 120,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "龙",
      "category": "物攻"
    },
    "龙息环爆": {
      "damage_type": "magical",
      "base_power": 55,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "下次技能无需蓄力",
          "effects": []
        }
      ],
      "element": "龙",
      "category": "魔攻"
    },
    "角击": {
      "damage_type": "magical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "龙",
      "category": "魔攻"
    },
    "龙炮": {
      "damage_type": "physical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "龙",
      "category": "物攻"
    },
    "隼鳞": {
      "damage_type": "physical",
      "base_power": 140,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "龙",
      "category": "物攻"
    },
    "龙威": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "龙",
      "category": "状态"
    },
    "龙血": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.7,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "下次技能无需蓄力",
          "effects": []
        }
      ],
      "element": "龙",
      "category": "防御"
    },
    "绵里藏针": {
      "damage_type": "magical",
      "base_power": 50,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 30
        }
      ],
      "counters": [],
      "element": "龙",
      "category": "魔攻"
    },
    "导电撞击": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "物攻"
    },
    "电弧": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 40,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "电",
      "category": "物攻"
    },
    "触电": {
      "damage_type": "magical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "魔攻"
    },
    "超导": {
      "damage_type": "magical",
      "base_power": 95,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "魔攻"
    },
    "引雷": {
      "damage_type": "magical",
      "base_power": 35,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 20,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "电",
      "category": "魔攻"
    },
    "闪击折返": {
      "damage_type": "physical",
      "base_power": 45,
      "energy_cost": 5,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "物攻"
    },
    "落雷": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 20
        }
      ],
      "counters": [],
      "element": "电",
      "category": "魔攻"
    },
    "雷暴": {
      "damage_type": "magical",
      "base_power": 55,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "魔攻"
    },
    "麻痹": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "atk",
          "layers": 7,
          "per_layer": 0.1
        },
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "matk",
          "layers": 7,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "额外使敌方获得双攻-70%",
          "effects": [
            {
              "type": "debuff",
              "target": "enemy",
              "stat": "atk",
              "layers": 7,
              "per_layer": 0.1
            },
            {
              "type": "debuff",
              "target": "enemy",
              "stat": "matk",
              "layers": 7,
              "per_layer": 0.1
            }
          ]
        }
      ],
      "element": "电",
      "category": "状态"
    },
    "增程电池": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "状态"
    },
    "加大功率": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 8,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 8
        }
      ],
      "counters": [],
      "element": "电",
      "category": "状态"
    },
    "集中": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己回合结束返场",
          "effects": []
        }
      ],
      "element": "电",
      "category": "防御"
    },
    "电流": {
      "damage_type": "magical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "魔攻"
    },
    "球状闪电": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "物攻"
    },
    "磁干扰": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "魔攻"
    },
    "离子火花": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "物攻"
    },
    "交叉闪电": {
      "damage_type": "physical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "物攻"
    },
    "超导加速": {
      "damage_type": "magical",
      "base_power": 70,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff_flat",
          "target": "self",
          "stat": "spd",
          "value": 30
        }
      ],
      "counters": [],
      "element": "电",
      "category": "魔攻"
    },
    "双联脉冲": {
      "damage_type": "magical",
      "base_power": 50,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "魔攻"
    },
    "过载回路": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "状态"
    },
    "远程访问": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "状态"
    },
    "感电": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "魔攻"
    },
    "强制重启": {
      "damage_type": "magical",
      "base_power": 90,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "回合结束时使敌方精灵返场",
          "effects": []
        }
      ],
      "element": "电",
      "category": "魔攻"
    },
    "电离爆破": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "电",
      "category": "状态"
    },
    "电磁偏转": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.7,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "下回合所选技能使用次数+1",
          "effects": []
        }
      ],
      "element": "电",
      "category": "防御"
    },
    "毒针": {
      "damage_type": "physical",
      "base_power": 20,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "毒",
      "category": "物攻"
    },
    "腐蚀酸液": {
      "damage_type": "magical",
      "base_power": 35,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 2,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "毒",
      "category": "魔攻"
    },
    "连续毒针": {
      "damage_type": "physical",
      "base_power": 15,
      "energy_cost": 2,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "毒",
      "category": "物攻"
    },
    "毒囊": {
      "damage_type": "physical",
      "base_power": 25,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 2,
          "target": "self"
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "改为获得6层",
          "effects": []
        }
      ],
      "element": "毒",
      "category": "物攻"
    },
    "毒液渗透": {
      "damage_type": "magical",
      "base_power": 120,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "毒",
      "category": "魔攻"
    },
    "感染病": {
      "damage_type": "magical",
      "base_power": 85,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 1,
          "target": "enemy"
        }
      ],
      "counters": [],
      "element": "毒",
      "category": "魔攻"
    },
    "毒孢子": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 5,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "毒",
      "category": "状态"
    },
    "毒雾": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "毒",
      "category": "状态"
    },
    "剧毒": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 3,
          "target": "self"
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为获得8层",
          "effects": []
        }
      ],
      "element": "毒",
      "category": "状态"
    },
    "以毒攻毒": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 3,
          "per_layer": 0.1
        },
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "毒",
      "category": "状态"
    },
    "落井下毒": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 6,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "毒",
      "category": "状态"
    },
    "毒泡泡": {
      "damage_type": "magical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "毒",
      "category": "魔攻"
    },
    "溃烂触碰": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "毒",
      "category": "物攻"
    },
    "毒沼": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "毒",
      "category": "物攻"
    },
    "瘴气喷射": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "毒",
      "category": "魔攻"
    },
    "鸩毒": {
      "damage_type": "magical",
      "base_power": 75,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 10,
          "conditional": true
        },
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "改为本次威力+20",
          "effects": []
        }
      ],
      "element": "毒",
      "category": "魔攻"
    },
    "腐化": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "atk",
          "layers": 3,
          "per_layer": 0.1
        },
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "matk",
          "layers": 3,
          "per_layer": 0.1
        },
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "毒",
      "category": "状态"
    },
    "疫病吐息": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "毒",
      "category": "状态"
    },
    "不可接触": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.5,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "",
          "effects": []
        }
      ],
      "element": "毒",
      "category": "防御"
    },
    "啃咬": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": 1
        }
      ],
      "counters": [],
      "element": "虫",
      "category": "物攻"
    },
    "飞断": {
      "damage_type": "physical",
      "base_power": 20,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "物攻"
    },
    "虫群过境": {
      "damage_type": "physical",
      "base_power": 45,
      "energy_cost": 5,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "物攻"
    },
    "虫群": {
      "damage_type": "physical",
      "base_power": 20,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "物攻"
    },
    "虫网": {
      "damage_type": "magical",
      "base_power": 30,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 1
        }
      ],
      "counters": [],
      "element": "虫",
      "category": "魔攻"
    },
    "虫击": {
      "damage_type": "physical",
      "base_power": 90,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_multiply",
          "value": 2,
          "conditional": true
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力变为2倍",
          "effects": [
            {
              "type": "power_multiply",
              "value": 2
            }
          ]
        }
      ],
      "element": "虫",
      "category": "物攻"
    },
    "虫鸣": {
      "damage_type": "magical",
      "base_power": 15,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "魔攻"
    },
    "捆缚": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "poison",
          "layers": 2,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "虫",
      "category": "状态"
    },
    "假寐": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 2
        }
      ],
      "counters": [],
      "element": "虫",
      "category": "状态"
    },
    "虫茧": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "heal",
          "target": "self",
          "percent": 0.2
        }
      ],
      "counters": [],
      "element": "虫",
      "category": "状态"
    },
    "虫群智慧": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "状态"
    },
    "贮藏": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 5,
          "per_layer": 0.1
        },
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 5,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "虫",
      "category": "状态"
    },
    "掩护": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.7,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "下个入场精灵获得减伤",
          "effects": []
        }
      ],
      "element": "虫",
      "category": "防御"
    },
    "蛰针": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "物攻"
    },
    "虫刺": {
      "damage_type": "magical",
      "base_power": 15,
      "energy_cost": 1,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "魔攻"
    },
    "噬心": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "物攻"
    },
    "尾后针": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "物攻"
    },
    "虫蛊": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "魔攻"
    },
    "翅刃": {
      "damage_type": "physical",
      "base_power": 95,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "改为偷取印记",
          "effects": []
        }
      ],
      "element": "虫",
      "category": "物攻"
    },
    "网缚": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "def",
          "layers": 3,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "虫",
      "category": "物攻"
    },
    "食腐": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "状态"
    },
    "虫结阵": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "己方队伍获得1次随机奉献",
          "effects": []
        }
      ],
      "element": "虫",
      "category": "防御"
    },
    "草虫冲击": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "虫",
      "category": "物攻"
    },
    "寸拳": {
      "damage_type": "physical",
      "base_power": 30,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 1
        }
      ],
      "counters": [],
      "element": "武",
      "category": "物攻"
    },
    "崩拳": {
      "damage_type": "physical",
      "base_power": 65,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 10,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "自己获得物攻+100%",
          "effects": [
            {
              "type": "buff",
              "target": "self",
              "stat": "atk",
              "layers": 10,
              "per_layer": 0.1
            }
          ]
        }
      ],
      "element": "武",
      "category": "物攻"
    },
    "散手": {
      "damage_type": "physical",
      "base_power": 35,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本技能改为6连击",
          "effects": []
        }
      ],
      "element": "武",
      "category": "物攻"
    },
    "无影脚": {
      "damage_type": "physical",
      "base_power": 85,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_multiply",
          "value": 2,
          "conditional": true
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力变为2倍",
          "effects": [
            {
              "type": "power_multiply",
              "value": 2
            }
          ]
        }
      ],
      "element": "武",
      "category": "物攻"
    },
    "斩断": {
      "damage_type": "physical",
      "base_power": 75,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "额外打断被应对技能",
          "effects": []
        }
      ],
      "element": "武",
      "category": "物攻"
    },
    "反击拳": {
      "damage_type": "physical",
      "base_power": 25,
      "energy_cost": 2,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "武",
      "category": "物攻"
    },
    "技巧打击": {
      "damage_type": "physical",
      "base_power": 35,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_multiply",
          "value": 10,
          "conditional": true
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力变为10倍",
          "effects": [
            {
              "type": "power_multiply",
              "value": 10
            }
          ]
        }
      ],
      "element": "武",
      "category": "物攻"
    },
    "截拳": {
      "damage_type": "physical",
      "base_power": 90,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "额外造成打断",
          "effects": []
        }
      ],
      "element": "武",
      "category": "物攻"
    },
    "化劲": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "武",
      "category": "状态"
    },
    "破绽": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 7,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "自己额外获得物攻+70%",
          "effects": [
            {
              "type": "buff",
              "target": "self",
              "stat": "atk",
              "layers": 7,
              "per_layer": 0.1
            }
          ]
        }
      ],
      "element": "武",
      "category": "状态"
    },
    "破防": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "额外使被应对技能冷却2回合",
          "effects": []
        }
      ],
      "element": "武",
      "category": "状态"
    },
    "气沉丹田": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 10,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 13,
          "per_layer": 0.1
        },
        {
          "type": "heal",
          "target": "self",
          "percent": 0.6
        }
      ],
      "counters": [],
      "element": "武",
      "category": "状态"
    },
    "硬门": {
      "damage_type": "physical",
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "打断被应对技能",
          "effects": []
        }
      ],
      "element": "武",
      "category": "防御"
    },
    "听桥": {
      "damage_type": "physical",
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.6,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "对敌方造成物理伤害",
          "effects": []
        }
      ],
      "element": "武",
      "category": "防御"
    },
    "气波": {
      "damage_type": "magical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "武",
      "category": "魔攻"
    },
    "爆冲": {
      "damage_type": "physical",
      "base_power": 65,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_multiply",
          "value": 5,
          "conditional": true
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力变为5倍",
          "effects": [
            {
              "type": "power_multiply",
              "value": 5
            }
          ]
        }
      ],
      "element": "武",
      "category": "物攻"
    },
    "缠丝劲": {
      "damage_type": "physical",
      "base_power": 25,
      "energy_cost": 1,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "武",
      "category": "物攻"
    },
    "贯手": {
      "damage_type": "magical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "武",
      "category": "魔攻"
    },
    "影袭": {
      "damage_type": "physical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "武",
      "category": "物攻"
    },
    "一拳": {
      "damage_type": "physical",
      "base_power": 140,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "武",
      "category": "物攻"
    },
    "叠势": {
      "damage_type": "magical",
      "base_power": 25,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "武",
      "category": "魔攻"
    },
    "提气": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "武",
      "category": "状态"
    },
    "预备势": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 8,
          "per_layer": 0.1
        },
        {
          "type": "debuff",
          "target": "enemy",
          "stat": "def",
          "layers": 8,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对防御",
          "desc": "额外使敌方获得物防-80%",
          "effects": [
            {
              "type": "debuff",
              "target": "enemy",
              "stat": "def",
              "layers": 8,
              "per_layer": 0.1
            }
          ]
        }
      ],
      "element": "武",
      "category": "状态"
    },
    "防御反击": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己获得全技能威力+40",
          "effects": []
        }
      ],
      "element": "武",
      "category": "防御"
    },
    "回旋踢": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "武",
      "category": "物攻"
    },
    "啄击": {
      "damage_type": "physical",
      "base_power": 15,
      "energy_cost": 0,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "物攻"
    },
    "扇风": {
      "damage_type": "physical",
      "base_power": 75,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 50,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "翼",
      "category": "物攻"
    },
    "翼击": {
      "damage_type": "magical",
      "base_power": 50,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "魔攻"
    },
    "疾风刺": {
      "damage_type": "physical",
      "base_power": 25,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "物攻"
    },
    "龙卷风": {
      "damage_type": "physical",
      "base_power": 70,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力变为1.5倍",
          "effects": []
        }
      ],
      "element": "翼",
      "category": "物攻"
    },
    "乘风": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff_flat",
          "target": "self",
          "stat": "spd",
          "value": 120
        }
      ],
      "counters": [],
      "element": "翼",
      "category": "状态"
    },
    "风起": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "状态"
    },
    "暴风眼": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "状态"
    },
    "风墙": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.5,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "",
          "effects": []
        }
      ],
      "element": "翼",
      "category": "防御"
    },
    "鸣叫": {
      "damage_type": "magical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "魔攻"
    },
    "鹰爪": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "物攻"
    },
    "羽刃": {
      "damage_type": "physical",
      "base_power": 75,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "回合结束使敌方紧急脱离",
          "effects": []
        }
      ],
      "element": "翼",
      "category": "物攻"
    },
    "风矢": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "物攻"
    },
    "回旋风暴": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "魔攻"
    },
    "俯冲猛击": {
      "damage_type": "physical",
      "base_power": 140,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "物攻"
    },
    "闪击": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "物攻"
    },
    "飞羽": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "状态"
    },
    "风隐": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "状态"
    },
    "羽化加速": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "状态"
    },
    "羽翼庇护": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.7,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己获得连击数+3",
          "effects": []
        }
      ],
      "element": "翼",
      "category": "防御"
    },
    "疾风连袭": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "状态"
    },
    "飞吻": {
      "damage_type": "magical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "魔攻"
    },
    "超级糖果": {
      "damage_type": "physical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 60,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "萌",
      "category": "物攻"
    },
    "砂糖弹球": {
      "damage_type": "physical",
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "物攻"
    },
    "生日蛋糕": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "状态"
    },
    "示弱": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "状态"
    },
    "赤子之心": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_cost_permanent",
          "value": -3
        }
      ],
      "counters": [],
      "element": "萌",
      "category": "状态"
    },
    "反弹": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "状态"
    },
    "甜心续航": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 40,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "heal",
          "target": "self",
          "percent": 0.4
        }
      ],
      "counters": [],
      "element": "萌",
      "category": "状态"
    },
    "破罐破摔": {
      "damage_type": "magical",
      "base_power": 80,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 60,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "萌",
      "category": "魔攻"
    },
    "鞭打": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "物攻"
    },
    "魅惑": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "魔攻"
    },
    "碰爪": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "物攻"
    },
    "撒娇": {
      "damage_type": "magical",
      "base_power": 30,
      "energy_cost": 3,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_permanent_bonus",
          "value": 20
        }
      ],
      "counters": [],
      "element": "萌",
      "category": "魔攻"
    },
    "爆米花爆破": {
      "damage_type": "physical",
      "base_power": 140,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "物攻"
    },
    "击鼓传花": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "状态"
    },
    "月光合奏": {
      "damage_type": "physical",
      "base_power": 30,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "物攻"
    },
    "捧杀": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.9,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "敌方获得1层萌化",
          "effects": []
        }
      ],
      "element": "萌",
      "category": "防御"
    },
    "鬼火": {
      "damage_type": "magical",
      "base_power": 30,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 1
        }
      ],
      "counters": [],
      "element": "幽灵",
      "category": "魔攻"
    },
    "惊吓盒子": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 6,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "使敌方失去6能量",
          "effects": []
        }
      ],
      "element": "幽灵",
      "category": "物攻"
    },
    "背袭": {
      "damage_type": "magical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "魔攻"
    },
    "坟场搏击": {
      "damage_type": "physical",
      "base_power": 180,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "物攻"
    },
    "恶作剧": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为敌方失去6能量",
          "effects": []
        }
      ],
      "element": "幽灵",
      "category": "状态"
    },
    "降灵": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "状态"
    },
    "报复": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 70,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.7,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "敌方失去3能量",
          "effects": []
        }
      ],
      "element": "幽灵",
      "category": "防御"
    },
    "恐吓": {
      "damage_type": "magical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "魔攻"
    },
    "幽灵爆发": {
      "damage_type": "magical",
      "base_power": 140,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "魔攻"
    },
    "诡刺": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "物攻"
    },
    "幻象": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "物攻"
    },
    "午夜噪音": {
      "damage_type": "magical",
      "base_power": 20,
      "energy_cost": 4,
      "hits": 5,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "魔攻"
    },
    "灵媒": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "魔攻"
    },
    "灵光": {
      "damage_type": "magical",
      "base_power": 25,
      "energy_cost": 3,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "魔攻"
    },
    "嘲弄": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 9,
          "per_layer": 0.1
        },
        {
          "type": "buff_flat",
          "target": "self",
          "stat": "spd",
          "value": 70
        }
      ],
      "counters": [],
      "element": "幽灵",
      "category": "状态"
    },
    "勾魂": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "状态"
    },
    "虚化": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "mdef",
          "layers": 7,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己获得魔防+70%",
          "effects": [
            {
              "type": "buff",
              "target": "self",
              "stat": "mdef",
              "layers": 7,
              "per_layer": 0.1
            }
          ]
        }
      ],
      "element": "幽灵",
      "category": "防御"
    },
    "魔爪": {
      "damage_type": "physical",
      "base_power": 30,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 1
        }
      ],
      "counters": [],
      "element": "恶",
      "category": "物攻"
    },
    "恶能量": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "物攻"
    },
    "蝙蝠": {
      "damage_type": "physical",
      "base_power": 65,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "物攻"
    },
    "撕裂": {
      "damage_type": "physical",
      "base_power": 85,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次攻击吸血100%",
          "effects": []
        }
      ],
      "element": "恶",
      "category": "物攻"
    },
    "撕咬": {
      "damage_type": "physical",
      "base_power": 30,
      "energy_cost": 3,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "物攻"
    },
    "暗突袭": {
      "damage_type": "physical",
      "base_power": 70,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次技能威力翻倍",
          "effects": []
        }
      ],
      "element": "恶",
      "category": "物攻"
    },
    "极限撕裂": {
      "damage_type": "physical",
      "base_power": 135,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "物攻"
    },
    "灾厄": {
      "damage_type": "physical",
      "base_power": 150,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "改为对敌方造成物伤",
          "effects": []
        }
      ],
      "element": "恶",
      "category": "物攻"
    },
    "彼岸之手": {
      "damage_type": "physical",
      "base_power": 150,
      "energy_cost": 10,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "物攻"
    },
    "贪婪": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "状态"
    },
    "力量吞噬": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "状态"
    },
    "欺诈契约": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "状态"
    },
    "恶意逃离": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "额外使敌方攻击技能能耗+4",
          "effects": []
        }
      ],
      "element": "恶",
      "category": "状态"
    },
    "隐藏条款": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 8,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "状态"
    },
    "等价交换": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.9,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "自己获得50%吸血",
          "effects": []
        }
      ],
      "element": "恶",
      "category": "防御"
    },
    "恶念交换": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "状态"
    },
    "迫害": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "物攻"
    },
    "掠夺": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "魔攻"
    },
    "黑手": {
      "damage_type": "magical",
      "base_power": 45,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "魔攻"
    },
    "诋毁": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "物攻"
    },
    "栽赃": {
      "damage_type": "magical",
      "base_power": 150,
      "energy_cost": 6,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "魔攻"
    },
    "跌落": {
      "damage_type": "physical",
      "base_power": 120,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "atk",
          "layers": 5,
          "per_layer": 0.1
        }
      ],
      "counters": [
        {
          "type": "应对状态",
          "desc": "改为获得物攻+50%",
          "effects": [
            {
              "type": "buff",
              "target": "self",
              "stat": "atk",
              "layers": 5,
              "per_layer": 0.1
            }
          ]
        }
      ],
      "element": "恶",
      "category": "物攻"
    },
    "牵连": {
      "damage_type": "magical",
      "base_power": 85,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "power_bonus",
          "value": 30,
          "conditional": true
        }
      ],
      "counters": [],
      "element": "恶",
      "category": "魔攻"
    },
    "暗箱操作": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "改为敌方获得双攻和双防-100%",
          "effects": []
        }
      ],
      "element": "恶",
      "category": "状态"
    },
    "虚假破产": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 80,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "",
          "effects": []
        }
      ],
      "element": "恶",
      "category": "防御"
    },
    "趁火打劫": {
      "damage_type": "physical",
      "base_power": 35,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "物攻"
    },
    "伪造账单": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 1,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "状态"
    },
    "念力膨胀": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "物攻"
    },
    "空间压迫": {
      "damage_type": "physical",
      "base_power": 70,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "物攻"
    },
    "坍缩": {
      "damage_type": "magical",
      "base_power": 85,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "buff",
          "target": "self",
          "stat": "matk",
          "layers": 7,
          "per_layer": 0.1
        }
      ],
      "counters": [],
      "element": "幻",
      "category": "魔攻"
    },
    "四维降解": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "魔攻"
    },
    "偷师": {
      "damage_type": "physical",
      "base_power": 30,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "energy_restore",
          "target": "self",
          "value": 1
        }
      ],
      "counters": [],
      "element": "幻",
      "category": "物攻"
    },
    "多维击打": {
      "damage_type": "magical",
      "base_power": 15,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "魔攻"
    },
    "错乱": {
      "damage_type": "magical",
      "base_power": 65,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "敌方获得3层星陨印记",
          "effects": [
            {
              "type": "add_mark",
              "target": "enemy",
              "mark_name": "星陨印记",
              "stacks": 3
            }
          ]
        }
      ],
      "element": "幻",
      "category": "魔攻"
    },
    "超维投射": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "状态"
    },
    "星轨裂变": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "状态"
    },
    "星链": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "状态"
    },
    "超新星馈赠": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "状态"
    },
    "心灵洞悉": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "状态"
    },
    "二律背反": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "额外使敌方星陨印记层数翻倍",
          "effects": [
            {
              "type": "double_mark",
              "target": "enemy",
              "mark_name": "星陨印记"
            }
          ]
        }
      ],
      "element": "幻",
      "category": "状态"
    },
    "粒子对撞": {
      "damage_type": "physical",
      "base_power": 40,
      "energy_cost": 0,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "物攻"
    },
    "星云漩涡": {
      "damage_type": "physical",
      "base_power": 60,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "物攻"
    },
    "双星": {
      "damage_type": "physical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "物攻"
    },
    "针状物": {
      "damage_type": "magical",
      "base_power": 30,
      "energy_cost": 3,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "魔攻"
    },
    "大爆炸": {
      "damage_type": "magical",
      "base_power": 100,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幻",
      "category": "魔攻"
    },
    "冥想": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.8,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "敌方获得2层星陨印记",
          "effects": [
            {
              "type": "add_mark",
              "target": "enemy",
              "mark_name": "星陨印记",
              "stacks": 2
            }
          ]
        }
      ],
      "element": "幻",
      "category": "防御"
    },
    "小偷小摸": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "幽灵",
      "category": "状态"
    },
    "柔弱": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "状态"
    },
    "逆向演化": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "状态"
    },
    "堆雪人": {
      "damage_type": "magical",
      "base_power": 60,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "魔攻"
    },
    "冲击": {
      "damage_type": "physical",
      "base_power": 80,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "物攻"
    },
    "极速冷冻": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对防御",
          "desc": "能耗+4",
          "effects": []
        }
      ],
      "element": "冰",
      "category": "状态"
    },
    "冰荆棘": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.7,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "敌方冻结层数翻倍",
          "effects": []
        }
      ],
      "element": "冰",
      "category": "防御"
    },
    "炎爆术": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "status_ailment",
          "ailment": "burn",
          "layers": 1,
          "target": "self"
        }
      ],
      "counters": [],
      "element": "火",
      "category": "状态"
    },
    "横纵斩": {
      "damage_type": "magical",
      "base_power": 25,
      "energy_cost": 2,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "魔攻"
    },
    "羽毛舞": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 2,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "状态"
    },
    "三鼓作气": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 3,
      "hits": 3,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "状态"
    },
    "冰刺": {
      "damage_type": "physical",
      "base_power": 85,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "敌方2回合无法换宠",
          "effects": []
        }
      ],
      "element": "冰",
      "category": "物攻"
    },
    "藤鞭": {
      "damage_type": "physical",
      "base_power": 35,
      "energy_cost": 3,
      "hits": 2,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "草",
      "category": "物攻"
    },
    "水星水": {
      "damage_type": "magical",
      "base_power": 0,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [
        {
          "type": "应对状态",
          "desc": "本次伤害不受自身属性减益和敌方属性增益影响",
          "effects": []
        }
      ],
      "element": "水",
      "category": "魔攻"
    },
    "缓冻": {
      "damage_type": "physical",
      "base_power": 85,
      "energy_cost": 3,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "魔攻"
    },
    "碎冰击": {
      "damage_type": "physical",
      "base_power": 90,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "冰",
      "category": "物攻"
    },
    "骗局": {
      "damage_type": "magical",
      "base_power": 110,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "恶",
      "category": "魔攻"
    },
    "幼态延续": {
      "damage_type": "magical",
      "base_power": 90,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "魔攻"
    },
    "疾风涡轮": {
      "damage_type": "physical",
      "base_power": 115,
      "energy_cost": 7,
      "hits": 1,
      "priority": 1,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "翼",
      "category": "物攻"
    },
    "玩具乐园": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 7,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "萌",
      "category": "状态"
    },
    "求雨": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 8,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "水",
      "category": "状态"
    },
    "指指点点": {
      "damage_type": "physical",
      "base_power": 0,
      "energy_cost": 10,
      "hits": 10,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [],
      "counters": [],
      "element": "普通",
      "category": "物攻"
    },
    "防御": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 1,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0.7,
      "effects": [],
      "counters": [
        {
          "type": "应对攻击",
          "desc": "",
          "effects": []
        }
      ],
      "element": "普通",
      "category": "防御"
    },
    "光墙": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "light_screen",
          "target": "self",
          "turns": 5
        }
      ],
      "counters": [],
      "element": "超能",
      "category": "状态"
    },
    "反射壁": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "reflect",
          "target": "self",
          "turns": 5
        }
      ],
      "counters": [],
      "element": "超能",
      "category": "状态"
    },
    "顺风": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "tailwind",
          "target": "self",
          "turns": 4
        }
      ],
      "counters": [],
      "element": "翼",
      "category": "状态"
    },
    "隐形岩": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 5,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "stealth_rock",
          "target": "enemy"
        }
      ],
      "counters": [],
      "element": "岩石",
      "category": "状态"
    },
    "毒菱": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 4,
      "hits": 1,
      "priority": 0,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "toxic_spikes",
          "target": "enemy"
        }
      ],
      "counters": [],
      "element": "毒",
      "category": "状态"
    },
    "戏法空间": {
      "damage_type": null,
      "base_power": 0,
      "energy_cost": 7,
      "hits": 1,
      "priority": -7,
      "damage_reduction": 0,
      "effects": [
        {
          "type": "trick_room",
          "target": "self",
          "turns": 5
        }
      ],
      "counters": [],
      "element": "超能",
      "category": "状态"
    }
  }
};