import requests
from bs4 import BeautifulSoup
import re
import sys
sys.path.append("/home/pi/Documents/python/cronjobs/product_checker/")
from lib import slack

def parse_prices(soup):
    price_str = soup.find('span',{'class':'u-sr-only'}).text
    prices = [float(p) for p in re.findall(r" (\d+(?:\.\d+)?)",price_str)]
    return prices

class GallProduct:
    
    BASE_URL = 'http://gall.nl/'

    def __init__(self,id):
        self.id = id

    def load(self):
        self.soup = BeautifulSoup(requests.get(self.BASE_URL + self.id).text, 'html.parser')
        prices = parse_prices(self.soup.find('div',{'class':'a-price'}))
        if len(prices) == 1:
            self.discounted = False
            self.currentPrice = prices[0]
            self.originalPrice = None
        elif len(prices) == 2:
            self.discounted = True
            self.currentPrice = prices[1]
            self.originalPrice = prices[0]

        self.name = self.soup.find('h1').text.strip()
    
    def define(self,params):
        self.name = params['name']
        self.discounted = params['discounted']
        self.currentPrice = params['currentPrice']
        self.originalPrice = params['originalPrice']

    def __repr__(self):
        return f'GallProduct({self.name}'



class GallSearch:
    SEARCH_URL = "https://www.gall.nl/zoeken/"
    lastsearch = []
    def search(self, query):
        payload = {'lang':'nl_NL', 'q':query}
        r = requests.get(self.SEARCH_URL, params = payload)
        self.soup = BeautifulSoup(r.text, 'html.parser')
        search_results = self.soup.find_all('div', {'class':'c-product-tile'}) 
        gallProducts = []
        for sr in search_results:
            name = sr.find('a',{'class':'product-tile__title-inner'}).text
            prices = parse_prices(sr)
            if len(prices) == 1:
                discounted = False
                currentPrice = prices[0]
                originalPrice = None
            elif len(prices) == 2:
                discounted = True
                currentPrice = prices[1]
                originalPrice = prices[0]
            id = sr.find('a',{'class':'product-tile__container-link'})['href'][1:]
            params = {
                'name': name,
                'discounted':discounted,
                'currentPrice':currentPrice,
                'originalPrice':originalPrice
            }
            gallProduct = GallProduct(id)
            gallProduct.define(params)
            gallProducts.append(gallProduct)
        self.lastsearch = gallProducts
        return gallProducts

    def show_discounts(self, products = None):
        if products == None:
            products = self.lastsearch
        discounts = [f'{g.name}:\n{g.originalPrice} -> {g.currentPrice}\n ' for g in products if g.discounted]
        print('\n'.join(discounts))
        return discounts

        
if __name__ == '__main__':
    f = open("/home/pi/Documents/python/cronjobs/product_checker/product_APIs/checklists/gallgall.txt","r")
    for line in f.readlines():
        gSearch = GallSearch()
        gSearch.search(line)
        discounts = gSearch.show_discounts()
        if len(discounts)>0:
            slack.send_message("### *" + line.strip().upper() + "* ###\n\n" + '\n'.join(discounts))
    f.close()
