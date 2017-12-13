#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Construct templates and categories for Tekniska museet data.
"""
from collections import OrderedDict
import os.path
import csv
import pywikibot

import batchupload.listscraper as listscraper
import batchupload.common as common
import batchupload.helpers as helpers
from batchupload.make_info import MakeBaseInfo

MAPPINGS_DIR = 'mappings'
IMAGE_DIR = 'Curman'
# stem for maintenance categories
BATCH_CAT = 'Media contributed by Tekniska museet'
BATCH_DATE = '2017-10'  # branch for this particular batch upload
LOGFILE = "Tekniska.log"


class TekniskaInfo(MakeBaseInfo):

    def load_wd_value(self, qid, props, cache=None):
        if cache and qid in cache:
            return cache[qid]

        data = {}
        wd_item = pywikibot.ItemPage(self.wikidata, qid)
        wd_item.exists()  # load data
        for pid, label in props.items():
            value = None
            claims = wd_item.claims.get(pid)
            if claims:
                value = claims[0].getTarget()
            data[label] = value

        if cache:
            cache[qid] = data
        return data

    def __init__(self, **options):
        super(TekniskaInfo, self).__init__(**options)
        self.batch_cat = "{}: {}".format(BATCH_CAT, BATCH_DATE)
        self.commons = pywikibot.Site('commons', 'commons')
        self.wikidata = pywikibot.Site('wikidata', 'wikidata')
        self.log = common.LogFile('', LOGFILE)
        self.photographer_cache = {}
        self.category_cache = []

    def load_data(self, in_file):
        return common.open_and_read_file(in_file, as_json=False)

    def generate_content_cats(self, item):
        # to do -- generate cats from keywords
        item.generate_place_cats()
        return [x for x in list(item.content_cats) if x is not None]

    def generate_filename(self, item):
        id_no = item.id_no
        title = item.image_title
        provider = "TEKM"
        return helpers.format_filename(
            title, provider, id_no)

    def generate_meta_cats(self, item, cats):
        cats = set(item.meta_cats)
        cats.add(self.batch_cat)
        return list(cats)

    def get_original_filename(self, item):
        #  should be updated if files named with another field
        return item.id_no

    def load_mappings(self, update_mappings):
        concrete_motif_file = os.path.join(MAPPINGS_DIR, 'concrete_motif.json')
        concrete_motif_page = 'Commons:Tekniska museet/Curman/mapping title'
        geo_file = os.path.join(MAPPINGS_DIR, 'geo.json')
        geo_page = 'Commons:Tekniska museet/Curman/mapping location'
        keywords_file = os.path.join(MAPPINGS_DIR, 'keywords.json')
        keywords_page = 'Commons:Tekniska museet/Curman/mapping amnesord'

        if update_mappings:
            print("Updating mappings...")
            self.mappings['concrete_motif'] = self.get_concrete_motif_mapping(
                concrete_motif_page)
            common.open_and_write_file(concrete_motif_file, self.mappings[
                'concrete_motif'], as_json=True)
            self.mappings['geo'] = self.get_geo_mapping(geo_page)
            common.open_and_write_file(geo_file, self.mappings[
                'geo'], as_json=True)
            self.mappings['keywords'] = self.get_keywords_mapping(keywords_page)
            common.open_and_write_file(keywords_file, self.mappings[
                'keywords'], as_json=True)
        else:
            self.mappings['concrete_motif'] = common.open_and_read_file(
                concrete_motif_file, as_json=True)
            self.mappings['geo'] = common.open_and_read_file(
                geo_file, as_json=True)
            self.mappings['keywords'] = common.open_and_read_file(
                keywords_file, as_json=True)

        pywikibot.output('Loaded all mappings')

    def get_concrete_motif_mapping(self, page):
        motifs = {}
        page = pywikibot.Page(self.commons, page)
        data = listscraper.parseEntries(
            page.text,
            row_t='User:André Costa (WMSE)/mapping-row',
            default_params={'name': '', 'category': '', 'frequency': ''})
        for entry in data:
            if entry['category'] and entry['name']:
                category = entry['category'][0]
                name = entry['name'][0]
                motifs[name] = category
        return motifs

    def get_keywords_mapping(self, p):
        keywords = {}
        page = pywikibot.Page(self.commons, p)
        data = listscraper.parseEntries(
            page.text,
            row_t='User:André Costa (WMSE)/mapping-row',
            default_params={'name': '', 'category': '', 'frequency': ''})
        for entry in data:
            if entry['category'] and entry['name']:
                category = entry['category'][0]
                name = entry['name'][0]
                keywords[name] = category
        return keywords

    def get_geo_mapping(self, p):
        page = pywikibot.Page(self.commons, p)
        data = listscraper.parseEntries(
            page.text,
            row_t='User:André Costa (WMSE)/mapping-row',
            default_params={'name': '', 'wikidata': '', 'frequency': ''})
        geo_ids = {}
        for entry in data:
            if entry['wikidata'] and entry['name']:
                wikidata = entry['wikidata'][0]
                name = entry['name'][0]
                if wikidata != '-':
                    geo_ids[name] = wikidata

        # look up data on Wikidata
        props = {'P373': 'commonscat'}
        geo = {}
        for name, qid in geo_ids.items():
            geo[name] = self.load_wd_value(
                qid, props)
            geo["wd"] = qid
        return geo

    def make_info_template(self, item):
        template_name = 'Photograph'
        template_data = OrderedDict()
        template_data['title'] = item.generate_title()
        template_data['description'] = item.generate_description()
        template_data['photographer'] = "{{Creator:Sigurd Curman}}"
        template_data['department'] = ("Sigurd Curmans arkiv / "
                                       "Tekniska museet (SC-K1-1)")
        # template_data['date'] = item.generate_date()
        template_data['permission'] = item.generate_license()
        template_data['ID'] = item.generate_id()
        template_data['source'] = item.generate_source()
        return helpers.output_block_template(template_name, template_data, 0)

    def process_data(self, raw_data):
        d = {}
        reader = csv.DictReader(raw_data.splitlines(), dialect='excel-tab')
        tagDict = {
            "image_title": "Titel",
            "id_no": "Identifikationsnr",
            "description": "Motiv-beskrivning",
            "location": "Avbildade - orter",
            "alt_id_no": "Alternativt nummer-Institutionsintern katalog/lista"
        }
        for r in reader:
            rec_dic = {}
            for tag in tagDict:
                column_name = tagDict[tag]
                value = r[column_name]
                rec_dic[tag] = value.strip()
            id_no = rec_dic["id_no"]
            d[id_no] = TekniskaItem(rec_dic, self)
        self.data = d


class TekniskaItem(object):

    def __init__(self, initial_data, info):

        for key, value in initial_data.items():
            setattr(self, key, value)

        self.wd = {}
        self.content_cats = set()
        self.meta_cats = set()
        self.info = info
        self.commons = pywikibot.Site('commons', 'commons')

    def generate_geo_cat(self):
        cats = self.info.mappings["geo"]
        if self.location in cats.keys():
            cat = cats[self.location].get("commonscat")
            self.content_cats.add(cat)

    def generate_place_cats(self):
        has_specific_place = False
        cats = self.info.mappings["concrete_motif"]
        if self.image_title in cats.keys():
            concr_cat = cats.get(self.image_title)
            self.content_cats.add(concr_cat)
            has_specific_place = True

        if not has_specific_place:
            self.generate_geo_cat()

    def generate_description(self):
        if self.description:
            swedish = "{{{{sv|{}}}}}".format(self.description)
            return swedish

    def generate_title(self):
        return "{{{{sv|{}}}}}".format(self.image_title)

    def generate_source(self):
        return "{{Tekniska museet cooperation project}}"

    def generate_id(self):
        return '{{TEKM-link|' + self.id_no + '}}'

    def generate_license(self):
        return "{{PD-old-70}}"


if __name__ == '__main__':
    TekniskaInfo.main()
