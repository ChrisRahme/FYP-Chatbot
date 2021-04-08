import os

def count(base_dir = '..', starts = '', notstarts = '[IGNORELINE]'):
    number = 0

    ignore_list = ['nlu.yml']
    dirs = os.listdir(base_dir)

    for f in ignore_list:
        if f in dirs:
            dirs.remove(f)

    for d in dirs:
        local = 0
        with open(base_dir + '/' + d, 'r', encoding='utf-8') as f:
            for line in f:
                l = line.strip()
                if l.startswith(starts) and not l.startswith(notstarts):
                    local += 1
        number += local
        #print(f'{local}\t in {d}')

    return number

####################################################################

number = count('../data/nlu', '- intent:')

print(f'\n{number} total intents'
      f'\n20% = {int(number*0.2)}\n')

####################################################################

number = count('../data/nlu', '- ', '- intent:')

print(f'\n{number} total NLU examples'
      f'\n20% = {int(number*0.2)}\n')

####################################################################

number = count('../data/stories', '- story:')

print(f'\n{number} total stories'
      f'\n20% = {int(number*0.2)}\n')

####################################################################

number = count('../data/rules', '- rule:')

print(f'\n{number} total rules'
      f'\n20% = {int(number*0.2)}\n')

input()
