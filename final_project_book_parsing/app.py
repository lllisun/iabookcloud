from flask import Flask, render_template, request, jsonify, send_file
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests
from PIL import Image
import io
from helpers import *
import asyncio
from cache_config import cache

app = Flask(__name__)

session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)

adapter = HTTPAdapter(max_retries=retry_strategy) #pretending to be browser, trying to speed up api response, cant tell if it worked lol
session.mount("http://", adapter)
session.mount("https://", adapter)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/search')
def index():
    query = request.args.get('query', '')
    page = int(request.args.get('page', 1))
    
    try:
        base_filters = (
            "(collection:(internetarchivebooks) OR collection:opensource) "
            "AND mediatype:texts "
            "AND language:eng OR en"
            "AND !subject:(erotica OR savita OR erotic OR dictionary OR dictionaries OR periodical OR periodicals OR Banasthali OR encyclopedia OR encyclopedias OR almanac OR almanacs 'C-DAC') "
            "AND !collection:(adult_only OR erotica OR 'no-preview' OR dictionaries OR periodicals OR magazines OR newspapers OR encyclopedias OR almanacs OR 'C-DAC') "
            "AND format:(Text PDF)"
            "AND !topic:('C-DAC' OR Banasthali OR savita)"
            "AND !title:(savita OR savitha) "
            "AND (format:DjVu OR format:Djvu OR format:Text)"
            "AND -access-restricted-item:true "
        )
        
        search_query = f"({base_filters}) AND ({query})" if query else base_filters
            
        search_url = (
            f"{ARCHIVE_URL}/advancedsearch.php"
            f"?q={quote(search_query)}"
            f"&fl[]=identifier&fl[]=title&fl[]=creator"
            f"&fl[]=downloads&fl[]=language"
            f"&fl[]=num_reviews&fl[]=avg_rating"
            f"&fl[]=subject"
            f"&sort[]=downloads desc"
            f"&output=json&rows=15&page={page}"
        )
        
        response = session.get(search_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        
        total_results = data.get('response', {}).get('numFound', 0)
        docs = data.get('response', {}).get('docs', [])
        accessible_results = []
        
        for doc in docs:
            try:
                identifier = doc['identifier']
                metadata = get_book_data(identifier)

                if metadata and has_txt_file(metadata):
                    accessible_results.append(doc)
            except Exception:
                continue

        total_pages = (total_results + 14) // 15
        start_page = max(1, page - 2)
        end_page = min(total_pages + 1, page + 3)
        page_range = list(range(start_page, end_page))

        return render_template(
            'results.html',
            results=accessible_results,
            query=query,
            total_results=total_results,
            current_page=page,
            total_pages=total_pages,
            page_range=page_range
        )
        
    except Exception:
        return "Error loading books.", 500

@app.route('/book/<identifier>')
def book_details(identifier: str): 
    try:
        metadata = get_book_data(identifier)  # This is already cached
        if not metadata:
            return "Could not fetch book details.", 404

        if not isinstance(metadata.get('metadata', {}), dict):
            metadata['metadata'] = {}
            
        metadata['metadata'].update({
            field: metadata['metadata'].get(field) 
            for field in ['title', 'creator', 'description', 'date', #changed from checking for actual values--very few entries have all filled values
                         'publisher', 'language', 'subject']
        })
        
        # skip text URL check if we already know there's no text file
        if not has_txt_file(metadata):
            metadata['has_text'] = False
        else:
            text_url = get_text_url_from_metadata(identifier)
            metadata['has_text'] = bool(text_url)
                
        return render_template('book_details.html', metadata=metadata)
        
    except Exception as e:
        print(f"Error in book_details: {str(e)}") 
    
@app.route('/analyze/<identifier>')
def analyze_book_text(identifier: str):
    try:
        result = analyze_text(identifier)
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'error': str(e),
        }), 500

if __name__ == '__main__':
    app.run(debug=True)