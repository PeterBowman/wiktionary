# -*- coding: utf-8 -*-

"""This script seeks to kill two birds with one stone: add examples of
usage to words that don't have them, and to include orphaned words in
these examples. It uses NKJP API (http://www.nkjp.uni.lodz.pl/help.jsp)
to fetch examples from the most comprehensive Polish language corpus.
"""

from nkjp_lookup import nkjp_lookup_new, nkjp_find_context
from lxml import etree
import re
import json
from importsjp import morfAnalyse, wikilink, phrases_wikilink, shortLink
import morfeusz
import xml.dom.minidom # for testing
from klasa import *
import pywikibot as pwb
from datetime import datetime, timedelta, time
import pdb
from difflib import SequenceMatcher
import xmltodict

def NKJP_to_text(left, match=[], right=[]):
    """
    Combine the results from an NKJP API query into one sentence. The results
    either come in threes (left side, matched phrase and right side), or in an
    OrderedDict (the result of xmltodict.parse) form when you query /select. /select
    is used to fetch the context of a phrase that is too short. This function will also work
    on a single list of tagged words. This function is necessary instead of a simple join()
    for two reasons: 1) in the API's output, the information about spaces is lost,
    so we need to correctly insert spaces around interpunction 2) we need to take care
    of agglutinates, which may be useful for morphological analysis, but they'd
    break wikitext.
    
    Args:
        left (OrderedDict or list): This function can parse two types of input.
            It's a consequence of NKJP API's different representation of /spans
            and /select query results.
            OrderedDict is the result from a nkjp_new.nkjp_find_context() call, while
            nkjp_new.nkjp_lookup_new() returns a list. In the latter case, this function
            can parse one, two or three lists. The first is useful when parsing only part
            of an NKJP API's result, but if you're parsing all 'lTks', 'mTks', 'rTks' then
            NKJP_to_text will return a full sentence from these three.
        match (list): when parsing a result from NKJP API's /spans, you can
            pass 'mTks' as the second argument
        right (list): when parsing a result from NKJP API's /spans, you can
            pass 'rTks' as the third argument
    Returns:
        str: API's output converted to plain text, with interpunction and
            agglutinates handled correctly
    """

    text_output = ''

    if type(left) == OrderedDict:
        listwords = left['s']['wts']['wt']
        try: listwords[0]
        except KeyError:
            listwords = [listwords]
    else:
        listwords = left + match + right

    #keep track of quotes - closing quote marks don't require spaces before,
    #opening marks do require spaces
    open_quote = 0

    for i, elem in enumerate(listwords):
        if type(left) == OrderedDict:
            tag = elem['ps']['p']['#text']
            word = elem['w']
            if i > 0:
                prev = listwords[i-1]['w']
        else:
            word_elems = elem.split('|')
            tag = word_elems[2]
            word = word_elems[0][2:]
            if i > 0:
                prev = listwords[i-1].split('|')[0][2:]

        excluded_interpunction = ('(', '-', '„')
        excluded_opening_chars = ('(', '„')


        if ('punct:interp' not in tag and 'aglt:' not in tag) or any([word == p for p in excluded_interpunction]):
            if i > 0 and all([prev != o_p for o_p in excluded_opening_chars]) and not (open_quote == 1 and prev == '"'):
                text_output += ' '
        elif word == '"':
            if open_quote == 0:
                open_quote = 1
                text_output += ' '
            else:
                open_quote = 0

        if word:
            text_output += word

    return text_output


def get_left_context(nkjp_match, nkjp_doc, minimum_length=60):
    """
    Short sentences are not the best matches, because the lack context.
    This function will calculate the length of a sentence and return 0 if
    it's too short.

    Args:
        nkjp_match (dict): one result of NKJP api request,
            i.e. one element of ['spans']
        nkjo_doc (dict): the corresponding ['doc'] element of the result, where
            seq and text_id are stored
        minimum_length (int): minimum length of the sentence
    """

    whole_sentence = NKJP_to_text(nkjp_match['lTks'], nkjp_match['mTks'], nkjp_match['rTks'])
    extra_left_context = ''

    seq = int(nkjp_doc['seq'])-1
    
    while (len(whole_sentence) + len(extra_left_context) < minimum_length):
        try: ctx_query_result = nkjp_find_context(seq, nkjp_match['text_id'])[0]['utt_tagged']
        except (IndexError, ValueError) as e:
            break
        ctx_stripped = NKJP_to_text(xmltodict.parse(ctx_query_result))
        extra_left_context = ctx_stripped + ' ' + extra_left_context
        seq -= 1

    
    return extra_left_context.strip()


