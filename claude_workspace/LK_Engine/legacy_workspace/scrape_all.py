import requests, json, time, sys, io, os, re
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0'}
PETS_FILE = 'Calculator/Data/pets.json'
pets = json.load(open(PETS_FILE, 'r', encoding='utf-8'))

# Identify leader forms (duplicate IDs)
from collections import Counter
id_counts = Counter(p['id'] for p in pets)
dup_ids = {k for k, v in id_counts.items() if v > 1}

# For duplicate IDs, the second one is likely the leader form
# Mark them
for pet_id in dup_ids:
    group = [p for p in pets if p['id'] == pet_id]
    if len(group) == 2:
        # First is base, second is leader
        group[1]['is_leader'] = True
        if not group[1].get('leader_name'):
            group[1]['leader_name'] = group[1]['name']

updated = 0
errors = 0
skipped = 0

for i, p in enumerate(pets):
    # Check what's missing
    has_stats = bool(p.get('stats', {}).get('生命'))
    has_traits = bool(p.get('traits') and len(p['traits']) > 0)
    has_evo = bool(p.get('evolution') and len(p['evolution']) > 0)
    
    if has_stats and has_traits and has_evo:
        skipped += 1
        continue
    
    name = p['name']
    url = 'https://wiki.biligame.com/rocom/' + requests.utils.quote(name)
    
    try:
        r = requests.get(url, headers=HDR, timeout=20)
        r.encoding = 'utf-8'
        
        if len(r.text) < 500:
            print(f"[{i+1}/{len(pets)}] {name}: empty page, skip")
            errors += 1
            time.sleep(2)
            continue
            
        soup = BeautifulSoup(r.text, 'html.parser')
        changed = False
        
        # 1. Traits
        if not has_traits:
            traits = []
            seen = set()
            for box in soup.find_all('div', class_='rocom_sprite_temp_characteristic_box'):
                title_el = box.find('p', class_='rocom_sprite_info_characteristic_title')
                text_el = box.find('p', class_=lambda c: c and 'rocom_sprite_info_characteristic_text' in c and 'font-fzltyjt' in c)
                if not text_el:
                    text_el = box.find('p', class_='rocom_sprite_info_characteristic_text')
                icon_div = box.find('div', class_='rocom_sprite_info_characteristic_content_icon')
                
                if not title_el:
                    continue
                tname = title_el.get_text(strip=True)
                if tname in seen or tname == '特性':
                    continue
                seen.add(tname)
                
                trait = {'name': tname}
                if text_el:
                    trait['desc'] = text_el.get_text(strip=True)
                if icon_div:
                    img = icon_div.find('img')
                    if img and img.get('src'):
                        trait['icon_url'] = img['src']
                traits.append(trait)
            
            if traits:
                p['traits'] = traits
                changed = True
        
        # 2. Stats (race values)
        if not has_stats:
            # Try multiple CSS patterns for stats
            stat_map = {}
            
            # Pattern 1: rocom_sprite_info_basevalue_box
            for item in soup.find_all('div', class_='rocom_sprite_info_basevalue_item'):
                label_el = item.find('p', class_=lambda c: c and 'label' in str(c).lower())
                val_el = item.find('p', class_=lambda c: c and 'value' in str(c).lower())
                if not label_el or not val_el:
                    children = item.find_all('p')
                    if len(children) >= 2:
                        label_el = children[0]
                        val_el = children[1]
                if label_el and val_el:
                    label = label_el.get_text(strip=True)
                    val_text = val_el.get_text(strip=True)
                    if val_text.isdigit():
                        stat_map[label] = int(val_text)
            
            # Pattern 2: look for stat table
            if not stat_map:
                for box in soup.find_all('div', class_=lambda c: c and 'basevalue' in str(c).lower()):
                    for p_tag in box.find_all('p'):
                        text = p_tag.get_text(strip=True)
                        # Look for "生命 123" pattern
                        for sn in ['生命','物攻','魔攻','物防','魔防','速度']:
                            if sn in text:
                                nums = re.findall(r'\d+', text)
                                if nums:
                                    stat_map[sn] = int(nums[0])
            
            if stat_map and '生命' in stat_map:
                p['stats'] = stat_map
                p['stats_total'] = sum(stat_map.values())
                changed = True
        
        # 3. Evolution chain
        if not has_evo:
            evo_chain = []
            evo_div = soup.find('div', class_='rocom_sprite_evolution')
            if not evo_div:
                evo_div = soup.find('div', class_=lambda c: c and 'evolution' in str(c).lower())
            
            if evo_div:
                for evo_item in evo_div.find_all(['div', 'a'], recursive=True):
                    img = evo_item.find('img')
                    if img:
                        evo_name = img.get('alt', '') or img.get('title', '')
                        if evo_name and evo_name not in [e['name'] for e in evo_chain]:
                            evo_entry = {'name': evo_name}
                            # Try to find level text nearby
                            level_el = evo_item.find(string=re.compile(r'Lv\.|级|等级|\d+级'))
                            if level_el:
                                level_nums = re.findall(r'\d+', str(level_el))
                                if level_nums:
                                    evo_entry['level'] = level_nums[0]
                            evo_chain.append(evo_entry)
            
            if evo_chain:
                p['evolution'] = evo_chain
                changed = True
        
        status_parts = []
        if not has_traits and p.get('traits'):
            status_parts.append(f"traits:{len(p['traits'])}")
        if not has_stats and p.get('stats', {}).get('生命'):
            status_parts.append(f"stats:ok")
        if not has_evo and p.get('evolution'):
            status_parts.append(f"evo:{len(p['evolution'])}")
        
        if changed:
            updated += 1
            print(f"[{i+1}/{len(pets)}] {name}: {', '.join(status_parts)}")
        else:
            print(f"[{i+1}/{len(pets)}] {name}: no new data")
            
    except Exception as e:
        errors += 1
        print(f"[{i+1}/{len(pets)}] {name}: ERROR {e}")
    
    time.sleep(0.8)
    
    # Save every 30 pets
    if (i + 1) % 30 == 0:
        json.dump(pets, open(PETS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f"--- Saved at {i+1} ({updated} updated, {errors} errors, {skipped} skipped) ---")

# Final save
json.dump(pets, open(PETS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nDone! {updated} updated, {errors} errors, {skipped} skipped out of {len(pets)}")
