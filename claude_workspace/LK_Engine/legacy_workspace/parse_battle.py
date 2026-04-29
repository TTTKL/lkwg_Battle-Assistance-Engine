"""
洛克王国技能描述解析器 - 将技能文本描述转译为结构化对战数据
规则版本: v1.0
"""
import json, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sdb = json.load(open('Calculator/Data/skills.json', 'r', encoding='utf-8'))
common = json.load(open('Calculator/Data/common.json', 'r', encoding='utf-8'))

# ========== 规则定义 ==========
BATTLE_RULES = {
    "version": "1.0",
    "initial_energy": 10,
    
    # 先手判定
    "priority_rules": [
        "1. 先手等级高的先行动",
        "2. 先手等级相同或均为0：速度快的先行动",
        "3. 速度一致：随机先手"
    ],
    
    # 伤害公式
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
    
    # 增益规则
    "buff_rules": {
        "definition": "增加属性、技能威力、连击数，以及降低能耗、吸血、过载等效果（不包括印记、特性、其他类效果）",
        "stack_rule": "获得魔攻+70%代表获得10%魔攻buff×7层",
        "clear_on_switch": True,
        "clear_on_battle_end": True,
        "buff_per_layer": 0.10
    },
    
    # 应对系统
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
    
    # 防御规则
    "defense_rules": {
        "duration": "当回合",
        "note": "防御类技能的减伤效果仅在当回合生效"
    }
}

