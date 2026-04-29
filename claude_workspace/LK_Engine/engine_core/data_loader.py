"""
数据加载器
优先从 battle_data.json（爬虫抓取的完整数据）加载技能，
skills.json 作为 battle_data 缺失时的补充。
"""
import json
from typing import Dict, List, Optional
from pathlib import Path
from core.models import (
    Skill, PetTemplate, Trait, Effect, EffectType,
    DamageType, SkillCategory, FieldMark
)
from core.status_effects import StatusEffectType
from paths import get_default_data_dir


class DataLoader:
    """游戏数据加载器"""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else get_default_data_dir()
        self.skills: Dict[str, Skill] = {}
        self.pets: Dict[str, PetTemplate] = {}
        self.type_chart: Dict[str, List[float]] = {}
        self.types: List[str] = []
        self.natures: Dict[str, Dict[str, float]] = {}
        self.iv_rules: Dict = {}
        self.formulas: Dict = {}
        self.bloodline_overrides = self._load_bloodline_overrides()

    def load_all(self):
        self.load_common()
        self.load_type_chart()
        self.load_skills()
        self.load_pets()

    def _load_bloodline_overrides(self) -> Dict[str, str]:
        path = Path(__file__).resolve().parent / "docs" / "bloodline_overrides.json"
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(name): self._normalize_bloodline(value) for name, value in data.items()}
        return {}

    def _normalize_bloodline(self, value) -> str:
        if value is None:
            return "unknown"

        text = str(value).strip()
        if not text:
            return "unknown"

        lowered = text.lower()
        if lowered == "unknown":
            return "unknown"
        if lowered in {"leader", "leader_bloodline"} or "首领" in text:
            return "leader"
        if lowered in {"polluted", "corrupted"} or "污染" in text:
            return "polluted"

        known_elements = set(self.types) | {
            "普通", "火", "水", "草", "土", "冰", "电", "机械", "萌",
            "毒", "翼", "武", "虫", "幽灵", "龙", "恶", "光", "幻",
        }
        if text in known_elements:
            return f"element:{text}"

        if lowered.startswith("element:"):
            return lowered

        return text

    # ── 属性克制表 ────────────────────────────────────────────────

    def load_common(self):
        path = self.data_dir / "common.json"
        if not path.exists():
            self.natures = {}
            self.iv_rules = {}
            self.formulas = {}
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.natures = data.get('natures', {}) or {}
        self.iv_rules = data.get('iv_rules', {}) or {}
        self.formulas = data.get('formulas', {}) or {}

    def load_type_chart(self):
        path = self.data_dir / "type_chart.json"
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.types = data['types']
            self.type_chart = data['chart']

    def get_nature_mods(self, nature_name: Optional[str]) -> Dict[str, float]:
        stat_names = ['生命', '物攻', '魔攻', '物防', '魔防', '速度']
        mods = {name: 0.0 for name in stat_names}
        if not nature_name:
            return mods
        raw = self.natures.get(str(nature_name), {})
        if isinstance(raw, dict):
            for key, value in raw.items():
                if key in mods:
                    try:
                        mods[key] = float(value)
                    except (TypeError, ValueError):
                        pass
        return mods

    @staticmethod
    def _normalize_defender_types(defender_types: Optional[List[str]]) -> List[str]:
        normalized: List[str] = []
        seen = set()
        for defender_type in defender_types or []:
            if not defender_type or defender_type in seen:
                continue
            seen.add(defender_type)
            normalized.append(defender_type)
        return normalized

    def get_combined_type_effectiveness(self, attacker_type: str, defender_types: Optional[List[str]]) -> float:
        """
        统一处理多属性目标的属性倍率。
        - 相同属性只计算一次
        - 不同属性分别查表后连乘
        - 双重克制 4x 压缩为 3x
        - 双重抵抗保留为 0.25x
        """
        effectiveness = 1.0
        for defender_type in self._normalize_defender_types(defender_types):
            effectiveness *= self.get_type_effectiveness(attacker_type, defender_type)
        if effectiveness >= 4.0:
            return 3.0
        return effectiveness

    def calc_actual_stats(
        self,
        base_stats: Dict[str, int],
        ivs: Optional[Dict[str, int]] = None,
        nature_name: Optional[str] = None,
    ) -> Dict[str, int]:
        """按前端 common.json 中定义的同一公式计算实战六维。"""
        ivs = ivs or {}
        nature_mods = self.get_nature_mods(nature_name)
        result: Dict[str, int] = {}
        for stat_name in ['生命', '物攻', '魔攻', '物防', '魔防', '速度']:
            base = int(base_stats.get(stat_name, 0) or 0)
            iv = int(ivs.get(stat_name, 0) or 0)
            nat_mod = float(nature_mods.get(stat_name, 0.0) or 0.0)
            iv_pvp = iv * 6
            if stat_name == '生命':
                value = round((1.7 * base + iv_pvp * 0.85 + 70) * (1 + nat_mod)) + 100
            else:
                value = round((1.1 * base + iv_pvp * 0.55 + 10) * (1 + nat_mod)) + 50
            result[stat_name] = int(value)
        return result

    # ── 技能数据 ──────────────────────────────────────────────────

    def load_skills(self):
        """
        加载技能数据。
        优先使用 battle_data.json（爬虫抓取，含描述和效果）。
        对 battle_data 中没有的技能，从 skills.json 补充基础数据。
        """
        # 1. 读 battle_data.json（主数据源）
        battle_path = self.data_dir / "battle_data.json"
        battle_skills: Dict = {}
        if battle_path.exists():
            with open(battle_path, 'r', encoding='utf-8') as f:
                battle_data = json.load(f)
                battle_skills = battle_data.get('skills', {})

        # 2. 读 skills.json（补充来源）
        skills_path = self.data_dir / "skills.json"
        skills_json: Dict = {}
        if skills_path.exists():
            with open(skills_path, 'r', encoding='utf-8') as f:
                skills_json = json.load(f)

        # 3. 合并：battle_data 优先
        all_names = set(battle_skills.keys()) | set(skills_json.keys())
        for name in all_names:
            bd = battle_skills.get(name, {})
            sj = skills_json.get(name, {})

            # 确定属性（element）
            element = bd.get('element') or sj.get('type', '普通')

            # 确定类别
            category_str = bd.get('category') or sj.get('category', '')
            category = self._parse_category(category_str)

            # 确定伤害类型
            damage_type = None
            if category == SkillCategory.ATTACK:
                dt_str = bd.get('damage_type') or sj.get('category', '')
                damage_type = self._parse_damage_type(dt_str)

            # 威力
            power = 0
            if bd.get('power') is not None:
                try:
                    power = int(bd['power'])
                except (ValueError, TypeError):
                    power = 0
            elif sj.get('power', '').isdigit():
                power = int(sj['power'])

            # 能耗
            energy = 0
            if bd.get('energy_cost') is not None:
                try:
                    energy = int(bd['energy_cost'])
                except (ValueError, TypeError):
                    energy = 0
            elif sj.get('energy', '').isdigit():
                energy = int(sj['energy'])

            # 效果（来自 battle_data 爬虫数据）
            effects = self._parse_effects(bd.get('effects', []))

            # 应对系统（来自旧 battle_data 格式）
            counters = self._parse_counters(bd.get('counters', []))

            # 对效果为空的技能，尝试从 battle_data / skills 的描述文字解析
            desc_text = (
                bd.get('desc', '')
                or bd.get('description', '')
                or sj.get('desc', '')
                or sj.get('description', '')
            )
            if not effects and desc_text:
                effects, extra_counters = self._parse_desc_to_effects(desc_text, category)
                if extra_counters and not counters:
                    counters = extra_counters

            # ── 默认参数 fallback ────────────────────────────────
            # 攻击技能威力为0时，按 60 + energy*15 补全（普通系）
            if category == SkillCategory.ATTACK and power == 0 and damage_type is not None:
                power = 60 + energy * 15

            # hits fallback：从 desc 解析连击数
            hits = bd.get('hits', 1)
            if hits == 1 and desc_text:
                hits = self._parse_hits_from_desc(desc_text, hits)

            # priority fallback：先手+1 / 先手-1
            priority = bd.get('priority', 0)
            if priority == 0 and desc_text:
                import re as _re
                if _re.search(r'先手\+(\d+)', desc_text):
                    priority = int(_re.search(r'先手\+(\d+)', desc_text).group(1))
                elif _re.search(r'先手-(\d+)', desc_text):
                    priority = -int(_re.search(r'先手-(\d+)', desc_text).group(1))

            skill = Skill(
                name=name,
                element=element,
                category=category,
                damage_type=damage_type,
                base_power=power,
                energy_cost=energy,
                hits=hits,
                priority=priority,
                damage_reduction=bd.get('damage_reduction', 0.0),
                effects=effects,
                counters=counters,
                cooldown=bd.get('cooldown', 0),
                desc=desc_text,
            )
            self.skills[name] = skill

    def _parse_hits_from_desc(self, desc: str, default: int = 1) -> int:
        """从技能描述中解析连击数"""
        import re
        # 匹配 N连击（2~10连击）
        m = re.search(r'(\d+)连击', desc)
        if m:
            return int(m.group(1))
        return default

    def _parse_counters(self, counters_raw) -> List[str]:
        """
        解析应对类型列表。
        旧格式：[{'type': '应对攻击', ...}]
        新格式：['attack', 'defense', 'status'] 或 ['应对攻击', ...]
        """
        if not counters_raw:
            return []
        result = []
        type_map = {
            '应对攻击': 'attack', '应对防御': 'defense', '应对状态': 'status',
            'attack': 'attack', 'defense': 'defense', 'status': 'status',
        }
        for item in counters_raw:
            if isinstance(item, dict):
                t = item.get('type', '')
                mapped = type_map.get(t, t)
                if mapped:
                    result.append(mapped)
            elif isinstance(item, str):
                mapped = type_map.get(item, item)
                result.append(mapped)
        return list(dict.fromkeys(result))  # 去重保序

    def _parse_effects(self, effects_data: List[Dict]) -> List[Effect]:
        """
        解析技能效果列表。
        支持新格式（爬虫产出）和旧格式（手写 battle_data）。
        """
        effects = []
        for ed in effects_data:
            t = ed.get('type', '')
            effect = self._parse_single_effect(t, ed)
            if effect is not None:
                effects.append(effect)
        return effects

    def _parse_single_effect(self, t: str, ed: Dict) -> Optional[Effect]:
        """将单条 effect dict 转换为 Effect 对象"""

        # ── 新格式（爬虫）─────────────────────────────────────────

        # buff/debuff（层数，按 stat 字段）
        if t in ('buff', 'debuff'):
            is_buff = (t == 'buff')
            stat = ed.get('stat', '')
            layers = ed.get('layers', 1)
            target = 'self' if ed.get('target') == 'self' else 'opponent'
            # 用 desc 传递 stat 名给 _apply_stat_modifier
            stat_cn = {'atk': '物攻', 'matk': '魔攻', 'def': '物防', 'mdef': '魔防', 'spd': '速度'}.get(stat, stat)
            return Effect(
                type=EffectType.STAT_BUFF if is_buff else EffectType.STAT_DEBUFF,
                target=target,
                value=layers,
                desc=stat_cn,
            )

        # buff_flat / debuff_flat（速度固定值）
        if t in ('buff_flat', 'debuff_flat'):
            stat = ed.get('stat', '')
            value = ed.get('value', 0)
            target = 'self' if ed.get('target') == 'self' else 'opponent'
            stat_cn = {'atk': '物攻', 'matk': '魔攻', 'def': '物防', 'mdef': '魔防', 'spd': '速度'}.get(stat, stat)
            return Effect(
                type=EffectType.STAT_BUFF if value > 0 else EffectType.STAT_DEBUFF,
                target=target,
                value=abs(value),
                desc=stat_cn + '_flat',  # 标记为 flat 型
            )

        # status_ailment（中毒/灼烧/冻结/眩晕/寄生）
        if t == 'status_ailment':
            ailment = ed.get('ailment', '')
            layers = ed.get('layers', 1)
            target = 'self' if ed.get('target') == 'self' else 'opponent'
            status_map = {
                'poison': 'poison', 'burn': 'burn',
                'freeze': 'freeze', 'stun': 'stun', 'parasite': 'parasite',
            }
            status_name = status_map.get(ailment, ailment)
            return Effect(
                type=EffectType.APPLY_STATUS,
                target=target,
                value=layers,
                status_type=status_name,
                stacks=layers,
            )

        # heal
        if t == 'heal':
            percent = ed.get('percent', ed.get('value', 0))
            target = 'self' if ed.get('target', 'self') == 'self' else 'opponent'
            return Effect(type=EffectType.HEAL, target=target, value=float(percent))

        # energy_restore
        if t == 'energy_restore':
            target = 'self' if ed.get('target', 'self') == 'self' else 'opponent'
            return Effect(type=EffectType.ENERGY_RESTORE, target=target, value=ed.get('value', 1))

        # energy_drain（降低对手能量）
        if t == 'energy_drain':
            return Effect(type=EffectType.ENERGY_RESTORE, target='opponent', value=-ed.get('value', 1))

        # apply_mark
        if t == 'apply_mark':
            mark_key = ed.get('mark', '')
            stacks = ed.get('stacks', 1)
            target = ed.get('target', 'enemy')
            if target == 'enemy':
                target = 'opponent'
            is_positive = ed.get('is_positive', False)
            return Effect(
                type=EffectType.APPLY_MARK,
                target=target,
                value=1 if is_positive else -1,
                status_type=mark_key,
                stacks=stacks,
            )

        # power_bonus（条件威力加成）
        if t == 'power_bonus':
            return Effect(
                type=EffectType.POWER_BONUS,
                target='opponent',
                value=ed.get('value', 0),
                conditional=ed.get('conditional', True),
            )

        # power_multiply
        if t == 'power_multiply':
            return Effect(
                type=EffectType.POWER_BONUS,
                target='opponent',
                value=ed.get('value', 2) * 100,  # 存为倍率×100便于识别
                conditional=ed.get('conditional', True),
                desc='multiply',
            )

        # energy_cost_permanent
        if t == 'energy_cost_permanent':
            return Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=ed.get('value', 0),
                desc='energy_cost_permanent',
            )

        # consume_all_energy
        if t == 'consume_all_energy':
            return Effect(
                type=EffectType.DYNAMIC_POWER,
                target='opponent',
                value=ed.get('power_per_energy', 21),
                desc='consume_all_energy',
            )

        # counter（应对额外效果，记录类型和描述）
        if t == 'counter':
            ct_map = {'应对攻击': 'attack', '应对防御': 'defense', '应对状态': 'status'}
            ct = ct_map.get(ed.get('counter_type', ''), ed.get('counter_type', ''))
            return Effect(
                type=EffectType.COUNTER,
                target='opponent',
                value=0,
                desc=ct + ':' + ed.get('extra_desc', ''),
            )

        # dispel_*
        if t == 'dispel_buff':
            target = 'self' if ed.get('target') == 'self' else 'opponent'
            return Effect(type=EffectType.DISPEL_BUFF, target=target, value=0)
        if t == 'dispel_debuff':
            target = 'self' if ed.get('target') == 'self' else 'opponent'
            return Effect(type=EffectType.DISPEL_DEBUFF, target=target, value=0)
        if t == 'dispel_mark':
            target = 'self' if ed.get('target') == 'self' else 'opponent'
            return Effect(type=EffectType.DISPEL_MARK, target=target, value=0)

        # lifesteal
        if t == 'lifesteal':
            return Effect(type=EffectType.LIFESTEAL, target='self', value=ed.get('value', 0.3))

        # ── 旧格式（手写 battle_data）───────────────────────────────

        old_map = {
            'energy_restore': EffectType.ENERGY_RESTORE,
            'power_bonus': EffectType.POWER_BONUS,
            'stat_buff': EffectType.STAT_BUFF,
            'stat_debuff': EffectType.STAT_DEBUFF,
            'damage_reduction': EffectType.DAMAGE_REDUCTION,
            'dynamic_power': EffectType.DYNAMIC_POWER,
            'lifesteal': EffectType.LIFESTEAL,
            'extra_hits': EffectType.EXTRA_HITS,
            'apply_status': EffectType.APPLY_STATUS,
            'apply_mark': EffectType.APPLY_MARK,
            'heal': EffectType.HEAL,
            'switch_out': EffectType.SWITCH_OUT,
            'revive': EffectType.REVIVE,
            'cute': EffectType.CUTE,
            'return': EffectType.RETURN,
            'charge': EffectType.CHARGE,
            'swift': EffectType.SWIFT,
            'burst': EffectType.BURST,
            'dispel_buff': EffectType.DISPEL_BUFF,
            'dispel_debuff': EffectType.DISPEL_DEBUFF,
            'dispel_mark': EffectType.DISPEL_MARK,
            'counter': EffectType.COUNTER,
        }
        if t in old_map:
            return Effect(
                type=old_map[t],
                target=ed.get('target', 'opponent'),
                value=ed.get('value', 0),
                conditional=ed.get('conditional', False),
                desc=ed.get('desc', ''),
                status_type=ed.get('status_type', ''),
                stacks=ed.get('stacks', 1),
            )

        return None  # 未知类型忽略

    # ── 精灵数据 ──────────────────────────────────────────────────

    def load_pets(self):
        path = self.data_dir / "pets.json"
        with open(path, 'r', encoding='utf-8') as f:
            pets_data = json.load(f)

        for pet_data in pets_data:
            types = []
            if pet_data.get('type'):
                types.append(pet_data['type'])
            if pet_data.get('type2'):
                types.append(pet_data['type2'])

            traits = [
                Trait(
                    name=t.get('name', ''),
                    desc=t.get('desc', ''),
                    icon_url=t.get('icon_url', ''),
                )
                for t in pet_data.get('traits', [])
            ]

            stats = pet_data.get('stats', {})

            weight_kg = self._parse_weight(pet_data.get('weight', ''))

            pet = PetTemplate(
                id=pet_data.get('id', 0),
                name=pet_data.get('name', ''),
                types=types,
                stats=stats,
                traits=traits,
                learnable_skills=pet_data.get('skills', []),
                evolution=pet_data.get('evolution', []),
                is_legendary=pet_data.get('is_legendary', False),
                bloodline=self._normalize_bloodline(
                    pet_data.get('bloodline') or self.bloodline_overrides.get(pet_data.get('name', ''))
                ),
                weight_kg=weight_kg,
            )
            self.pets[pet.name] = pet

    @staticmethod
    def _parse_weight(weight_str: str) -> float:
        """解析体重字符串，如 '5.5~7KG' → 6.25（取均值）"""
        if not weight_str:
            return 0.0
        import re
        # 移除单位，提取数字
        clean = weight_str.upper().replace('KG', '').strip()
        parts = re.split(r'[~\-]', clean)
        try:
            values = [float(p.strip()) for p in parts if p.strip()]
            if values:
                return sum(values) / len(values)
        except ValueError:
            pass
        return 0.0

    # ── 辅助解析 ──────────────────────────────────────────────────

    def _parse_category(self, category_str: str) -> SkillCategory:
        s = category_str.lower()
        if any(k in s for k in ['物攻', '魔攻', 'attack', '攻击']):
            return SkillCategory.ATTACK
        elif any(k in s for k in ['防御', 'defense', '减伤', '护盾']):
            return SkillCategory.DEFENSE
        return SkillCategory.STATUS

    def _parse_damage_type(self, type_str: str) -> DamageType:
        if '物攻' in type_str or 'physical' in type_str.lower():
            return DamageType.PHYSICAL
        return DamageType.MAGICAL

    def get_type_effectiveness(self, attacker_type: str, defender_type: str) -> float:
        if attacker_type not in self.type_chart:
            return 1.0
        if defender_type not in self.types:
            return 1.0
        return self.type_chart[attacker_type][self.types.index(defender_type)]

    def _parse_desc_to_effects(self, desc: str, category: SkillCategory):
        """
        从技能描述文字解析效果列表。
        用于补全 battle_data 中 effects=[] 的技能。
        返回 (effects_list, counters_list)。
        """
        import re
        effects = []
        counters = []

        # ── 应对系统识别 ─────────────────────────────────────────────
        if '应对攻击' in desc:
            counters.append('attack')
        if '应对防御' in desc:
            counters.append('defense')
        if '应对状态' in desc:
            counters.append('status')

        # 拆分主效果和应对效果，分别处理
        main_desc = re.split(r'[，。]?\s*应对[攻防状]', desc)[0]
        counter_desc = ''
        m = re.search(r'应对[攻击防御状态]+：(.+)', desc)
        if m:
            counter_desc = m.group(1)

        # ── 主效果解析 ───────────────────────────────────────────────

        # 天气变更
        weather_map = {'雨天': 'rain', '沙暴': 'sandstorm', '暴风雪': 'blizzard'}
        for weather_cn, weather_key in weather_map.items():
            if '将天气' in main_desc and weather_cn in main_desc:
                effects.append(Effect(
                    type=EffectType.ENERGY_RESTORE,
                    target='self',
                    value=0,
                    desc=f'set_weather:{weather_key}',
                ))
                break

        # 减伤（damage_reduction，防御技能）
        m = re.search(r'减伤(\d+)%', main_desc)
        if m:
            reduction = int(m.group(1)) / 100
            effects.append(Effect(type=EffectType.DAMAGE_REDUCTION, target='self', value=reduction))

        # 自身回复生命
        m = re.search(r'自己回复(\d+)%生命', main_desc)
        if m:
            effects.append(Effect(type=EffectType.HEAL, target='self', value=int(m.group(1)) / 100))

        # 自己脱离（换宠）
        if '自己脱离' in main_desc or ('随后脱离' in main_desc and '自身及背包' not in main_desc):
            effects.append(Effect(type=EffectType.SWITCH_OUT, target='self', value=0))

        # 使敌方返场
        if '使敌方精灵返场' in main_desc or '敌方返场' in main_desc:
            effects.append(Effect(type=EffectType.SWITCH_OUT, target='opponent', value=0))

        # 偷取/失去能量
        m = re.search(r'偷取敌方(\d+)能量', main_desc)
        if m:
            v = int(m.group(1))
            effects.append(Effect(type=EffectType.ENERGY_RESTORE, target='opponent', value=-v))
            effects.append(Effect(type=EffectType.ENERGY_RESTORE, target='self', value=v))

        # 自己回复N能量（种子弹、火苗、藤绞等）
        m = re.search(r'自己回复(\d+)能量', main_desc)
        if m:
            effects.append(Effect(type=EffectType.ENERGY_RESTORE, target='self', value=int(m.group(1))))

        # 敌方失去N能量
        m = re.search(r'敌方失去(\d+)能量', main_desc)
        if m:
            effects.append(Effect(type=EffectType.ENERGY_RESTORE, target='opponent', value=-int(m.group(1))))

        # 能耗永久-N（每次使用后，水炮/冲撞类）
        # 排除"全技能能耗永久"，那类由赤子之心专项处理
        m = re.search(r'(?<!全技能)能耗永久-(\d+)', main_desc)
        if m and '全技能能耗永久' not in main_desc:
            delta = -int(m.group(1))
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=delta,
                desc='energy_cost_permanent_self',
            ))

        # 能耗永久+N（每次使用后，重击类）
        m = re.search(r'能耗永久\+(\d+)', main_desc)
        if m:
            delta = int(m.group(1))
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=delta,
                desc='energy_cost_permanent_self',
            ))

        # ── Stat buff/debuff 解析 ────────────────────────────────────
        STAT_PATTERNS = [
            (r'自己获得物攻和魔攻\+(\d+)%', [('物攻', 'self', True), ('魔攻', 'self', True)]),
            (r'自己获得双攻\+(\d+)%', [('物攻', 'self', True), ('魔攻', 'self', True)]),
            (r'自己获得双防\+(\d+)%', [('物防', 'self', True), ('魔防', 'self', True)]),
            (r'自己获得全攻\+(\d+)%', [('物攻', 'self', True), ('魔攻', 'self', True)]),
            (r'自己获得物攻\+(\d+)%', [('物攻', 'self', True)]),
            (r'自己获得魔攻\+(\d+)%', [('魔攻', 'self', True)]),
            (r'自己获得物防\+(\d+)%', [('物防', 'self', True)]),
            (r'自己获得魔防\+(\d+)%', [('魔防', 'self', True)]),
            (r'提升自身(\d+)%物攻', [('物攻', 'self', True)]),
            (r'提升自身(\d+)%魔攻', [('魔攻', 'self', True)]),
            (r'提升自身(\d+)%物防', [('物防', 'self', True)]),
            (r'提升自身(\d+)%魔防', [('魔防', 'self', True)]),
            (r'降低敌方(\d+)%物攻(?!和)', [('物攻', 'opponent', False)]),
            (r'降低敌方(\d+)%魔攻(?!和)', [('魔攻', 'opponent', False)]),
            (r'降低敌方(\d+)%物防(?!和)', [('物防', 'opponent', False)]),
            (r'降低敌方(\d+)%魔防(?!和)', [('魔防', 'opponent', False)]),
            (r'降低敌方(\d+)%物攻和物防', [('物攻', 'opponent', False), ('物防', 'opponent', False)]),
            (r'降低敌方(\d+)%魔攻和魔防', [('魔攻', 'opponent', False), ('魔防', 'opponent', False)]),
            (r'降低敌方(\d+)%双防', [('物防', 'opponent', False), ('魔防', 'opponent', False)]),
            (r'降低敌方(\d+)%双攻', [('物攻', 'opponent', False), ('魔攻', 'opponent', False)]),
            (r'敌方获得物攻-(\d+)%', [('物攻', 'opponent', False)]),
            (r'敌方获得魔攻-(\d+)%', [('魔攻', 'opponent', False)]),
            (r'敌方获得物防-(\d+)%', [('物防', 'opponent', False)]),
            (r'敌方获得魔防-(\d+)%', [('魔防', 'opponent', False)]),
            (r'敌方获得双防-(\d+)%', [('物防', 'opponent', False), ('魔防', 'opponent', False)]),
            (r'敌方获得双攻-(\d+)%', [('物攻', 'opponent', False), ('魔攻', 'opponent', False)]),
            (r'敌方获得物防和魔防-(\d+)%', [('物防', 'opponent', False), ('魔防', 'opponent', False)]),
            # 攻防自身debuff（极限撕裂等：自己双攻-50%）
            (r'自己获得双攻-(\d+)%', [('物攻', 'self', False), ('魔攻', 'self', False)]),
            (r'使用后自己获得双攻-(\d+)%', [('物攻', 'self', False), ('魔攻', 'self', False)]),
            # 堆雪人：降低敌方20%魔防
            (r'降低敌方(\d+)%魔防', [('魔防', 'opponent', False)]),
        ]

        added_stats = set()  # 防止重复添加
        for pattern, stat_list in STAT_PATTERNS:
            m = re.search(pattern, main_desc)
            if m:
                val = int(m.group(1))
                layers = max(1, val // 10)
                for stat_name, tgt, is_buff in stat_list:
                    key = (stat_name, tgt, is_buff)
                    if key not in added_stats:
                        added_stats.add(key)
                        effects.append(Effect(
                            type=EffectType.STAT_BUFF if is_buff else EffectType.STAT_DEBUFF,
                            target=tgt,
                            value=layers,
                            desc=stat_name,
                        ))

        # 石肤术：物防+160% 魔防-60%（不重复添加）
        if '物防' in main_desc and '魔防-' in main_desc:
            m1 = re.search(r'物防\+(\d+)%', main_desc)
            m2 = re.search(r'魔防-(\d+)%', main_desc)
            if m1 and m2 and ('物防', 'self', True) not in added_stats:
                added_stats.add(('物防', 'self', True))
                added_stats.add(('魔防', 'self', False))
                effects.append(Effect(type=EffectType.STAT_BUFF, target='self',
                                      value=max(1, int(m1.group(1))//10), desc='物防'))
                effects.append(Effect(type=EffectType.STAT_DEBUFF, target='self',
                                      value=max(1, int(m2.group(1))//10), desc='魔防'))

        # 双攻+X% 和 双防-Y%（怒火类）
        m_da = re.search(r'双攻\+(\d+)%和双防-(\d+)%', main_desc)
        if m_da and ('物攻', 'self', True) not in added_stats:
            va = max(1, int(m_da.group(1))//10)
            vd = max(1, int(m_da.group(2))//10)
            for stat in ('物攻', '魔攻'):
                added_stats.add((stat, 'self', True))
                effects.append(Effect(type=EffectType.STAT_BUFF, target='self', value=va, desc=stat))
            for stat in ('物防', '魔防'):
                added_stats.add((stat, 'self', False))
                effects.append(Effect(type=EffectType.STAT_DEBUFF, target='self', value=vd, desc=stat))

        # 速度固定加成
        m = re.search(r'速度\+(\d+)(?!%)', main_desc)
        if m:
            effects.append(Effect(type=EffectType.STAT_BUFF, target='self',
                                  value=int(m.group(1)), desc='速度_flat'))
        m = re.search(r'速度-(\d+)(?!%)', main_desc)
        if m:
            effects.append(Effect(type=EffectType.STAT_DEBUFF, target='self',
                                  value=int(m.group(1)), desc='速度_flat'))

        # 速度百分比加成
        m = re.search(r'速度\+(\d+)%', main_desc)
        if m:
            effects.append(Effect(type=EffectType.STAT_BUFF, target='self',
                                  value=max(1, int(m.group(1))//10), desc='速度'))
        m = re.search(r'速度-(\d+)%', main_desc)
        if m:
            effects.append(Effect(type=EffectType.STAT_DEBUFF, target='self',
                                  value=max(1, int(m.group(1))//10), desc='速度'))

        # 双防-X%（独立匹配，防止遗漏）
        m = re.search(r'双防-(\d+)%', main_desc)
        if m and ('物防', 'self', False) not in added_stats:
            vd = max(1, int(m.group(1)) // 10)
            for stat in ('物防', '魔防'):
                added_stats.add((stat, 'self', False))
                effects.append(Effect(type=EffectType.STAT_DEBUFF, target='self', value=vd, desc=stat))

        # 焚烧烙印：驱散双方印记，每层给敌方5层灼烧
        # 注意：必须在 STATUS_PATTERNS 之前处理，避免直接解析"5层灼烧"
        is_burn_per_mark = '驱散双方所有印记' in main_desc and '灼烧' in main_desc
        if is_burn_per_mark:
            # 先记录对手印记层数再驱散（通过特殊 effect 在引擎中处理）
            effects.append(Effect(type=EffectType.DISPEL_MARK, target='self', value=0))
            effects.append(Effect(type=EffectType.DISPEL_MARK, target='opponent', value=0))
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='opponent',
                value=0,
                desc='burn_per_mark_dispelled',
            ))
            return effects, counters  # 直接返回，避免后续解析产生冲突

        # ── 状态效果 ──────────────────────────────────────────────────
        STATUS_PATTERNS = [
            (r'敌方获得(\d+)层中毒', 'poison', 'opponent'),
            (r'使敌方获得(\d+)层中毒', 'poison', 'opponent'),
            (r'敌方获得(\d+)层灼烧', 'burn', 'opponent'),
            (r'使敌方获得(\d+)层灼烧', 'burn', 'opponent'),
            (r'敌方获得(\d+)层冻结', 'freeze', 'opponent'),
            (r'使敌方获得(\d+)层冻结', 'freeze', 'opponent'),
            (r'敌方获得(\d+)层寄生', 'parasite', 'opponent'),
            (r'使敌方获得(\d+)层寄生', 'parasite', 'opponent'),
            (r'使敌方(\d+)回合内无法行动', 'stun', 'opponent'),  # 眩晕
            (r'自己获得(\d+)层中毒', 'poison', 'self'),
            (r'自己获得(\d+)层灼烧', 'burn', 'self'),
        ]
        for pat, status_type, tgt in STATUS_PATTERNS:
            m = re.search(pat, main_desc)
            if m:
                stacks = int(m.group(1))
                if status_type == 'stun':
                    effects.append(Effect(
                        type=EffectType.APPLY_STATUS,
                        target=tgt,
                        value=stacks,
                        status_type='stun',
                        stacks=stacks,
                    ))
                else:
                    effects.append(Effect(
                        type=EffectType.APPLY_STATUS,
                        target=tgt,
                        value=stacks,
                        status_type=status_type,
                        stacks=stacks,
                    ))

        # ── 印记 ──────────────────────────────────────────────────────
        m = re.search(r'敌方获得(\d+)层减速印记', main_desc)
        if m:
            from core.status_effects import StatusEffectType
            effects.append(Effect(
                type=EffectType.APPLY_MARK,
                target='opponent',
                value=-1,
                status_type=StatusEffectType.SLOW_MARK.value,
                stacks=int(m.group(1)),
            ))

        m = re.search(r'敌方获得(\d+)层萌化', main_desc)
        if m:
            effects.append(Effect(type=EffectType.CUTE, target='opponent', value=int(m.group(1))))

        if '蓄势印记' in main_desc:
            from core.status_effects import StatusEffectType
            m = re.search(r'(\d+)层蓄势印记', main_desc)
            stacks = int(m.group(1)) if m else 1
            effects.append(Effect(
                type=EffectType.APPLY_MARK,
                target='self',
                value=1,
                status_type=StatusEffectType.MOMENTUM_MARK.value,
                stacks=stacks,
            ))

        # 星陨印记
        m = re.search(r'敌方获得(\d+)层星陨印记', main_desc)
        if m:
            from core.status_effects import StatusEffectType
            effects.append(Effect(
                type=EffectType.APPLY_MARK,
                target='opponent',
                value=-1,
                status_type=StatusEffectType.STAR_FALL_MARK.value,
                stacks=int(m.group(1)),
            ))

        # ── 蓄力技能（无标记时自动识别）────────────────────────────
        if '蓄力' in main_desc and not any(e.type == EffectType.CHARGE for e in effects):
            effects.append(Effect(type=EffectType.CHARGE, target='self', value=0))

        # ── 迸发 ──────────────────────────────────────────────────────
        if '迸发' in main_desc and not any(e.type == EffectType.BURST for e in effects):
            effects.append(Effect(type=EffectType.BURST, target='self', value=1))

        # ── 迅捷（swift）──────────────────────────────────────────────
        if '迅捷' in main_desc:
            effects.append(Effect(type=EffectType.SWIFT, target='self', value=0))

        # ── 驱散 ───────────────────────────────────────────────────────
        if '驱散敌方' in main_desc and '增益' in main_desc:
            effects.append(Effect(type=EffectType.DISPEL_BUFF, target='opponent', value=0))
        if '驱散自身' in main_desc and '减益' in main_desc:
            effects.append(Effect(type=EffectType.DISPEL_DEBUFF, target='self', value=0))
        if '驱散敌方' in main_desc and '减益' in main_desc:
            effects.append(Effect(type=EffectType.DISPEL_DEBUFF, target='opponent', value=0))
        if ('驱散双方' in main_desc or '驱散所有印记' in main_desc) and '印记' in main_desc:
            if not is_burn_per_mark:  # 焚烧烙印在前面已处理
                effects.append(Effect(type=EffectType.DISPEL_MARK, target='self', value=0))
                effects.append(Effect(type=EffectType.DISPEL_MARK, target='opponent', value=0))

        # ── 双方换宠（均脱离）──────────────────────────────────────────
        if '均脱离' in main_desc:
            effects.append(Effect(type=EffectType.SWITCH_OUT, target='self', value=0))
            effects.append(Effect(type=EffectType.SWITCH_OUT, target='opponent', value=0))

        # ── 萌化（自身获得萌化的降属性效果）────────────────────────────
        if '自己获得萌化' in main_desc or ('获得萌化' in main_desc and '敌方获得萌化' not in main_desc):
            m = re.search(r'降低敌方(\d+)%物攻和物防', main_desc)
            if m:
                v = max(1, int(m.group(1)) // 10)
                if ('物攻', 'opponent', False) not in added_stats:
                    added_stats.add(('物攻', 'opponent', False))
                    effects.append(Effect(type=EffectType.STAT_DEBUFF, target='opponent', value=v, desc='物攻'))
                if ('物防', 'opponent', False) not in added_stats:
                    added_stats.add(('物防', 'opponent', False))
                    effects.append(Effect(type=EffectType.STAT_DEBUFF, target='opponent', value=v, desc='物防'))

        # ── 钧势（物防+X% 速度-Y 固定值）────────────────────────────
        if '物防' in main_desc and '速度-' in main_desc:
            m_def = re.search(r'物防\+(\d+)%', main_desc)
            m_spd = re.search(r'速度-(\d+)(?!%)', main_desc)
            if m_def and m_spd and ('物防', 'self', True) not in added_stats:
                added_stats.add(('物防', 'self', True))
                effects.append(Effect(type=EffectType.STAT_BUFF, target='self',
                                      value=max(1, int(m_def.group(1))//10), desc='物防'))
                effects.append(Effect(type=EffectType.STAT_DEBUFF, target='self',
                                      value=int(m_spd.group(1)), desc='速度_flat'))

        # ── 特殊复杂技能（按技能描述关键词硬编码）─────────────────────

        # 冰锋横扫：威力=敌方技能总能耗×10（运行时计算）
        if '威力等于敌方精灵技能总能耗的10倍' in main_desc:
            effects.append(Effect(
                type=EffectType.DYNAMIC_POWER,
                target='opponent',
                value=10,
                desc='sum_enemy_energy_cost',
            ))

        # 雾气环绕：回复能量=敌方技能总能耗的一半
        if '回复能量' in main_desc and '敌方技能总能耗' in main_desc:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=0,
                desc='half_enemy_energy_cost',
            ))

        # 炎爆术：将敌方印记转换为三倍灼烧层数
        if '将敌方印记转换为三倍' in main_desc and '灼烧' in main_desc:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='opponent',
                value=0,
                desc='convert_mark_to_burn',
            ))

        # 恶念交换：与敌方交换生命比例
        if '与敌方交换生命比例' in main_desc:
            effects.append(Effect(
                type=EffectType.HEAL,
                target='self',
                value=0,
                desc='swap_hp_ratio',
            ))

        # 欺诈契约：与敌方交换增益和减益
        if '与敌方交换增益和减益' in main_desc:
            effects.append(Effect(
                type=EffectType.DISPEL_BUFF,
                target='self',
                value=0,
                desc='swap_buffs_debuffs',
            ))

        # 隐藏条款：与敌方交换本回合所用技能
        if '与敌方交换技能' in main_desc:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=0,
                desc='swap_current_skills',
            ))

        # 伪造账单：敌方下次回复生命改为失去2倍
        if '回复生命改为失去2倍' in main_desc:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='opponent',
                value=0,
                desc='heal_to_damage:2',
            ))

        # 逆向演化：解除萌化，每层转移给敌方
        if ('解除萌化' in main_desc and '转移给敌方' in main_desc) or \
           ('解除萌化' in main_desc and '给敌方赋予' in main_desc):
            effects.append(Effect(
                type=EffectType.CUTE,
                target='self',
                value=0,
                desc='reverse_cute',
            ))

        # 反弹：将自己的萌化转移给敌方
        if '将自己的萌化转移给敌方' in main_desc:
            effects.append(Effect(
                type=EffectType.CUTE,
                target='self',
                value=0,
                desc='transfer_cute',
            ))

        # 落井下毒：敌方减益层数翻倍
        if '敌方精灵减益的层数翻倍' in main_desc:
            effects.append(Effect(
                type=EffectType.STAT_DEBUFF,
                target='opponent',
                value=0,
                desc='double_debuff_stacks',
            ))

        # 耀眠/震击：敌方连击数-N（减少下回合连击）
        m = re.search(r'敌方获得连击数-(\d+)', main_desc)
        if m:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='opponent',
                value=0,
                desc=f'hits_debuff:{m.group(1)}',
            ))

        # 腐化：敌方每有1层中毒，获得双攻-30%
        if '每有1层中毒效果' in main_desc and '双攻-' in main_desc:
            effects.append(Effect(
                type=EffectType.STAT_DEBUFF,
                target='opponent',
                value=0,
                desc='poison_to_debuff',
            ))
            # 移除 STAT_PATTERNS 已添加的重复 debuff（双攻-30%被直接解析了）
            effects[:] = [e for e in effects if not (
                e.type == EffectType.STAT_DEBUFF
                and e.desc in ('物攻', '魔攻')
                and e.target == 'opponent'
                and e.value > 0  # STAT_PATTERNS 添加的是正数 layers
            )]

        # 暴风眼：行动时连击数+100%（下回合生效）
        if '行动时连击数+100%' in main_desc:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=0,
                desc='storm_eye_buff',
            ))

        # 热身运动：自己获得连击数+3
        if '自己获得连击数+3' in main_desc or '获得连击数+3' in main_desc:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=0,
                desc='warmup_hits_bonus',
            ))

        # 赤子之心：萌化+全技能能耗永久-3
        if '全技能能耗永久-3' in main_desc:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=-3,
                desc='energy_cost_permanent',
            ))

        # 蓄水：下次使用技能能耗-6
        if '下次使用的技能能耗-6' in main_desc or '下次使用技能能耗-6' in main_desc:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=0,
                desc='next_skill_energy_discount',
            ))

        # 交换两侧技能位置
        if '交换两侧技能位置' in main_desc:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=0,
                desc='swap_adjacent_skills',
            ))

        # 使用后两侧技能威力永久+N
        m = re.search(r'使用后两侧技能(?:的)?威力永久\+(\d+)', main_desc)
        if m:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=int(m.group(1)),
                desc='adjacent_power_permanent',
            ))

        # 己方队伍获得N次随机奉献
        m = re.search(r'己方队伍获得(\d+)次随机奉献', main_desc)
        if m:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='self',
                value=int(m.group(1)),
                desc='grant_random_devotion',
            ))

        # 己方队伍获得1次奉献：获得X
        devotion_map = {
            '敌方获得2层中毒': 'poison',
            '获得10%吸血': 'lifesteal',
            '获得连击数+1': 'combo',
            '威力+20': 'power',
            '能耗-2': 'energy',
        }
        for phrase, kind in devotion_map.items():
            if f'己方队伍获得1次奉献：{phrase}' in main_desc:
                effects.append(Effect(
                    type=EffectType.ENERGY_RESTORE,
                    target='self',
                    value=1,
                    desc=f'grant_specific_devotion:{kind}',
                ))
                break

        # 三鼓作气：物攻+30%，3连击
        if '提升自身30%物攻' in main_desc and '3连击' in main_desc:
            if ('物攻', 'self', True) not in added_stats:
                added_stats.add(('物攻', 'self', True))
                effects.append(Effect(type=EffectType.STAT_BUFF, target='self', value=3, desc='物攻'))


        # 示弱：萌化+速度永久+150
        if '自己获得萌化' in main_desc and '速度永久+150' in main_desc:
            # 萌化效果（清除增益降攻防）+ 速度
            if ('速度', 'self', True) not in added_stats:
                added_stats.add(('速度', 'self', True))
                effects.append(Effect(type=EffectType.STAT_BUFF, target='self', value=150, desc='速度_flat'))

        # 聒噪：敌方全攻击技能能耗+3，持续3回合
        if '全攻击技能能耗+3' in main_desc:
            effects.append(Effect(
                type=EffectType.ENERGY_RESTORE,
                target='opponent',
                value=0,
                desc='all_attack_energy_cost_up',
            ))

        # 槽位条件 buff/debuff：本技能位于特定槽位时额外获得属性变化
        slot_condition_patterns = [
            (r'本技能位于1号或3号位时额外获得(.+?)([+-]\d+%?)', 'slot_13', 'self'),
            (r'本技能位于1号位时额外获得(.+?)([+-]\d+%?)', 'slot_1', 'self'),
            (r'本技能位于3号位时额外获得(.+?)([+-]\d+%?)', 'slot_3', 'self'),
            (r'本技能位于1号或3号位时敌方获得(.+?)([+-]\d+%?)', 'slot_13', 'opponent'),
            (r'本技能位于1号位时敌方获得(.+?)([+-]\d+%?)', 'slot_1', 'opponent'),
            (r'本技能位于3号位时敌方获得(.+?)([+-]\d+%?)', 'slot_3', 'opponent'),
        ]
        slot_stat_map = {
            '物攻': ['物攻'],
            '魔攻': ['魔攻'],
            '物防': ['物防'],
            '魔防': ['魔防'],
            '双攻': ['物攻', '魔攻'],
            '双防': ['物防', '魔防'],
            '速度': ['速度'],
        }
        for pattern, slot_tag, target in slot_condition_patterns:
            m = re.search(pattern, main_desc)
            if not m:
                continue
            stat_text = m.group(1).strip()
            value_text = m.group(2).strip()
            sign = 1 if value_text.startswith('+') else -1
            raw_value = value_text[1:]
            is_percent = raw_value.endswith('%')
            numeric_value = int(raw_value.rstrip('%'))
            stat_names = slot_stat_map.get(stat_text)
            if not stat_names:
                continue

            effect_type = EffectType.STAT_BUFF if sign > 0 else EffectType.STAT_DEBUFF
            effect_value = numeric_value if not is_percent else max(1, numeric_value // 10)
            desc_suffix = '_flat' if (not is_percent and stat_text == '速度') else ''

            for stat_name in stat_names:
                effect_desc = f'{slot_tag}:{stat_name}{desc_suffix}'
                base_desc = f'{stat_name}{desc_suffix}'
                effects[:] = [e for e in effects if not (
                    e.type == effect_type and
                    e.target == target and
                    e.desc == base_desc and
                    int(e.value) == effect_value
                )]
                effects.append(Effect(
                    type=effect_type,
                    target=target,
                    value=effect_value,
                    desc=effect_desc,
                ))

        # 均势已被上方“物防+X% 且 速度-Y”规则覆盖；
        # 荟萃疑似已从游戏中删除，当前不自动解析。

        # ── 应对效果写入 COUNTER Effect ──────────────────────────────
        if counters and counter_desc:
            ct_key = counters[0]
            effects.append(Effect(
                type=EffectType.COUNTER,
                target='opponent',
                value=0,
                desc=f'{ct_key}:{counter_desc}',
            ))

        return effects, counters
