
import requests
from urllib.parse import quote
import re
from collections import Counter
import os
from cache_config import cache
from io import BytesIO
from typing import  List, Optional, Dict, Any, Tuple, Union #for accomodating diff types fetched by api
from dotenv import load_dotenv #for heroku

load_dotenv()

ARCHIVE_URL = 'https://archive.org'
IA_S3_ACCESS_KEY = os.environ.get('IA_S3_ACCESS_KEY')
IA_S3_SECRET_KEY = os.environ.get('IA_S3_SECRET_KEY')

HEADERS = {
    'Authorization': f'LOW {IA_S3_ACCESS_KEY}:{IA_S3_SECRET_KEY}', #access provided in .env and uploaded to heroku config
}

 #added common misspellings i found in the pdfs
 #tracked down location of typos--from text files created by IA ocr, have not created a solve for correcting these typos
 #future function--finding the consistent typos and replacing it in the text with the correct word, before the analyze function
 #currently analyze function is messed up for this reason, only could entirely remove as a stop word if it was a common word--the same significant word is being counted separately in certain texts
STOP_WORDS = set(
    'the and did ahd tke ike tkat kis then said didn more well even be to of and a in that have i it for not on with he as you do at '
    'this can don but his by from they we say her she or an will my one all would ' 
    'there let kad doh ckris coold aih their what so up out if about who get which go me is was were '
    'are been has had when its very now such yet way where why com www min how am your than the a he him his '
    'they their them with would dowhs make arouhd like time just know take people year '
    'into good some could over think because also back after use two how our first'.split() #don't count these
)

session = requests.Session()

#broke apart from try_alternate_identifiers and gave it priority--successfully reduced load time bc most texts are txt files or pdfy, not others in alternate identifier
#issue with this is now if you HAPPEN to be loading a page with a file type in alternate identifiers, it still takes FOREVER
#caching only fixed this for after first load

def get_pdfy_variations(identifier: str) -> List[str]: #for internectarchivebook collection having diff urls
    variations = [identifier]
    
    if identifier.startswith('pdfy-'):
        variations.append(identifier[5:])  
    else:
        variations.append(f"pdfy-{identifier}") 
    
    parts = identifier.split('/')
    if len(parts) > 1:
        last_part = parts[-1]
        if last_part.startswith('pdfy-'):
            variations.append(f"{'/'.join(parts[:-1])}/{last_part[5:]}")
        else:
            variations.append(f"{'/'.join(parts[:-1])}/pdfy-{last_part}")
            
    base_id = identifier.replace('pdfy-', '')
    variations.extend([
        f"pdfy-{base_id}", 
        f"pdfy_{base_id}",
        base_id.replace('-', '_'),
        base_id.replace('_', '-')
    ])
    
    return list(set(variations))

def test_url(url: str, headers: dict) -> bool: #try if its there so we dont load failed tries
    try:
        response = session.head(url, headers=headers, timeout=5)
        return response.ok
    except Exception:
        return False

def has_txt_file(metadata: Dict[str, Any]) -> bool: 
    files = metadata.get('files', [])
    if not isinstance(files, list):
        return False
        
    return any(
        isinstance(f, dict) and 
        f.get('name', '').endswith(('.txt', '_djvu.txt', '_text.txt'))
        for f in files
    )
    
#opportunity for accelerating load times---can't figure out how to reduce needing both these functions, redudant functions and running into so many errors when combining
def get_text_url_from_metadata(identifier: str) -> Optional[str]: #still not sure why code fails when i replace this OR has_txt_file
    try:
        metadata_url = f"{ARCHIVE_URL}/metadata/{identifier}"
        response = session.get(metadata_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        metadata = response.json()
        
        # raw text
        files = metadata.get('files', [])
        for file_info in files:
            if not isinstance(file_info, dict):
                continue
                
            filename = file_info.get('name', '')
            if filename.endswith(('_djvu.txt', '_text.txt')):
                url = f"{ARCHIVE_URL}/download/{identifier}/{filename}"
                if test_url(url, HEADERS):
                    return url

        # fallback
        for file_info in files:
            filename = file_info.get('name', '')
            if filename.endswith('.txt') and 'html' not in filename.lower():
                url = f"{ARCHIVE_URL}/download/{identifier}/{filename}"
                if test_url(url, HEADERS):
                    return url
                    
        return None
        
    except Exception:
        return None
        
@cache
def get_book_data(identifier: str) -> Optional[Dict[str, Any]]:
    try:
        print(f"Fetching new metadata for {identifier}")
        metadata_url = f"{ARCHIVE_URL}/metadata/{identifier}"
        response = session.get(metadata_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        metadata = response.json()
        if not isinstance(metadata.get('metadata', {}), dict):
            metadata['metadata'] = {}
        if not isinstance(metadata.get('files', []), list):
            metadata['files'] = []
            
        metadata['identifier'] = identifier
        return metadata
        
    except Exception as e:
        print(f"Error getting metadata for {identifier}: {str(e)}")
        return None
        
def analyze_text(identifier: str) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    try:
        text_url = get_text_url_from_metadata(identifier)
        if not text_url:
            return {
                'error': 'No text file available',
                'details': 'Could not find a valid text URL for this identifier'
            }, 404

        response = session.get(text_url, headers=HEADERS, timeout=30)
        #added explanations for failed tries, but still not displayed on page to user outside of console: TBD
        if not response.ok:
            return {
                'error': 'Failed to fetch text content',
                'status_code': response.status_code,
                'details': 'The text content might be restricted or require authentication'
            }, 404

        text = response.text
        if not text or len(text.strip()) == 0:
            return {
                'error': 'Empty text content',
                'details': 'The text file exists but contains no content'
            }, 404

        text = text.replace('-\n', '')
        words = [
            word for word in re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            if word not in STOP_WORDS
        ]
        
        unique_words = len(set(words))
        total_words = len(words)
        lexical_diversity = round((unique_words / total_words) * 100, 2)
        
        word_frequencies = Counter(words)
        most_common = dict(word_frequencies.most_common(500))
        
        # percentages for page
        word_percentages = {word: round((freq / total_words) * 100, 2) for word, freq in most_common.items()}
        
        return {
            'frequencies': most_common,
            'percentages': word_percentages,
            'total_words': len(words),
            'unique_words': unique_words,
            'lexical_diversity': lexical_diversity,
            'full_text': text, 
            #not useing this anymore: 'pages_analyzed': "Full text (excluding common words and words ≤ 3 characters)"
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'details': 'An unexpected error occurred during text analysis'
        }, 500

def try_alternate_identifiers(identifier: str) -> List[str]:#adding another try function, still need to reduce the now THREE into one, keep running into bugs
    alternates = get_pdfy_variations(identifier)
    
    try:
        search_url = (
            f"{ARCHIVE_URL}/advancedsearch.php"
            f"?q=identifier:({' OR '.join(quote(alt) for alt in alternates)})"
            f"&fl[]=identifier"
            f"&output=json"
        )
        
        response = session.get(search_url, headers=HEADERS)
        
        if response.ok:
            data = response.json()
            docs = data.get('response', {}).get('docs', [])
            return [doc['identifier'] for doc in docs]
            
    except Exception:
        pass
    
    return alternates