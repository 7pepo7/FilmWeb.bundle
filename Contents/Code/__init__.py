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
			search_filmweb_result = HTML.ElementFromURL(FILMWEB_SEARCH % (search_name, str(int(media.year) - search_years), str(int(media.year) + search_years)), 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
		else:
			search_filmweb_result = HTML.ElementFromURL(FILMWEB_SEARCH % (search_name, str(1900), str(Datetime.Now().year)), 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
    
		#mine = []
		movies_list = search_filmweb_result.xpath("//ul[@class='sep-hr resultsList']");
 
		if not movies_list:
			return 1;
    
		trust_score = 100;
		order_num = 0;
		for movie in movies_list[0].xpath("./li"):
			score_penalty = 0
			#YEAR
			try:
				year = int(movie.xpath(".//a[contains(@class, 'hitTitle')]")[0].get('href')[-11:-7])        
			except:
				year = 0;
			if year and media.year:
				score_penalty += abs(int(media.year) - year)*4
			Log("Year: " + str(year));
			#TITLE
			title = movie.xpath(".//a[contains(@class, 'hitTitle')]")[0].text_content()
			title = title.strip()
			Log("Title: " + title);
			index = title.find(" / ")
			if index > -1:
				polish_title = title[0:index]
				original_title = title[(index+3):]
				s1 = Util.LevenshteinDistance(media.name, polish_title)
				s2 = Util.LevenshteinDistance(media.name, original_title)
				if s1 < s2:
					score_penalty += s1
				else:
					score_penalty += s2
			else:
				polish_title = ''
				original_title = title
				score_penalty += Util.LevenshteinDistance(media.name, original_title)
			name = polish_title
			if name == '':
				name = original_title
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
			id = movie.xpath(".//a[contains(@class, 'hitTitle')]")[0].get('href').encode('hex')
			Log("ID: " + str(id));
			#mine.append((name, year, score))
			results.Append(MetadataSearchResult(id=id, name=name, year=year, score=score, lang=lang))

				

	def update(self, metadata, media, lang): 
		proxy = Proxy.Preview
		
		movie_id = metadata.id.decode('hex')
		
		info_filmweb_result = HTML.ElementFromURL(FILMWEB + movie_id, 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
		
		#TITLE
		metadata.title = media.title			
		
		#SUMMARY 
		overview = ""       
		try:
			overview = info_filmweb_result.xpath(".//div[contains(@class, 'filmMainDescription')]/p[contains(@itemprop, 'description')]")[0].text      
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
		info_filmweb_dates_result = HTML.ElementFromURL(FILMWEB + movie_id + '/dates', 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
		try:
			release_day = info_filmweb_dates_result.xpath("//table[contains(@class, 'sep-hr-table')]")[0].xpath("./tr")[0].xpath("./td")[1].text;
			Log("RELEASE DAY: " + release_day);	
			var = 2;
			if release_day[1:2] == " ":
				var = 1;
			if "stycznia" in release_day:
				release_day = release_day[-4:] + "-01-" + release_day[:var];
			elif "lutego" in release_day:
				release_day = release_day[-4:] + "-02-" + release_day[:var];
			elif "marca" in release_day:
				release_day = release_day[-4:] + "-03-" + release_day[:var];
			elif "kwietnia" in release_day:
				release_day = release_day[-4:] + "-04-" + release_day[:var];
			elif "maja" in release_day:
				release_day = release_day[-4:] + "-05-" + release_day[:var];
			elif "czerwca" in release_day:
				release_day = release_day[-4:] + "-06-" + release_day[:var];
			elif "lipca" in release_day:
				release_day = release_day[-4:] + "-07-" + release_day[:var];
			elif "sierpnia" in release_day:
				release_day = release_day[-4:] + "-08-" + release_day[:var];
			elif "wrze" in release_day:
				release_day = release_day[-4:] + "-09-" + release_day[:var];        
			elif "pa" in release_day:
				release_day = release_day[-4:] + "-10-" + release_day[:var];
			elif "listopada" in release_day:
				release_day = release_day[-4:] + "-11-" + release_day[:var];
			elif "grudnia" in release_day:
				release_day = release_day[-4:] + "-12-" + release_day[:var];  
		except:
			release_day = ''
		Log("RELEASE DAY: " + release_day);			
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
			info_filmweb_titles_result = HTML.ElementFromURL(FILMWEB + movie_id + '/titles', 0, {'Cookie':HTTP.CookiesForURL(FILMWEB)}, cacheTime = 0)
			original_title = info_filmweb_titles_result.xpath(".//li/div[div[contains(@class, 'text-right')][text()=contains(.,'oryginalny')]]/div[contains(@class, 's-16')]")[0].text;    
			metadata.original_title = original_title
			Log("ORIGINAL TITLE: " + original_title);
		except:
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
		metadata.directors.clear()
		for directors in info_filmweb_result.xpath(".//div[contains(@class, 'filmInfo')]//th[text()=starts-with(.,'re')]/parent::tr//a"):
			try:
				director = directors.text_content().strip()
				metadata.directors.new().name = director
				Log("DIRECTOR: " + director)
			except:
				pass
		
    #WRITERS
		metadata.writers.clear()
		for writers in info_filmweb_result.xpath(".//div[contains(@class, 'filmInfo')]//th[text()=starts-with(.,'sc')]/parent::tr//a"):
			try:
				writer = writers.text_content().strip()
				metadata.writers.new().name = writer
				Log("WRITER: " + writer)
			except:
				pass
    
		#POSTER
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
		