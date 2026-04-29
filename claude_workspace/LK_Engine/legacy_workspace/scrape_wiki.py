"""
洛克王国 Wiki 爬虫
从两个来源抓取技能数据并合并：
  1. https://wiki.lcx.cab/lk/  → 技能基础数据（API形式）
  2. https://wiki.biligame.com/rocom/ → 每个技能的效果描述

输出：更新后的 Calculator/Data/battle_data.json
"""

import requests
import urllib.parse
import json
import time
import re
import sys
import io
from pathlib import Path
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
}
OUTPUT_PATH = Path('Calculator/Data/battle_data.json')
DELAY = 0.25  # 请求间隔（秒）
_log_file = None


def log(msg: str):
    """写入 stdout（已设为 utf-8）和日志文件"""
    print(msg, flush=True)
    if _log_file:
        _log_file.write(msg + '\n')
        _log_file.flush()


# ══════════════════════════════════════════════════════════════════
# Part 1: lcx.cab 技能列表
# ══════════════════════════════════════════════════════════════════

def fetch_lcx_skills() -> list:
    log("=== 从 lcx.cab 抓取技能列表 ===")
    base = 'https://wiki.lcx.cab/lk/get_skill_data.php'
    params = 'category=all&attribute=all&search=&sort=&direction=desc&energy_value=all'
    all_skills = []
    page = 1
    while True:
        url = f'{base}?page={page}&{params}'
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            batch = r.json()
            if not batch:
                break
            all_skills.extend(batch)
            log(f"  第{page}页: {len(batch)}个技能（累计{len(all_skills)}）")
            page += 1
            time.sleep(DELAY)
        except Exception as e:
            log(f"  第{page}页出错: {e}")
            break
    log(f"lcx.cab 共获取 {len(all_skills)} 个技能\n")
    return all_skills


# ══════════════════════════════════════════════════════════════════
# Part 2: biligame 技能详情
# ══════════════════════════════════════════════════════════════════

def fetch_biligame_skill(name: str) -> dict | None:
    """抓取 biligame wiki 上一个技能的详情页"""
    url = 'https://wiki.biligame.com/rocom/' + urllib.parse.quote(name)
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.content, 'html.parser')
        content = (soup.find('div', class_='mw-parser-output') or
                   soup.find('div', id='mw-content-text'))
        if not content:
            return None
        text = content.get_text(separator=' | ', strip=True)
        if '此页面目前没有内容' in text or '✦' not in text:
            return None
        return parse_biligame_skill_page(name, text)
    except Exception:
        return None


def parse_biligame_skill_page(name: str, text: str) -> dict:
    """从 biligame 页面文本中解析技能信息"""
    result = {'name': name, 'raw_desc': '', 'parsed_effects': []}
    parts = [p.strip() for p in text.split('|') if p.strip()]

    # 提取效果描述（✦ 之后的部分，直到"可以学会"）
    desc = ''
    for i, part in enumerate(parts):
        if '✦' in part:
            desc = part.replace('✦', '').strip()
            for j in range(i + 1, len(parts)):
                if '可以学会' in parts[j] or '图鉴' in parts[j]:
                    break
                desc += ' ' + parts[j]
            break
    result['raw_desc'] = desc.strip()

    # 元数据
    for part in parts[1:4]:
        if '系' in part and len(part) <= 4:
            result['element'] = part.replace('系', '')
            break
    for i, part in enumerate(parts):
        if '耗能' in part and i > 0:
            try:
                result['energy_cost'] = int(parts[i - 1])
            except Exception:
                pass
            break
    for i, part in enumerate(parts):
        if '技能威力' in part and i > 0:
            try:
                result['power'] = int(parts[i - 1])
            except Exception:
                result['power'] = 0
            break
    for part in parts:
        if part in ('物攻', '魔攻', '防御', '状态'):
            result['category'] = part
            break

    result['parsed_effects'] = parse_effect_description(desc)
    return result


