# -*- coding: utf-8 -*-
"""
Created on Tue Oct 31 12:54:41 2023

@author: jesal
"""

import csv
import sqlite3
import uuid
import datetime
from nltk import pos_tag
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

def create_table(cursor, table_name, fields):
    field_string = ', '.join(fields)
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            {field_string}
        )
    ''')

def insert_movie_data(cursor, movies):
    for movie in movies:
        cursor.execute("SELECT * FROM movies WHERE title = ?", (movie[0],))
        # Checks for duplicate movies
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO movies (title, genre, release_year, director, show_time) VALUES (?, ?, ?, ?, ?)",
                movie
            )

def retrieve_movies(cursor):
    cursor.execute("SELECT * FROM movies")
    return cursor.fetchall()

# Movie database
with sqlite3.connect('movie_database.db') as conn:
    cursor = conn.cursor()
    
    create_table(cursor, 'movies', [
        'id INTEGER PRIMARY KEY',
        'title TEXT NOT NULL',
        'genre TEXT',
        'release_year INTEGER',
        'director TEXT',
        'show_time TEXT'
    ])
    
    # Adds movie data into database
    movies = [
    ('The Godfather', 'Crime', 1972, 'Francis Ford Coppola', '10:00,14:00,18:00'),
    ('The Shawshank Redemption', 'Drama', 1994, 'Frank Darabont', '11:00,15:00,19:00'),
    ('Titanic', 'Romance', 1997, 'James Cameron', '12:00,16:00,20:00'),
    ('The Dark Knight', 'Action', 2008, 'Christopher Nolan', '13:00,17:00,21:00'),
    ('Avatar', 'Action', 2009, 'James Cameron', '10:30,14:30,18:30'),
    ('Inception', 'Sci-Fi', 2010, 'Christopher Nolan', '11:30,15:30,19:30'),
    ('Interstellar', 'Sci-Fi', 2014, 'Christopher Nolan', '12:30,16:30,20:30'),
    ('The Menu', 'Comedy', 2022, 'Mark Mylod', '13:30,17:30,21:30'),
    ('Spider-Man: Across the Spider-Verse', 'Animation', 2023, 'Joaquim Dos Santos', '10:00,14:00,18:00'),
    ('Hunger-Games: Ballad of Songbirds-Snakes', 'Adventure', 2023, 'Francis Lawrence', '11:00,15:00,19:00'),
    ('Wonka', 'Musical', 2023, 'Paul King', '12:00,16:00,20:00'),
    ('Napoleon', 'Biography', 2023, 'Ridley Scott', '13:00,17:00,21:00'),
    ('Wish', 'Animation', 2023, 'Chris Buck', '10:30,14:30,18:30'),
    ('Godzilla Minus One', 'Action', 2023, 'Takashi Yamazaki', '11:30,15:30,19:30')
    ]

    insert_movie_data(cursor, movies)

# TF-IDF vectors for  movies matching
movie_tfidf_vectorizer = TfidfVectorizer()
movie_texts = [f"{movie[1]} {movie[4]}" for movie in retrieve_movies(cursor)]
movie_vectors = movie_tfidf_vectorizer.fit_transform(movie_texts)

# Booking database
with sqlite3.connect('bookings.db') as conn_bookings:
    cursor_bookings = conn_bookings.cursor()

    create_table(cursor_bookings, 'bookings', [
            'id INTEGER PRIMARY KEY',
            'booking_id TEXT',
            'user_name TEXT',
            'movie TEXT',
            'date DATE',
            'time TEXT',
            'tickets INTEGER'   
    ])

# loads dataset.csv
data = []
with open('dataset.csv', 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        data.append(row)

def preprocess(user_input):
    # The preprocess function cleans user_input by converting it to lowercase, removing extra space and non-alphanumeric characters.
    # It then tokenizes the user input, performs POS tagging, and removes stopwords, except for ‘ what, show, your etc’ which I keep.
    # The tokens are then lemmatized and joined back into a string. 
    user_input = user_input.lower()
    user_input = ' '.join(user_input.split())
    tokens = word_tokenize(user_input)
    pos_tags = pos_tag(tokens)
    stop_words = set(stopwords.words('english'))
    not_stopwords = {'what', 'show', 'your', 'a', 'of', 'do', 'can', 'how', 'yes', 'are', 'me', 'doing', 'you', 'name', 'my', 'is', 'all'}
    stop_words = set([word for word in stop_words if word not in not_stopwords])
    tokens = [token for token, pos in pos_tags if token not in stop_words]
    lemmatizer = WordNetLemmatizer()
    lemmatized_tokens = [lemmatizer.lemmatize(token) for token in tokens]
    processed_input = ' '.join(lemmatized_tokens)
    return processed_input

# TF-IDF vectors for user input
intent_tfidf_vectorizer = TfidfVectorizer()
intent_texts = [row[0] for row in data]
intent_vectors = intent_tfidf_vectorizer.fit_transform(intent_texts)

def chatbot_functions(response, user_name, movie=""):

    def choose_movie():
        movie = ""  # Initialise movie as an empty string
        chatbot_state = False
        while True:
            user_input = input("You: ")
            if user_input.lower() == 'no':
                chatbot_state = True
                break
            movie = find_movie(user_input)
            if movie == "not_found":
                print("Bot:","I'm sorry,", user_name, "I couldn't find that movie. Please try enter it again.")
                movie = ("not_found", "")
            else:
                print("Bot:", user_name, "You have selected the movie", movie[1])
                break

        return movie, chatbot_state

    def choose_date():
        date = ""  # Initialise date as an empty string
        chatbot_state = False
        while True:
            user_input_date = input("You: ")
            if user_input_date.lower() == 'no':
                chatbot_state = True
                break
            try:
                date = datetime.datetime.strptime(user_input_date, '%Y-%m-%d').date()
                if date < datetime.date.today():
                    print("Bot: Booking date in the past. Try again.")
                else:
                    print("Bot:", user_name, "You have choosen to book a move on", date)
                    break
            except ValueError:
                print("Bot: Invalid date format. Please enter the date in YYYY-MM-DD format.")

        return date, chatbot_state

    def choose_time(movie):
        time = ""  # Initialise time as an empty string
        chatbot_state = False
        show_times = movie[5].split(',')
        print(f"Bot: The available show times for {movie[1]} ({movie[3]}) are {', '.join(show_times)}.")

        while True:
            time = input("You: ")
            if time.lower() == 'no':
                chatbot_state = True
                break
            elif time in show_times:
                print("Bot:", user_name, "you have selected", time)
                break
            else:
                print("Bot: That time is not available", user_name, "please choose one of the available show times.")
        return time, chatbot_state
    
    def choose_tickets():
        tickets = ""  # Initialise tickets as an empty string
        chatbot_state = False

        while True:
            user_input_tickets = input("You: ")
            if user_input_tickets.lower() == 'no':
                chatbot_state = True
                break
            elif user_input_tickets.isdigit() and int(user_input_tickets) <= 10:
                tickets = int(user_input_tickets)
                print("Bot:", user_name, "your total number of tickets booked is", tickets)
                break
            elif user_input_tickets.isdigit() and int(user_input_tickets) > 10:
                print("Bot:", user_name, "you can't book more than 10 tickets per booking")
            else:
                print("Bot: Invalid input.")

        return tickets, chatbot_state
    
    def get_confirmation():
        confirmation = input("Bot: Please type confirm to continue booking or no to stop: ")
        if confirmation.lower() == 'no':
            return confirmation, True
        elif confirmation.lower() == 'confirm':
            return confirmation, False
        else:
            print("Bot: I'm sorry, I didn't understand that. Type confirm or no.")
            return get_confirmation()

    def book_movie():
        chosen_movie = movie
        chatbot_state = False
        if chosen_movie == "":
            print("Bot: These are the current movies available")
            movies = retrieve_movies(cursor)
            movie_list = '\n'.join([f"{movie[1]} ({movie[3]}) - {movie[4]}" for movie in movies])
            print(movie_list)
            print("Bot: " + user_name + ", what movie would you like to book? (Type no at any point to stop) ")
            chosen_movie, chatbot_state = choose_movie()
        if chatbot_state:
            print("Bot: I'm sorry you stopped booking and that i could not find your movie ")
            return "Unfortunately, " + user_name + ", the movie selection process has been stopped"
        
        print("Bot: " + user_name + ", enter a day you would like to book the movie in YYYY-MM-DD format")
        date, chatbot_state = choose_date()
        if chatbot_state:
            print("Bot: I'm sorry you stopped booking and that you changed your mind about booking a movie")
            return "Unfortunately, " + user_name + ", the date selection process has been stopped"

        print("Bot: " + user_name + ", what time would you like to book the movie for? ")
        time, chatbot_state = choose_time(chosen_movie)
        if chatbot_state:
            print("Bot: I'm sorry you stopped booking and that the time you picked wasn't available")
            return "Unfortunately, " + user_name + ", the time selection process has been stopped"
        
        print("Bot: " + user_name + ", how many tickets would you like to book? ")
        tickets, chatbot_state = choose_tickets()
        if chatbot_state:
            print("Bot: I'm sorry you stopped booking and that the ticket number was not available")
            return "Unfortunately, " + user_name + ", the ticket selection process has been stopped"
        
        confirmation, chatbot_state = get_confirmation()
        if chatbot_state or confirmation.lower() != 'confirm':
            print("Bot: I'm sorry you stopped booking")
            return "Unfortunately, " + user_name + ", the booking process has been stopped"
        
        booking_id = f"booking_{uuid.uuid4().hex}"
        print("Bot: Thank you for booking " + user_name + ", this is your Booking ID: " + booking_id)
        cursor_bookings.execute("INSERT INTO bookings (booking_id, user_name, movie, date, time, tickets) VALUES (?, ?, ?, ?, ?, ?)",
                                (booking_id, user_name, chosen_movie[1], date, time, tickets))
        conn_bookings.commit()
        return "You have booked " + str(chosen_movie[1]) + " for " + str(time) + " on " + str(date) + " with a ticket total of " + str(tickets) + "."

    def cancel_booking(user_name):
        while True:
            print("Bot: If you do not know booking id, stop this process and ask find booking id")
            booking_id_to_cancel = input("Bot: Please enter a Booking ID: ")
            user_name_to_cancel = input("Bot: Please enter a name: ")
            cursor_bookings.execute("SELECT * FROM bookings WHERE booking_id=? AND user_name=?", (booking_id_to_cancel, user_name_to_cancel))
            booking_found = cursor_bookings.fetchone()

            if booking_found:
                print(f"Bot: Booking Details: {booking_found[3]} for {booking_found[5]} on {booking_found[4]} with a ticket total of {booking_found[6]}")
                while True:
                    confirmation = input("Bot: " + user_name + ", do you want to cancel this booking? (yes/no): ").lower()
                    if confirmation == 'yes':
                        # Delete the booking from the bookings database
                        cursor_bookings.execute("DELETE FROM bookings WHERE id=?", (booking_found[0],))
                        conn_bookings.commit()
                        return user_name + ", you have successfully cancelled your booking for " + str(booking_found[3]) + " for " + str(booking_found[5]) + " on " + str(booking_found[4]) + " with a ticket total of " + str(booking_found[6])
                    elif confirmation == 'no':
                        return "Booking cancellation stopped."
                    else:
                        print("Bot: Invalid input. Please enter 'yes' or 'no'.")
            else:
                return "No matching booking found to cancel, " + user_name + ", please try ask to cancel again."
        
    def show_genre():
        while True:
            print("Bot: These are the genre's I have: Crime, Drama, Romance, Action, Sci-Fi, Comedy, Animation, Adventure, Musical, Biography")
            genre = input("Bot: Please enter a genre or no to stop: ").lower()
            if genre.lower() == 'no':
                return user_name + ", unfortunately the genre process has been stopped"
            
            cursor.execute("SELECT * FROM movies WHERE genre LIKE ?", ('%' + genre + '%',))
            genre_finder = cursor.fetchall()
            
            if genre_finder:
                movie_list = '\n'.join([f"{movie[1]} ({movie[3]}) - {movie[4]}" for movie in genre_finder])
                print(movie_list)
                return "These are movies of your chosen genre: " + genre + ", " + user_name
            else:
                print(f"No movies found under this genre: {genre}, username")

    def show_booking():
        while True:
            unkown_booking_id = input("Bot: Do you know your Booking ID? (yes/no/cancel): ").lower()
            if unkown_booking_id == "no":
                print("Bot: That's ok, I will help find your booking id.")
                return find_booking_id()
            elif unkown_booking_id == "yes":
                booking_id = input("Bot: Please enter your Booking ID: ")
                user_name = input("Bot: Please enter your name: ")
                cursor_bookings.execute("SELECT * FROM bookings WHERE booking_id=? AND user_name=?", (booking_id, user_name))
                booking_details = cursor_bookings.fetchone()

                if booking_details:
                    return f"Booking Details: {booking_details[3]} for {booking_details[5]} on {booking_details[4]} with a ticket total of {booking_details[6]}"
                else:
                    print("Bot: No matching booking found. Let's try to find it with more details.")
                    return find_booking_id()
            elif unkown_booking_id == "cancel":
                return "I'm sorry you have stopped trying to show your booking"
            else:
                print("Bot: Invalid input. Please enter 'yes', 'no' or 'cancel'.")

    def find_booking_id():
        user_name = input("Bot: What name did you enter whilst making your booking? ")
        print("Bot: What movie did you enter whilst making your book (Type no to cancel)? ")
        movie, chatbot_state = choose_movie()
        if chatbot_state == True:
            return "I'm sorry that the movie you were trying to book was not available"
        
        print("Bot: Please enter a day you booked the movie (in YYYY-MM-DD format)? ")
        date, chatbot_state = choose_date()
        if chatbot_state == True:
            return "I'm sorry you couldn't decide on a date to book the movie"
        
        print("Bot: What time did you enter whilst making your booking?")
        time, chatbot_state = choose_time(movie)
        if chatbot_state == True:
            return "I'm sorry that the available times didn't suit you"
        
        cursor_bookings.execute("SELECT * FROM bookings WHERE user_name=? AND movie=? AND date=? AND time=?", (user_name, movie[1], date, time))
        booking = cursor_bookings.fetchone()
        
        if booking:
            print("Bot: This is your Booking ID: ", {booking[1]})
            return f"Booking Details: {booking[3]} for {booking[5]} on {booking[4]} with a ticket total of {booking[6]}"
        else:
            return "No matching booking found. Please try again."
            
    def update_booking(field, new_value, booking_edit):
        cursor_bookings.execute(f"UPDATE bookings SET {field} = ? WHERE id=?", (new_value, booking_edit[0]))
        conn_bookings.commit()
        return f"{field} updated successfully."

    def change_date(booking_edit):
        print("Bot: Choose date you would now like to book")
        date, chatbot_state = choose_date()
        if chatbot_state:
            return "Booking Process Stopped (edit date)", True
        update_booking('date', date, booking_edit)
        return "Date changed successfully.", False

    def change_time(booking_edit):
        cursor_bookings.execute("SELECT * FROM bookings WHERE id=?", (booking_edit[0],))
        movie_finder = cursor_bookings.fetchone()
        cursor.execute("SELECT * FROM movies WHERE title=?", (movie_finder[3],))
        movie = cursor.fetchone()
        time, chatbot_state = choose_time(movie)
        if chatbot_state:
            return "Booking Process Stopped (edit time)", True
        update_booking('time', time, booking_edit)
        return "Time changed successfully.", False

    def change_tickets(booking_edit):
        print("Bot: choose tickets you would now like to book")
        tickets, chatbot_state = choose_tickets()
        if chatbot_state:
            return "Booking Process Stopped (edit tickets)", True
        update_booking('tickets', tickets, booking_edit)
        return "Number of tickets changed successfully.", False

    def edit_booking():
        while True:
            print("Bot: Please choose an option: 1. change date |2. change time |3. change ticket |Type 'no' to exit")
            print("Bot: If you do not know your booking id, ask the chatbot find booking id as you will need it in the next steps")
            user_input = input("Bot: Enter Your choice: ")
            
            if user_input.lower() == 'no':
                return "I'm sorry you decided to stop the editing booking process"
            
            if user_input not in ['1', '2', '3']:
                print("Bot: Invalid input. Please enter a number between 1 and 3.")
                continue
            
            booking_id = input("Bot: Please enter your Booking ID: ")
            user_name = input("Bot: Please enter your name: ")
            cursor_bookings.execute("SELECT * FROM bookings WHERE booking_id=? AND user_name=?", (booking_id, user_name))
            booking_edit = cursor_bookings.fetchone()

            if not booking_edit:
                print("Bot: No matching booking found to edit, please try again.")
                continue

            # Call the chosen function
            if user_input == '1':
                response, chatbot_state = change_date(booking_edit)
            elif user_input == '2':
                response, chatbot_state = change_time(booking_edit)
            elif user_input == '3':
                response, chatbot_state = change_tickets(booking_edit)

            print(response)

            if chatbot_state:
                return "Bot: Edit booking process stopped."

    def change_name():
        while True:
            new_name = input("Please enter your new name: ")
            new_name = ' '.join(word.capitalize() for word in new_name.split())
            while True:
                confirm = input(f"You entered '{new_name}'. enter yes or no to confirm change ")
                if confirm.lower() == 'yes':
                    user_name = new_name
                    return f"Your name has been updated to {user_name}."
                elif confirm.lower() == 'no':
                    new_name = input("Please enter your new name: ")
                    new_name = ' '.join(word.capitalize() for word in new_name.split())
                else:
                    print("Invalid input. Please enter 'yes' or 'no'.")

    if 'show_movies' in response:
        movies = retrieve_movies(cursor)
        movie_list = '\n'.join([f"{movie[1]} ({movie[3]}) - {movie[4]}" for movie in movies])
        return movie_list

    if 'show_name' in response:
        return f"Your name is {user_name}"

    if 'book_movie' in response:
        return book_movie()
    
    if 'cancel_booking' in response:
        return cancel_booking(user_name)
    
    if 'show_genre' in response:
        return show_genre()
    
    if 'change_name' in response:
        return change_name()
    
    if 'show_booking' in response:
        return show_booking()
    
    if 'find_booking_id' in response:
        return find_booking_id()
    
    if 'edit_booking' in response:
        return edit_booking()

    if 'what_can_you_do' in response:
        print("Bot: I can book, cancel, show you a list of movie available")
        print("Bot: My other functions can show you your name and change your name")
        print("Bot: I can even tell you the description of the movie, if you use description before entering a movie")
        print("Bot: I can even tell you what type of movie it is, happy sad etc")
        return "I can even filter movies via genre, show your booking and find your booking id"

    return response

def process_intent(cosine_similarities, best_match_index, processed_input, intent_texts, data, user_name):
    if cosine_similarities[0][best_match_index] > 0.5:
        response = data[best_match_index][1]
        return chatbot_functions(response, user_name)
    else:
        # Check for exact keyword match
        if processed_input in intent_texts:
            index = intent_texts.index(processed_input)
            return data[index][1]
            
    return "I'm sorry, I don't understand your request"

# Intent matching for movies
def find_movie(user_input):
    processed_input = preprocess(user_input)
    user_vector = movie_tfidf_vectorizer.transform([processed_input])
    cosine_similarities = cosine_similarity(user_vector, movie_vectors)
    best_match_index = cosine_similarities.argmax()
    if cosine_similarities[0][best_match_index] > 0.5:
        movie_match = retrieve_movies(cursor)[best_match_index]
        return movie_match
    else:
        return "not_found"

# Outputs response for bot
def get_response(user_input, user_name):
    # Context Tracking
    global last_movie
    if 'description' in user_input.lower():
        movie_name = user_input.lower().replace('description', '').strip()
        movie = find_movie(movie_name)
        if movie != "not_found":
            last_movie = movie
            return f"Title: {movie[1]}\nGenre: {movie[2]}\nRelease Year: {movie[3]}\nDirector: {movie[4]}"
            
    elif ('movie' in user_input.lower() or 'film' in user_input.lower()) and any(keyword in user_input.lower() for keyword in ['scary', 'happy', 'sad', 'romantic', 'love', 'comedy', 'laughable', 'exciting', 'intense', 'futuristic', 'crime', 'drama', 'action', 'sci-fi', 'animation', 'adventure', 'musical', 'biography']):
        if last_movie is not None:
            genre = last_movie[2].lower()
            if 'scary' in user_input.lower() and genre == 'horror':
                return "Yes, it is a scary movie."
            elif ('laughable' in user_input.lower() or 'comedy' in user_input.lower()) and genre == 'comedy':
                return "Yes, it is a funny movie that will make you laugh."
            elif ('romantic' in user_input.lower() or 'love' in user_input.lower()) and genre == 'romance':
                return "Yes, it is a romantic movie that might make you cry."
            elif 'happy' in user_input.lower() and genre == 'musical':
                return "Yes, it is a happy movie with lots of songs."
            elif 'exciting' in user_input.lower() and genre == 'action':
                return "Yes, it is an action-packed movie full of excitement."
            elif 'intense' in user_input.lower() and genre == 'drama':
                return "Yes, it is a dramatic movie with intense moments."
            elif 'futuristic' in user_input.lower() and genre == 'sci-fi':
                return "Yes, it is a science fiction movie that will take you to another world."
            elif 'crime' in user_input.lower() and genre == 'crime':
                return "Yes, it is a crime movie."
            elif 'animation' in user_input.lower() and genre == 'animation':
                return "Yes, it is an animated movie."
            elif 'adventure' in user_input.lower() and genre == 'adventure':
                return "Yes, it is an adventure movie."
            elif 'biography' in user_input.lower() and genre == 'biography':
                return "Yes, it is a biographical movie."
            else:
                return "It's a great movie that you might enjoy."
        else:
            return "I'm not sure, you haven't mentioned a movie."
        
    else:
        # If user enters movie name, it will start to book movie
        movie = find_movie(user_input)
        if movie != "not_found":
            last_movie = movie
            print("Bot: You have selected the movie", movie[1])
            response = chatbot_functions('book_movie', user_name, movie)
            return response
    # get reposnse based on cosine sim and tfid vectors
    processed_input = preprocess(user_input)
    user_vector = intent_tfidf_vectorizer.transform([processed_input])
    cosine_similarities = cosine_similarity(user_vector, intent_vectors)
    best_match_index = cosine_similarities.argmax()
    response = process_intent(cosine_similarities, best_match_index, processed_input, intent_texts, data, user_name)
    return response

def chatbot_program():
    while True:
        user_name = input("Please enter your name: ")
        user_name = ' '.join(word.capitalize() for word in user_name.split())
        while True:
            confirm_user_name = input(f"Is {user_name} correct? (yes/no): ")
            if confirm_user_name.lower() == 'yes':
                break
            elif confirm_user_name.lower() == 'no':
                print("Let's try again.")
                user_name = input("Please enter your name: ")
                user_name = ' '.join(word.capitalize() for word in user_name.split())

        while True:
            user_input = input("You: ")
            if user_input.lower() == 'exit':
                print("Bot: Goodbye!")
                return
            response = get_response(user_input, user_name)
            if isinstance(response, str) and response.startswith("Your name has been updated to"):
                user_name = response.split()[-1]
            print("Bot:", response)

            if 'Anytime' in response:
                while True:
                    user_input = input("Do you want to make another booking? (yes/no): ").lower()
                    if user_input == 'yes':
                        break
                    elif user_input == 'no':
                        print("Restarting the chatbot :)")
                        break
                    else:
                        print("Invalid input. Please enter 'yes' or 'no'.")
                if user_input == 'no':
                    break

chatbot_program()

conn_bookings.close()
conn.close()