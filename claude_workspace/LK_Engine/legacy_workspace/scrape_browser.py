import json, sys, io, re, time
from playwright.sync_api import sync_playwright
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PETS_FILE = 'Calculator/Data/pets.json'
pets = json.load(open(PETS_FILE, 'r', encoding='utf-8'))

STAT_NAMES = ['生命','物攻','魔攻','物防','魔防','速度']

def scrape_pet(page, pet_name):
    """Scrape a single pet's data using browser"""
    url = 'https://wiki.biligame.com/rocom/' + pet_name
    try:
        page.goto(url, wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(2000)  # extra wait for JS
    except:
        return {}
    
    info = {}
    
    # 1. Stats (种族值)
    try:
        stats = {}
        # Look for stat items with value
        stat_items = page.query_selector_all('.rocom_sprite_info_basevalue_item')
        if not stat_items:
            stat_items = page.query_selector_all('[class*=basevalue] [class*=item]')
        for item in stat_items:
            text = item.inner_text().strip()
            for sn in STAT_NAMES:
                if sn in text:
                    nums = re.findall(r'\d+', text)
                    if nums:
                        stats[sn] = int(nums[-1])
        
        # Fallback: look for stat bars/labels
        if not stats:
            all_text = page.inner_text('body')
            for sn in STAT_NAMES:
                pattern = sn + r'\s*[：:]*\s*(\d+)'
                m = re.search(pattern, all_text)
                if m:
                    stats[sn] = int(m.group(1))
        
        if stats and '生命' in stats:
            info['stats'] = stats
            info['stats_total'] = sum(stats.values())
    except Exception as e:
        print(f"    Stats error: {e}")
    
    # 2. Traits
    try:
        traits = []
        seen = set()
        boxes = page.query_selector_all('.rocom_sprite_temp_characteristic_box')
        for box in boxes:
            title_el = box.query_selector('.rocom_sprite_info_characteristic_title')
            text_el = box.query_selector('p[class*=rocom_sprite_info_characteristic_text][class*=font-fzltyjt]')
            if not text_el:
                text_el = box.query_selector('.rocom_sprite_info_characteristic_text')
            icon_el = box.query_selector('.rocom_sprite_info_characteristic_content_icon img')
            
            if not title_el:
                continue
            name = title_el.inner_text().strip()
            if name in seen or name == '特性':
                continue
            seen.add(name)
            
            trait = {'name': name}
            if text_el:
                trait['desc'] = text_el.inner_text().strip()
            if icon_el:
                src = icon_el.get_attribute('src')
                if src:
                    trait['icon_url'] = src
            traits.append(trait)
        
        if traits:
            info['traits'] = traits
    except Exception as e:
        print(f"    Traits error: {e}")
    
    # 3. Evolution chain
    try:
        evo = []
        evo_div = page.query_selector('.rocom_sprite_evolution')
        if evo_div:
            # Get all evolution items/stages
            items = evo_div.query_selector_all('.rocom_sprite_evolution_item')
            if not items:
                items = evo_div.query_selector_all('[class*=evolution_item]')
            
            for item in items:
                # Name from text or link
                name_el = item.query_selector('.rocom_sprite_evolution_item_name')
                if not name_el:
                    name_el = item.query_selector('a')
                if not name_el:
                    name_el = item.query_selector('[class*=name]')
                
                evo_name = ''
                if name_el:
                    evo_name = name_el.inner_text().strip()
                
                if not evo_name:
                    # Try img alt
                    img = item.query_selector('img')
                    if img:
                        evo_name = img.get_attribute('alt') or img.get_attribute('title') or ''
                        # Clean "页面 宠物 立绘 XXX 1.png" format
                        m = re.match(r'页面\s*宠物\s*立绘\s*(.+?)\s*\d*\.png', evo_name)
                        if m:
                            evo_name = m.group(1).strip()
                
                if not evo_name or evo_name in [e.get('name') for e in evo]:
                    continue
                
                entry = {'name': evo_name}
                
                # Level
                level_el = item.query_selector('.rocom_sprite_evolution_item_level')
                if not level_el:
                    level_el = item.query_selector('[class*=level]')
                if level_el:
                    level_text = level_el.inner_text().strip()
                    nums = re.findall(r'\d+', level_text)
                    if nums:
                        entry['level'] = nums[0]
                
                evo.append(entry)
            
            # If items approach didn't work, try a simpler approach
            if not evo:
                all_names = []
                for link in evo_div.query_selector_all('a'):
                    title = link.get_attribute('title') or link.inner_text().strip()
                    if title and title not in all_names and len(title) < 20:
                        all_names.append(title)
                evo = [{'name': n} for n in all_names]
        
        if evo:
            info['evolution'] = evo
    except Exception as e:
        print(f"    Evo error: {e}")
    
    # 4. Height/Weight
    try:
        body_text = page.inner_text('body')
        hm = re.search(r'身高[：:\s]*([0-9.]+)\s*M', body_text)
        wm = re.search(r'体重[：:\s]*([0-9.]+)\s*KG', body_text, re.I)
        if hm: info['height'] = hm.group(1) + 'M'
        if wm: info['weight'] = wm.group(1) + 'KG'
    except:
        pass
    
    return info

# Find pets needing data
needs_work = []
for p in pets:
    need_stats = not p.get('stats', {}).get('生命')
    need_traits = not p.get('traits')
    need_evo = not p.get('evolution') or len(p.get('evolution', [])) == 0
    # Also fix bad evolution names
    bad_evo = False
    for e in p.get('evolution', []):
        if '页面' in e.get('name', '') or '.png' in e.get('name', ''):
            bad_evo = True
            break
    need_evo_level = False
    for e in p.get('evolution', []):
        if e.get('level', '?') == '?':
            need_evo_level = True
            break
    
    if need_stats or need_traits or need_evo or bad_evo or need_evo_level:
        needs_work.append((p, need_stats, need_traits, need_evo or bad_evo or need_evo_level))

print(f"Total pets needing work: {len(needs_work)}")
print(f"  Need stats: {sum(1 for _,s,_,_ in needs_work if s)}")
print(f"  Need traits: {sum(1 for _,_,t,_ in needs_work if t)}")
print(f"  Need evo fix: {sum(1 for _,_,_,e in needs_work if e)}")

updated = 0
errors = 0

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    page = ctx.new_page()
    
    for i, (p, need_s, need_t, need_e) in enumerate(needs_work):
        name = p['name']
        print(f"[{i+1}/{len(needs_work)}] {p['id']} {name}...", end=' ')
        
        data = scrape_pet(page, name)
        
        changed = False
        parts = []
        if need_s and data.get('stats'):
            p['stats'] = data['stats']
            p['stats_total'] = data['stats_total']
            parts.append('stats')
            changed = True
        if need_t and data.get('traits'):
            p['traits'] = data['traits']
            parts.append(f"traits:{len(data['traits'])}")
            changed = True
        if need_e and data.get('evolution'):
            p['evolution'] = data['evolution']
            parts.append(f"evo:{len(data['evolution'])}")
            changed = True
        if data.get('height') and not p.get('height'):
            p['height'] = data['height']
        if data.get('weight') and not p.get('weight'):
            p['weight'] = data['weight']
        
        if changed:
            updated += 1
            print(', '.join(parts))
        else:
            errors += 1
            print('no data')
        
        # Save every 20
        if (i + 1) % 20 == 0:
            json.dump(pets, open(PETS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            print(f"--- Saved ({updated} updated, {errors} no data) ---")
        
        time.sleep(1.5)
    
    browser.close()

json.dump(pets, open(PETS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"\nDone! {updated} updated, {errors} no data")
