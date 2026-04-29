"""快速测试解析逻辑"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from scrape_wiki import parse_effect_description, fetch_biligame_skill

test_cases = [
    ('抓挠',    '造成物伤，自己回复1能量。'),
    ('棘刺',    '敌方获得1层棘刺印记。'),
    ('摇篮曲',  '敌方获得全技能能耗+3，应对防御：额外造成打断，且敌方下回合获得眩晕。'),
    ('快速移动','自己获得速度+80，应对防御：改为速度+160。'),
    ('见招拆招','造成物伤，若上回合使用状态技能，本次技能威力+55。'),
    ('灼烧',   '对敌方造成物理伤害并附加2层灼烧。'),
    ('剧毒',   '对敌方施加5层中毒。'),
    ('休息回复','自己恢复30%生命。'),
]

for name, desc in test_cases:
    effects = parse_effect_description(desc)
    print(f'[{name}]')
    print(f'  描述: {desc}')
    if effects:
        for e in effects:
            print(f'  效果: {e}')
    else:
        print('  效果: (未解析到)')
    print()

print('--- 实际抓取测试（3个技能）---')
import time
for name in ['抓挠', '棘刺', '摇篮曲']:
    result = fetch_biligame_skill(name)
    print(f'[{name}]')
    if result:
        print(f'  描述: {result.get("raw_desc", "")}')
        for e in result.get('parsed_effects', []):
            print(f'  效果: {e}')
    else:
        print('  (抓取失败或页面不存在)')
    print()
    time.sleep(0.3)
