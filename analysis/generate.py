from impacts_estimation.impacts_estimation import estimate_impacts

import json
import sys
import copy


def all_percentage_combinations(prod, switch_index=0):
    if switch_index == len(prod['ingredients']) - 1:
        yield prod
        cpy = copy.deepcopy(prod)
        del cpy['ingredients'][switch_index]['percent']
        yield cpy
    else:
        yield from all_percentage_combinations(prod, switch_index=switch_index+1)
        cpy = copy.deepcopy(prod)
        del cpy['ingredients'][switch_index]['percent']
        yield from all_percentage_combinations(cpy, switch_index=switch_index+1)

def all_unicorn_combinations(prod, switch_index=0):
    if switch_index == len(prod['ingredients']) - 1:
        yield prod
        cpy = copy.deepcopy(prod)
        cpy['ingredients'][switch_index]['id'] = 'en:unicorn-feces'
        yield cpy
    else:
        yield from all_unicorn_combinations(prod, switch_index=switch_index+1)
        cpy = copy.deepcopy(prod)
        cpy['ingredients'][switch_index]['id'] = 'en:unicorn-feces'
        yield from all_unicorn_combinations(cpy, switch_index=switch_index+1)

def generate_for_product(prod, f):
    impact_categories = ['EF single score',
                         'Climate change']
    for percentage_combo in all_percentage_combinations(prod):
        for unicorn_combo in all_unicorn_combinations(percentage_combo):
            print(f'Percentages: {list(map(lambda i: "percent" in i, unicorn_combo["ingredients"]))}')
            print(f'Known: {list(map(lambda i: "en:unicorn-feces" == i["id"], unicorn_combo["ingredients"]))}')
            sys.stdout.flush()
            result = {
                    'ground_truth': unicorn_combo,
                    }
            try:
                impact_estimation_result = estimate_impacts(
                        seed=1,
                        product=unicorn_combo,
                        distributions_as_result=True,
                        impact_names=impact_categories)
                result['estimation'] = impact_estimation_result
            except Exception as e:
                result['error'] = f'{e.__class__.__name__}'
            finally:
                json.dump(result, f, indent=2, sort_keys=True)
                f.write(',\n')

def main():
    print('Loading all ground truth objects...')
    with open('test_dataset_nutri_from_ciqual.json') as f:
        ground_truth = json.load(f)

    print('Generating data...')
    with open('generated_test_data.json', 'w') as f:
        f.write('[')
        n = 1
        for prod in ground_truth:
            print(f'{n}/{len(ground_truth)}\t{prod["product_name"]}')
            sys.stdout.flush()
            generate_for_product(prod, f)
            n = n + 1
        f.write(']')

if __name__ == '__main__':
    main()
