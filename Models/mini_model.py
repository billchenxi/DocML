'''
Name: mini_model.py
Time: 11-14 6:40

Author: Bill Chen
---

This is a mini version of the actual model, here it will extract title, 
effective date, terminate date, and parties

Return JSON file with the above information for front end to show.
'''

import sys
import os
import dataclasses

from os import path
from nltk import word_tokenize, pos_tag, ne_chunk
from nltk.corpus import wordnet
from nltk.chunk import tree2conlltags

import pandas as pd
import numpy as np
import argparse
import json
import nltk
import spacy
import re

#optimize this by dowloading during container creation
# nltk.download('stopwords')
# nltk.download('averaged_perceptron_tagger')
# nltk.download('maxent_ne_chunker')
# nltk.download('words')

sys.path.append(path.join(path.dirname(__file__), '../'))
from FeatureGeneration.PDF_paser import Features_Generation
from collections import OrderedDict
from pprint import pprint

@dataclasses.dataclass(init=True)
class Data:
    eng_word = set(nltk.corpus.words.words())

    trigger_terms = ["( The","( the","("]

    defined_terms = ["Company", "Buyer", "Seller", "Sellers", 
                    "Purchaser", "Parent", "Guarantor", "Lender", 
                    "Borrower", "Lessor", "Lessee", "Landlord", 
                    "Tenant", "Creditor", "Contractor", "Customer",
                    "Indemnitee", "Employer", "Employee", "Bank",
                    "Trustee", "Supplier", "Licensee", "Licensor",
                    "Investor", "Debtor"]
                    
    known_org     = ["a Delaware corporation", "a Kansas corporation", 
                    "an Arizona corporation", "an Illinois corporation",
                    "a California corporation"]

    non_info_list = ["Art.", "Art", "Article", "Sec.", "Sect.", "Section", 
                    "Sec", "Part", "Exhibit", "Name:", "name:"]

    punc = [","]

    biz_frag = ["Inc.", "INC.", "Incorp.", "INCORP.", "LLC", "N.A.", "L.L.C.", 
            "LP", "L.P.", "B.V.", "BV", "N.V.", "NV", "Corp.", "CORP."]
    
    effect_date_signals = ["Effective Date", "Dated", "dated", 
            "effective as of", "Effective as of", "effective",
            "entered into as of", "Entered into as of", "as of"]


