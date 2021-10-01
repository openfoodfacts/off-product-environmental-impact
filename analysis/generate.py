from impacts_estimation.impacts_estimation import estimate_impacts

import json
import sys
import copy
import multiprocessing
import queue


PARALLELLISM = 64

DONE = "DONE"

def print_now(s):
    print(s)
    sys.stdout.flush()

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

def generate_combos(products, product_queue):
    n = 1
    for prod in products:
        for percentage_combo in all_percentage_combinations(prod):
            for unicorn_combo in all_unicorn_combinations(percentage_combo):
                print_now(f'{n}/{len(products)} {prod["product_name"]}\n * percentages: {list(map(lambda i: "percent" in i, unicorn_combo["ingredients"]))}\n * known: {list(map(lambda i: "en:unicorn-feces" != i["id"], unicorn_combo["ingredients"]))}')
                product_queue.put(unicorn_combo)
        n = n + 1
    product_queue.put(DONE)

def queue_all(queue):
    while True:
        val = queue.get()
        if val == DONE:
            break
        yield val

def save_results(result_queue, done_queue):
    with open('generated_test_data.json', 'w') as f:
        f.write('[')
        for result in queue_all(result_queue):
            json.dump(result, f, indent=2, sort_keys=True)
            f.write(',\n')
        f.write(']\n')
    done_queue.put(DONE)

def estimate_products(product_queue, result_queue):
    impact_categories = ['EF single score',
            'Climate change']
    for prod in queue_all(product_queue):
        result = {
                'ground_truth': prod,
                }
        try:
            impact_estimation_result = estimate_impacts(
                    seed=1,
                    product=prod,
                    distributions_as_result=True,
                    impact_names=impact_categories)
            result['estimation'] = impact_estimation_result
        except Exception as e:
            result['error'] = f'{e.__class__.__name__}'
        result_queue.put(result)
    result_queue.put(prod)


def main():
    print_now('Loading all ground truth objects...')
    with open('test_dataset_nutri_from_ciqual.json') as f:
        ground_truth = json.load(f)

    product_queue = multiprocessing.Queue(1)
    result_queue = multiprocessing.Queue(1)
    done_queue = multiprocessing.Queue(1)
    multiprocessing.Process(target=save_results, args=(result_queue, done_queue)).start()
    for i in range(PARALLELLISM):
        multiprocessing.Process(target=estimate_products, args=(product_queue, result_queue)).start()

    print_now('Generating data...')
    generate_combos(ground_truth, product_queue)
    print(done_queue.get())

if __name__ == '__main__':
    main()
