import json, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

pets = json.load(open('Calculator/Data/pets.json', 'r', encoding='utf-8'))
pet_names = {p['name'] for p in pets}

fixed_evo = 0
fixed_names = 0

for p in pets:
    evo = p.get('evolution', [])
    if not evo:
        continue
    
    changed = False
    for e in evo:
        name = e.get('name', '')
        # Fix "页面 宠物 立绘 XXX 1.png" -> "XXX"
        m = re.match(r'页面\s*宠物\s*立绘\s*(.+?)\s*\d*\.png', name)
        if m:
            clean = m.group(1).strip()
            e['name'] = clean
            changed = True
            fixed_names += 1
    
    if changed:
        fixed_evo += 1

# Now build evolution chains from relationships
# For pets without evolution, try to infer from other pets in the same chain
name_to_pet = {}
for p in pets:
    name_to_pet[p['name']] = p

# Build chains: group pets that share evolution data
chains = {}  # chain_key -> [pet_names]
for p in pets:
    evo = p.get('evolution', [])
    if evo and len(evo) > 1:
        key = tuple(e['name'] for e in evo)
        if key not in chains:
            chains[key] = []
        chains[key].append(p['name'])

# For pets without evolution, check if they appear in any chain
no_evo_pets = [p for p in pets if not p.get('evolution') or len(p.get('evolution', [])) <= 1]
for p in no_evo_pets:
    for chain_key, members in chains.items():
        if p['name'] in chain_key:
            # Found! Copy the chain
            # Find an existing pet with this chain
            for member_name in members:
                member = name_to_pet.get(member_name)
                if member and member.get('evolution'):
                    p['evolution'] = [dict(e) for e in member['evolution']]
                    fixed_evo += 1
                    break
            break

print(f"Fixed {fixed_names} evolution names")
print(f"Fixed/added evolution for {fixed_evo} pets")

# Verify stage classification
from collections import Counter
stages = Counter()
for p in pets:
    evo = p.get('evolution', [])
    is_leader = p.get('is_leader')
    if is_leader:
        stages['leader'] += 1
        continue
    if not evo or len(evo) <= 1:
        stages['no_chain'] += 1
        continue
    evo_names = [e['name'] for e in evo]
    if p['name'] in evo_names:
        idx = evo_names.index(p['name'])
        if idx == 0:
            stages['stage1'] += 1
        elif idx == len(evo) - 1:
            stages['final'] += 1
        else:
            stages['stage2'] += 1
    else:
        stages['not_in_chain'] += 1

print(f"\nStage distribution: {dict(stages)}")
print(f"Missing stats: {sum(1 for p in pets if not p.get('stats',{}).get('生命'))}")
print(f"Missing traits: {sum(1 for p in pets if not p.get('traits'))}")

json.dump(pets, open('Calculator/Data/pets.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print("Saved!")