class Model(Data):
    def __init__(self, pdf_input_path, json_output_path=None, to_df=False):
        """Parse PDF and output Date, Parties, and Title
        
        Args:
            pdf_input (str): path of input pdf file
            json_output (str): path of output json file
            to_df (bool): whether to convert results to data frame for 
                generating csv.
        """
        super(Model).__init__()
        self.pdf_input_path = pdf_input_path
        self.json_output_path = json_output_path
        self.to_df = to_df
        self.features_obj = Features_Generation(pdf_path=self.pdf_input_path,\
            page_list=None, convert_to_text=True)
        self.tokenize_words = self.features_obj.tokenize_words
        self.tokenize_raw_words = self.features_obj.tokenize_raw_words
        self.tokenize_original = self.features_obj.tokenize_original
        self.tokenize_sentences = self.features_obj.tokenize_sentences
        self.features = self.features_obj.features

        self.title = ' '.join(self.extract_title())
        self.clean_title = " ".join(w for w in nltk.wordpunct_tokenize(self.title) \
            if w.lower() in self.eng_word or not w.isalpha())

        self.parties, self.persons = self.extract_parties(self.tokenize_original)
        # self.effective_date = 
        # self.text = " ".join(self.features_obj.text)
        # self.results_300 = self.parsing_content()

    @property
    def pdf_input_path(self):
        """Path where input PDF located.
        
        Returns:
            str: Input path
        """
        return self._pdf_input_path
    
    @pdf_input_path.setter
    def pdf_input_path(self, val):
        if not isinstance(val, str) and val is not None:
            raise TypeError("Input path should be of class str.")
        if val is not None and not os.path.isfile(val):
            raise ValueError("Input path doesn't exist")
        self._pdf_input_path = val
    
    @property
    def json_output_path(self):
        """Path where output JSON located.
        
        Returns:
            str: Output path
        """
        return self._json_output_path

    @json_output_path.setter
    def json_output_path(self, val):
        if not isinstance(val, str) and val is not None:
            raise TypeError("Output path should be of class str.") 
        self._json_output_path = val


    def extract_title(self):
        title_list = []
        first_10 = self.features[:10]

        for indx, val in enumerate(first_10):
            if val != {} and val != None:
                s = val["textline"]
                words = val["textline"].split(' ')
                # Find title index
                if val["textalign"] == 1 and \
                    indx < 10 and \
                    len(words) < 10 and \
                    not all([i.lower() in val["textline"].lower() for i \
                        in self.non_info_list]) and \
                    (words[0].istitle() or words[0].isupper()):
                    title_list.append(s)
        return title_list



    def extract_effective_dates(self, tokens, indx):
        # for sentence in self.tokenize_sentences:
            # if any()
        # return dates
        pass

    def clean_party(self, party_name):
        party_name = party_name.replace("_", "")
        return party_name

    def preceding_phrase(self, tokens, indx, phrases):
        for phrase in phrases:
            phrase_tokens = phrase.split()
            i = 1
            pre_words = []
            while i <= len(phrase_tokens):
                pre_words.insert(0, tokens[indx - i])
                i += 1
            if phrase_tokens == pre_words:
                return True
            else:
                return False
    
    def looks_like_party_name(self, tokens, indx):
        if tokens[indx].istitle() or tokens[indx].isupper():
            return True
        else:
            return False
    
    def capture_party_name(self, tokens, indx, direction):
        party_name = tokens[indx]

        if direction == "right" and (party_name.istitle() or party_name.isupper()):
            i = 1
            while tokens[indx + i].isupper():
                party_name += " " + tokens[indx + i]
                i += 1
            while tokens[indx + i][-1] in self.punc:
                x = i + 1
                if tokens[indx + x] in self.biz_frag:
                    party_name += tokens[indx + i] + " " + tokens[indx + x]
                i += 1  
            return party_name
                
        if direction == "left":
            i = 1
            while tokens[indx - i].isupper() or tokens[indx - i] in self.biz_frag or \
                    tokens[indx - i][-1] in self.punc:            
                if tokens[indx - i].isupper() or tokens[indx - i] in self.biz_frag:
                    party_name = tokens[indx - i] + " " + party_name
                    i += 1
                if tokens[indx - i][-1] in self.punc:
                    x = i + 1
                    party_name = tokens[indx - x] + tokens[indx - i] + " " + party_name
                    i += 2
            return party_name

    def extract_parties(self, tokens):
        parties_list = []
        persons_list = []
        for indx, token in enumerate(tokens):
            # Extract the person's name
            party_name, _ = self._whether_person_name(tokens, indx)
            if party_name != None:
                party_name = self.clean_party(party_name)
                party_name.encode('utf-8')
                persons_list.append(party_name)  

            if self.preceding_phrase(tokens, indx, ["among", "between"]) and self._whether_orgnization_name(tokens, indx):
                print('yes')
                party_name = self.capture_party_name(tokens, indx, "right")
                party_name = clean_party(party_name)
                party_name.encode('utf-8')
                parties_list.append(party_name)  
            
            if self.preceding_phrase(tokens,indx,["(Exact name of"]) and tokens[indx] == "registrant" and _whether_orgnization_name(tokens, indx - 5):
                print('yes')
                party_name = self.capture_party_name(tokens, indx - 5, "left")
                party_name = self.clean_party(party_name)
                party_name.encode('utf-8')
                if party_name.upper() not in (party.upper() for party in parties_list):
                    parties_list.append(party_name)
            
            if self.preceding_phrase(tokens, indx, ['(The']) and tokens[indx] == "Company" and self.subsequent_phrase(tokens,indx,[')'],1) and looks_like_party_name(tokens, indx - 3):
                party_name = self.capture_party_name(tokens, indx - 3, "left")
                party_name = self.clean_party(party_name)
                party_name.encode('utf-8')
                if party_name.upper() not in (party.upper() for party in parties_list):
                    parties_list.append(party_name)

            if (self.preceding_phrase(tokens,indx,['(The']) or self.preceding_phrase(tokens,indx,['(the']) or self.preceding_phrase(tokens,indx,['('])) and tokens[indx] in self.defined_terms:
                print('yes')
                if self.preceding_phrase(tokens,indx - 2, self.known_org):
                    party_name = self.capture_party_name(tokens, indx - 5, "left")
                    party_name = self.clean_party(party_name)
                    party_name.encode('utf-8')
                    if party_name.upper() not in (party.upper() for party in parties_list):
                        parties_list.append(party_name)
                elif self.looks_like_party_name(tokens,indx - 3):
                    party_name = self.capture_party_name(tokens, indx - 3, "left")
                    party_name = self.clean_party(party_name)
                    party_name.encode('utf-8')
                    if party_name.upper() not in (party.upper() for party in parties_list):
                        parties_list.append(party_name)
                
        return list(set(parties_list)), list(set(persons_list))
    
    def preceding_phrase(self, tokens, indx, phrases):
        for phrase in phrases:
            phrase_tokens = phrase.split()
            i = 1
            pre_words = []
            while i <= len(phrase_tokens):
                pre_words.insert(0, tokens[ indx - i])
                i += 1
            if phrase_tokens == pre_words:
                return True
            else:
                return False


    def _check_trigger_word(self, tokens, indx, trigger_words, direction=-1, step=1):
        result = None
        if direction == -1:
            for trigger in trigger_words:
                trigger_tokens = nltk.word_tokenize(trigger)
                target_tokens = tokens[(indx+direction*len(trigger_tokens)):indx]

                if trigger_tokens == target_tokens:
                    result = True
                else:
                    result = False
        return result

    def _whether_orgnization_name(self, tokens, indx):
        word = tokens[indx]
        if word.isupper() or word.istitle():
            return True
        else:
            return False

    def _whether_person_name(self, tokens, indx):
        try:
            first_name, second_name, third_name, forth_name = tokens[indx], tokens[indx+1], tokens[indx+2], tokens[indx+3]

            if (first_name.istitle() or first_name.isupper()) and \
                (forth_name.istitle() or forth_name.isupper()) and \
                (len(second_name)==1 and second_name.isalpha()) and third_name=='.' and \
                first_name not in self.non_info_list:
                return ' '.join([first_name, second_name, third_name, forth_name]), indx + 5

            elif (first_name.istitle() or first_name.isupper()) and \
                (third_name.istitle() or third_name.isupper()) and \
                (len(second_name)==2 and  second_name[0].isalpha()) and second_name[1]=='.' and \
                first_name not in self.non_info_list:
                return ' '.join([first_name, second_name, third_name]), indx + 4
            else:
                return None, indx
        except: 
            return None, indx
        
        
        
        

                

        # model_300_output = OrderedDict([
        #     ("parties", ' '.join(list(subset_parties_df))),
        #     ("effective_date", date_dict["effective_date"]),
        #     ("signed_date", date_dict["signed_date"]),
        #     ("titles", ' '.join(title_list))
        # ])

        # return model_300_output


    def write_json_output(self, output_dict):
        with open(self.json_output_path, 'w') as fp:
            json.dump(output_dict, fp, indent=4, sort_keys=True)




if __name__ == '__main__':
    arguments_parser = argparse.ArgumentParser(description='Process PDF file\
        and output Data, Title, and Parties')
    arguments_parser.add_argument('-i', '--input', required=True,\
        help='path of input PDF file', type=str)

    ret = arguments_parser.parse_known_args()
    options = ret[0]
    if ret[1]:
        raise ValueError(f'unknow argument: \
            {arguments_parser.parse_known_args()[1]}')
    pdf_parser = Model(options.input)
    print('(the' in pdf_parser.tokenize_original)
    print(pdf_parser.tokenize_sentences)
    print(pdf_parser.parties, pdf_parser.persons)




