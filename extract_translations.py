from pathlib import Path
import json
import re
import requests
import yaml
import os

API = os.environ['TRANSIFEX_TOKEN']
HEB=re.compile('[א-ת]')

def themes():
    for fn in Path('.').glob('*.he.json'):
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

def allkeys():
    for _, project, theme in themes():
        yield from keys(theme, project + '___')

def hebrew(x):
    return HEB.match(x) is not None

if __name__ == '__main__':
    content = ''
    content += 'he:\n'
    for k, v in allkeys():
        if hebrew(v) and '__filters__' not in k:
            content += f'  {k}: {v}\n'

    s = requests.Session()
    s.auth = ('api', API)

    resp = s.get('https://www.transifex.com/api/2/project/budgetkey/resource/themes/')

    if resp.status_code == requests.codes.ok:
        print('Update file:')
        data = dict(
            content=content,
        )

        resp = s.put(
            'https://www.transifex.com/api/2/project/budgetkey/resource/themes/',
            json=data
        ) 

    else:
        print('New file:')
        data = dict(
            slug='themes',
            name='Common Theme Translation',
            accept_translations=True,
            i18n_type='YAML_GENERIC',
            content=content,
        )

        resp = s.post(
            'https://www.transifex.com/api/2/project/budgetkey/resources/',
            json=data
        ) 
    print(resp.status_code)

    for lang in ('en', ):
        translations = s.get(
            f'https://www.transifex.com/api/2/project/budgetkey/resource/themes/translation/{lang}/',
            json=data
        ).json()
        translations = yaml.load(translations['content'])['he']

        for fn, project, theme in themes():
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
            

