import json, re

f = 'Calculator/Data/battle_data.json'
data = json.load(open(f, 'r', encoding='utf-8'))
skills = data['skills']

# Also load skills.json for desc
sdb = json.load(open('Calculator/Data/skills.json', 'r', encoding='utf-8'))

fixed = 0
for name, sk in skills.items():
    desc = sdb.get(name, {}).get('desc', '') or ''
    counters = sk.get('counters', [])
    existing_types = [c.get('type', '') for c in counters]
    
    # Check desc for counter keywords
    for kw, ctype in [('应对攻击', '应对攻击'), ('应对防御', '应对防御'), ('应对状态', '应对状态')]:
        if kw in desc and ctype not in existing_types:
            # Extract the text after the counter keyword for desc
            idx = desc.find(kw)
            after = desc[idx+len(kw):]
            # Clean up: remove leading punctuation
            after = re.sub(r'^[：:，,\s]+', '', after)
            # Take until next period or end
            m = re.match(r'([^。]+)', after)
            cdesc = m.group(1).strip() if m else ''
            
            counters.append({
                'type': ctype,
                'desc': cdesc,
                'effects': []
            })
            fixed += 1
            print(f'Fixed {name}: added {ctype} (desc: {cdesc})')
    
    sk['counters'] = counters

json.dump(data, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'\nTotal fixed: {fixed} counters added')
