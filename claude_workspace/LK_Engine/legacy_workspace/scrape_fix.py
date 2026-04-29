import requests, json, time, sys, io, re
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdout.reconfigure(line_buffering=True)

HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0'}
PETS_FILE = 'Calculator/Data/pets.json'
pets = json.load(open(PETS_FILE, 'r', encoding='utf-8'))
STAT_NAMES = ['生命','物攻','魔攻','物防','魔防','速度']

def scrape_pet(name):
    url = 'https://wiki.biligame.com/rocom/' + requests.utils.quote(name)
    r = requests.get(url, headers=HDR, timeout=20)
    r.encoding = 'utf-8'
    if len(r.text) < 1000:
        return {}
    soup = BeautifulSoup(r.text, 'html.parser')
    info = {}
    
    # Stats
    stats = {}
    for item in soup.find_all('div', class_='rocom_sprite_info_basevalue_item'):
        texts = item.get_text(strip=True)
        for sn in STAT_NAMES:
            if sn in texts:
                nums = re.findall(r'\d+', texts)
                if nums:
                    stats[sn] = int(nums[-1])
    if not stats:
        # Fallback: search all text
        for div in soup.find_all(['div','p','span'], class_=lambda c: c and 'basevalue' in str(c)):
            for sn in STAT_NAMES:
                text = div.get_text()
                if sn in text:
                    nums = re.findall(r'\d+', text.split(sn)[-1][:20])
                    if nums:
                        stats[sn] = int(nums[0])
    if stats and '生命' in stats:
        info['stats'] = stats
        info['stats_total'] = sum(stats.values())
    
    # Traits
    traits = []
    seen = set()
    for box in soup.find_all('div', class_='rocom_sprite_temp_characteristic_box'):
        title_el = box.find('p', class_='rocom_sprite_info_characteristic_title')
        text_el = box.find('p', class_=lambda c: c and 'rocom_sprite_info_characteristic_text' in str(c) and 'font-fzltyjt' in str(c))
        if not text_el:
            text_el = box.find('p', class_=lambda c: c and 'characteristic_text' in str(c))
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
        info['traits'] = traits
    
    # Evolution
    evo = []
    evo_div = soup.find('div', class_='rocom_sprite_evolution')
    if evo_div:
        for item in evo_div.find_all('div', class_=lambda c: c and 'evolution_item' in str(c)):
            name_el = item.find('p', class_=lambda c: c and 'name' in str(c))
            evo_name = ''
            if name_el:
                evo_name = name_el.get_text(strip=True)
            if not evo_name:
                a = item.find('a')
                if a: evo_name = a.get('title', '') or a.get_text(strip=True)
            if not evo_name:
                img = item.find('img')
                if img:
                    alt = img.get('alt', '')
                    m = re.match(r'页面\s*宠物\s*立绘\s*(.+?)\s*\d*\.png', alt)
                    evo_name = m.group(1).strip() if m else alt
            if evo_name and evo_name not in [e['name'] for e in evo]:
                entry = {'name': evo_name}
                level_el = item.find('p', class_=lambda c: c and 'level' in str(c))
                if level_el:
                    nums = re.findall(r'\d+', level_el.get_text())
                    if nums: entry['level'] = nums[0]
                evo.append(entry)
    if evo and len(evo) > 1:
        info['evolution'] = evo
    
    # Height/weight
    for div in soup.find_all(['div','p','span']):
        text = div.get_text()
        if '身高' in text:
            hm = re.search(r'(\d+\.?\d*)\s*M', text, re.I)
            if hm and 'height' not in info: info['height'] = hm.group(1) + 'M'
        if '体重' in text:
            wm = re.search(r'(\d+\.?\d*)\s*KG', text, re.I)
            if wm and 'weight' not in info: info['weight'] = wm.group(1) + 'KG'
    
    return info

# Find pets needing work
needs = []
for p in pets:
    need_s = not p.get('stats', {}).get('生命')
    need_t = not p.get('traits')
    bad_evo = any('页面' in e.get('name','') or '.png' in e.get('name','') for e in p.get('evolution',[]))
    need_lv = any(e.get('level','?') == '?' for e in p.get('evolution',[]))
    if need_s or need_t or bad_evo or need_lv:
        needs.append((p, need_s, need_t, bad_evo or need_lv))

print(f"Need work: {len(needs)}", flush=True)
updated = 0
errors = 0

for i, (p, ns, nt, ne) in enumerate(needs):
    name = p['name']
    try:
        data = scrape_pet(name)
        parts = []
        if ns and data.get('stats'):
            p['stats'] = data['stats']; p['stats_total'] = data['stats_total']; parts.append('stats')
        if nt and data.get('traits'):
            p['traits'] = data['traits']; parts.append(f"traits:{len(data['traits'])}")
        if ne and data.get('evolution'):
            p['evolution'] = data['evolution']; parts.append(f"evo:{len(data['evolution'])}")
        if data.get('height') and not p.get('height'): p['height'] = data['height']
        if data.get('weight') and not p.get('weight'): p['weight'] = data['weight']
        if parts:
            updated += 1
            print(f"[{i+1}/{len(needs)}] {p['id']} {name}: {', '.join(parts)}", flush=True)
        else:
            errors += 1
            print(f"[{i+1}/{len(needs)}] {p['id']} {name}: no data", flush=True)
    except Exception as e:
        errors += 1
        print(f"[{i+1}/{len(needs)}] {p['id']} {name}: ERR {e}", flush=True)
    
    time.sleep(1.2)
    if (i+1) % 25 == 0:
        json.dump(pets, open(PETS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f"--- Saved ({updated}/{errors}) ---", flush=True)

json.dump(pets, open(PETS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nDone! {updated} updated, {errors} no data", flush=True)
