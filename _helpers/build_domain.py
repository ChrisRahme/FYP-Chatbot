# https://forum.rasa.com/t/splitting-up-domain-yml/15861

import os
import glob
import hiyapyco

path = 'domain'
yaml_list = []


globs = glob.glob(os.path.join(path, '*.yml'))

for filename in globs:
    with open(filename, 'r', encoding='utf-8') as fp:
        yaml_file = fp.read()
        yaml_list.append(yaml_file)

merged_yaml = hiyapyco.load(yaml_list, method=hiyapyco.METHOD_MERGE)
print(hiyapyco.dump(merged_yaml))

domain_yml_file = open('.test_domain.yml', 'w+', encoding='utf-8')
domain_yml_file.writelines(hiyapyco.dump(merged_yaml))