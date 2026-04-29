import json

f = 'Calculator/Data/battle_data.json'
data = json.load(open(f, 'r', encoding='utf-8'))
skills = data['skills']
sdb = json.load(open('Calculator/Data/skills.json', 'r', encoding='utf-8'))

fixed = 0
for name, sk in skills.items():
    cat = sk.get('category', '') or sdb.get(name, {}).get('category', '')
    if cat != '防御':
        continue
    
    # Check if damage_reduction > 0 (actual defense skill, not attack skill in defense category)
    dmg_r = sk.get('damage_reduction', 0)
    
    counters = sk.get('counters', [])
    has_counter_atk = any(c.get('type') == '应对攻击' for c in counters)
    
    if not has_counter_atk and dmg_r > 0:
        # All defense skills with damage_reduction should have 应对攻击
        # Find existing counter desc from skill desc
        desc = sdb.get(name, {}).get('desc', '') or ''
        cdesc = ''
        if '应对攻击' in desc:
            idx = desc.find('应对攻击')
            after = desc[idx+4:]
            import re
            after = re.sub(r'^[：:，,\s]+', '', after)
            m = re.match(r'([^。]+)', after)
            cdesc = m.group(1).strip() if m else ''
        
        counters.append({
            'type': '应对攻击',
            'desc': cdesc,
            'effects': []
        })
        sk['counters'] = counters
        fixed += 1
        print(f'Fixed: {name} (reduction={dmg_r}, added 应对攻击, desc="{cdesc}")')
    elif not has_counter_atk and dmg_r == 0:
        print(f'Skip: {name} (no damage_reduction, likely attack-type in defense category)')

json.dump(data, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# Also regenerate battle_data.js
raw = open(f, 'r', encoding='utf-8').read()
open('Calculator/Data/battle_data.js', 'w', encoding='utf-8').write('var _BATTLE_RAW=' + raw + ';\n')

print(f'\nTotal fixed: {fixed}')
print('battle_data.js regenerated')
