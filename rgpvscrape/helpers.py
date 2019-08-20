import time
import urllib.request

import requests
from PIL import Image
import pytesseract
from bs4 import BeautifulSoup

from .constants import (BASE_URL,
                        RESULT_SUFFIX,
                        HEADERS_GET,
                        HEADERS_POST,
                        COOKIES,
                        TIMEOUT)


POST_DATA = {
  '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$btnviewresult',
  '__EVENTARGUMENT': '',
  '__VIEWSTATE': '',
  '__VIEWSTATEGENERATOR': '',
  '__EVENTVALIDATION': '',
  'ctl00$ContentPlaceHolder1$txtrollno': '',
  'ctl00$ContentPlaceHolder1$drpSemester': '',
  'ctl00$ContentPlaceHolder1$rbtnlstSType': '',
  'ctl00$ContentPlaceHolder1$TextBox1': '',
  'ctl00$ContentPlaceHolder1$btnviewresult': 'View Result'
}


def gen_roll_num_list(
        college_code, branch, year, roll_num_range, sem, gng='G'):
    '''
    Generates a list of roll numbers from given parameters.
    NOTE: The year has to be in short form (eg. '16' for '2016')
    NOTE 2 : The roll number range is inclusive
    '''
    range_low, range_high = roll_num_range

    base_roll_num = college_code + branch + str(year)[-2:]
    roll_num_list = [[base_roll_num + str(num), sem, gng]
                     for num in range(range_low, range_high)]

    return roll_num_list



def get_result_page():
    '''
    Returns the HTML source of the result form page. By default the
    URL for the page is "http://result.rgpv.ac.in/result/BErslt.aspx"
    Change the RESULT_SUFFIX constant to get result for a  different
    program.
    '''
    url = BASE_URL + RESULT_SUFFIX
    response = requests.get(url, headers=HEADERS_GET, cookies=COOKIES)
    return BeautifulSoup(response.text, 'html.parser')


def download_captcha(page_src):
    '''
    Downloads the captcha image on the form page
    '''
    # The image we want is the second image on the page
    captcha_img_src = page_src.find_all('img')[1]['src']
    img_url = BASE_URL + captcha_img_src

    # Download the image
    img_response = requests.get(
        img_url, headers=HEADERS_POST, cookies=COOKIES, stream=True)
    img_response.raw.decode_content = True

    # Store the image for debugging
    urllib.request.urlretrieve(img_url, 'a.jpeg')

    return img_response.raw


def solve_captcha(image):
    '''
    Solves a capthca given an image
    '''
    # List of all characters that are present in the image
    char_whitelist = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    tess_config = ('--psm 8 --oem 0 -c '
                   'tessedit_char_whitelist={0}'.format(char_whitelist))
    captcha_txt = pytesseract.image_to_string(Image.open(image),
                                       config=tess_config)
    return captcha_txt


def submit_form(src, roll_num, sem, gng, captcha_txt, wrong_captcha_count=0):
    '''
    Submit the form with the student details and captcha text.
    Returns -1 in case of invalid roll number.
    '''

    # Deal with ASP.net stuff
    POST_DATA['__VIEWSTATE'] = src.select('#__VIEWSTATE')[0]['value']
    POST_DATA['__VIEWSTATEGENERATOR'] = \
        src.select('#__VIEWSTATEGENERATOR')[0]['value']
    POST_DATA['__EVENTVALIDATION'] = \
        src.select('#__EVENTVALIDATION')[0]['value']
    POST_DATA['ctl00$ContentPlaceHolder1$txtrollno'] = roll_num
    POST_DATA['ctl00$ContentPlaceHolder1$drpSemester'] = sem
    POST_DATA['ctl00$ContentPlaceHolder1$rbtnlstSType'] = gng
    POST_DATA['ctl00$ContentPlaceHolder1$TextBox1'] = captcha_txt

    # Sleep for some time because RGPV servers can't handle more than
    # one request every few seconds :( (or it's a anti-scraping measure)
    # Default value is 5 seconds. Can be changed in constants.py
    time.sleep(TIMEOUT)


    form_response = requests.post(BASE_URL + RESULT_SUFFIX,
                                  headers=HEADERS_POST,
                                  cookies=COOKIES,
                                  data=POST_DATA)
    response_src = BeautifulSoup(form_response.text, 'html.parser')

    # Check for errors. Re-submit in case of wrong captcha text.
    # Return -1 for invalid roll number.

    # The second last "script" tag contains error message if any occured
    error = response_src('script')[-2].string

    if error == 'alert("you have entered a wrong text");':
        # Resubmit the form with new captcha
        print('Wrong captcha. ({0}) [{1}]'.format(captcha_txt, roll_num))
        captcha_new_img = download_captcha(response_src)
        captcha_new_text = solve_captcha(captcha_new_img)
        wrong_captcha_count += 1
        return submit_form(
            response_src, roll_num, sem,gng, captcha_new_text,
            wrong_captcha_count)

    elif error == 'alert("Result for this Enrollment No. not Found");':
        print('{0} is invalid. Skipping'.format(roll_num))        
        return -1

    return parse_result(response_src, roll_num)


def parse_result(src, roll_num):
    '''
    Parses the result page and returns the data in the form of a
    dictionary.
    '''
    name = src.select('#ctl00_ContentPlaceHolder1_lblNameGrading')[0].string
    sgpa = src.select('#ctl00_ContentPlaceHolder1_lblSGPA')[0].string
    cgpa = src.select('#ctl00_ContentPlaceHolder1_lblcgpa')[0].string

    # Some ugly parsing. Sorry.
    grading_table = src.select('#ctl00_ContentPlaceHolder1_pnlGrading')[0]\
                        .table('tr')[6]('table')[1:]

    # Dict comprehension
    grades = {subject('td')[0].string: subject('td')[3].string
                for subject in grading_table}

    return {
        'roll_num': roll_num,
        'name': name,
        'sgpa': sgpa,
        'cgpa': cgpa,
        'grades': grades
    }  # Final grades
