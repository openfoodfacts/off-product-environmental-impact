"""
Generates `COMBOS_PER_PRODUCTS` pseudo-products for each product in
`args.input_file` where (optionally) each ingredient percentage
is 50% likely to be known, and (optionally) each ingredient name is 
50% likely to be replaced by `en:unicorn-meat`.
Does this in `args.parallellism` OS processes in parallell.
"""
from impacts_estimation.impacts_estimation import estimate_impacts

import json
import sys
import copy
import multiprocessing
import numpy as np
import traceback
import argparse
from datetime import datetime


parser = argparse.ArgumentParser(description='Generate product combinations and compute their Eco-Score.')
parser.add_argument('--parallellism', type=int, help='number of parallell processes', default=64)
parser.add_argument('--seed', type=int, help='random seed', default=1)
parser.add_argument('--combos_per_product', type=int, help='combinations per product in the input file', default=16)
parser.add_argument('--input_file', type=str, help='input file', default='test_dataset_nutri_from_ciqual.json')
parser.add_argument('--output_file', type=str, help='output file', default='generated_data.json')
parser.add_argument('--with_unrecognized_ingredients', type=str, help='make each ingredient for each combination 50% likely to be replaced with "en:unicorn-meat"', default="yes")
parser.add_argument('--only_missing_percentages', type=str, help='make each ingredient be without the provided percentage', default='no')
parser.add_argument('--with_missing_percentages', type=str, help='make each ingredient for each combination 50% likely to be without the provided percentage', default="yes")
args = parser.parse_args()

DONE = "DONE"

np.random.seed(args.seed)

def indexed_combo(prod, percentages, unicorns):
    cpy = copy.deepcopy(prod)
    if args.only_missing_percentages == 'yes':
        for ing in cpy['ingredients']:
            if 'percent' in ing:
                del ing['percent']
    else:
        if args.with_missing_percentages == 'yes':
            for idx, known in enumerate(percentages):
                if not known:
                    del cpy['ingredients'][idx]['percent']
    if args.with_unrecognized_ingredients == 'yes':
        for idx, unicorn in enumerate(unicorns):
            if unicorn:
                cpy['ingredients'][idx]['id'] = 'en:unicorn-meat'
    return cpy

def all_percentage_combinations(prod, switch_index=0):
    if args.with_missing_percentages != 'yes':
        yield prod
    else:
        cpy = copy.deepcopy(prod)
        if args.only_missing_percentages == 'yes':
            for ing in cpy['ingredients']:
                if 'percent' in ing:
                    del ing['percent']
            yield cpy
        else:
            if switch_index == len(prod['ingredients']) - 1:
                yield cpy
                if 'percent' in cpy['ingredients'][switch_index]:
                    del cpy['ingredients'][switch_index]['percent']
                yield cpy
            else:
                yield from all_percentage_combinations(cpy, switch_index=switch_index+1)
                if 'percent' in cpy['ingredients'][switch_index]:
                    del cpy['ingredients'][switch_index]['percent']
                yield from all_percentage_combinations(cpy, switch_index=switch_index+1)

def all_unicorn_combinations(prod, switch_index=0):
    if args.with_unrecognized_ingredients != 'yes':
        yield prod
    else:
        cpy = copy.deepcopy(prod)
        if switch_index == len(prod['ingredients']) - 1:
            yield cpy
            cpy['ingredients'][switch_index]['id'] = 'en:unicorn-meat'
            yield cpy
        else:
            yield from all_unicorn_combinations(cpy, switch_index=switch_index+1)
            cpy['ingredients'][switch_index]['id'] = 'en:unicorn-meat'
            yield from all_unicorn_combinations(cpy, switch_index=switch_index+1)

def push_prod(iterated, current_num, total_num, prod_num, prod, product_queue):
  known = len(list(filter(lambda i: "en:unicorn-meat" != i["id"], prod["ingredients"])))
  if known > 0:
      print(f'{datetime.now()} {current_num}/{total_num} {prod["product_name"]} #{prod_num} (iterated {iterated})\n * percentages: {list(map(lambda i: "percent" in i, prod["ingredients"]))}\n * known: {list(map(lambda i: "en:unicorn-meat" != i["id"], prod["ingredients"]))}', flush=True)
      product_queue.put(prod)

