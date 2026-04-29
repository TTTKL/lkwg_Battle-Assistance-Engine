import os

base = os.path.join(os.path.dirname(__file__), 'Calculator', 'Data')

files = [
    ('pets.json', 'pets.js', '_PETS_RAW'),
    ('common.json', 'common.js', '_COMMON_RAW'),
    ('skills.json', 'skills.js', '_SKILLS_RAW'),
    ('battle_data.json', 'battle_data.js', '_BATTLE_RAW'),
]

for src, dst, var in files:
    src_path = os.path.join(base, src)
    dst_path = os.path.join(base, dst)
    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(dst_path, 'w', encoding='utf-8') as f:
        f.write('var ' + var + '=' + content + ';\n')
    print(f'Generated {dst} ({os.path.getsize(dst_path)} bytes)')

print('Done!')
