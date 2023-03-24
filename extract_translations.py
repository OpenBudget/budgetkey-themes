from pathlib import Path
import json
import re
import yaml
import os

import requests
from yaml.loader import SafeLoader

from transifex.api import transifex_api

API = os.environ['TRANSIFEX_TOKEN']
HEB=re.compile('[א-ת]')

transifex_api.setup(auth=API)

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
    return len(HEB.findall(x)) > 0

def handle_kind(kind):
    content = ''
    content += 'he:\n'
    for k, v in allkeys(kind):
        if hebrew(v) and '__filters__' not in k:
            content += f'  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}\n'
    content = content.encode('utf-8')

    organization = transifex_api.Organization.filter(slug="the-public-knowledge-workshop")[0]
    project = transifex_api.Project.filter(organization=organization, slug="budgetkey")[0]
    resource = transifex_api.Resource.filter(project=project, slug=kind[1])
    YAML_GENERIC = transifex_api.i18n_formats.filter(organization=organization, name='YAML_GENERIC')[0]

    if len(resource) > 0:
        resource = resource[0]
        print('Update file:', resource, resource.attributes)
        ret = transifex_api.ResourceStringsAsyncUpload.upload(resource=resource, content=content)
        print('UPDATE', ret)

    else:
        print('New file:')

        resource = transifex_api.Resource.create(
            name=kind[2],
            slug=kind[1],
            accept_translations=True,
            i18n_format=YAML_GENERIC,
            project=project)
        ret = transifex_api.ResourceStringsAsyncUpload.upload(resource=resource, content=content)
        print('NEW', ret)


    for lang in ('en', 'ar', 'am', 'ru'):
        print(lang, kind)
        language = transifex_api.Language.get(code=lang)
        url = transifex_api.ResourceTranslationsAsyncDownload.download(resource=resource, language=language)
        translations = requests.get(url).text
        translations = yaml.load(translations, Loader=SafeLoader)['he']

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
