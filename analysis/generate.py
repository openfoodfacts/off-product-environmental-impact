"""
Generates `COMBOS_PER_PRODUCTS` pseudo-products for each product in
`test_dataset_nutri_from_ciqual.json` where each ingredient percentage
is 50% likely to be known, and each ingredient name is 50% likely to
be replaced by `en:unicorn-meat`. Does this in `PARALLELLISM` OS
processes in parallell.
"""
from impacts_estimation.impacts_estimation import estimate_impacts

import json
import sys
import copy
import multiprocessing
import numpy as np
import traceback

PARALLELLISM = 64
SEED = 1
DONE = "DONE"
COMBOS_PER_PRODUCT = 16.0

np.random.seed(SEED)

def indexed_combo(prod, percentages, unicorns):
    cpy = copy.deepcopy(prod)
    for idx, known in enumerate(percentages):
        if not known:
            del cpy['ingredients'][idx]['percent']
    for idx, unicorn in enumerate(unicorns):
        if unicorn:
          cpy['ingredients'][idx]['id'] = 'en:unicorn-meat'
    return cpy

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
        cpy['ingredients'][switch_index]['id'] = 'en:unicorn-meat'
        yield cpy
    else:
        yield from all_unicorn_combinations(prod, switch_index=switch_index+1)
        cpy = copy.deepcopy(prod)
        cpy['ingredients'][switch_index]['id'] = 'en:unicorn-meat'
        yield from all_unicorn_combinations(cpy, switch_index=switch_index+1)

def push_prod(iterated, n, num, prod, product_queue):
  known = len(list(filter(lambda i: "en:unicorn-meat" != i["id"], prod["ingredients"])))
  if known > 0:
      print(f'{n}/{num} {prod["product_name"]} (iterated {iterated})\n * percentages: {list(map(lambda i: "percent" in i, prod["ingredients"]))}\n * known: {list(map(lambda i: "en:unicorn-meat" != i["id"], prod["ingredients"]))}', flush=True)
      product_queue.put(prod)

def generate_combos(products, product_queue):
    try:
        n = 1
        for prod in products:
            combos = 2.0 ** (len(prod["ingredients"]) * 2)
            likelihood_per_combo = COMBOS_PER_PRODUCT / combos
            if likelihood_per_combo > 0.005:
                for percentage_combo in all_percentage_combinations(prod):
                    for unicorn_combo in all_unicorn_combinations(percentage_combo):
                        if np.random.rand() < likelihood_per_combo:
                            push_prod(True, n, len(products), unicorn_combo, product_queue)
            else:
                for _ in range(int(COMBOS_PER_PRODUCT)):
                    combo = indexed_combo(prod,
                                          np.random.choice([True, False], size=[len(prod["ingredients"])]).tolist(),
                                          np.random.choice([True, False], size=[len(prod["ingredients"])]).tolist())
                    push_prod(False, n, len(products), combo, product_queue)
            n = n + 1
        product_queue.put(DONE)
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__), file=sys.stderr, flush=True)

def queue_all(queue):
    while True:
        val = queue.get()
        if val == DONE:
            break
        yield val

def save_results(result_queue, done_queue):
    try:
        with open('generated_test_data.json', 'w') as f:
            f.write('[')
            for result in queue_all(result_queue):
                json.dump(result, f, indent=2, sort_keys=True)
                f.write(',\n')
            f.write(']\n')
        done_queue.put(DONE)
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__), file=sys.stderr, flush=True)

def estimate_products(product_queue, result_queue):
    try:
        impact_categories = ['EF single score',
                'Climate change']
        for prod in queue_all(product_queue):
            result = {
                    'ground_truth': prod,
                    }
            try:
                impact_estimation_result = estimate_impacts(
                        seed=SEED,
                        product=prod,
                        distributions_as_result=True,
                        impact_names=impact_categories)
                result['estimation'] = impact_estimation_result
            except Exception as e:
                result['error'] = f'{e.__class__.__name__}'
            result_queue.put(result)
        result_queue.put(DONE)
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__), file=sys.stderr, flush=True)


def main():
    print('Loading all ground truth objects...', flush=True)
    with open('test_dataset_nutri_from_ciqual.json') as f:
        ground_truth = json.load(f)

    product_queue = multiprocessing.Queue(1)
    result_queue = multiprocessing.Queue(1)
    done_queue = multiprocessing.Queue(1)
    multiprocessing.Process(target=save_results, args=(result_queue, done_queue)).start()
    for i in range(PARALLELLISM):
        multiprocessing.Process(target=estimate_products, args=(product_queue, result_queue)).start()

    print('Generating data...', flush=True)
    generate_combos(ground_truth, product_queue)
    print(done_queue.get(), flush=True)

if __name__ == '__main__':
    main()
