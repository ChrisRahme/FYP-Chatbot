import os

number = 0

base_dir = '../data/nlu'
dirs = os.listdir(base_dir)
dirs.remove('nlu.yml')

for d in dirs:
    local = 0
    with open('../data/nlu/' + d, 'r', encoding='utf-8') as f:
        for line in f:
            l = line.strip()
            if l.startswith('- ') and not l.startswith('- intent:'):
                local += 1
    number += local
    print(f'{local}\texamples in {d}')

input(f'\n{number} total NLU examples'
      f'\n20% = {int(number*0.2)}')
