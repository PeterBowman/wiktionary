#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators
import re
from pywikibot import xmlreader
import collections
from klasa import *
	
def rzeczownikRodzajNiepotrzebny(data):

	data_slownie = data[6] + data[7] + u'.' + data[4] + data[5] + u'.' + data[0] + data[1] + data[2] + data[3]
	lista_stron = getListFromXML(data)
	wikt = pywikibot.Site('pl', 'wiktionary')
	outputPage = pywikibot.Page(wikt, u'Wikipedysta:AlkamidBot/listy/rodzaj_niepotrzebny')
	noGenderPage = pywikibot.Page(wikt, u'Wikipedysta:AlkamidBot/listy/rodzaj/wykluczone')
	
	re_excluded = re.compile(ur'Lista języków, w których rzeczowniki nie mają rodzaju. Jeśli wiesz o takim, dopisz go do poniższej listy, a bot nie będzie uwzględniał go w tworzeniu listy:\n\n(.*)', re.DOTALL)
	s_excluded = re.search(re_excluded, noGenderPage.get())
	noGenderList = s_excluded.group(1).split(u'\n')
	for a in noGenderList:
		a = a.strip()

	tempLangs = []
	
	notFound = []
	text = u'Lista słów, w których w sekcji "znaczenia" występuje "rzeczownik" i "rodzaj", mimo że w danym języku nie ma rodzajów. Dane z %s. Jeśli znasz język, w którym rzeczowniki nie mają rodzaju, dodaj go [[Wikipedysta:AlkamidBot/listy/rodzaj/wykluczone|tutaj]].\n' % (data_slownie)
	foundList = collections.defaultdict(list)
	
	LangsMediaWiki = getAllLanguages()

	for a in lista_stron:
		try: word = Haslo(a)
		except notFromMainNamespace:
			pass
		except sectionsNotFound:
			pass
		except WrongHeader:
			pass
		else:
			if word.type == 3:
				for lang in word.listLangs:
					if lang.type != 2:
						lang.pola()
						if lang.type == 1 and lang.znaczeniaDetail:
							for d in lang.znaczeniaDetail:
								if (u'rzeczownik' in d[0]) and (u'rodzaj' in d[0]):
									foundList[u'%s' % lang.lang].append(lang.title)
													
	for a in noGenderList:
		if foundList[a]:
			text += u'== %s ==' % (a)
			for b in foundList[a]:
				text += u'\n*[[%s]]' % (b)
			text += u'\n'

	file = open('output/rodzaj_niepotrzebny.txt', 'w')
	file.write(text.encode( "utf-8" ))
	file.close
	
        outputPage.text(text)
	outputPage.save(comment=u"Aktualizacja listy", botflag=False)
