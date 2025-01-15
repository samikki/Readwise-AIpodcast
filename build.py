from datetime import datetime, timedelta
import requests  # This may need to be installed from pip
import json
import os
from dotenv import load_dotenv

load_dotenv()
from openai import OpenAI
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

readwise_token = os.getenv("READWISE_TOKEN")

def fetch_reader_document_list_api(updated_after=None, location=None):
    full_data = []
    next_page_cursor = None
    while True:
        params = {}
        if next_page_cursor:
            params['pageCursor'] = next_page_cursor
        if updated_after:
            params['updatedAfter'] = updated_after
        if location:
            params['location'] = location
#        print("Making export api request with params " + str(params) + "...")
        response = requests.get(
            url="https://readwise.io/api/v3/list/",
            params=params,
            headers={"Authorization": f"Token {readwise_token}"}
        )
        full_data.extend(response.json()['results'])
        next_page_cursor = response.json().get('nextPageCursor')
        if not next_page_cursor:
            break
    return full_data

# Later, if you want to get new documents updated after some date, do this:
docs_after_date = datetime.now() - timedelta(days=1)  # use your own stored date
new_data = fetch_reader_document_list_api(docs_after_date.isoformat(), 'feed')


if isinstance(new_data, list) and all(isinstance(doc, dict) for doc in new_data):
    new_data = [doc for doc in new_data if doc['reading_progress'] < 0.8]
    new_data = [{'title': doc['title'], 'author': doc['author'], 'tags': [tag['name'] for tag in doc['tags'].values()] if isinstance(doc['tags'], dict) else [], 'summary': doc['summary'], 'site_name': doc['site_name']} for doc in new_data]
else:
    print("Unexpected data structure:", new_data)

# count how many articles there are in the new_data
print("There are " + str(len(new_data)) + " articles in the new_data")

# create a different json variable for each tag
tags = {}
for doc in new_data:
    for tag in doc['tags']:
        if tag not in tags:
            tags[tag] = []
        tags[tag].append(doc)

# Define the priority tags and ignore tags
priority_tags = ["Local", "Tesla", "AI", "Movies", "TV", "Games", "Technology"]
ignore_tags = ["Humour", "Summary"]

# Filter out ignore_tags from the tags dictionary
filtered_tags = {tag: docs for tag, docs in tags.items() if tag not in ignore_tags}
# Sort the tags, prioritizing the specified tags in the defined order
sorted_tags = {k: v for k, v in sorted(filtered_tags.items(), key=lambda item: (priority_tags.index(item[0]) if item[0] in priority_tags else len(priority_tags), item[0]))}

# a table of tags and hosts for that tag
hosts = {
    "Introduction": "Frasier Crane",
    "Humour": "Bill Burr and Deadpool",
    "Local": "Moominpappa and Snufkin",
    "Movies": "Deadpool and Moira Rose",
    "TV": "Troy McClure and Miss Piggy",
    "Books": "Tyrion Lannister and Wednesday Addams",
    "Games": "Felicia Day and Geralt of Rivia",
    "Tesla": "KITT from Knight Rider and Tony Stark",
    "Technology": "Tony Stark and Q from James Bond",
    "AI": "Data from Star Trek and GLaDOS from Portal",
    "Health & Wellness": "Oprah Winfrey and Dr. Ian Malcolm",
    "Science": "Carl Sagan and The Doctor from Doctor Who",
    "Business & Finance": "Rupert Giles and Lucille Bluth",
    "Startups": "Erlich Bachman and Richard Hendricks",
    "Lifestyle": "Moira Rose and Tahani Al-Jamil",
    "Family & Relationships": "Leslie Knope and Ted Lasso",
    "Arts & Culture": "Frasier Crane and Oscar Wilde",
    "Education": "The Doctor from Doctor Who and Hermione Granger",
    "Environment": "Captain Planet and The Lorax",
    "Politics & Society": "Jon Stewart and Selina Meyer",
    "History": "Frasier Crane and Terry Jones from Monty Python",
    "Sports & Recreation": "Ted Lasso and John Oliver",
    "Food & Drink": "Gordon Ramsay and Julia Child",
    "Entertainment": "Miss Piggy and Jimmy Fallon",
    "Productivity & Self-Improvement": "David Allen and Marie Kondo",
    "Research Papers": "Alan Turing and Dr. Ian Malcolm",
    "Professional Documents": "Miranda Priestly and Harvey Specter",
    "Summary": "Frasier Crane"
}

podcast_script = ""

