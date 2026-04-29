import requests, json, time, sys, io, os
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
pets = json.load(open('Calculator/Data/pets.json', 'r', encoding='utf-8'))

updated = 0
errors = 0

for i, p in enumerate(pets):
    # Skip if already has traits
    if p.get('traits') and len(p['traits']) > 0:
        continue
    
    url = 'https://wiki.biligame.com/rocom/' + requests.utils.quote(p['name'])
    try:
        r = requests.get(url, headers=HDR, timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Traits
        traits = []
        seen = set()
        for box in soup.find_all('div', class_='rocom_sprite_temp_characteristic_box'):
            title_el = box.find('p', class_='rocom_sprite_info_characteristic_title')
            text_el = box.find('p', class_='rocom_sprite_info_characteristic_text')
            icon_div = box.find('div', class_='rocom_sprite_info_characteristic_content_icon')
            
            if not title_el:
                continue
            name = title_el.get_text(strip=True)
            if name in seen:
                continue
            seen.add(name)
            
            trait = {'name': name}
            if text_el:
                trait['desc'] = text_el.get_text(strip=True)
            if icon_div:
                img = icon_div.find('img')
                if img and img.get('src'):
                    trait['icon_url'] = img['src']
            traits.append(trait)
        
        if traits:
            p['traits'] = traits
            updated += 1
            print(f"[{i+1}/{len(pets)}] {p['name']}: {len(traits)} traits")
        else:
            print(f"[{i+1}/{len(pets)}] {p['name']}: no traits found")
        
        # Also fill missing stats if needed
        if not p.get('stats', {}).get('生命'):
            stat_map = {}
            for row in soup.find_all('div', class_='rocom_sprite_info_stats_item'):
                label = row.find('div', class_='rocom_sprite_info_stats_item_label')
                val = row.find('div', class_='rocom_sprite_info_stats_item_value')
                if label and val:
                    stat_map[label.get_text(strip=True)] = int(val.get_text(strip=True))
            if stat_map:
                p['stats'] = stat_map
                total = sum(stat_map.values())
                p['stats_total'] = total
                print(f"  + stats: {stat_map}")
    
    except Exception as e:
        errors += 1
        print(f"[{i+1}/{len(pets)}] {p['name']}: ERROR {e}")
    
    time.sleep(0.8)
    
    # Save periodically every 20 pets
    if (i + 1) % 20 == 0:
        json.dump(pets, open('Calculator/Data/pets.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f"--- Saved ({updated} updated, {errors} errors) ---")

# Final save
json.dump(pets, open('Calculator/Data/pets.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nDone! {updated} updated, {errors} errors")
