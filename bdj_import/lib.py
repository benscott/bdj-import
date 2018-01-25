# -*- coding: utf-8 -*-
# @Author: benscott
# @Date:   2018-01-24 09:32:13
# @Last Modified by:   benscott
# @Last Modified time: 2018-01-24 09:51:03

import unicodedata


def normalize(s):
    return unicodedata.normalize("NFKD", s).strip()
