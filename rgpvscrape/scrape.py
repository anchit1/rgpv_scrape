# Author : Anchit Shukla
# License : MIT
import time
import multiprocessing as mp
import sys

import pandas as pd

from .helpers import (gen_roll_num_list,
                      get_result_page,
                      download_captcha,
                      solve_captcha,
                      submit_form,
                      parse_result)
from .constants import RECURSION_LIMIT


sys.setrecursionlimit(RECURSION_LIMIT)


def scrape_single(roll_num, sem, gng):
    '''
    This method is used by the pool class.
    It scrapes a single record
    '''

    print('Fetching {0}.'.format(roll_num))

    result_page_src = get_result_page()
    captcha_img = download_captcha(result_page_src)
    captcha_text = solve_captcha(captcha_img)

    result = submit_form(result_page_src, roll_num, sem, gng, captcha_text)

    return result


def scrape(college_code, branch, year, roll_num_range, sem,
            gng='G', n_threads=8, filename=None, verbose=True):

    # Generate a list of roll numbers to scrape
    roll_num_list = gen_roll_num_list(
        college_code, branch, year, roll_num_range, sem, gng)


    # Some constats used for stats
    wrong_captcha_count = 0
    invalid_user_count = 0

    # Allocate a pool of workers and start fetching student details
    pool = mp.Pool(n_threads)
    result_list = pool.starmap(scrape_single, roll_num_list)
    pool.close()
    pool.join()
    
    # Create dataframe for storing student data
    result_list = [val for val in result_list if val != -1]

    columns = [
        'roll_num', 'name', 'sgpa', 'cgpa', 'grades'
    ]

    df = pd.DataFrame(columns=columns, data=result_list) 

    if filename is None:
        filename = '{0}_{1}_{2}_sem({3}).csv'.format(
            branch, year, sem, college_code)

    df.to_csv(filename, index=False)


    if verbose:
        print('/n--------------------------------')
        print('Finished downloading')
        print('Number of records scraped : {0}'.format(df.shape[0]))
        print('Number of wrong capthcas : {0}'.format(wrong_captcha_count))
        print('Number of invalid roll numbers : {0}'.format(
                                                        invalid_user_count))
