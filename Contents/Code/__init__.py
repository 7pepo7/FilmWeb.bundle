# -*- coding: utf-8 -*-
import time, urllib, re, unicodedata

FILMWEB = 'http://www.filmweb.pl'
FILMWEB_SEARCH = 'http://www.filmweb.pl/search/film?q=%s&startYear=%s&endYear=%s&startRate=&endRate=&startCount=&endCount=&sort=TEXT_SCORE&sortAscending=false'

class FilmWebStandaloneAgent(Agent.Movies):
	name = 'FilmWeb.pl'
	languages = [Locale.Language.Polish]
	primary_provider = True
	accepts_from = ['com.plexapp.agents.localmedia']

	def search(self, results, media, lang):

		search_name = media.name.replace(' ', '+')
		search_name = unicodedata.normalize('NFD', unicode(search_name)).encode('ascii', 'ignore')

		Log("search_name: " + search_name);
    
		search_years = int(Prefs['searchYears']);
    
		if media.year:
			search_url = FILMWEB_SEARCH % (search_name, str(int(media.year) - search_years), str(int(media.year) + search_years))
		else:
			search_url = FILMWEB_SEARCH % (search_name, str(1900), str(Datetime.Now().year))
	
		search_filmweb_result = HTML.ElementFromURL(search_url, 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
		   
		#mine = []
		movies_list = search_filmweb_result.xpath("//ul[@class='resultsList hits']");
 
		if not movies_list:
			Log('filmweb.pl - nothing found')
			return 1;
		else:
			Log('filmweb.pl - found')
    
		trust_score = 100;
		order_num = 0;
		for movie in movies_list[0].xpath("./li"):
			score_penalty = 0
	
			#YEAR
			try:
				year = int(movie.xpath(".//span[contains(@class, 'filmPreview__year')]/text()")[0])
			except:
				year = 0;
			if year and media.year:
				score_penalty += abs(int(media.year) - year) * 4
				
			Log("Year: " + str(year));
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
			Log("Polish title: " + polish_title);
			
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
          
			Log("Score: " + str(score));
			#ID
			id_string = movie.xpath("string(.//a[contains(@class, 'filmPreview__link')]/@href)")
			id_string.replace(FILMWEB, '') # niektore zawieraja sam tytul np. www.filmweb.pl/Auta
			id = id_string.encode('hex')
			Log("ID: " + str(id));
			#mine.append((name, year, score))
			results.Append(MetadataSearchResult(id=id, name=name, year=year, score=score, lang=lang))
				

	def update(self, metadata, media, lang): 
		proxy = Proxy.Preview
		
		movie_id = metadata.id.decode('hex')
		
		info_filmweb_result = HTML.ElementFromURL(FILMWEB + movie_id, 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
		
		#TITLE
		metadata.title = media.title
		Log("TITLE: " + metadata.title)			
		
		#SUMMARY 
		overview = ""       
		try:
			overview = info_filmweb_result.xpath("string(.//div[contains(@class, 'filmMainDescription')]/p[contains(@itemprop, 'description')])").replace(u"... wi\u0119cej", "")
			metadata.summary = overview
		except:
			pass 
		Log("SUMMARY: " + str(overview));
    
		#TAGLINE 
		tagline = ""       
		try:
			tagline = info_filmweb_result.xpath(".//div[contains(@class, 'filmPlot')]/p")[0].text      
			try:
				tagline += info_filmweb_result.xpath(".//div[contains(@class, 'filmPlot')]/p/span")[0].text
			except:      
				pass
			metadata.tagline = tagline
		except:
			pass 
		Log("TAGLINE: " + str(tagline));
		
		#RELEASE DAY
		release_day = info_filmweb_result.xpath("string(//div[contains(@class, 'filmMainHeaderParent')]/div['filmMainHeader']/span[@itemprop='datePublished']/@content)")
		Log("RELEASE DAY: " + release_day)

		if release_day != '':
			metadata.year = int(release_day[:4])
			metadata.originally_available_at = Datetime.ParseDate(release_day).date()		
			
		#RATING
		try:
			vote_script = info_filmweb_result.xpath(".//script[contains(., 'filmVoteRatingPanelWrapper')]")[0].text_content()
			rate = re.search(r"communityRateInfo:\"(...)\"", vote_script).group(1)
			rate = rate.replace(',','.')
			metadata.rating = round(float(rate), 2)
			metadata.rating_image = "http://2.fwcdn.pl/gf/iri-static/logo.310.png"
			Log("RATE: " + rate);
		except:
			pass
		
		#ORIGINAL TITLE
		try:
			setfilm_script = info_filmweb_result.xpath("string(//div[contains(@class, 'filmMainHeaderParent')]/div['filmMainHeader']/script)")
			original_title = re.search(r"originalTitle:\"(.+?)\"", setfilm_script).group(1)
			
			metadata.original_title = original_title
			Log("ORIGINAL TITLE: " + original_title)
		except:
			Log("ORIGINAL TITLE: Error getting original title")
			metadata.original_title = metadata.title
			pass
		
		#COUNTRIES
		metadata.countries.clear()
		for countries in info_filmweb_result.xpath(".//div[contains(@class, 'filmInfo')]//th[text()=starts-with(.,'produkcja')]/parent::tr//a"):
			try:
				country = countries.text_content().strip()
				metadata.countries.add(country)
				Log("COUNTRY: " + country);
			except:
				pass
					
		#GENRES
		metadata.genres.clear()
		for genres in info_filmweb_result.xpath(".//div[contains(@class, 'filmInfo')]//th[text()=starts-with(.,'gatunek')]/parent::tr//a"):
			try:
				genre = genres.text_content().strip()
				metadata.genres.add(genre)
				Log("GENRE: " + genre);
			except:
				pass
		
		#ACTORS
		metadata.roles.clear()
		for actors in info_filmweb_result.xpath(".//table[contains(@class, 'filmCast')]//tr[starts-with(@id, 'role')]"):
			try:
				role = metadata.roles.new()
				role.role = actors.xpath(".//td")[3].xpath(".//span[contains(@itemprop, 'characterName')]/span")[0].text_content()
				role.name = actors.xpath(".//td/a")[1].text_content()
				role.photo = actors.xpath(".//td")[0].xpath(".//img")[0].get('src').replace('2.jpg','1.jpg')
				Log("ACTOR: " + role.name + " AS " + role.role);        
			except:
				pass
			
		#DIRECTORS
		crew_page = None
		metadata.directors.clear()
		directors_links = info_filmweb_result.xpath(".//div[contains(@class, 'filmInfo')]//th[text()=starts-with(.,'re')]/parent::tr//a/@href")
		if len(directors_links) > 0 and str(directors_links[-1]).startswith('/film'):
			# get directors from crew page
			crew_url = FILMWEB + str(directors_links[-1]).replace('#director', '')
			info_filmweb_crew_result = HTML.ElementFromURL(crew_url, 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)

			for director in info_filmweb_crew_result.xpath("//form/h2[starts-with(text(), 're')]/following-sibling::div[1]/table/tr/td/a[starts-with(@href, '/person') and @title]/@title"):
				metadata.directors.new().name = director.strip()
				Log("DIRECTOR: " + director.strip())
			pass
		else:
			for directors in info_filmweb_result.xpath(".//div[contains(@class, 'filmInfo')]//th[text()=starts-with(.,'re')]/parent::tr//a"):
				try:
					director = directors.text_content().strip()
					metadata.directors.new().name = director
					Log("DIRECTOR: " + director)
				except:
					pass		
				
		
		#WRITERS
		metadata.writers.clear()
		writers_links = info_filmweb_result.xpath(".//div[contains(@class, 'filmInfo')]//th[text()=starts-with(.,'sce')]/parent::tr//a/@href")
		if len(writers_links) > 0 and str(writers_links[-1]).startswith('/film'):
			# get writers from crew page
			if crew_page is None:
				crew_url = FILMWEB + str(writers_links[-1]).replace('#screenwriter', '')
				info_filmweb_crew_result = HTML.ElementFromURL(crew_url, 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)

			for writer in info_filmweb_crew_result.xpath("//form/h2[starts-with(text(), 'sce')]/following-sibling::div[1]/table/tr/td/a[starts-with(@href, '/person') and @title]/@title"):
				metadata.writers.new().name = writer.strip()
				Log("WRITER: " + writer.strip())
			pass
		else:
			for writers in info_filmweb_result.xpath(".//div[contains(@class, 'filmInfo')]//th[text()=starts-with(.,'sce')]/parent::tr//a"):
				try:
					writer = writers.text_content().strip()
					metadata.writers.new().name = writer
					Log("WRITER: " + writer)
				except:
					pass		

		#POSTERS
		info_filmweb_posters_result = HTML.ElementFromURL(FILMWEB + movie_id + '/posters', 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
    
		#del metadata.posters
		if Prefs['delthumb']:
			for x in range(len(metadata.posters)):
				for item in metadata.posters:
					t = item
					break;
				del metadata.posters[t]  
         
		num_posters = Prefs['numthumb'];
		i = 0;
		sort = 1
		for posters in info_filmweb_posters_result.xpath(".//ul[contains(@class, 'postersList')]/li"):
			try:
				poster_url = posters.xpath(".//img")[0].get('src').replace('2.jpg','3.jpg')
				poster = HTTP.Request(poster_url)
				metadata.posters[poster_url] = proxy(poster, sort_order = sort)
				sort = sort + 1
				i = i + 1
				Log("POSTER: " + poster_url) 
				if i == int(num_posters):
					break;        
			except:
				pass
        
		#ART (BACKGROUND)
		info_filmweb_art_result = HTML.ElementFromURL(FILMWEB + movie_id + '/photos', 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
    
		#del metadata.posters
		if Prefs['delthumb']:
			for x in range(len(metadata.art)):
				for item in metadata.art:
					t = item
					break;
				del metadata.art[t]  
    
		num_arts = Prefs['numthumb'];
		i = 0;
		sort = 1
		for arts in info_filmweb_art_result.xpath(".//ul[contains(@class, 'photosList')]/li"):
			try:
				i = i + 1
				art_url = arts.xpath(".//img")[0].get('src').replace('2.jpg','1.jpg')
				art = HTTP.Request(art_url)
				metadata.art[art_url] = proxy(art, sort_order = sort)
				sort = sort + 1
				Log("ART: " + art_url)  
				if i == int(num_posters):
					break;       
			except:
				pass
    		
		#TRIVIA
		trivia = ''
		info_filmweb_trivia_result = HTML.ElementFromURL(FILMWEB + movie_id + '/trivia', 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
		for trivias in info_filmweb_trivia_result.xpath(".//div[contains(@class, 'filmCuriosities')]//ul/li/p"):      
			try:
				trivia += trivias.text_content().strip() + ' *** '
			except:
				pass
		metadata.trivia = trivia[:-5]
		Log("TRIVIA: " + metadata.trivia);
		