# ========== 技能解析器 ==========
def parse_skill(skill):
    """将技能描述解析为结构化battle_effect"""
    desc = skill.get('desc', '')
    cat = skill.get('category', '')
    power = skill.get('power', '')
    energy = skill.get('energy', '0')
    typ = skill.get('type', '普通')
    
    effect = {
        "damage_type": None,      # "physical" / "magical" / None
        "base_power": int(power) if power and power.isdigit() else 0,
        "energy_cost": int(energy) if energy and energy.isdigit() else 0,
        "hits": 1,                # 连击数
        "priority": 0,            # 先手等级
        "damage_reduction": 0,    # 减伤百分比 (0-1)
        "effects": [],            # 效果列表
        "counters": [],           # 应对效果列表
        "element": typ,
        "category": cat
    }
    
    # === 1. 伤害类型 ===
    if '物伤' in desc or '物理伤害' in desc or cat == '物攻':
        effect['damage_type'] = 'physical'
    elif '魔伤' in desc or '魔法伤害' in desc or cat == '魔攻':
        effect['damage_type'] = 'magical'
    
    # === 2. 连击数 ===
    hit_match = re.search(r'(\d+)连击', desc)
    if hit_match:
        effect['hits'] = int(hit_match.group(1))
    
    # === 3. 先手等级 ===
    prio_match = re.search(r'先手\+(\d+)', desc)
    if prio_match:
        effect['priority'] = int(prio_match.group(1))
    if '必定先手' in desc:
        effect['priority'] = 99
    
    # === 4. 减伤 (防御技能) ===
    dr_match = re.search(r'减伤(\d+)%', desc)
    if dr_match:
        effect['damage_reduction'] = int(dr_match.group(1)) / 100.0
    
    # === 5. 自身增益效果 ===
    stat_aliases = {
        '物攻': ['atk'], '魔攻': ['matk'], '物防': ['def'], '魔防': ['mdef'],
        '速度': ['spd'], '双攻': ['atk','matk'],
        '攻防速': ['atk','matk','def','mdef','spd'],
        '全属性': ['atk','matk','def','mdef','spd'],
        '物攻和魔攻': ['atk','matk'], '物防和魔防': ['def','mdef'],
    }
    # Pattern: 自己获得 [stat]+N% or [stat]+N
    for m in re.finditer(r'(?:自己|己方)?获得(物攻和魔攻|物防和魔防|物攻|魔攻|物防|魔防|速度|双攻|攻防速|全属性)\+(\d+)(%|)', desc):
        stat, val, pct = m.group(1), int(m.group(2)), m.group(3)
        mapped = stat_aliases.get(stat, [stat])
        if pct == '%':
            layers = val // 10
            for s in mapped:
                effect['effects'].append({
                    "type": "buff", "target": "self",
                    "stat": s, "layers": layers, "per_layer": 0.10
                })
        else:
            for s in mapped:
                effect['effects'].append({
                    "type": "buff_flat", "target": "self",
                    "stat": s, "value": val
                })
    
    # === 6. 敌方debuff ===
    for m in re.finditer(r'敌方获得(物攻和魔攻|物防和魔防|物攻|魔攻|物防|魔防|速度|双攻|攻防速|全属性)-(\d+)(%|)', desc):
        stat, val, pct = m.group(1), int(m.group(2)), m.group(3)
        mapped = stat_aliases.get(stat, [stat])
        if pct == '%':
            layers = val // 10
            for s in mapped:
                effect['effects'].append({
                    "type": "debuff", "target": "enemy",
                    "stat": s, "layers": layers, "per_layer": 0.10
                })
    
    # === 7. 回复效果 ===
    hp_heal = re.search(r'回复(\d+)%生命', desc)
    if hp_heal:
        effect['effects'].append({
            "type": "heal",
            "target": "self",
            "percent": int(hp_heal.group(1)) / 100.0
        })
    
    energy_heal = re.search(r'(?:自己)?回复(\d+)能量', desc)
    if energy_heal:
        effect['effects'].append({
            "type": "energy_restore",
            "target": "self",
            "value": int(energy_heal.group(1))
        })
    
    # === 8. 威力修正 ===
    pw_add = re.search(r'(?:本次|本)技能威力\+(\d+)', desc)
    if pw_add:
        # Conditional power bonus (needs condition check at runtime)
        effect['effects'].append({
            "type": "power_bonus",
            "value": int(pw_add.group(1)),
            "conditional": True  # Runtime condition parsing needed
        })
    
    pw_perm = re.search(r'威力永久\+(\d+)', desc)
    if pw_perm:
        effect['effects'].append({
            "type": "power_permanent_bonus",
            "value": int(pw_perm.group(1))
        })
    
    pw_mult = re.search(r'威力变为(\d+)倍', desc)
    if pw_mult:
        effect['effects'].append({
            "type": "power_multiply",
            "value": int(pw_mult.group(1)),
            "conditional": True
        })
    
    # === 9. 应对效果 ===
    counter_patterns = [
        (r'应对攻击[：:]\s*(.+?)(?:[。，]|$)', '应对攻击'),
        (r'应对防御[：:]\s*(.+?)(?:[。，]|$)', '应对防御'),
        (r'应对状态[：:]\s*(.+?)(?:[。，]|$)', '应对状态'),
    ]
    for pat, ctype in counter_patterns:
        cm = re.search(pat, desc)
        if cm:
            counter_desc = cm.group(1).strip()
            counter_effect = {"type": ctype, "desc": counter_desc, "effects": []}
            
            # Parse counter sub-effects
            if '连击数翻倍' in counter_desc:
                counter_effect['effects'].append({"type": "hits_multiply", "value": 2})
            if '变为' in counter_desc and '连击' in counter_desc:
                cm2 = re.search(r'变为(\d+)连击', counter_desc)
                if cm2:
                    counter_effect['effects'].append({"type": "hits_set", "value": int(cm2.group(1))})
            if '威力变为' in counter_desc and '倍' in counter_desc:
                cm2 = re.search(r'威力变为(\d+)倍', counter_desc)
                if cm2:
                    counter_effect['effects'].append({"type": "power_multiply", "value": int(cm2.group(1))})
            if '先手+' in counter_desc:
                cm2 = re.search(r'先手\+(\d+)', counter_desc)
                if cm2:
                    counter_effect['effects'].append({"type": "priority_bonus", "value": int(cm2.group(1))})
            if '敌方脱离' in counter_desc:
                counter_effect['effects'].append({"type": "force_switch"})
            
            # Buff/debuff in counter
            for bm in re.finditer(r'(物攻和魔攻|物防和魔防|物攻|魔攻|物防|魔防|速度|双攻|攻防速|全属性)(\+|-)(\d+)(%|)', counter_desc):
                cstat, sign, cval, cpct = bm.group(1), bm.group(2), int(bm.group(3)), bm.group(4)
                mapped_c = stat_aliases.get(cstat, [cstat])
                if cpct == '%':
                    clayers = cval // 10
                    for cs in mapped_c:
                        counter_effect['effects'].append({
                            "type": "buff" if sign == '+' else "debuff",
                            "target": "self" if sign == '+' else "enemy",
                            "stat": cs, "layers": clayers, "per_layer": 0.10
                        })
                else:
                    for cs in mapped_c:
                        counter_effect['effects'].append({
                            "type": "buff_flat" if sign == '+' else "debuff_flat",
                            "target": "self" if sign == '+' else "enemy",
                            "stat": cs, "value": cval * (1 if sign == '+' else -1)
                        })
            
            # Heal in counter
            hm = re.search(r'回复(\d+)%生命', counter_desc)
            if hm:
                counter_effect['effects'].append({"type": "heal", "target": "self", "percent": int(hm.group(1))/100.0})
            em = re.search(r'回复(\d+)能量', counter_desc)
            if em:
                counter_effect['effects'].append({"type": "energy_restore", "target": "self", "value": int(em.group(1))})
            
            effect['counters'].append(counter_effect)
    
    # === 10. 能耗修正 ===
    ecost_perm = re.search(r'能耗永久([+-])(\d+)', desc)
    if ecost_perm:
        sign = 1 if ecost_perm.group(1) == '+' else -1
        effect['effects'].append({
            "type": "energy_cost_permanent",
            "value": sign * int(ecost_perm.group(2))
        })
    
    # === 11. 状态异常 ===
    for status, keyword in [('burn','灼烧'), ('poison','中毒'), ('freeze','冰冻'),
                             ('paralyze','麻痹'), ('confuse','混乱'), ('stun','眩晕')]:
        if keyword in desc:
            layers_m = re.search(r'(\d+)层' + keyword, desc)
            if not layers_m:
                layers_m = re.search(keyword + r'(\d+)层', desc)  
            layers = int(layers_m.group(1)) if layers_m else 1
            effect['effects'].append({
                "type": "status_ailment",
                "ailment": status,
                "layers": layers,
                "target": "enemy" if '敌' in desc.split(keyword)[0][-5:] else "self"
            })
    
    # === 12. 特殊威力计算 ===
    if '威力等于' in desc:
        effect['effects'].append({
            "type": "dynamic_power",
            "desc": desc,
            "note": "Runtime calculation needed"
        })
        effect['base_power'] = 0
    
    if '消耗所有能量' in desc:
        effect['effects'].append({
            "type": "consume_all_energy",
            "note": "Power scales with energy consumed"
        })
    
    return effect