def check_sentence_quality(nkjp_match):
    """
    Take a tuple with the left and right side of the matched word
    and check a few conditions to determine whether it's a good example or not

    Args:
        left_match_right (tuple): a tuple of three strings: the left side
            of the NKJP match, the match itself (in [[baseform|match]] form)
            and the right side

    Returns:
        int: 0 for bad quality, 1 for good quality
    """

    joined_sentence = NKJP_to_text(nkjp_match['lTks'], nkjp_match['mTks'], nkjp_match['rTks'])

    # the proportion of upper case letters to all letters is too high
    allowed_uppercase_proportion = 0.1

    if sum(1 for c in joined_sentence if c.isupper())/len(joined_sentence) > allowed_uppercase_proportion:
        return 0

    #too many titlecase words
    allowed_titlecase_proportion = 0.4
    if sum(1 for c in joined_sentence.split() if c[0].isupper())/len(joined_sentence.split()) > allowed_titlecase_proportion:
        return 0

    # the sentence is too long
    allowed_length = 200
    minimum_length = 60

    if len(joined_sentence) > allowed_length:
        return 0
    if len(joined_sentence) < minimum_length:
        return 0

    # there are too many newlines (most likely a list)
    allowed_newlines = 3
    
    if joined_sentence.count('\n') > allowed_newlines:
        return 0

    return 1

def wikitext_one_sentence(left_context, nkjp_match, match_base_form):
    """
    Take a tuple with the left and right side of the matched word
    and format it for printing. This is a way to circumvent doing
    wikilink('[[word]]'), which doesn't work properly as of 01/2015

    Args:
        left_match_right (tuple): a tuple of three strings: the left side
            of the NKJP match, the match itself (in [[baseform|match]] form)
            and the right side
        match_base_form (str): base form of the queried word, for wikisation

    Returns:
        str: [[the|The]] [[input]] [[sentence]] [[format]]ted [[like]] [[this]].
    """


    left_ctx_wikised = wikilink(left_context)
    left_match_wikised = wikilink(NKJP_to_text(nkjp_match['lTks']))

    final_sentence = left_ctx_wikised + left_match_wikised

    quote_count = final_sentence.count('"')
    
    try: last_left = nkjp_match['lTks'][-1].split('|')[0]
    except IndexError:
        last_left = None

    try: first_right = nkjp_match['rTks'][0].split('|')[0]
    except IndexError:
        first_right = None
        first_right_tag = ''
    else:
        first_right_tag = nkjp_match['rTks'][0].split('|')[2][2:]

    if ( last_left == 'w:"' and quote_count % 2 == 1)\
       or last_left == 'w:(':
        pass
    else:
        final_sentence += ' '

    final_sentence += shortLink(match_base_form, NKJP_to_text(nkjp_match['mTks']))
    
    if (first_right == 'w:"' and quote_count % 2 == 1)\
       or 'punct:interp' in first_right_tag:
        pass
    else:
        final_sentence += ' '

    final_sentence += wikilink(NKJP_to_text(nkjp_match['rTks']))

    return final_sentence.strip()

def get_reference(doc):
    """
    Take one result from NKJP api (within <line> tags), extract info
    about autorship and format it for printing

    Args:
        api_output (lxml.etree._Element): one result of NKJP api request,
            i.e. the content within one <line> tag

    Returns:
        str: pretty formated citation. If the source is on the blacklist,
            returns ''
    """
    
    ref = {}
    ref['authors'] = doc['authors']
    
    excluded_titles = ['Wikipedia:']

    # article title exists for newspaper records
    a_title = doc['title_a_s']
    if a_title != '':
        if any(a_title.startswith(c) for c in excluded_titles):
            return ''
        else:
            ref['article_title'] = a_title

    # this is a book title or a newspaper name
    if doc['title_m_s'] != '':
        ref['pub_title'] = doc['title_m_s']

    if doc['title_j_s'] != '':
        ref['journal_title'] = doc['title_j_s']
         
    pub_date = doc['pub_date']

    refdate = ''
    if len(pub_date) == 10:
        refdate += '{0}/{1}/'.format(pub_date[8:], pub_date[5:7])
    if len(pub_date) in (4, 10):
        refdate += pub_date[:4]
    ref['date'] = refdate
    
    #extras
    ref['id'] = doc['id']
    ref['channel'] = doc['medium']
    ref['domain'] = doc['genre']

    return ref