podcast_script +="\n<h1>INTRODUCTION</h1>\n"
print ("<h1>Intro...</h1>")
if "Introduction" in hosts:
    host = hosts["Introduction"]
else:
    host = "Frasier Crane"

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": """
            We are creating a podcast. Create a script for a podcast based on the following newsfeed. 
            This is the first segment of the podcast and contains only the introduction.
            There are segments after this one. End this segment so that other segments can be added.
            The host for this segment is """ + host + """ and the style follows the entertaining style which is particular to them. 
            The next segment has a different host.
            Format the script so that I can feed it to TTS to make it sound like a real podcast. 
            Keep the segment about 1 minutes long.
            The output should be in raw HTML format without header or footer.
            Leave out the sound effects and music.
            """
        }
    ]
)

podcast_script += response.choices[0].message.content


# go through each tag
for tag, docs in sorted_tags.items():
    this_data = []
    for doc in docs:
        this_data.append({
            "title": doc['title'],
            "author": doc['author'],
            "tags": doc['tags'],
            "summary": doc['summary'],
            "site_name": doc['site_name']
        })
    podcast_script +="\n<h1>SEGMENT: " + tag + "</h1>"  
    print ("<h1>Segment: " + tag + "</h1>")   
    # if there is a host for that tag
    if tag in hosts:
        host = hosts[tag]
    else:
        host = "Frasier Crane"
        
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": """
                We are creating a podcast. Create a script for a podcast based on the following newsfeed. 
                This is one segment of the podcast and topic here is about """ + tag + """.
                There are segments before and after this one. You do not need introductions, just continue the story.
                The host for this segment is """ + host + """ and the style for the whole segment follows the entertaining style which is particular to them. 
                The previous segment and next segment probably have different hosts.
                Keep the script informative and entertaining. 
                The script's main purpose is to help listener learn about new topics with the subject """ + tag + """.
                Include content from all of the articles in the newsfeed. 
                Only use the content from the articles. Do not invent new content.
                Dig deeper into the article summaries to find interesting information and use it to guide the script with the host's style.
                If possible, find a common theme or topic from all the articles and use it to guide the script.
                Format the script so that I can feed it to TTS to make it sound like a real podcast. 
                Leave out the sound effects and music.
                Keep the segment up to 3 minutes long.
                The output should be in raw HTML format without header or footer.
                Here is the newsfeed for topic """ + tag + """: """ + json.dumps(this_data)
            }
        ]
    )

    podcast_script += response.choices[0].message.content

podcast_script +="\n<h1>ENDING</h1>"
print ("<h1>Ending...</h1>")
if "Summary" in hosts:  
    host = hosts["Summary"]
else:
    host = "Frasier Crane"

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": """
            We are creating a podcast. Create a script for a podcast based on the following newsfeed. 
            This is the last segment of the podcast and contains only the introduction.
            There are segments before this one. Start this segment so it continues the story. 
            End this segment with the ending of the podcast episode.
            The host for this segment is """ + host + """ and the style follows the entertaining style which is particular to them. 
            Previous segments had different hosts.
            Format the script so that I can feed it to TTS to make it sound like a real podcast. 
            Keep the segment about 1 minutes long.
            The output should be in raw HTML format without header or footer.
            Leave out the sound effects and music.
            """
        }
    ]
)

podcast_script += response.choices[0].message.content

# add HTML header and footer to the script
podcast_script = "<html><body>" + podcast_script + "</body></html>"

# create a json structure of the podcast script with following variables:
# url = "https://example.com/podcast.mp3"
# title = "Feed summary" 
# should_clean_html = True
# html = podcast_script
# tags = ["Summary"]
# published_date = now in ISO 8601 format
# location = "feed" 
# category = "article"
# summary = "This is a summary of feed items for previous 24 hours."

print ("Saving to Readwise...")
timestamp = datetime.now().isoformat()
# today's date in dd.mm.yyyy format
date_title = timestamp[:10].replace("-", ".")

podcast_json = {
    "url": "https://example.com/podcast" + timestamp,
    "title": "Feed summary on " + date_title,
    "should_clean_html": True,
    "html": podcast_script,
    "tags": ["Summary"],
    "published_date": timestamp,
    "location": "feed",
    "category": "article"
}

# post and get the returned status code

response = requests.post(
    url="https://readwise.io/api/v3/save/",
    headers={"Authorization": "Token " + readwise_token},
    json=podcast_json
)

if response.status_code == 201:
    print("Podcast saved successfully!")
else:
    print("Failed to save podcast. Status code:", response.status_code)

print (response.json())
