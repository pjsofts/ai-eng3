# past_conversation.py — earlier turns of a long session, used by step 8.
# About 1,000 tokens: too much for step 8's tiny context window, on purpose.
# The decisions to remember are marked with ★ in the comments.

PAST_MESSAGES = [
    {"role": "user", "content":
        "I want to build a small notes app for the terminal. Help me plan it. "
        "It should let me write a note, add tags, and find notes later. I am a "
        "beginner with Python, so please keep things simple."},
    {"role": "assistant", "content":
        "Happy to help. Let's keep the first version very small. A note has a title, "
        "a body, a list of tags, and the date it was created. You need four commands: "
        "add a note, list notes, search notes by a word or a tag, and delete a note. "
        "We can store everything in one file at first, and move to a database if it "
        "grows. For the interface, a simple command line is enough: python app.py add, "
        "python app.py list, and so on. Later we can add a small web page so you can "
        "read your notes in the browser. Do you already have a name for the project? "
        "A name helps when you create the folder, the README and the config file."},

    # ★ the name
    {"role": "user", "content":
        "Let's call it Pocket Notes. What should I use to store the notes? A friend "
        "said I should use PostgreSQL because that's what real companies use."},
    {"role": "assistant", "content":
        "Pocket Notes is a good name. About storage: PostgreSQL is excellent, but it is "
        "a server you have to install, start, configure and keep running, and it needs "
        "a user and a password. For a personal notes app with a few thousand notes that "
        "is a lot of work for no benefit. SQLite is a better fit here. It is a database "
        "in a single file, it comes with Python (import sqlite3), there is nothing to "
        "install or run, and it is fast for this size. You still write real SQL, so "
        "what you learn carries over to PostgreSQL later. If Pocket Notes ever becomes "
        "a service with many users, you can move the data then. My suggestion: start "
        "with SQLite, keep all the database code in one file called storage.py, so "
        "changing the database later only touches that one file."},

    # ★ the database
    {"role": "user", "content":
        "OK, convinced. We use SQLite, not PostgreSQL. Now, the web page you "
        "mentioned. Which port should it run on? My config says 8080 right now."},
    {"role": "assistant", "content":
        "Port 8080 works, but it is a very common default: other tools on your machine, "
        "like a Java server, a proxy or another course project, often use it already, and "
        "then your app fails to start with 'address already in use'. Many small Python and "
        "JavaScript projects use port 3000 for local development. It doesn't matter much "
        "which number you choose, as long as it is free and you write it in one place. "
        "Keep it in config.json, read it once when the app starts, and never type the "
        "number anywhere else in the code. Then changing it later is a one-line edit."},

    # ★ the port
    {"role": "user", "content":
        "Let's use port 3000 then. I'll change config.json later. What about tags? "
        "Should a tag be its own table?"},
    {"role": "assistant", "content":
        "In a big app, yes: a tags table and a note_tags table that connects notes to "
        "tags. That is the 'proper' design and it makes some searches faster. For Pocket "
        "Notes version 1, keep it simpler: store the tags as one text column, separated by "
        "commas, like 'work,ideas,python'. Searching by tag is then a LIKE query. It is not "
        "perfect: a search for 'py' would also match 'python', so search for ',py,' with "
        "commas around the stored value. When this becomes a real problem you can move to "
        "the two-table design without changing how the user uses the app. Write a small "
        "function, find_by_tag(tag), so the rest of the code does not care how tags are "
        "stored."},

    # ★ the deadline and the bug
    {"role": "user", "content":
        "Makes sense. One more thing: the team wants version 1.0 out this Friday. Sara "
        "found that the login page crashes when the password is empty, she's fixing it. "
        "What else should we do before Friday?"},
    {"role": "assistant", "content":
        "With Friday as the deadline, I would only do what is needed for 1.0 and write "
        "everything else down for later. Before Friday: one, Sara's fix for the empty "
        "password crash, plus a test so it never comes back. Two, change the port in "
        "config.json from 8080 to 3000, as we decided. Three, write a short README: what "
        "the app does, how to install it, and the four commands. Four, try every command "
        "once on a fresh copy of the project, so you know a new user can run it. After "
        "Friday, in version 1.1: export all notes to one markdown file, a dark theme for "
        "the web page, and maybe the proper tags tables. Keep that list in todo.txt so "
        "nobody has to remember it. Shall I help with the README first?"},

    {"role": "user", "content":
        "Not now, thanks. I'll come back to it after lunch."},
    {"role": "assistant", "content":
        "Sounds good. When you're back, we can start with the README or the port change, "
        "whichever you prefer. Enjoy your lunch."},
]