def get_definitions(word):
    """
    Load a page from pl.wikt and find all definitions in the Polish section.
    This can be used to show the user a list of definitions beside an example,
    so they can match the two.

    Args:
        word (str): page title on pl.wikt
    Returns:
        tuple:
            str: all definitions found in page along with their part of speech
            descriptions
            pywikibot.Timestamp: time at which definitions were retrieved (useful
                for checking for edit conflicts
    """

    # https://regex101.com/r/sX1yF7/1
    re_numbers = re.compile(r'\: \(([0-9]\.[0-9]{1,2})\)\s*.*')
    re_refs = re.compile(r'(<ref.*?(?:/>|</ref>))')

    try: wikipage = Haslo(word)
    except sectionsNotFound:
        pass
    else:
        if wikipage.type == 3:
            for langsection in wikipage.listLangs:
                if langsection.lang == 'polski':
                    langsection.pola()
                    nums = re.findall(re_numbers, langsection.subSections['znaczenia'].text)

                    return (re.sub(re_refs, '', langsection.subSections['znaczenia'].text), pwb.Page(pwb.Site(), word).editTime())

    return 0


class ExampleDict(dict):
    def __init__(self,*arg,**kw):
        super(ExampleDict, self).__init__(*arg, **kw)
        self['examples'] = []



def log_verification(verified_entry, example_index, error=''):

    #format: title##bool(good_example)##verificator##example##correct_def##orphan##authors##a_title##pub_title##pub_date##channel##domain##error

    #https://regex101.com/r/nN1bN2/2

    this_example = verified_entry['examples'][example_index]
    re_correct_def = re.compile(r'(?:\: \(' + re.escape(this_example['correct_num']) + r'\)\s{0,1}(.*?))(?=\n\: \([0-9]\.[0-9]{1,2}\)|\n\'\'|\n\{\{|$)', re.DOTALL)
    
    todays_date = (datetime.today()).strftime('%Y%m%d')

    with open('log/{0}_examples.log'.format(todays_date), 'a') as f:
        log_line = ''
        log_line += verified_entry['title']

        log_line += '##' + ('1' if this_example['good_example'] else '0')

        for field in ['verificator', 'example']:
            log_line += '##' + this_example[field]

        s_correct_def = re.search(re_correct_def, verified_entry['definitions'])
        if s_correct_def:
            log_line += '##' + s_correct_def.group(1)
        elif this_example['bad_example'] == True:
            log_line += '##none'
        else:
            error += ';cant_find_correct_def'

        if this_example['orphan']:
            log_line += '##{0}'.format(this_example['orphan'])
        else:
            log_line += '##none'

        if type(this_example['source']) != str:
            #TODO: add 'journal_title' but first check if there will be no conflicts in accesing the logs
            for field in ['authors', 'article_title', 'pub_title', 'date', 'channel', 'domain']:
                if field in this_example['source'] and this_example['source'][field]:
                    log_line += '##{0}'.format(this_example['source'][field])
                else:
                    log_line += '##none'

        if error != '':
            log_line += '##' + error
        else:
            log_line += '##none'

        f.write('\n' + log_line)
        print(log_line)

def add_ref_to_example(example, ref):
    
    #https://regex101.com/r/dW1xU3/4
    #https://pl.wiktionary.org/w/index.php?oldid=4957309#odno.C5.9Bniki_a_interpunkcja
    #https://pl.wiktionary.org/w/index.php?diff=4957513

    #three dots below because 'error: look-behind requires fixed-width pattern'
    re_ref_punctuation = re.compile(r'(.*?)((?<!itp|itd|etc|.\.\.|.\s[A-Z])\.$|$)', re.DOTALL)
    s_ref_punctuation = re.search(re_ref_punctuation, example)

    if type(ref) == str:
        r = ref
    else:
        r = '{{NKJP'
        for field in ref:
            r += '|{0}={1}'.format(field, ref[field])
        r += '}}'

    referenced_example = '\'\'' + s_ref_punctuation.group(1) + '\'\''\
                         + '<ref>' + r + '</ref>'

    if s_ref_punctuation.group(2) != '':
        referenced_example += s_ref_punctuation.group(2)

    return referenced_example

