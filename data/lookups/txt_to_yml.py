filename = input('Enter filename: ')
entity   = input('Enter entity name:  ')

text  = 'version: "2.0"\n'
text += 'nlu:\n'
text += '  - lookup: {}\n'.format(entity)
text += '    examples: |\n'

with open(filename + '.txt', 'r') as f:
    for line in f:
        text += '      - ' + line.strip() + '\n'

with open(filename + '.yml', 'w') as f:
    f.write(text)
