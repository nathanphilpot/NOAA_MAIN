import requests
from bs4 import BeautifulSoup
import PIL
from PIL import Image
from io import BytesIO
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from nltk.tokenize import word_tokenize
from textblob import TextBlob

def download_links(url):
    list_of_links = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    response = requests.get(url, headers=headers)
    print("Requesting access to this site gave status code: " + str(response.status_code))
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)
        for link in links:
            link_url = link["href"]
            list_of_links.append(link_url)
    elif response.status_code == 403:
        print("It looks like the site is actively blocking your request, try a different browser?")
    else:
        print("I couldn't access the site, check the status code above to what's wrong")
    return list_of_links

def clean_links(list_of_links):
    new_list_of_links = []
    #remove duplicates
    list_of_links = set(list_of_links)
    list_of_links = list(list_of_links)
    #convert to absolute links
    filtered_links = [link for link in list_of_links if ('/news' in link or '/stories' in link
                      or '/explainers' in link) and 'news-features' not in link]
    for link in filtered_links:
        link = "https://www.noaa.gov/" + link
        new_list_of_links.append(link)
    return new_list_of_links


def get_titles(list_of_links):
    titles = []
    for link in list_of_links:
        try:
            # Fetch the webpage with headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(link, headers=headers, timeout=10)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            soup = BeautifulSoup(response.text, 'html.parser')
            h1_tag = soup.find('h1')
            if h1_tag:
                title = h1_tag.get_text()
                title = title.strip()
                titles.append(title)
            else:
                titles.append("No <h1> tag found on this page.")
        except requests.exceptions.RequestException as e:
            titles.append(f"Error fetching link: {link}. Details: {e}")
        except Exception as e:
            titles.append(f"An unexpected error occurred for link: {link}. Details: {e}")
    return titles

def get_link_data(link):
    #get article words contained on the page
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(link, headers=headers, timeout=10)
    response.raise_for_status()
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        article_tag = soup.find('article')
        if not article_tag:
            article_tag = soup.find('div', class_='story-body')
        if not article_tag:
            article_tag = soup.find('div', class_='content')
        if not article_tag:
            article_tag = soup.find('div', class_='field')
        if article_tag:
            paragraphs = article_tag.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'blockquote', 'li'])
            return paragraphs, article_tag
        else:
            print("Could not find any info in this article")
            return None
    else:
        print("Unfortunately, I don't think this page is allowing data scraping. Try another.")
    return None