def check_edit_conflicts(verified_entry, page_section):
    fetch_time = datetime.strptime(verified_entry['fetch_time'], '%Y-%m-%dT%H:%M:%SZ')
    re_refs = re.compile(r'(<ref.*?(?:/>|</ref>))')
    
    try: fullpage = pwb.Page(pwb.Site('pl', 'wiktionary'), verified_entry['title'])
    except (pwb.NoPage, IsRedirectPage) as e:
        return 1
    else:
        if fullpage.editTime() > fetch_time:
            new_meanings = re.sub(re_refs, '', page_section.subSections['znaczenia'].text)
            old_meanings = verified_entry['definitions']
            if new_meanings == old_meanings:
                return 0
            else:
                return 1
        else:
            return 0

def add_example_to_page(verified_entry, revid):
        
    try: page = Haslo(verified_entry['title'])
    except (sectionsNotFound, WrongHeader) as e:
        pass
    else:
        if page.type == 3:
            for lang_section in page.listLangs:
                if lang_section.lang == 'polski':

                    changes = False
                    verificators = set()
                    already_added = 0

                    bad_only = [ex['bad_example'] for ex in verified_entry['examples']]
                    if all(bad_only):
                        for ix, ex in enumerate(verified_entry['examples']):
                            log_verification(verified_entry, ix)
                        return 1
                    not_wikified_and_bad_only = [((ex['good_example'] and wikified_proportion(ex['example']) < 0.98) or ex['bad_example']) for ex in verified_entry['examples']]
                    if all(not_wikified_and_bad_only):
                        return 0
                    good_example_indices = [(ex['good_example'] and wikified_proportion(ex['example']) > 0.98) for ex in verified_entry['examples']]
                    if sum(good_example_indices) > 0:
                        lang_section.pola()
                        edit_conflict = check_edit_conflicts(verified_entry, lang_section)

                    for ix, verified_example in enumerate(verified_entry['examples']):
                        if verified_example['bad_example'] == True:
                            log_verification(verified_entry, ix)
                        elif verified_example['good_example'] == True and wikified_proportion(verified_example['example']) > 0.98:
                            if edit_conflict:
                                log_verification(verified_entry, ix, 'edit_conflict')
                                return 0

                            if verified_example['correct_num'] == '':
                                print('{0} - error - no number'.format(verified_entry['title']))
                                continue
                            example_with_ref = add_ref_to_example(verified_example['example'], verified_example['source'])
                            if lang_section.subSections['przykłady'].add_example(verified_example['correct_num'],\
                                                                                 example_with_ref) == -1:
                                already_added = 1
                                continue
                            if 'references' not in lang_section.subSections['źródła'].text:
                                lang_section.subSections['źródła'].text += '\n<references />'
                            lang_section.saveChanges()
                            verificators.add(verified_example['verificator'])
                            changes = True

                    if changes:
                        if len(verificators) > 1:
                            comment = ''
                            for i, ver in enumerate(verificators):
                                if i > 0:
                                    comment += ', '
                                comment += ver
                        else:
                            (only_ver, ) = verificators
                            comment = only_ver

                        page.push(offline=False, myComment='[[Wikisłownik:Dodawanie przykładów|WS:Dodawanie przykładów]]. Źródło przykładu: http://nkjp.pl/. [[Special:Permalink/{0}|Weryfikacja: {1}]]'.format(revid, comment))
                        for i, ex in enumerate(good_example_indices):
                            if ex:
                                log_verification(verified_entry, i)
                        return 1
                    elif already_added == 1:
                        return 1
                    return 0
    
    log_verification(verified_entry, 'not_written_to_page')

def sweep_all_pages():
    
    buffer_size = 20
    site = pwb.Site()
    prefix = 'Wikisłownik:Dodawanie_przykładów/dane/'
    
    with open('output/example_queue.json', 'r') as inp:
        example_queue = json.loads(inp.read())

    for i in range(100):
        page = pwb.Page(site, prefix + '{0:03d}'.format(i))
        page_remaining_examples = check_verifications(page)
        
        if page_remaining_examples != -1:
            while(len(page_remaining_examples) < buffer_size):
                page_remaining_examples.append(example_queue.pop())
                if len(example_queue) == 0:
                    return -1
            
            with open('output/example_queue.json', 'w') as out:
                json_remaining = json.dumps(ordermydict(example_queue), ensure_ascii=False, indent=4)
                json_output = json.dumps(ordermydict(page_remaining_examples), ensure_ascii=False, indent=4)
                out.write(json_remaining)
                page.text = json_output
                page.save(comment='Pobranie nowych przykładów z NKJP.pl')
    
    write_stats_data()
    return 0