def parse_effect_description(desc: str) -> list:
    """从自然语言效果描述中提取结构化效果列表"""
    effects = []
    if not desc:
        return effects

    # 先把应对后的部分切掉，只对主效果做 flat 类解析
    main_desc = desc
    for ct in ('应对攻击', '应对防御', '应对状态'):
        if ct in desc:
            main_desc = desc[:desc.index(ct)].strip().rstrip('，,；;')
            break

    # ── buff/debuff（层数）──────────────────────────────────────────
    stat_map = {
        '物攻': 'atk', '魔攻': 'matk',
        '物防': 'def', '魔防': 'mdef',
        '速度': 'spd',
        '攻击': 'atk',
    }
    for stat_cn, stat_key in stat_map.items():
        pats = [
            (r'(?:自[己方]|我方)[^\n，。，,]*?' + stat_cn + r'[+＋](\d+)层', 'self', True),
            (r'(?:对手|敌方|对方)[^\n，。，,]*?' + stat_cn + r'[+＋](\d+)层', 'enemy', True),
            (r'(?:自[己方]|我方)[^\n，。，,]*?' + stat_cn + r'[-－](\d+)层', 'self', False),
            (r'(?:对手|敌方|对方)[^\n，。，,]*?' + stat_cn + r'[-－](\d+)层', 'enemy', False),
        ]
        for pat, target, is_buff in pats:
            m = re.search(pat, desc)
            if m:
                effects.append({
                    'type': 'buff' if is_buff else 'debuff',
                    'target': target,
                    'stat': stat_key,
                    'layers': int(m.group(1)),
                    'per_layer': 0.1,
                })

    # ── buff_flat（速度固定值，只解析主效果部分）────────────────────
    for m in re.finditer(r'速度[+＋](\d+)', main_desc):
        effects.append({'type': 'buff_flat', 'target': 'self', 'stat': 'spd', 'value': int(m.group(1))})
    for m in re.finditer(r'速度[-－](\d+)', main_desc):
        ctx = main_desc[max(0, m.start()-8):m.start()]
        target = 'self' if '自' in ctx else 'enemy'
        effects.append({'type': 'debuff_flat', 'target': target, 'stat': 'spd', 'value': -int(m.group(1))})

    # ── 能量 ────────────────────────────────────────────────────────
    for m in re.finditer(r'(?:回复|获得)(\d+)能量', desc):
        effects.append({'type': 'energy_restore', 'target': 'self', 'value': int(m.group(1))})
    for m in re.finditer(r'(?:对手|敌方)(?:失去|减少)(\d+)能量', desc):
        effects.append({'type': 'energy_drain', 'target': 'enemy', 'value': int(m.group(1))})

    # ── 治疗 ────────────────────────────────────────────────────────
    for m in re.finditer(r'(?:回复|恢复)(\d+)%(?:生命|血量|HP)', desc, re.IGNORECASE):
        effects.append({'type': 'heal', 'target': 'self', 'percent': int(m.group(1)) / 100})

    # ── 状态：中毒 ──────────────────────────────────────────────────
    for m in re.finditer(r'(\d+)层中毒', desc):
        ctx = desc[max(0, m.start()-10):m.start()]
        target = 'self' if any(w in ctx for w in ('自', '己')) else 'enemy'
        effects.append({'type': 'status_ailment', 'ailment': 'poison', 'layers': int(m.group(1)), 'target': target})
    if '中毒' in desc and not any(e.get('ailment') == 'poison' for e in effects):
        target = 'enemy' if any(w in desc for w in ('对手', '敌方', '对方')) else 'self'
        effects.append({'type': 'status_ailment', 'ailment': 'poison', 'layers': 1, 'target': target})

    # ── 状态：灼烧 ──────────────────────────────────────────────────
    for m in re.finditer(r'(\d+)层灼烧', desc):
        ctx = desc[max(0, m.start()-10):m.start()]
        target = 'self' if '自' in ctx else 'enemy'
        effects.append({'type': 'status_ailment', 'ailment': 'burn', 'layers': int(m.group(1)), 'target': target})
    if '灼烧' in desc and not any(e.get('ailment') == 'burn' for e in effects):
        effects.append({'type': 'status_ailment', 'ailment': 'burn', 'layers': 1, 'target': 'enemy'})

    # ── 状态：冻结 ──────────────────────────────────────────────────
    for m in re.finditer(r'(\d+)层冻结', desc):
        effects.append({'type': 'status_ailment', 'ailment': 'freeze', 'layers': int(m.group(1)), 'target': 'enemy'})
    if '冻结' in desc and not any(e.get('ailment') == 'freeze' for e in effects):
        effects.append({'type': 'status_ailment', 'ailment': 'freeze', 'layers': 1, 'target': 'enemy'})

    # ── 状态：眩晕 ──────────────────────────────────────────────────
    if '眩晕' in desc:
        effects.append({'type': 'status_ailment', 'ailment': 'stun', 'layers': 1, 'target': 'enemy'})

    # ── 状态：寄生 ──────────────────────────────────────────────────
    if '寄生' in desc:
        effects.append({'type': 'status_ailment', 'ailment': 'parasite', 'layers': 1, 'target': 'enemy'})

    # ── 威力加成（条件）────────────────────────────────────────────
    for m in re.finditer(r'(?:技能)?威力\+(\d+)', desc):
        effects.append({'type': 'power_bonus', 'value': int(m.group(1)), 'conditional': True})

    # ── 威力倍率 ────────────────────────────────────────────────────
    for m in re.finditer(r'(?:威力|伤害)(?:变为)?(\d+)倍', desc):
        effects.append({'type': 'power_multiply', 'value': int(m.group(1)), 'conditional': True})

    # ── 能耗永久变化 ────────────────────────────────────────────────
    for m in re.finditer(r'(?:全技能)?能耗([+＋\-－])(\d+)', desc):
        sign = 1 if m.group(1) in ('+', '＋') else -1
        effects.append({'type': 'energy_cost_permanent', 'value': sign * int(m.group(2))})

    # ── 印记 ────────────────────────────────────────────────────────
    mark_map = {
        '棘刺印记': ('thorn', False),
        '降灵印记': ('descent_mark', False),
        '星陨印记': ('star_fall_mark', False),
        '光合印记': ('photosynthesis_mark', True),
        '凝霜印记': ('frost_mark', False),
        '蓄电印记': ('charge_mark', True),
        '蓄势印记': ('momentum_mark', True),
        '攻击印记': ('attack_mark', True),
        '风起印记': ('wind_mark', True),
        '龙噬印记': ('dragon_bite_mark', True),
        '湿润印记': ('moist_mark', True),
        '中毒印记': ('poison_mark', False),
    }
    for mark_cn, (mark_key, is_positive) in mark_map.items():
        if mark_cn in desc:
            m2 = re.search(r'(\d+)层' + re.escape(mark_cn), desc)
            stacks = int(m2.group(1)) if m2 else 1
            target = 'self' if is_positive else 'enemy'
            effects.append({
                'type': 'apply_mark',
                'mark': mark_key,
                'stacks': stacks,
                'target': target,
                'is_positive': is_positive,
            })

    # ── 应对额外效果 ─────────────────────────────────────────────────
    for ct_cn in ('应对攻击', '应对防御', '应对状态'):
        if ct_cn in desc:
            m3 = re.search(re.escape(ct_cn) + r'[：:]?\s*(.+?)(?=[。，]|$)', desc)
            extra = m3.group(1).strip() if m3 else ''
            effects.append({'type': 'counter', 'counter_type': ct_cn, 'extra_desc': extra})

    # ── 消耗全部能量 ─────────────────────────────────────────────────
    if '消耗全部能量' in desc or '消耗所有能量' in desc:
        effects.append({'type': 'consume_all_energy', 'power_per_energy': 21})

    # ── 驱散 ─────────────────────────────────────────────────────────
    if any(w in desc for w in ('驱散', '消除', '清除')):
        if '增益' in desc:
            effects.append({'type': 'dispel_buff', 'target': 'enemy'})
        if '减益' in desc:
            effects.append({'type': 'dispel_debuff', 'target': 'self'})
        if '印记' in desc and 'apply_mark' not in str(effects):
            target = 'enemy' if any(w in desc for w in ('对手', '敌方')) else 'self'
            effects.append({'type': 'dispel_mark', 'target': target})

    # ── 吸血 ─────────────────────────────────────────────────────────
    for m in re.finditer(r'吸取[^，。]*?(\d+)%', desc):
        effects.append({'type': 'lifesteal', 'target': 'self', 'value': int(m.group(1)) / 100})
    if '吸血' in desc and not any(e['type'] == 'lifesteal' for e in effects):
        effects.append({'type': 'lifesteal', 'target': 'self', 'value': 0.3})

    return effects