def put_article_info_in_file(data, article_tag, max_line_length=80):
    # Extract and clean the article text
    article_text = article_tag.get_text()
    cleaned_list = [item.strip() for item in article_text.split("\n") if item.strip()]

    def split_long_lines(text, max_length):
        """Split long lines into smaller chunks."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 > max_length:
                lines.append(' '.join(current_line))
                current_line = []
                current_length = 0
            current_line.append(word)
            current_length += len(word) + 1

        if current_line:
            lines.append(' '.join(current_line))
        return lines

    with open('../article_info.txt', 'w') as file:
        for item in cleaned_list:
            if item.isupper():  # Likely a header if it's all uppercase
                file.write(f"\n=== {item} ===\n\n")
            elif item.startswith('-') or item.startswith('*') or item.startswith("•"):  # Likely a list item
                file.write(f"  • {item.lstrip('-*•').strip()}\n")
            else:  # Body text
                # Split long paragraphs into shorter lines
                split_lines = split_long_lines(item, max_line_length)
                for line in split_lines:
                    file.write(f"{line}\n")
                file.write("\n")
    print("Great! I just extracted the article's information to a separate file if you would like to read it.")
    with open("../article_info.txt", "r") as file:
        lines = file.readlines()
        return lines

def summarize_data(data):
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('stopwords')

    article = " ".join(data)

    # Tokenize the article into sentences
    sentences = sent_tokenize(article)

    # Tokenize words and remove stopwords
    words = word_tokenize(article.lower())
    stop_words = set(stopwords.words('english'))
    filtered_words = [word for word in words if word.isalnum() and word not in stop_words]

    # Find word frequency distribution
    fdist = FreqDist(filtered_words)

    # Rank sentences based on word frequency
    sentence_scores = {}
    for sentence in sentences:
        sentence_tokens = word_tokenize(sentence.lower())
        score = sum(fdist[word] for word in sentence_tokens if word in fdist)
        sentence_scores[sentence] = score

    # Sort sentences by score and select top sentences
    summarized_article = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:5]
    print(" ".join(summarized_article))

def visualize_data(link):
    print("\n")
    response = requests.get(link)
    url = "https://www.noaa.gov"
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        images = soup.find_all('img')
        for image in images:
            img_url = image.get('src')
            if img_url:
                # Handle relative URLs by making them absolute
                if not img_url.startswith('http'):
                    img_url = url + img_url
                img_response = requests.get(img_url)
                if img_response.status_code == 200:
                    try:
                        img = Image.open(BytesIO(img_response.content))
                        img.show()
                    except PIL.UnidentifiedImageError:
                        print(f"Failed to identify image from {img_url}")
                else:
                    print(f"Failed to retrieve image from {img_url}")
    else:
        print(f"I couldn't find any images on this particular site unfortunately.")
    print("Great! That's about all of the images. If any didn't pop up, it probably means the shown links just lead to logos, but you can")
    print("click on them to make sure you didn't miss any important info!")


def advanced_analysis(data):
    article = " ".join(data)
    blob = TextBlob(article)
    sentiment = blob.sentiment
    print(f"Sentiment polarity: {sentiment.polarity}")
    print(f"Sentiment subjectivity: {sentiment.subjectivity}")
    interpret_sentiment(sentiment.polarity, sentiment.subjectivity)

def interpret_sentiment(polarity, subjectivity):
    # Interpret polarity
    print("Sentiment polarity ranges from -1 to 1, with negative showing a negative sentiment in the subject material and vice versa")
    print("Subjectivity polarity ranges from 0 to 1, with zero being purely objective and 1 being purely subjective")
    if polarity > 0:
        polarity_interpretation = "positive"
    elif polarity < 0:
        polarity_interpretation = "negative"
    else:
        polarity_interpretation = "neutral"

    # Interpret subjectivity
    if subjectivity > 0.5:
        subjectivity_interpretation = "subjective (opinion-based)"
    else:
        subjectivity_interpretation = "objective (factual)"

    # Print the interpretation
    print(f"Overall,The sentiment is {polarity_interpretation} with a polarity of {polarity:.2f},")
    print(f"while the text is {subjectivity_interpretation} with a subjectivity of {subjectivity:.2f}.")

def create_dashboard(data, link):
    while True:
        print("\n")
        print("You have three options for this article!\n")
        print("A: Summarize article data")
        print("B: See the images provided in this article")
        print("C: Advanced AI analysis")
        print("\n")
        user_input = input("Please type the letter of your choice, or press enter to return to the article choices: ")
        if user_input:
            user_input = user_input.lower()
            if user_input == "a":
                print("\n")
                summarize_data(data)
            elif user_input == "b":
                print("\n")
                visualize_data(link)
            elif user_input == "c":
                print("\n")
                advanced_analysis(data)
            elif user_input == "":
                break
            else:
                print("I dont think I understand your input. Try typing one of the options given.")


def main():
    while True:
        url = "https://www.noaa.gov/"
        print("\nThis scraper is focused on analyzing the latest articles from the National Oceanic and Atmospheric Administration web site.")
        print("We have data analysis open for articles in weather, climate, ocean-coasts, fisheries, satellites, research, marine-aviation, charting, and sanctuaries!")
        pathway = input("Please type out what topic you would like to explore: ")
        print("\n")
        pathway = pathway.lower().strip()
        if pathway == "weather":
            url = url + pathway
        elif pathway == "climate":
            url = url + pathway
        elif pathway == "ocean-coasts":
            url = url + pathway
        elif pathway == "fisheries":
            url = url + pathway
        elif pathway == "satellites":
            url = url + pathway
        elif pathway == "research":
            url = url + pathway
        elif pathway == "marine-aviation":
            url = url + pathway
        elif pathway == "charting":
            url = url + pathway
        elif pathway == "sanctuaries":
            url = url + pathway
        else:
            print("Invalid category! Try typing the category exactly how it is given.")
            continue
        list_of_links = download_links(url)
        list_of_links = clean_links(list_of_links)
        if list_of_links:
            size = len(list_of_links)
            print(f"Wonderful! I found {size} link(s):\n")
            count = 1
            for link in list_of_links:
                print(f"{count}: {link}")
                count += 1
        else:
            print("Sorry, I couldn't find any link(s):")
            continue
        print("\nThe titles of these articles are: \n")
        titles = get_titles(list_of_links)
        count = 1
        for title in titles:
            print(f"{count}: {title}")
            count += 1
        print("\n")
        while True:
            print("\n")
            article_choice = input("Enter the number of an article if you want info on it, or press enter to return to the categories: ")
            print("\n")
            if article_choice == '':
                break
            try:
                article_choice = int(article_choice)
                if article_choice > len(list_of_links) or article_choice < 1 or not isinstance(article_choice, int):
                    print("Your input is outside of the range of articles")
                    continue
                else:
                    page_data = None
                    article_tag = None
                    if get_link_data(list_of_links[article_choice - 1]) is not None:
                        page_data, article_tag = get_link_data(list_of_links[article_choice-1])
                    if page_data and article_tag:
                        article_page_data = put_article_info_in_file(page_data, article_tag)
                        create_dashboard(article_page_data, list_of_links[article_choice-1])
                    else:
                        print("Sorry I couldn't find any written info in this article!")
                        continue
            except ValueError:
                print("Your entry doesn't seem to be a number")



if __name__ == "__main__":
    main()