from collections import OrderedDict
def ordermydict(words_list):

    newlist = []
    for word in words_list:
        examples_ordered = [OrderedDict(sorted(item.items())) for item in word['examples']]
        newword = OrderedDict()
        for field in sorted(word.keys()):
            if field != 'examples':
                newword.update({field : word[field]})
        newword.update({'examples' : examples_ordered})
        newlist.append(newword)
    return newlist

def wikified_proportion(input_text):
    """
    Calculate the proportion of wikified words in a string. Numbers and
    words starting with a capital letters are ignored — they don't need
    too be wikified on pl.wikt (unless it's a normal word at the beginning
    of a sentence — but there is no reliable way for me now of checking this

    Args:
        input_text (str): wikified text ([[word]]s [[be|are]] [[write|written]]
            [[like]] [[this]])
    Returns:
        float: the proportion of wikified text
    """

    re_nonwords = re.compile(r'([\W0-9]*)', re.UNICODE)
    allwords = input_text.split()
    counted = []
    i = 0
    while (i < len(allwords)):
        a = allwords[i]
        s_nonword = re.search(re_nonwords, a)
        if (s_nonword and s_nonword.group(1) == a) or any(char.isdigit() for char in a):
            #ignore punctuation and numbers
            i += 1
        elif '[[' in a and ']]' in a:
            #these are [[proper]] [[wikified]] [[words]]
            counted.append(a)
            i += 1
        elif '[[' in a:
            #wikified phrases [[can have spaces]] in them - all this loop
            #does is to search for them and merge at the end 
            cache = []
            cache.append(a)
            for j, b in enumerate(allwords[(i+1):]):
                if ']]' in b:
                    counted.append(' '.join(cache) + ' ' + b)
                    i += j + 2
                    break
                elif '[[' in b:
                    counted += cache
                    i += j + 1
                    break
                else:
                    cache.append(b)
        elif a[0].upper() == a[0]:
            #ignore titlecase words
            i += 1
        else:
            counted.append(a)
            i += 1
    
    wikified = [a for a in counted if ('[[' in a and ']]' in a)]
    return len(wikified)/len(counted)
    
def check_verifications(page):
    anon_edit = False

    new_revid = page.latest_revision_id
    
    for a in page.revisions():
        if not anon_edit and a.anon == True:
            anon_edit = True

        if a.user == 'AlkamidBot':
            old_revid = a.revid
            break
    
    #site = pwb.Site()
    #new = json.loads(pwb.Page(site, 'Wikisłownik:Dodawanie przykładów/dane/049').getOldVersion(4953820))
    
    if new_revid != old_revid:
        old = json.loads(page.getOldVersion(old_revid))
        new = json.loads(page.text)
    else:
        return -1
    
    #we can't really get anonymous editors' IP from JS, so this is
    #a way of retrieving them from page history
    if anon_edit:
        for ix, verified_word in enumerate(new):
            for ex_ix, verified_example in enumerate(verified_word['examples']): 
                if verified_example['verificator'] == None:
                    for rev in page.revisions():
                        temp = json.loads(page.getOldVersion(rev.revid))
                        if temp[ix]['examples'][ex_ix]['verificator'] != None:
                            verified_word['examples'][ex_ix]['verificator'] = previous_user
                            break
                        previous_id = rev.revid
                        previous_user = rev.user
                        if rev.revid == old_revid:
                            break

    revised_wordlist = []
    changes_in_list = 0
    
    for verified_word in new:
        found = 0
        for verified_example in verified_word['examples']:
            if (verified_example['good_example'] == True and wikified_proportion(verified_example['example']) > 0.98) or verified_example['bad_example'] == True:
                found = add_example_to_page(verified_word, new_revid)
                changes_in_list += found
                break
        if not found:
            revised_wordlist.append(verified_word)

    if not changes_in_list:
        return -1
    return revised_wordlist
                                                                     
def fetch_active_words():
    page_prefix = 'Wikisłownik:Dodawanie_przykładów/dane/'
    
    active_words = []
    inactive_words = []
    words_in_active_pages = []
    for i in range(100):
        page = pwb.Page(pwb.Site(), page_prefix + '{0:03d}'.format(i))
        text = json.loads(page.text)

        active_page = page.userName() != 'AlkamidBot'

        for j in text:
            found = 0
            if active_page:
                words_in_active_pages.append(j['title'])
            for k in j['examples']:
                if k['good_example'] or k['bad_example']:
                    active_words.append(j['title'])
                    found = 1
                    break
            if not found:
                inactive_words.append(j['title'])

    return {'active': active_words, 'inactive': inactive_words, 'under_review': words_in_active_pages}

