import requests, json, time, sys, io, re
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0'}
PETS_FILE = 'Calculator/Data/pets.json'
pets = json.load(open(PETS_FILE, 'r', encoding='utf-8'))

# Only process pets missing traits or stats
missing = [p for p in pets if not p.get('traits') or not p.get('stats',{}).get('生命')]
print(f"Missing data: {len(missing)} pets")

updated = 0
errors = 0

for i, p in enumerate(missing):
    name = p['name']
    url = 'https://wiki.biligame.com/rocom/' + requests.utils.quote(name)
    
    try:
        r = requests.get(url, headers=HDR, timeout=20)
        r.encoding = 'utf-8'
        
        if len(r.text) < 500:
            errors += 1
            time.sleep(2)
            continue
            
        soup = BeautifulSoup(r.text, 'html.parser')
        changed = False
        
        # Traits
        if not p.get('traits'):
            traits = []
            seen = set()
            for box in soup.find_all('div', class_='rocom_sprite_temp_characteristic_box'):
                title_el = box.find('p', class_='rocom_sprite_info_characteristic_title')
                text_el = box.find('p', class_=lambda c: c and 'rocom_sprite_info_characteristic_text' in c and 'font-fzltyjt' in c)
                if not text_el:
                    text_el = box.find('p', class_='rocom_sprite_info_characteristic_text')
                icon_div = box.find('div', class_='rocom_sprite_info_characteristic_content_icon')
                
                if not title_el: continue
                tname = title_el.get_text(strip=True)
                if tname in seen or tname == '特性': continue
                seen.add(tname)
                
                trait = {'name': tname}
                if text_el: trait['desc'] = text_el.get_text(strip=True)
                if icon_div:
                    img = icon_div.find('img')
                    if img and img.get('src'): trait['icon_url'] = img['src']
                traits.append(trait)
            
            if traits:
                p['traits'] = traits
                changed = True
        
        # Stats
        if not p.get('stats',{}).get('生命'):
            stat_map = {}
            for item in soup.find_all('div', class_=lambda c: c and 'basevalue' in str(c)):
                for pp in item.find_all('p'):
                    text = pp.get_text(strip=True)
                    for sn in ['生命','物攻','魔攻','物防','魔防','速度']:
                        if sn in text:
                            nums = re.findall(r'\d+', text)
                            if nums: stat_map[sn] = int(nums[-1])
            if stat_map and '生命' in stat_map:
                p['stats'] = stat_map
                p['stats_total'] = sum(stat_map.values())
                changed = True
        
        if changed:
            updated += 1
            t = 'traits' if p.get('traits') else ''
            s = 'stats' if p.get('stats',{}).get('生命') else ''
            print(f"[{i+1}/{len(missing)}] {name}: {t} {s}")
        else:
            print(f"[{i+1}/{len(missing)}] {name}: still missing")
            
    except Exception as e:
        errors += 1
        print(f"[{i+1}/{len(missing)}] {name}: ERROR {e}")
    
    time.sleep(1.0)
    
    if (i + 1) % 30 == 0:
        json.dump(pets, open(PETS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

json.dump(pets, open(PETS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nDone! {updated} updated, {errors} errors")
