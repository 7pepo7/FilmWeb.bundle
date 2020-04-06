# -*- coding: utf-8 -*-
import time, urllib, re, unicodedata
import json

FILMWEB = 'http://www.filmweb.pl'
FILMWEB_SEARCH = 'http://www.filmweb.pl/search/film?q=%s&startYear=%s&endYear=%s&startRate=&endRate=&startCount=&endCount=&sort=TEXT_SCORE&sortAscending=false'

class FilmWebStandaloneAgent(Agent.Movies):
	name = 'FilmWeb.pl'
	languages = [Locale.Language.Polish]
	primary_provider = True
	accepts_from = ['com.plexapp.agents.localmedia']

	def search(self, results, media, lang):

		def remove_accents(tekst):
			pol_acc = {'\xc4\x84': 'A', '\xc4\x86': 'C', '\xc4\x98': 'E', '\xc5\x81': 'L', '\xc5\x83': 'N', '\xc3\x93': 'O',
					   '\xc5\x9a': 'S', '\xc5\xb9': 'Z', '\xc5\xbb': 'Z', '\xc4\x85': 'a', '\xc4\x87': 'c', '\xc4\x99': 'e',
					   '\xc5\x82': 'l', '\xc5\x84': 'n', '\xc3\xB3': 'o', '\xc5\x9b': 's', '\xc5\xba': 'z', '\xc5\xbc': 'z'}
			for x in pol_acc.keys():
				tekst = tekst.replace(x, pol_acc[x])

			return tekst
			
		search_name = media.name
		search_name = remove_accents(search_name)
		search_name = search_name.replace(' ', '+')
		search_name = unicodedata.normalize('NFD', unicode(search_name)).encode('ascii', 'ignore')
		#search_name = unicodedata.normalize('NFKD', unicode(search_name)).encode('ascii', 'ignore') 

		Log("search_name: " + search_name)
    
		search_years = int(Prefs['searchYears'])
    
		if media.year:
			search_url = FILMWEB_SEARCH % (search_name, str(int(media.year) - search_years), str(int(media.year) + search_years))
		else:
			search_url = FILMWEB_SEARCH % (search_name, str(1900), str(Datetime.Now().year))
	
		search_filmweb_result = HTML.ElementFromURL(search_url, 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
		   
		#mine = []
		movies_list = search_filmweb_result.xpath("//ul[@class='resultsList hits']")
 
		if not movies_list:
			Log('filmweb.pl - nothing found')
			return 1
		else:
			Log('filmweb.pl - found')
    
		trust_score = 100
		order_num = 0
		for movie in movies_list[0].xpath("./li"):
			score_penalty = 0
	
			#YEAR
			try:
				#year = int(movie.xpath(".//div[contains(@class, 'filmPreview filmPreview--FILM Film')]/@data-release")[0][:4])	# pierwszy sposob
				year = int(movie.xpath(".//span[contains(@class, 'filmPreview__year')]/text()")[0])
			except:
				year = 0
			if year and media.year:
				score_penalty += abs(int(media.year) - year) * 4
				
			Log("Year: " + str(year))
			#TITLE
			el = movie.xpath(".//h3[contains(@class, 'filmPreview__title')]/text()")
			if (el):
				polish_title = el[0]
			else:
				polish_title = ''
			el = movie.xpath(".//div[contains(@class, 'filmPreview__originalTitle')]/text()")
			if el:
				original_title = el[0]
			else:
				original_title = polish_title			
			
			Log("Original title: " + original_title)
			Log("Polish title: " + polish_title)
			
			s1 = Util.LevenshteinDistance(media.name, polish_title)
			s2 = Util.LevenshteinDistance(media.name, original_title)
			if s1 < s2:
				score_penalty += s1
			else:
				score_penalty += s2
				
			name = polish_title
			if name == '':
				name = original_title
			Log("NAME: " + name)        
			#SCORE
			score = 100 - score_penalty
			for i in range(len(results)):
				if score == results[i].score:
					score = score - 1
          
			if Prefs['firstPlaceBonus']:
				if order_num == 0:
					score = score + 20
				else:
					score = score - (order_num * 20)
				order_num = order_num + 1
                
			if Prefs['overrideFilmWebOrder']:
				score = trust_score
				trust_score = trust_score - 5
          
			Log("Score: " + str(score))
			#ID
			id_string = movie.xpath("string(.//a[contains(@class, 'filmPreview__link')]/@href)")
			id_string.replace(FILMWEB, '') # niektore zawieraja sam tytul np. www.filmweb.pl/Auta
			id = id_string.encode('hex')
			Log("ID: " + str(id))
			#mine.append((name, year, score))
			results.Append(MetadataSearchResult(id=id, name=name, year=year, score=score, lang=lang))
				

	def update(self, metadata, media, lang): 
		proxy = Proxy.Preview
		
		movie_id = metadata.id.decode('hex')
		
		info_filmweb_result = HTML.ElementFromURL(FILMWEB + movie_id, 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
		
		#TITLE
		metadata.title = media.title
		Log("TITLE: " + metadata.title)

		# TAGLINE
		tagline = ""
		try:
			tagline = info_filmweb_result.xpath("//div[@class='filmPosterSection__plot']")[0].text
			metadata.tagline = tagline
		except:
			pass
		Log("TAGLINE: " + tagline)

		# SUMMARY
		overview = ""
		try:
			overview = info_filmweb_result.xpath("//span[@class='filmDescriptionSection__moreText hide']")[0].text
			metadata.summary = overview
		except:
			pass
		Log("SUMMARY: " + overview)

		# RELEASE DAY, RATING, ORIGINAL TITLE
		original_title = ''
		release_day = ''
		rate = 0
		try:
			film_data_basic = info_filmweb_result.xpath("//script[@type='application/json' and @id='filmDataBasic']")[0].text
			json_data = json.loads(film_data_basic)
			original_title = json_data.get('originalTitle', '')

			film_data_ratings = info_filmweb_result.xpath("//script[@type='application/json' and @id='filmDataRating']")[0].text
			json_data = json.loads(film_data_ratings)
			rate = round(float(json_data.get('rate', 1)), 1)
			release_day = json_data.get('releaseWorldString', '')

			metadata.original_title = original_title

			if release_day != '':
				metadata.year = int(release_day[:4])
				metadata.originally_available_at = Datetime.ParseDate(release_day).date()

			metadata.rating = rate
			metadata.rating_image = "http://2.fwcdn.pl/gf/iri-static/logo.310.png"
			Log("RATE: " + str(rate))
		except err:
			Log("Film data get error: {}".format(err))
			metadata.original_title = metadata.title

		Log("ORGINAL TITLE: " + original_title)
		Log("RELEASE DAY: " + release_day)
		Log("RATE: " + str(rate))

		# GENRES, COUNTRIES
		info = info_filmweb_result.xpath("//div[@class='filmInfo__info']/span/a")
		for i in info:
			if 'genres' in i.get('href'):
				metadata.genres.add(i.text)
				Log("GENRE: " + i.text)
			if 'countries' in i.get('href'):
				metadata.countries.add(i.text)
				Log("COUNTRY: " + i.text)

		# ACTORS
		actors_url = "{}{}/cast/actors".format(FILMWEB, movie_id)
		info_filmweb_actors_result = HTML.ElementFromURL(actors_url)
		metadata.roles.clear()

		for person_list in info_filmweb_actors_result.xpath(".//div[@class = 'filmFullCastSection__item castRoleListElement ']"):

			person_image = person_list.xpath(".//img[@class = 'simplePoster__image']/@data-src")
			if person_image is not None and len(person_image) > 0:
				person_image = person_image[0]

			person_info_name = person_list.xpath(".//div[@class = 'castRoleListElement__info']/a/text()")
			if person_info_name is not None and len(person_info_name) > 0:
				person_info_name = person_info_name[0]

			person_info_role = person_list.xpath(".//div[@class = 'castRoleListElement__info']/span/text()")
			if person_info_role is not None and len(person_info_role) > 0:
				person_info_role = person_info_role[0]

			person_profession = person_list.xpath(".//div[@class = 'personRole roleSource ']/@data-profession")

			if person_profession is not None and len(person_profession) > 0:
				if person_profession[0] == 'actors':
					role = metadata.roles.new()
					role.role = person_info_role
					role.name = person_info_name
					role.photo = person_image

		# DIRECTORS, WRITERS
		crew_url = "{}{}/cast/crew".format(FILMWEB, movie_id)
		info_filmweb_crew_result = HTML.ElementFromURL(crew_url)

		metadata.directors.clear()
		metadata.writers.clear()
		for person_element in info_filmweb_crew_result.xpath("//div[@class = 'personRole roleSource ']"):
			if person_element.get('data-profession') == 'director':
				metadata.directors.new().name = person_element.get('data-person')
			elif person_element.get('data-profession') == 'screenwriter':
				metadata.writers.new().name = person_element.get('data-person')

		# MAIN POSTER
		# TODO: setPoster("http://1.fwcdn.pl/po/19/57/731957/7751671.0.jpg")

		# OTHER POSTERS
		info_filmweb_posters_result = HTML.ElementFromURL(FILMWEB + movie_id + '/posters', 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
    
		#del metadata.posters
		if Prefs['delthumb']:
			for x in range(len(metadata.posters)):
				for item in metadata.posters:
					t = item
					break
				del metadata.posters[t]  
         
		num_posters = Prefs['numthumb']
		i = 0
		sort = 1
		for posters in info_filmweb_posters_result.xpath(".//img[@class = 'simplePoster__image']/@data-src"):
			try:
				poster_url = posters.replace('6.jpg', '3.jpg')
				poster = HTTP.Request(poster_url)
				metadata.posters[poster_url] = proxy(poster, sort_order = sort)
				sort = sort + 1
				i = i + 1
				Log("POSTER: " + poster_url) 
				if i == int(num_posters):
					break
			except:
				pass
        
		#ART (BACKGROUND)
		info_filmweb_art_result = HTML.ElementFromURL(FILMWEB + movie_id + '/photos', 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
    
		#del metadata.posters
		if Prefs['delthumb']:
			for x in range(len(metadata.art)):
				for item in metadata.art:
					t = item
					break
				del metadata.art[t]  
    
		num_arts = Prefs['numthumb']
		i = 0
		sort = 1
		for arts in info_filmweb_art_result.xpath(".//ul[@class='gallery__photos-list grid']/li/a[1]/@data-photo"):
			try:
				i = i + 1
				art_url = arts
				art = HTTP.Request(art_url)
				metadata.art[art_url] = proxy(art, sort_order=sort)
				sort = sort + 1
				Log("ART: " + art_url)  
				if i == int(num_arts):
					break
			except:
				Log('PHOTOLIST PASS')
				pass
    		
		# #TRIVIA
		# trivia = ''
		# info_filmweb_trivia_result = HTML.ElementFromURL(FILMWEB + movie_id + '/trivia', 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
		# for trivias in info_filmweb_trivia_result.xpath(".//div[contains(@class, 'filmCuriosities')]//ul/li/p"):
		# 	try:
		# 		trivia += trivias.text_content().strip() + ' *** '
		# 	except:
		# 		pass
		# metadata.trivia = trivia[:-5]
		# Log("TRIVIA: " + metadata.trivia)