def write_edit_conflicts():
    
    todays_date = (datetime.today()).strftime('%Y%m%d')
    conflicts_page = pwb.Page(pwb.Site(), 'Wikisłownik:Dodawanie przykładów/konflikty edycji')

    added = []
    with open('log/' + todays_date + '_examples.log', 'r') as inp:
        for line in inp:
            lsp = line.split('##')
            if len(lsp) > 3:
                if lsp[1] == '1' and 'edit_conflict' in lsp[-1]:
                    added.append(tuple(lsp))

    output = ''
    ref_mapping = {'authors': 6, 'domain': 11, 'channel': 10, 'pub_title': 8, 'date': 9, 'article_title': 7}

    for a in set(added):

        not_in_page = 0
        already_added = 0

        try: page = Haslo(a[0])
        except sectionsNotFound:
            pass
        else:
            if page.type == 3:
                for langsection in page.listLangs:
                    if langsection.lang == 'polski':
                        langsection.pola()
                        #I'm not adding anything to page - this is just a convenient method to check
                        #if an example has already been added to a page
                        not_in_page = langsection.subSections['przykłady'].add_example('1.1', a[3])

                        already_added = 0
                        for line in conflicts_page.text.split('\n'):
                            if not line.startswith('\'\'\'') and not line.startswith('<code>'):
                                if SequenceMatcher(None, dewikify(a[3]), dewikify(line)).ratio() > 0.8:
                                    already_added = 1
                                    break
                        break

        if not_in_page == 1 and already_added == 0:
            ref = {}
            for r in ref_mapping:
                try: val = a[ref_mapping[r]]
                except IndexError:
                    continue
                else:
                    if a[ref_mapping[r]] != 'none':
                        ref[r] = a[ref_mapping[r]]
            output += '\n\n\'\'\'[[{0}]]\'\'\' ({1}) {{{{re|{2}}}}}'.format(a[0], a[4], a[2])
            output += '\n\n{0}'.format(a[3])
            output += '\n\n<code><nowiki>{0}</nowiki></code>'.format(add_ref_to_example(a[3], ref))
    
    conflicts_page.text += output
    conflicts_page.save(comment='aktualizacja - lista wymaga weryfikacji')

def write_stats_data():
    edit_history = read_edit_history()
    
    data_text = 'data = {}\n'
    data_text += 'data[\'pages\'] = { '
    for i in range(100):
        data_text += '\'{0:03d}\', '.format(i)

    data_text = data_text[:-2] + ' }\n'
    data_text += 'data[\'added_examples\'] = {0}\n'.format(edit_history['added_number'])
    data_text += 'data[\'unorphaned\'] = {0}\n'.format(len(set(edit_history['orphans'])))
    data_text += 'data[\'verificators\'] = { '
    for v in edit_history['verificators']:
        data_text += '{"' + v[0] + '", ' + str(v[1]) +'}, '

    data_text = data_text[:-2] + ' }\n'
    data_text += 'return data'
    
    site = pwb.Site()
    output_page = pwb.Page(site, 'Moduł:examplesCheck/data')
    output_page.text = data_text
    output_page.save(comment='Aktualizacja statystyk')

import os
from operator import itemgetter
def read_edit_history():

    added = []
    bad_examples = []
    orphans = []
    verificators = {}

    for file in os.listdir("log"):
        if file.endswith("examples.log"):
            with open('log/' + file, 'r') as inp:
                for line in inp:
                    lsp = line.split('##')
                    if len(lsp) > 3:
                        if lsp[1] == '1' and lsp[-1] == 'none\n':
                            added.append(tuple(lsp))
                            if len(lsp) > 6:
                                if lsp[5] != 'none':
                                    orphans.append(lsp[5])
                        elif lsp[1] == '0':
                            bad_examples.append(dewikify(lsp[2]))

    added_words = []
    for a in set(added):
        added_words.append(a[0])
        verificators[a[2]] = verificators.get(a[2], 0) + 1
    
    return {'added': added_words, 'added_number': len(set(added)),\
        'bad_examples': bad_examples, 'orphans': orphans,\
            'verificators': sorted(verificators.items(), key=itemgetter(1), reverse=True)}
    
