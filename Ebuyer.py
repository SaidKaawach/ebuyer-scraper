"""Copyright® Said Kaawach 2020"""

import requests
import bs4
from urllib.parse import parse_qs, urlparse
import os
from bs4 import BeautifulSoup
import datetime, random, pause
import time
import csv
import sys
import glob, os
import re
import io

url_base = 'https://www.ebuyer.com'
product_id_tracker = []
project_name = 'Ebuyers'

# insert your paths here

# create crawled products ID to know which products have been scraped
product_id_file = 'crawled_product_ids.txt'
today = str(datetime.date.today())
csv_out = csv_path + project_name + today + '.csv'
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

def load_previous_product_id():
    global product_id_tracker, product_id_file
    if not os.path.isfile(product_id_file):
        with open(product_id_file, 'w') as file:
            pass
    with open(product_id_file) as fl:
        for line in fl:
            product_id_tracker.append(line.strip('\n'))


def save_crawled_product_id(id):
    global product_id_tracker, product_id_file
    product_id_tracker.append(id)
    with open(product_id_file, 'a') as the_file:
        the_file.write(str(id) + '\n')


def get_review(id):
    global headers
    rating = ''
    reviews_count = ''
    jar = requests.cookies.RequestsCookieJar()
    url = 'https://mark.reevoo.com/reevoomark/en-GB/product?sku=' + str(id) + '&tab=reviews&trkref=EBU'

    try:
        response = requests.get(url, cookies=jar, headers=headers).text
        response = BeautifulSoup(response, 'lxml')
        rating = response.find('div', attrs={'class': 'overall-score-wrapper'}).find('div', attrs={'class': 'score-container'}).contents[0]['data-score']
        reviews_count = response.find('h3', attrs={'class': 'filtered-count summary'}).text
        reviews_count = re.sub(r"[a-z\s]", '', reviews_count)
    except:
        pass

    return rating + ';' + reviews_count

def fetch_html(url, filename):
    global headers, html_path
    if not os.path.isfile(html_path + filename):
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
        jar = requests.cookies.RequestsCookieJar()
        response = requests.get(url, cookies=jar, headers=headers).text
        with open(html_path + filename, 'wb') as f:
            f.write(response.encode('utf-8'))
        time.sleep(5)
        print('downloading', filename)
    page = open(html_path + filename, 'r', encoding='utf8')
    page = BeautifulSoup(page, 'lxml')
    return page
def removeNonAscii(string):
    return "".join(i for i in string if ord(i) < 128)

def string_clean(string):
    string = re.sub(r"[\?//\/]", "_", string)
    string = re.sub(r"[:;\"\n\'\s]", "", string)
    string = re.sub(r"[,]", "-", string)
    return string

'''
Note: The below function grabs all the category links of the site and is a recursive function. Please don't change anything here or it amy not work.
'''
def get_all_category_links(url_base, categories={}):
    url = string_clean(url_base)
    soup = fetch_html(url_base, 'categories_' + url + '.html')
    categories_soup = soup.find('ul', attrs={'class': 'departments-panel'}).children
    for cat in categories_soup:
        try:
            cat_text = None
            special_link = cat.find('a', recursive=False)
            if special_link is None:
                cat_text = cat.find('span', recursive=False, attrs={'class': 'js-nav-department'}).text
            if cat_text is not None and cat_text not in categories:
                categories[cat_text] = {}
            # home appliances code below:
            if special_link is not None:
                special_link = special_link['href']
            if special_link not in ['#', '/clearance']:
                if special_link == '/store/Home-Appliances':
                    soup = fetch_html(url_base + special_link, 'categories_' + url + special_link.replace('/', '_') + '.html')
                    a_s = soup.findAll('a', attrs={'class': 'facet__bucket js-facet-bucket'})
                    categories['Home-Appliances'] = {}
                    for a in a_s:
                        categories['Home-Appliances'][removeNonAscii(a.text.replace('\n', ''))] = a['href']
                if special_link == '/office-stationery':
                    get_all_category_links(url_base + '/office-stationery', categories=categories)
                    continue
            #################################################################
            sub_cat_1_soups = cat.findAll('ul', attrs={'class': 'nav-column'})
            #laptop
            for sub_cat_1_soup in sub_cat_1_soups:
                curr_sub_cat_1 = None
                for sub_cat_1_item in sub_cat_1_soup.children:
                    try:
                        # if it's a sub_category_1 and it's not in our dict add it as a key
                        if sub_cat_1_item.has_attr('class') and len(sub_cat_1_item['class']) and sub_cat_1_item['class'][0] == 'nav-header':
                            curr_sub_cat_1 = None
                            curr_sub_cat_1 = sub_cat_1_item.text
                            if curr_sub_cat_1 not in categories[cat_text]:
                                categories[cat_text][curr_sub_cat_1] = {}
                        else:
                            if curr_sub_cat_1 is not None:
                                href_ref = sub_cat_1_item.find('a')
                                # else it is a sub_cat_2 and add it to list under sub_cat_1
                                categories[cat_text][curr_sub_cat_1][href_ref.text] = href_ref['href']
                    except:
                        pass
        except:
            pass
    return categories


