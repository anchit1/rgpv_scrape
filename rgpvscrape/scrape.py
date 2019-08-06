# Author : Anchit Shukla
# License : MIT
import time

import pandas as pd

from .helpers import (gen_roll_num_list,
                      get_result_page,
                      download_captcha,
                      solve_captcha,
                      submit_form,
                      parse_result)


def scrape(college_code, branch, year, roll_num_range, sem,
            gng='G', threads=1, filename=None, verbose=True):

    # Generate a list of roll numbers to scrape
    roll_num_list = gen_roll_num_list(
        college_code, branch, year, roll_num_range)

    # Create dataframe for storing student data
    columns = [
        'roll_num', 'name', 'grades', 'sgpa', 'cgpa'
    ]
    df = pd.DataFrame(columns=columns)

    # Some constats used for stats
    wrong_captcha_count = 0
    invalid_user_count = 0

    # Iterate over the roll numbers and scrape their results
    for i, num in enumerate(roll_num_list):
        result_page_src = get_result_page()
        captcha_img = download_captcha(result_page_src)
        captcha_text = solve_captcha(captcha_img)

        result = submit_form(result_page_src, num, sem, gng, captcha_text)

        if result == -1:  # invalid roll number
            if verbose:
                #print('{0} is invalid. Skipping'.format(num))
                invalid_user_count += 1
            continue

        (result_html, count) = result
        wrong_captcha_count += count

        result = parse_result(result_html)

        # Save the student data
        df.loc[i] = [
            num, result['name'], result['grades'], result['sgpa'],
            result['cgpa']
        ]

        if filename is None:
            filename = '{0}_{1}_{2}_sem({3}).csv'.format(
                branch, year, sem, college_code)

        df.to_csv(filename, index=False)

        # if verbose:
        #     print('{0} saved.'.format(num))

    if verbose:
        print('/n--------------------------------')
        print('Finished downloading')
        print('Number of records scraped : {0}'.format(df.shape[0]))
        print('Number of wrong capthcas : {0}'.format(wrong_captcha_count))
        print('Number of invalid roll numbers : {0}'.format(
                                                        invalid_user_count))