from pywikibot import pagegenerators
def verify_added_examples():


    re_exam = re.compile(r'{{przykłady}}(.*?){{składnia}}', re.DOTALL)
    re_num = re.compile(r'(\([0-9]\.[0-9]\))')

  
    pages = pagegenerators.UserContributionsGenerator('AlkamidBot', 0, total=299)
    with open('log/alkadsbot.txt', 'w') as f:
        cnt = 0
        for page in pages:
            revs = page.revisions()
            
            for rev in revs:
                if rev.user == 'AlkamidBot':
                    przy = re.search(re_exam, page.getOldVersion(rev.revid))
                    if przy:
                        nr = re.findall(re_num, przy.group(1))
                        cnt += len(nr)
                        f.write(page.title() + '\t{0}'.format(len(nr)) + '\n')
                    break


import urllib.request
from lxml import html
def refresh_orphans_list():

    with urllib.request.urlopen('http://tools.wmflabs.org/alkamidbot/porzucone.html') as response,\
         open('input/orphans.txt', 'w') as orphans:
        t = html.parse(response)
        for a in t.iter('a'):
            text = a.text_content()
            orphans.write(text + '\n')


def check_if_includes_orphan(sentence, orphan_list, excluded_orphans):
    re_base_form = re.compile(r'\[\[(.*?)(?:\||\]\])')
    allwords = re.findall(re_base_form, wikilink(sentence[0] + sentence[2]))
    for word in allwords:
        if ' się' in word:
            word = word[:-4]
        if '\n*{0}\n'.format(word) in orphan_list and word not in excluded_orphans:
            return word
    return None


