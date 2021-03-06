#!/usr/bin/python
# -*- coding: utf-8 -*-

import codecs
import pywikibot as pwb
import re
from klasa import *
import config


# the list of words that are ignored in all frequency lists
def getDeletedList():
    deleted = set()
    site = pwb.Site()
    pageDeleted = pwb.Page(site, 'Wikisłownik:Ranking brakujących tłumaczeń/zawsze usuwane')
    for line in pageDeleted.get().split('\n'):
        if line[0] == ':':
            lineList = line.split('[[')
            deleted.add(lineList[1].strip(']'))
    return deleted

def frequencyList(date):

    site = pwb.Site()
    lista_stron2 = getListFromXML(date)
    ranking = {}
    re_example_translation = re.compile('→(.*?)(?=\<ref|\n|$)')
    re_colloc_translation = re.compile('→(.*?)(?=\<ref|\n|•|;|$)')
    re_link = re.compile('\[\[([^\:]*?)(?=\]\]|\||#pl)')
    alltitles = set()

    deleted = getDeletedList()

    i = 1
    for a in lista_stron2:
        alltitles.add(a.title)
        if 'Wikipedysta:AlkamidBot' not in a.title:
            try: h = Haslo(a)
            except sectionsNotFound:
                pass
            except WrongHeader:
                pass
            else:
                if h.type == 3:
                    to_search = ''
                    for sekcja in h.listLangs:
                        sekcja.pola()
                        if sekcja.type not in (2,4,5,7,11):
                            if sekcja.lang == 'polski' or sekcja.lang == 'termin obcy w języku polskim':
                                for elem in ('dodatki', 'znaczenia', 'przykłady', 'składnia', 'kolokacje', 'synonimy', 'antonimy', 'pokrewne', 'frazeologia', 'etymologia', 'uwagi'):
                                    to_search += sekcja.subSections[elem].text

                            else:
                                s_example_translation = None
                                s_colloc_translation = None

                                if '→' in sekcja.subSections['przykłady'].text:
                                    s_example_translation = re.findall(re_example_translation, sekcja.subSections['przykłady'].text)
                                if s_example_translation:
                                    for a in s_example_translation:
                                        to_search += a
                                if '→' in sekcja.subSections['kolokacje'].text:
                                    s_colloc_translation = re.findall(re_colloc_translation, sekcja.subSections['kolokacje'].text)
                                if s_colloc_translation:
                                    for a in s_colloc_translation:
                                        to_search += a

                                to_search = to_search + sekcja.subSections['znaczenia'].text

                    s_link = re.findall(re_link, to_search)
                    for link in s_link:
                        if '#' not in link and link not in deleted: #if there is a hash in the link, it is not '#pl' (excluded in regex), therefore not a Polish link; also, exlude words from deleted list
                            try: ranking[link]
                            except KeyError:
                                ranking[link] = 1
                            else:
                                ranking[link] += 1


    dictlist = []
    for key, value in ranking.items():
        temp = [key,value]
        dictlist.append(temp)

    def sortkey(row):
        return float(row[1])

    dictlist.sort(key=sortkey, reverse=True)

    htmllist = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"\n"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml\nxml:lang="pl">\n<head>\n<meta http-equiv="content-type" content="text/html; charset=UTF-8" />\n</head><body>'

    alltext = []

    for i in range(5):
        alltext.append('')

    i = 0
    for elem in dictlist:
        if i>20000:
            break
        htmllist += '\n%s=%d' % (elem[0], elem[1])
        if i<10000:
            alltext[i//2000] += '\n[[%s]]=%d' % (elem[0], elem[1])
        i+= 1

    dictlist = [s for s in dictlist if s[0] not in alltitles]

    nonExistingText = ''
    for elem in dictlist:
        nonExistingText += '\n%s=%d' % (elem[0], elem[1])

    nonExistingText = nonExistingText.strip()

    for num, elem in enumerate(alltext):
        elem = elem.strip()
        outputPage = pwb.Page(site, 'Indeks:Polski - Najpopularniejsze słowa %d-%d' % (num*2000+1, (num+1)*2000))
        elem = 'Lista frekwencyjna języka polskiego na podstawie odnośników na stronach Wikisłownika.\n\n{{język linków|polski}}\n' + elem + '\n[[Kategoria:Polski (słowniki tematyczne)]]\n[[Kategoria:Listy frekwencyjne|polski]]'
        outputPage.text = elem
        outputPage.save(comment='aktualizacja')

    htmllist += '</body></html>'
    with open('%spublic_html/frequencyListPL.html' % (config.path['home']), encoding='utf-8', mode='w') as f:
        f.write(htmllist)

    with open('%soutput/frequencyListPL.txt' % (config.path['scripts']), encoding='utf-8', mode='w') as f:
        f.write(nonExistingText)

#if __name__ == "__main__":
#    frequencyList('20141024')