# ══════════════════════════════════════════════════════════════════
# Part 3: 合并并输出
# ══════════════════════════════════════════════════════════════════

def normalize_category(cat: str) -> str:
    mapping = {'物攻': '物攻', '物理': '物攻', '魔攻': '魔攻', '魔法': '魔攻', '防御': '防御', '状态': '状态'}
    return mapping.get(cat, cat)


def build_skill_record(lcx: dict, bili: dict | None) -> dict:
    power_raw = lcx.get('power', '--')
    try:
        power = int(power_raw)
    except Exception:
        power = 0
    try:
        energy = int(lcx.get('energy_consumption', 0))
    except Exception:
        energy = 0

    category = ''
    if bili:
        category = bili.get('category', '')
    if not category:
        category = normalize_category(lcx.get('category', ''))

    record = {
        'id': lcx.get('id', ''),
        'name': lcx.get('name', ''),
        'element': lcx.get('attribute', '普通'),
        'category': category,
        'power': power,
        'energy_cost': energy,
        'description': '',
        'effects': [],
    }
    if bili:
        record['description'] = bili.get('raw_desc', lcx.get('description', ''))
        record['effects'] = bili.get('parsed_effects', [])
    else:
        record['description'] = lcx.get('description', '')
    return record


def main():
    log("洛克王国 Wiki 技能爬虫\n")

    # 1. 抓取 lcx 技能列表
    lcx_skills = fetch_lcx_skills()

    # 2. 读取现有 battle_data.json
    existing = {}
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    existing_skills = existing.get('skills', {})

    # 3. 抓取 biligame 详情
    log("=== 从 biligame 抓取技能详情 ===")
    bili_cache = {}
    total = len(lcx_skills)
    success = 0
    for i, sk in enumerate(lcx_skills):
        name = sk['name']
        bili = fetch_biligame_skill(name)
        bili_cache[name] = bili
        if bili:
            success += 1
        if (i + 1) % 50 == 0 or i == total - 1:
            log(f"  进度: {i+1}/{total} （成功{success}个）")
        time.sleep(DELAY)

    log(f"\nbiligame 抓取完成: {success}/{total} 成功\n")

    # 4. 合并
    log("=== 合并数据 ===")
    merged_skills = {}
    for sk in lcx_skills:
        name = sk['name']
        bili = bili_cache.get(name)
        record = build_skill_record(sk, bili)
        # 保留现有数据中的战斗字段
        if name in existing_skills:
            ex = existing_skills[name]
            for field in ('counters', 'priority', 'hits', 'damage_reduction', 'damage_type', 'cooldown'):
                if field in ex:
                    record[field] = ex[field]
        merged_skills[name] = record

    output = {
        'rules': existing.get('rules', {}),
        'skills': merged_skills,
        'metadata': {
            'source': ['wiki.lcx.cab', 'wiki.biligame.com/rocom'],
            'total_skills': len(merged_skills),
            'with_bili_data': success,
        }
    }

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log(f"已写入 {OUTPUT_PATH}")
    log(f"总计 {len(merged_skills)} 个技能，{success} 个有效果描述")

    # 统计
    with_effects = sum(1 for s in merged_skills.values() if s.get('effects'))
    log(f"有解析到效果的技能: {with_effects}/{len(merged_skills)}")
    eff_types: dict = {}
    for s in merged_skills.values():
        for e in s.get('effects', []):
            t = e.get('type', '?')
            eff_types[t] = eff_types.get(t, 0) + 1
    if eff_types:
        log("\n效果类型分布:")
        for t, c in sorted(eff_types.items(), key=lambda x: -x[1]):
            log(f"  {t}: {c}个")


if __name__ == '__main__':
    # 仅在作为主程序运行时才重设 stdout 编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    with open('scrape_log_new.txt', 'w', encoding='utf-8') as lf:
        _log_file = lf
        main()
        _log_file = None