# ========== 执行解析 ==========
print("Parsing all skills...", flush=True)

battle_data = {
    "rules": BATTLE_RULES,
    "skills": {}
}

stats = {"total": 0, "has_damage": 0, "has_counter": 0, "has_buff": 0, "has_heal": 0, "defense": 0}

for name, skill in sdb.items():
    parsed = parse_skill(skill)
    battle_data["skills"][name] = parsed
    stats["total"] += 1
    if parsed["damage_type"]: stats["has_damage"] += 1
    if parsed["counters"]: stats["has_counter"] += 1
    if any(e["type"] in ("buff","debuff","buff_flat","debuff_flat") for e in parsed["effects"]): stats["has_buff"] += 1
    if any(e["type"] == "heal" for e in parsed["effects"]): stats["has_heal"] += 1
    if parsed["damage_reduction"] > 0: stats["defense"] += 1

print(f"\nParsing complete!")
print(f"  Total: {stats['total']}")
print(f"  Has damage: {stats['has_damage']}")
print(f"  Has counter: {stats['has_counter']}")
print(f"  Has buff/debuff: {stats['has_buff']}")
print(f"  Has heal: {stats['has_heal']}")
print(f"  Defense (reduction): {stats['defense']}")

# Save
out_path = 'Calculator/Data/battle_data.json'
json.dump(battle_data, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nSaved to {out_path}")

# Show some parsed examples
print("\n=== Example parsed skills ===")
examples = ['抓挠','魔法增效','防反','力量增效','连续爪击','火焰护盾','快速移动','迫近攻击']
for ex in examples:
    if ex in battle_data["skills"]:
        e = battle_data["skills"][ex]
        print(f"\n  {ex}:")
        print(f"    dmg={e['damage_type']} pow={e['base_power']} hits={e['hits']} prio={e['priority']}")
        print(f"    reduction={e['damage_reduction']} cost={e['energy_cost']}")
        if e['effects']:
            print(f"    effects: {json.dumps(e['effects'], ensure_ascii=False)[:200]}")
        if e['counters']:
            print(f"    counters: {json.dumps(e['counters'], ensure_ascii=False)[:200]}")
