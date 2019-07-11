'''
This file demonstrates the usage of the tool.
'''

import rgpvscrape as r

# The following statement fetches the 6th semester results for all 
# roll numbers between 0208CS161001 and 0208CS161125.
# Note that the last 4 digits of the roll numbers are part of the
# roll number's "range"
r.scrape(college_code='0208',
         branch='CS',
         year=2016,
         roll_num_range=(1001, 1125),
         sem=6)