def grab_products(url, filename, cat='', subcat1='', subcat2=''):
    global csv_out, today, product_id_tracker
    product_page_soup = fetch_html(url, filename)
    products = product_page_soup.find('div', attrs={'id': 'grid-view'})
    if products is None or (products is not None and len(products.contents) == 0):
        if os.path.exists(html_path + filename):
            os.remove(html_path + filename)
        return True
    products = products.children
    for product in products:
        [quick_find, mfr_part_code, good_name, brand, features, old_price, price, save, availability, deliverydate, review] = ['', '', '', '', '', '', '', '', '', '', '']
        if type(product) is bs4.element.NavigableString:
            continue
        try:
            product_id = product['data-product-id']
            if product_id in product_id_tracker:
                continue
            save_crawled_product_id(product_id)
        except:
            pass
        try:
            product_link = product.find('h3', attrs={'class': 'grid-item__title'}).find('a')['href']
        except:
            pass
        try:
            try:
                product_info = fetch_html(url_base + product_link, today + '_' + product_id + '.html')
            except:
                raise Exception('Error fetching ' + url_base + product_link, today + '_' + product_id + '.html')
            try:
                quick_find = removeNonAscii(product_info.find('span', attrs={'class': 'quickfind'}).text.split(':')[1].strip())
            except:
                pass
            try:
                mfr_part_code = removeNonAscii(product_info.find('span', attrs={'class': 'mfr'}).text.split(':')[1].strip())
            except:
                pass
            try:
                good_name = removeNonAscii(product_info.find('h1', attrs={'class': 'product-hero__title'}).text.replace(',', '-'))
            except:
                pass
            try:
                brand = removeNonAscii(product_info.find('div', attrs={'class': 'product-hero__mfr'}).find('img')['alt'])
            except:
                pass
            try:
                features_li = product_info.find('ul', attrs={'class': 'product-hero__key-selling-points'}).children
                for feature in features_li:
                    features = features + feature.text + ' '
                features = removeNonAscii(features.replace('"', '').replace(',', '-'))
            except:
                pass
            try:
                old_price = removeNonAscii(product_info.find('span', attrs={'class': 'was'}).text)
            except:
                pass
            try:
                price_box = product_info.find('div', attrs={'class': 'purchase-info__price'})
                price = string_clean(price_box.find('p', attrs={'class': 'price'}).text.replace('inc. vat', ''))
            except:
                pass
            try:
                save = string_clean(product_info.find('span', attrs={'class': 'saving'}).text.replace('save', ''))
            except:
                pass
            try:
                availability = removeNonAscii(product_info.find('span', attrs={'class': 'unique-selling-points__stock-bold'}).text)
            except:
                pass
            try:
                deliverydate = removeNonAscii(product_info.find('span', attrs={'class', 'unique-selling-points__deliv-date'}).text.replace(',', ''))
            except:
                pass
            try:
                review = removeNonAscii(get_review(product_id))
            except:
                pass
        except Exception as error:
            print(error)
        data_row = str(project_name)+";"+str(quick_find)+";"+str(mfr_part_code)+";"+str(good_name)+";"+str(brand)+";"+str(features)+";"+str(old_price)+";"+str(price)+";"+str(save)+";"+str(cat)+";"+str(subcat1)+";"+str(subcat2)+";"+str(availability)+";"+str(deliverydate)+";"+str(review)+";"+today+"\n"
        print('data_row')
        with open(csv_out, 'a') as f:
            f.write(data_row)

    next_page = product_page_soup.find('li', attrs={'class': 'next-page'})
    if next_page is not None and not len(next_page):
        print('reached last page')
        return True
    else:
        return False
    time.sleep(5)

web_links = get_all_category_links(url_base)

with open(csv_out, 'w') as f:
    f.write('project_name;Quickfind;Mfr_part_code;good_name;brand;features;old_price;price;save;category;subcat1;subcat2;availability;deliverydate;rating;rating_count;date\n')

load_previous_product_id()

for cat in web_links:
    for sub_cat_1 in web_links[cat]:
        sub_cat_1_links = web_links[cat][sub_cat_1]
        val_type = type(sub_cat_1_links)
        if val_type is dict:
            for sub_cat_2, link in sub_cat_1_links.items():
                curr_page = 1
                while True:
                    filename = string_clean(today + '_' + cat + '_' + sub_cat_1 + '_' + sub_cat_2 + '_' + link + '_page=' + str(curr_page) + '.html')
                    link_unfiltered = url_base + link
                    params_len = len(parse_qs(urlparse(link_unfiltered).query))
                    url = ''
                    if params_len > 0:
                        url = link_unfiltered + '&page='
                    else:
                        url = link_unfiltered + '?page='
                    url = url + str(curr_page)
                    print('url ===', url)
                    if grab_products(url, filename, cat=cat, subcat1=sub_cat_1, subcat2=sub_cat_2):
                        break
                    curr_page = curr_page + 1
        if val_type is str:
            curr_page = 1
            while True:
                filename = string_clean(today + '_' + cat + '_' + sub_cat_1 + '_' + sub_cat_1_links + '.html')
                link_unfiltered = url_base + sub_cat_1_links
                params_len = len(parse_qs(urlparse(link_unfiltered).query))
                url = ''
                if params_len > 0:
                    url = link_unfiltered + '&page='
                else:
                    url = link_unfiltered + '?page='
                url = url + str(curr_page)
                if grab_products(url, filename, cat=cat, subcat1=sub_cat_1, subcat2=''):
                    break
                curr_page = curr_page + 1
                
os.chdir(html_path)
zipcommand = "tar -cvzf "+project_name+today+".tar.gz *"+today+"* --remove-files"
os.system(zipcommand)
print (project_name, "done", today)
#when downloading starts e.g. 1 am
hour_start = 5
pause.until(int(int(time.time())/60/60/24)*60*60*24+60*60*(24+hour_start)+random.randint(1, 60)*60)