import random
def orphaned_examples(test_word=None, online=False, complete_overwrite=False, onepage_testmode=False):

    output_pages_number = 100
    buffer_size = 20 #how many words will be printed on one page
    if online:
        active_words = fetch_active_words() # prepare only as many pages as we need at the moment
    else:
        active_words = {'active': [], 'inactive': [], 'under_review': []}

    edit_history = read_edit_history()
    excluded_words =  active_words['active'] + edit_history['added']

    with open('output/empty_sections.txt', 'r') as g:
        empty_sections = g.readlines()
        random.shuffle(empty_sections)

    if not complete_overwrite:
        excluded_words += active_words['inactive']
    else:
        excluded_words += active_words['under_review']
    
    site = pwb.Site()

    # this is a dirty trick, because morfAnalyse() and wikilink() don't
    # really work as they should. The following regex extracts the first part
    # of [[these|links]]
    re_base_form = re.compile(r'\[\[(.*?)(?:\||\]\])')


    words_count = 0
    with open('input/orphans.txt') as f,\
    open('output/empty_sections.txt', 'r') as g:

        # list of pages with no examples (obtained by empty_section.py)
        orphans = f.read()
        
        # for testing purposes
        if test_word:
            empty_sections = [test_word]

        pages_count = 666 if onepage_testmode else 0 #loop helper
        output = [] #list-container for examples

        for input_word in empty_sections:
            
            if complete_overwrite == False and words_count > 2*len(active_words['active']):
                with open('output/example_queue.json', 'w') as o:
                    formatted_output = json.dumps(ordermydict(output), ensure_ascii=False, indent=4)
                    o.write(formatted_output)
                return 2
            
            if (pages_count == output_pages_number+1) or (pages_count == 667 and onepage_testmode):
                return 0

            # dealing with various list formats, e.g. *[[word]]
            input_word = input_word.strip('*[]\n')
            if len(input_word) < 4 or input_word.upper == input_word:
                continue

            if input_word in excluded_words:
                continue

            print(input_word)

            if complete_overwrite:
            # write to file/page every N words
                if len(output) == buffer_size:
                    formatted_output = json.dumps(ordermydict(output), ensure_ascii=False, indent=4)

                    if online:                        
                        while(True):
                            output_page = pwb.Page(site, 'Wikisłownik:Dodawanie przykładów/dane/{0:03d}'.format(pages_count))
                            if pages_count == 666 or output_page.userName() == 'AlkamidBot':
                                output_page.text = formatted_output
                                output_page.save(comment='Pobranie nowych przykładów z NKJP.pl')
                                break
                            else:
                                pages_count += 1
                                if pages_count == output_pages_number:
                                    return 0
                            

                    with open('output/json_examples_{0}.json'.format(pages_count), 'w') as o:
                        o.write(formatted_output)
                        pages_count += 1
                        output = []


            if input_word[0] == '-' or input_word[-1] == '-' or input_word[0].isupper():
                continue # let's skip prefixes and sufixes for now, also whatever starts with a capital leter

            query = '({0}**)'.format(input_word).replace(' ', '** ')
            query_escaped = query.replace('.', '\.')
            result = nkjp_lookup_new(query_escaped, 50)
            #print(xml.dom.minidom.parseString(etree.tostring(root)).toprettyxml())
            #return -1
            if result['spanResponse']['numFound'] != 0:
                found = 0
                found_orphan = 0

                defs = get_definitions(input_word)
                if defs == 0:
                    continue

                new_word = ExampleDict()
                new_word['title'] = input_word
                new_word['fetch_time'] = str(defs[1])
                new_word['definitions'] = defs[0]

                for line in result['spanResponse']['spans']:
                    doc = result['response']['docs'][line['doc_seq']]

                    matched_sentence = NKJP_to_text(line['lTks'], line['mTks'], line['rTks'])
                    left_context = get_left_context(line, doc)
                    sentence =  left_context + ' ' + matched_sentence
                    
                    matched_tag = line['mTks'][0].split('|')[2][2:]

                    # NKJP treats gerunds as verb forms. We don't
                    if '\'\'czasownik' in new_word['definitions'] and\
                       ('ger:' in matched_tag or 'subst:' in matched_tag):
                        continue

                    if check_sentence_quality(line) == 0:
                        continue
                    
                    ref = get_reference(doc)
                    if ref == '':
                        break

                    if len(new_word['examples']) < 2:
                        temp_example = {'verificator': 'None', 'correct_num': 'None', 'good_example': False, 'bad_example': False}
                        #temp_example['left'] = line.find('left').text
                        #temp_example['right'] = line.find('right').text
                        temp_example['example'] = wikitext_one_sentence(left_context, line, input_word)
                        #temp_example['left_extra'] = phrases_wikilink(wikilink(sentence[3]))
                        #temp_example['right_extra'] = phrases_wikilink(wikilink(sentence[4]))
                        temp_example['source'] = ref
 
                        orphan_switch = check_if_includes_orphan(sentence, orphans, edit_history['orphans'])
                        temp_example['orphan'] = orphan_switch
                        new_word['examples'].append(temp_example)

                    else:
                        
                        found_new = 0
                        wikified_example = wikitext_one_sentence(left_context, line, input_word)

                        for ex_ix, ex in enumerate(new_word['examples']):
                            neworphan = check_if_includes_orphan(sentence, orphans, edit_history['orphans'])
                            if neworphan:
                                if ex['orphan']:
                                    if wikified_proportion(ex['example']) < wikified_proportion(wikified_example):
                                        new_example = new_word['examples'][ex_ix]
                                        found_new = 1
                                        orphan_switch = neworphan
                                        break
                                elif not orphan_switch:
                                    new_example = new_word['examples'][ex_ix]
                                    found_new = 1
                                    break
                            else:
                                if not ex['orphan']:
                                    if wikified_proportion(ex['example']) < wikified_proportion(wikified_example):
                                        new_example = new_word['examples'][ex_ix]
                                        found_new = 1
                                        break
                            
                        if found_new:
                            new_example['orphan'] = neworphan
                            #new_example['left'] = line.find('left').text
                            #new_example['right'] = line.find('right').text
                            new_example['example'] = wikitext_one_sentence(left_context, line, input_word)
                            #new_example['left_extra'] = phrases_wikilink(wikilink(sentence[3]))
                            #new_example['right_extra'] = phrases_wikilink(wikilink(sentence[4]))
                            new_example['source'] = ref

                if new_word and len(new_word['examples']) > 0:
                    output.append(new_word)
                    words_count += 1
                    if test_word:
                        with open('output/test_word.json', 'w') as o:
                            formatted_output = json.dumps(ordermydict(output), ensure_ascii=False, indent=4)
                            o.write(formatted_output)
                


if __name__ == '__main__':
    refresh_orphans_list()
    orphaned_examples(test_word=None, online=False, complete_overwrite=True, onepage_testmode=False)
    if orphaned_examples(test_word=None, online=True, complete_overwrite=False, onepage_testmode=False) == 2:
        sweep_all_pages()
        write_edit_conflicts()
        #refresh all pages on Monday
        if datetime.today().weekday() == 4:
            orphaned_examples(test_word=None, online=True, complete_overwrite=True, onepage_testmode=False)
