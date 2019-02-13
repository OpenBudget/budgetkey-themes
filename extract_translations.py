from pathlib import Path
import json
import re
import requests
import yaml
import os

API = os.environ['TRANSIFEX_TOKEN']
HEB=re.compile('[א-ת]')

KINDS = [
    # File prefix, Transifex resource, Transifex Description
    ('theme', 'themes', 'Common Theme Translation'),
    ('main_page.translations', 'main_page', 'Main Page Translations'),
]

def sources(kind):
    for fn in Path('.').glob('{}*.he.json'.format(kind[0])):
        project = str(fn).split('.')[1]
        yield fn, project, json.load(open(fn))

def keys(v, root=''):
    if isinstance(v, list):
        for i, vv in enumerate(v):
            yield from keys(vv, root=f'{root[:-3]}[{i}]___')
    elif isinstance(v, dict):
        for k, v in v.items():
            yield from keys(v, root=f'{root}{k}___')
    elif isinstance(v, str):
        yield root[:-3], v
    else:
        pass

def replace_with(v, replacements, project):
    for k, _ in keys(v, project + '___'):
        if k in replacements and replacements[k]:
            yield k, replacements[k]

def allkeys(kind):
    for _, project, theme in sources(kind):
        yield from keys(theme, project + '___')

def hebrew(x):
    return HEB.match(x) is not None

def handle_kind(kind):
    content = ''
    content += 'he:\n'
    for k, v in allkeys(kind):
        if hebrew(v) and '__filters__' not in k:
            content += f'  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}\n'

    s = requests.Session()
    s.auth = ('api', API)

    resp = s.get(f'https://www.transifex.com/api/2/project/budgetkey/resource/{kind[1]}/')

    if resp.status_code == requests.codes.ok:
        print('Update file:')
        data = dict(
            content=content,
        )

        resp = s.put(
            f'https://www.transifex.com/api/2/project/budgetkey/resource/{kind[1]}/content/',
            json=data
        )
        print(resp.text)

    else:
        print('New file:')
        data = dict(
            slug=kind[1],
            name=kind[2],
            accept_translations=True,
            i18n_type='YAML_GENERIC',
            content=content,
        )

        resp = s.post(
            'https://www.transifex.com/api/2/project/budgetkey/resources/',
            json=data
        ) 
    print(resp.status_code, resp.text)

    for lang in ('en', 'ar', 'am', 'ru'):
        print(lang, kind)
        translations = s.get(
            f'https://www.transifex.com/api/2/project/budgetkey/resource/{kind[1]}/translation/{lang}/',
            json=data
        ).json()
        translations = yaml.load(translations['content'])['he']

        for fn, project, theme in sources(kind):
            fn = str(fn).replace('.he.', f'.{lang}.')
            for k, v in list(replace_with(theme, translations, project)):
                parts = k.split('___')[1:]
                ptr = theme
                while len(parts) > 1:
                    part = parts.pop(0)
                    if '[' in part:
                        k, idx = part[:-1].split('[')
                        ptr = ptr[k][int(idx)]
                    else:
                        ptr = ptr[part]
                ptr[parts[0]] = v
            json.dump(theme, open(fn, 'w'), indent=2, sort_keys=True, ensure_ascii=False)
            
if __name__ == '__main__':
    for kind in KINDS:
        handle_kind(kind)