def generate_combos(products, product_queue):
    try:
        n = 1
        for prod in products:
            combos = 2.0 ** (len(prod["ingredients"]) * 2)
            likelihood_per_combo = args.combos_per_product / combos
            if likelihood_per_combo > 0.005:
                possible_combos = []
                for percentage_combo in all_percentage_combinations(prod):
                    for unicorn_combo in all_unicorn_combinations(percentage_combo):
                        possible_combos.append(unicorn_combo)
                for prod_num in range(args.combos_per_product):
                    combo = possible_combos.pop(np.random.randint(len(possible_combos)))
                    push_prod(True, n, len(products), prod_num, combo, product_queue)
                    if len(possible_combos) == 0:
                        break
            else:
                for prod_num in range(int(args.combos_per_product)):
                    combo = indexed_combo(prod,
                                          np.random.choice([True, False], size=[len(prod["ingredients"])]).tolist(),
                                          np.random.choice([True, False], size=[len(prod["ingredients"])]).tolist())
                    push_prod(False, n, len(products), prod_num, combo, product_queue)
            n = n + 1
        for i in range(args.parallellism):
            product_queue.put(DONE)
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__), file=sys.stderr, flush=True)
    print('DONE generating combos', flush=True)

def queue_all(queue):
    while True:
        val = queue.get()
        if val == DONE:
            break
        yield val

def save_results(result_queue, done_queue):
    try:
        with open(args.output_file, 'w') as f:
            f.write('[')
            for i in range(args.parallellism):
                for result in queue_all(result_queue):
                    json.dump(result, f, indent=2, sort_keys=True)
                    f.write(',\n')
            f.write(']\n')
        done_queue.put(DONE)
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__), file=sys.stderr, flush=True)
    print('DONE saving results', flush=True)

def estimate_outside_process(product, queue):
    """This function runs in a separate process, and communicates with the parent
    through the provided queue. The queue must get a tuple of (result, exception-string)
    when this function terminates."""
    impact_categories = ['EF single score',
            'Climate change']
    try:
        impact = estimate_impacts(
                        ignore_unknown_ingredients=False,
                product=product,
                distributions_as_result=True,
                impact_names=impact_categories)
        queue.put((impact, None))
    except Exception as e:
        queue.put((None, f"{e.__class__.__name__}: {e}"))

def estimate_with_deadline(product, deadline=600):
    """This function starts estimate_outside_process in a separate process, giving
    it a queue to return a (result, exception-string) through.
    The process can time out, and the queue can be empty - both need to provide
    exceptions in addition to anything received via the queue."""
    q = multiprocessing.Queue(1)
    p = multiprocessing.Process(target=estimate_outside_process, args=(product, q))
    try:
        p.start()
        p.join(deadline)
        if p.is_alive():
            raise Exception(f"estimation process timed out after {deadline} seconds")
    finally:
        p.kill()
        p.join()
        p.close()
    results = (None, "no results yet")
    try:
        results = q.get(block=False)
    except Exception as e:
        raise Exception(f"estimation queue read: {e.__class__.__name__}: {e}")
    if results[1]:
        raise Exception(f"estimation process got exception: {results[1]}")
    return results[0]

def estimate_products(product_queue, result_queue, worker_id):
    try:
        for prod in queue_all(product_queue):
            result = {
                    'ground_truth': prod,
                    }
            try:
                result['estimation'] = estimate_with_deadline(prod)
            except Exception as e:
                result['error'] = f'{e.__class__.__name__}: {e}'
            result_queue.put(result)
        result_queue.put(DONE)
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__), file=sys.stderr, flush=True)
    print(f'Worker {worker_id} DONE estimating products', flush=True)


def main():
    print('Loading all ground truth objects...', flush=True)
    with open(args.input_file) as f:
        ground_truth = json.load(f)

    product_queue = multiprocessing.Queue(1)
    result_queue = multiprocessing.Queue(1)
    done_queue = multiprocessing.Queue(1)
    multiprocessing.Process(target=save_results, args=(result_queue, done_queue)).start()
    for i in range(args.parallellism):
        multiprocessing.Process(target=estimate_products, args=(product_queue, result_queue, i)).start()

    print('Generating data...', flush=True)
    generate_combos(ground_truth, product_queue)
    done_queue.get()
    print('DONE with everything!', flush=True)

if __name__ == '__main__':
    main()
