import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

pets = json.load(open('Calculator/Data/pets.json', 'r', encoding='utf-8'))

# Check 024
for p in pets:
    if p['id'] == '024':
        print(f"=== {p['id']} {p['name']} ===")
        print(f"  stats: {p.get('stats')}")
        print(f"  traits: {p.get('traits')}")
        print(f"  evolution: {p.get('evolution')}")
        print(f"  height: {p.get('height')}, weight: {p.get('weight')}")
        print()

# Check evolution chain quality
print("\n=== Evolution chain samples ===")
for p in pets[:30]:
    evo = p.get('evolution', [])
    if evo:
        print(f"  {p['id']} {p['name']}: {[(e.get('name'), e.get('level','?')) for e in evo]}")

# Check stage classification
from collections import Counter
stages = Counter()
for p in pets:
    evo = p.get('evolution', [])
    is_leader = p.get('is_leader')
    if is_leader:
        stages['leader'] += 1
        continue
    if len(evo) <= 1:
        stages['final (no chain)'] += 1
        continue
    idx = -1
    for i, e in enumerate(evo):
        if e.get('name') == p['name']:
            idx = i
            break
    if idx < 0:
        stages['final (not in chain)'] += 1
    elif idx == 0:
        stages['stage1'] += 1
    elif idx == len(evo) - 1:
        stages['final'] += 1
    else:
        stages['stage2'] += 1

print(f"\n=== Stage distribution ===")
for k, v in sorted(stages.items()):
    print(f"  {k}: {v}")

# Count missing
no_stats = [p for p in pets if not p.get('stats', {}).get('生命')]
no_traits = [p for p in pets if not p.get('traits')]
no_evo = [p for p in pets if not p.get('evolution') or len(p.get('evolution', [])) == 0]
print(f"\nMissing stats: {len(no_stats)}")
print(f"Missing traits: {len(no_traits)}")
print(f"No evolution chain: {len(no_evo)}")
print(f"Missing stats names: {[p['id']+' '+p['name'] for p in no_stats[:20]]}")
