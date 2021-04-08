import re

entity = 'person_name'#input('Enter entity name: ')

text  = 'version: "2.0"\n'
text += 'nlu:\n'
text += '  - lookup: {}\n'.format(entity)
text += '    examples: |\n'


with open(entity + '.txt', 'r', encoding='utf-8') as f:
    for line in f:
        bad_chars = ['','\u008a'] # There is an invisible char here
        regex     = '|'.join(bad_chars)
        new_line  = re.sub(regex, '', line.strip())#.encode('utf-8').decode('utf-8')
        text += '      - ' + new_line + '\n'

with open(entity + '.yml', 'w', encoding='utf-8') as f:
    f.write(text)
