import requests, sys, io, os, json, re, time
from bs4 import BeautifulSoup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HDR = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
PETS = json.load(open('Calculator/Data/pets.json','r',encoding='utf-8'))

def scrape_extra(pet):
    url = 'https://wiki.biligame.com/rocom/' + requests.utils.quote(pet['name'])
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HDR, timeout=20)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            content = soup.find('div', class_='mw-parser-output')
            if content: break
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            print(f"  ERROR: {e}")
            return {}
    if not content: return {}
    
    info = {}
    
    # 1. Traits (特性) - search entire page for characteristic
    traits = []
    for char_box in soup.find_all('div', class_='rocom_sprite_temp_characteristic_box'):
        title_el = char_box.find('div', class_='rocom_sprite_info_characteristic_title')
        content_el = char_box.find('div', class_='rocom_sprite_info_characteristic_content')
        icon_el = char_box.find('div', class_='rocom_sprite_info_characteristic_content_icon')
        trait = {}
        if title_el:
            trait['name'] = title_el.get_text(strip=True)
        if content_el:
            texts = [t for t in content_el.stripped_strings if t != trait.get('name','')]
            trait['desc'] = ''.join(texts)
        if icon_el:
            img = icon_el.find('img')
            if img:
                src = img.get('data-src') or img.get('src') or ''
                if src.startswith('//'): src = 'https:' + src
                trait['icon_url'] = src
        if trait.get('name'):
            traits.append(trait)
    # Deduplicate (page has 2 copies due to visible-lg/sm)
    seen = set()
    unique_traits = []
    for t in traits:
        if t['name'] not in seen:
            seen.add(t['name'])
            unique_traits.append(t)
    if unique_traits: info['traits'] = unique_traits
    
    # 2. Evolution chain (进化链)
    evo_div = content.find('div', class_='rocom_sprite_evolution')
    if not evo_div:
        # Try finding by text
        for div in content.find_all('div'):
            if '进化链' in div.get_text()[:10]:
                evo_div = div
                break
    
    if evo_div:
        evo_chain = []
        # Look for evolution items with level info
        evo_items = evo_div.find_all('div', class_='rocom_sprite_evolution_item')
        if not evo_items:
            # Try broader search - look for images with "立绘" in alt
            for img in evo_div.find_all('img'):
                alt = img.get('alt','')
                if '立绘' in alt:
                    name_match = re.search(r'立绘\s*(.+?)(?:\s|\.)', alt)
                    if name_match:
                        evo_chain.append({'name': name_match.group(1).strip()})
        else:
            for item in evo_items:
                evo_entry = {}
                img = item.find('img')
                if img:
                    alt = img.get('alt','')
                    name_match = re.search(r'立绘\s*(.+?)(?:\s|\.)', alt)
                    if name_match:
                        evo_entry['name'] = name_match.group(1).strip()
                # Look for level text
                for span in item.find_all(['span','div']):
                    text = span.get_text(strip=True)
                    if re.match(r'^\d+$', text):
                        evo_entry['level'] = int(text)
                if evo_entry.get('name'):
                    evo_chain.append(evo_entry)
        
        if not evo_chain:
            # Fallback: parse all images and level numbers from evo section
            tokens = list(evo_div.stripped_strings)
            imgs = evo_div.find_all('img')
            for img in imgs:
                alt = img.get('alt','')
                if '立绘' in alt:
                    nm = re.search(r'立绘\s*(.+?)(?:\s|\.)', alt)
                    if nm:
                        entry = {'name': nm.group(1).strip()}
                        evo_chain.append(entry)
            # Try to find level numbers
            for i, tok in enumerate(tokens):
                if re.match(r'^\d+$', tok) and int(tok) < 100:
                    lv = int(tok)
                    # Assign to the next evo entry that doesn't have a level
                    for e in evo_chain:
                        if 'level' not in e and e != evo_chain[0]:
                            e['level'] = lv
                            break
        
        if evo_chain: info['evolution'] = evo_chain
    
    # 3. Multiple images (精灵/异色/果实/精灵蛋)
    images = {}
    gl = content.find('div', class_='rocom_sprite_grament_list')
    if gl:
        buttons = gl.find_all('li', class_='rocom_sprite_grament_botton')
        labels = ['normal','shiny','fruit','egg']
        # The images are in grament_img area, controlled by JS tabs
        # We need to find all pet images from the grament area
        gimg = content.find('div', class_='rocom_sprite_grament_img')
        if gimg:
            all_imgs = gimg.find_all('img')
            for img in all_imgs:
                alt = img.get('alt','')
                src = img.get('data-src') or img.get('src') or ''
                if src.startswith('//'): src = 'https:' + src
                if '立绘' in alt:
                    if '异色' in alt:
                        images['shiny'] = src
                    elif '果实' in alt or '坐骑' in alt:
                        images['fruit'] = src
                    elif '蛋' in alt:
                        images['egg'] = src
                    else:
                        images['normal'] = src
    
    # Also check for images in tabber panels
    for tab in content.find_all('div', class_='tabbertab'):
        title = tab.get('title','')
        for img in tab.find_all('img'):
            alt = img.get('alt','')
            src = img.get('data-src') or img.get('src') or ''
            if src.startswith('//'): src = 'https:' + src
            if '立绘' in alt and src:
                if '异色' in alt:
                    images['shiny'] = src
                elif '果实' in alt:
                    images['fruit'] = src
                elif '蛋' in alt or '精灵蛋' in alt:
                    images['egg'] = src
    
    if images: info['images'] = images
    
    # 4. Trait icon download
    pet_dir = 'Calculator/Image/Pet/' + pet['name']
    os.makedirs(pet_dir, exist_ok=True)
    
    for trait in info.get('traits', []):
        if trait.get('icon_url'):
            fname = 'trait_' + trait['name'] + '.png'
            fpath = os.path.join(pet_dir, fname)
            if not os.path.exists(fpath):
                try:
                    d = requests.get(trait['icon_url'], headers=HDR, timeout=10).content
                    if len(d) > 500:
                        with open(fpath, 'wb') as f: f.write(d)
                        trait['local_icon'] = pet_dir.replace('Calculator/','') + '/' + fname
                except: pass
            else:
                trait['local_icon'] = pet_dir.replace('Calculator/','') + '/' + fname
    
    # 5. Download variant images
    for key, url in info.get('images', {}).items():
        if not url or 'Special:' in url: continue
        fname = key + '.png'
        fpath = os.path.join(pet_dir, fname)
        if not os.path.exists(fpath):
            try:
                d = requests.get(url, headers=HDR, timeout=10).content
                if len(d) > 5000:
                    with open(fpath, 'wb') as f: f.write(d)
                    info['images'][key] = pet_dir.replace('Calculator/','') + '/' + fname
                else:
                    info['images'][key] = None
            except:
                info['images'][key] = None
        else:
            info['images'][key] = pet_dir.replace('Calculator/','') + '/' + fname
    
    return info

# Process
total = len(PETS)
updated = 0
for idx, pet in enumerate(PETS):
    print(f"[{idx+1}/{total}] {pet['name']}...", end=' ', flush=True)
    extra = scrape_extra(pet)
    if extra:
        for k, v in extra.items():
            pet[k] = v
        t = extra.get('traits',[])
        e = extra.get('evolution',[])
        im = extra.get('images',{})
        print(f"traits={len(t)} evo={len(e)} imgs={list(im.keys())}")
        updated += 1
    else:
        print("SKIP")
    if idx % 10 == 9:
        time.sleep(0.5)
    else:
        time.sleep(0.2)

json.dump(PETS, open('Calculator/Data/pets.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"\nDone! Updated {updated}/{total}")

# Verify
p = [x for x in PETS if x['name']=='喵喵']
if p:
    d=p[0]
    print(f"喵喵: traits={d.get('traits')}, evo={d.get('evolution')}, imgs={d.get('images')}")
