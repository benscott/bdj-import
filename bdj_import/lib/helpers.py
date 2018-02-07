# -*- coding: utf-8 -*-
# @Author: benscott
# @Date:   2018-01-24 09:32:13
# @Last Modified by:   benscott
# @Last Modified time: 2018-01-24 09:51:03

import re
import unicodedata
import requests
from bs4 import BeautifulSoup


def normalize(s):
    return unicodedata.normalize("NFKD", s).strip()


def file_exists(url):
    r = requests.head(url)
    r.headers
    return r.status_code == 200


def strip_parenthesis(s):
    return re.sub(r'\(|\)', '', s)


def soupify(html, vars=[]):
    """
    Convert html string to beautiful soup
    """
    return BeautifulSoup(html.format(vars), "html.parser")

# def prettify_html(ugly_html):
#     body = normalize(ugly_html)
#     soup = BeautifulSoup(body, "html.parser")
#     # Remove embedded image tags - cannot be handled by BDJ
#     [x.extract() for x in soup.findAll('img')]
#     return '<div>%s</div>' % soup.prettify()


def ensure_list(v):
    # Ensure elements is a list
    return v if type(v) is list else [v]
