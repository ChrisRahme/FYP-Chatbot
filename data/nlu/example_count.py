import os

number = 0

dirs = os.listdir('.')
dirs.remove(__file__.split('\\')[-1])
dirs.remove('nlu.yml')

for d in dirs:
    local = 0
    with open(d, 'r', encoding='utf-8') as f:
        for line in f:
            l = line.strip()
            if l.startswith('- ') and not l.startswith('- intent:'):
                local += 1
    number += local
    print(f'{local}\texamples in {d}')

print(f'\n{number} total examples'
      f'\n20% = {int(number*0.2)}')
