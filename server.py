from socket import *
from threading import *
from sqlite3 import *
from json import *
import os


class Server:
    """
    This server object will be responsible for:
    1-sending and receiving messages to and from the clients
    2-processing those messages and querying the database
    3-storing tables in a database and files in a "files" folder
    """

    def __init__(self):
        # set the decoding encoding format of all messages to utf-8
        self.format = 'utf-8'
        # Fetch the IP address from the current server machine.
        self.server_ip = gethostbyname(gethostname())
        # Create a TCP internet socket.
        self.server = socket(AF_INET, SOCK_STREAM)
        # Bind the socket to the IP address and a PORT number
        self.server.bind((self.server_ip, 8000))

        # Create a dictionary variable that will store the clients and their usernames if available.
        # key = username, value = client object
        self.clients = {}
        # get the absolute path of the directory of this python file
        self.main_directory = os.path.dirname(os.path.realpath(__file__))
        # Creates a folder that will store all the files.
        os.makedirs("files", exist_ok=True)
        # Get the absolute path of the newly create "files" directory.
        self.files_dir = os.path.join(self.main_directory, "files")
        # Call a function that will set up the database
        self.database_setup()
        # Call a function that will start the server
        self.start_server()

    def database_setup(self):
        """
        This function creates a database with a table to store users data and a table to store messages data.
        """
        # opens the messaging.db sqlite3 database file or creates if it doesn't exist.
        # Then closes it after we are done using it.
        with connect("messaging.db") as connection:
            # create a cursor which will allow us to execute sql commands.
            cursor = connection.cursor()
            # create a Users table if it doesn't exist.
            cursor.execute("""
                            CREATE TABLE IF NOT EXISTS Users
                                (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    username TEXT NOT NULL UNIQUE,
                                    password TEXT NOT NULL                       
                                )
                           """)
            # create a Messages table if it doesn't exist.
            cursor.execute("""   
                            CREATE TABLE IF NOT EXISTS Messages
                                (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    sender_id INTEGER NOT NULL,
                                    recipient_id INTEGER NOT NULL,
                                    date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    
                                    message TEXT NOT NULL,
                                    message_type TEXT NOT NULL
                                )                     
                            """)
            # commit the previously executed sql commands with cursor to the database (always should be done when editing data )
            connection.commit()

    def send_to_client(self, message, client, type):
        """
        This function is responsible for sending string, table, file and list messages to the client
        """
        if type == "string":
            """
            Send the string message length first to the client so the client knows the length of the next coming message (the actual message)
            Then send the actual string message
            """
            #message is encoded to bytes in utf-8 format
            message = message.encode(self.format)
            # find the encoded message in bytes
            message_length = str(len(message)).encode(self.format)
            # makes sure the client receives exactly 64 bytes
            # this includes the message length in bytes
            # then extra spaces are stripped by the client and message length is stored
            message_length += b' ' * (64 - len(message_length))
            # first send the message length to the client
            client.send(message_length)
            # the then send the actual message to  the client
            client.send(message)
        elif type == "table":
            """
            First send a string message that inform the client that a Json table will be sent
            encode then send the table as segments
            send the an end tag to let the client know that all segments have been sent
            """
            self.send_to_client("messages_table", client, "string")
            messages = message.encode(self.format)
            # using sendall to transfer large data in chunks/packets
            client.sendall(messages)
            # a byte tag is sent to indicate when the data transfer is over
            client.send(b"<DONE>")
        elif type == "file":
            """
            1- Find the current client username
            2- select all messages with type attribute == file_message and reciver = current_client_username
            3- find the path of each of those files and get its size
            4- send a string to the client to tell him that we are sending him a file, the file name, and the file size
            5- open each file and read then send all as segments 
            """
            current_client_username = None
            for key, value in self.clients.items():
                if value == client:
                    current_client_username = key
            for msg in message:
                if msg["message_type"] == "file_message":
                    if msg["sender"] != current_client_username:
                        file_path = os.path.join(self.files_dir, msg["message"])
                        file_size = os.path.getsize(file_path)
                        self.send_to_client(f"messages_files\x1f{msg['message']}\x1f{str(file_size)}", client, "string")
                        with open(file_path, 'rb') as file:
                            data = file.read()
                            client.sendall(data)
        elif type == "list":
            """
            Converts the list into Json format and encode it then send it the same way as a table
            """
            list_json = dumps(message).encode(self.format)
            client.sendall(list_json)
            client.send(b"<DONE>")

    def receive_from_client(self,client, type):
        """
        This function is used to receive string messages from a client
        first the string length is received then the actual string message is received and returned
        """
        if type == "string":
            message_length = int(client.recv(64).decode(self.format))
            if message_length:
                message = client.recv(message_length).decode(self.format)
                return message
        return None

    def handle_receive_from_client(self ,client):
        """
        This function handles all type of messages(like strings and files) that the client sent to the server
        first it receives a string message which are written this format: f"{request_name}:{parameter1}:{parameter2}:{parameter3}:......etc"
        then it removes the {request_name}: from the message after knowing its purpose.
        then it assigns each of those parameter values to a variable
        lastly call the appropriate function that will fulfill the request
        """
        # keep receiving messages while this thread is active
        while True:
            # call a function that receive a string message
            # which starts with the name of the request that the client is requesting from the server
            message = self.receive_from_client(client, "string")
            if message.startswith("register"):
                """
                handle receiving a user registration request from the client,
                and call the register function
                """
                username, password = message[9:].split(":")
                self.register(username, password, client)
            elif message.startswith("login"):
                """
                handle receiving a user login request from the client,
                and call the login function
                """
                username, password = message[6:].split(":")
                self.login(username, password, client)
            elif message.startswith("logout"):
                """
                handle receiving a user logout request from the client,
                and call the logout function
                """
                username = message[7:]
                self.logout(username, client)
            elif message.startswith("username_exist"):
                """
                handle receiving a request to find if a user with a specific username exists,
                and call the username_check function
                """
                message = message[15:]
                self.username_check(message, client)

            elif message.startswith("chat_messages_request"):
                """
                Responsible for sending the text and file messages to the user when he opens a chat and the messages need to be loaded.
                Acts similar to a new_message request but only fetches and sends data (no new data is being added)
                """
                message = message[22:]
                current_client_username, other_client_username = message.split(":")

                table_rows = self.select_messages_from_db(current_client_username, other_client_username, True)

                self.send_to_client(f"temp_client_username_update:{current_client_username}:{other_client_username}", client, "string")

                self.send_to_client(table_rows, client, "table")

                files = self.select_messages_from_db(current_client_username, other_client_username, False)
                if files is None:
                   pass
                else:
                    self.send_to_client(files, client, "file")
            elif message.startswith("new_message"):
                """
                Handles receiving a new message, that can be a file name or a text message
                Calls the function to store the message in the database
                calls a function to send the text messages and file names to the client receiver and the sender clients
                Calls a function to send the file messages to the reciver client
                """
                message = message[12:]
                # \x1f is a special seperator that is used to separate text segments with a peace in mind that no other character in the string will be the same as the seperator
                message_type, current_client_username, other_client_username, text = message.split("\x1f")
                self.insert_message_to_db(current_client_username, other_client_username, text, message_type)
                table_rows = self.select_messages_from_db(current_client_username, other_client_username, True)
                self.send_to_client(table_rows, client, "table")

                for key, value in self.clients.items():
                    if key == other_client_username:
                        # get this message (the username of the sender client) is received by the receiver client and later when files are sent it is compared with the current contact that the client is opening
                        # if names don't match this mean that the receiver is not actually opening the chat, or he is in another chat, so the file message will not be received
                        # (however the messages not lost because when the client logs in and load the chat between him and the sender client, new files will automatically be sent)
                        self.send_to_client(f"temp_client_username_update:{current_client_username}:{other_client_username}", value,"string")
                        self.send_to_client(table_rows, value, "table")

                        # select all the file names that we want to send in the database, but converting them into json format (JSON = false)
                        # we do this just to know the names of the files be fore sending them
                        files = self.select_messages_from_db(current_client_username, other_client_username, False)
                        if files is None:
                            pass
                        else:
                            #send the files to the reciver
                            self.send_to_client(files, value, "file")

            elif message.startswith("file_send_to_server"):
                """
                handle receiving a file from the client,
                and call the file_send_to_server function to receive the file and store it in the server
                """
                message = message[20:]
                file_name, file_size = message.split(":")
                self.file_send_to_server(file_name, file_size, client)
            elif message.startswith("update_current_user_contacts_request"):
                """
                handle receiving an update request for the contacts of the user user in real time,
                tells the client we are sending an updated contacts list
                create that list and send it
                """
                username = message[37:]
                self.send_to_client(f"update_current_user_contacts", client, "string")
                contacts_usernames = self.select_contacts(username, client)
                self.send_to_client(contacts_usernames, client, "list")

    def register(self, username, password, client):
        """
        This function opens the database, checks if a user with the same username exist,
        if yes then it sends an error message to the client,
        if no then it inserts the new user information into the database
        """
        with connect("messaging.db") as connection:
            cursor = connection.cursor()
            # Selects all rows where the value of the column "username" is equal to the username that the client want to register.
            cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
            # first get the first row from the previously executes SELECT command in sql
            # if a rows is selected(first row not None) then this mean that there is already a user with this username
            if cursor.fetchone():
                # call a function to send an error message to the client to tell him that this username already exist
                self.send_to_client("error_message:Username already exists", client, "string")
            # else if no rows are selected(first row is None) then this mean no user in the database have the same username,
            # Therefore, we are allowed to proceed in creating/registering the new user
            else:
                # Insert the username and password of the new user into the database
                cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", (username, password))
                # commit this change in the Users table to the database
                connection.commit()
                # call a function to send a success message to the client to tell him that registration has been done.
                self.send_to_client(f"registration_confirmed:{username}", client, "string")

    def login(self, username, password, client):
        """
        This function opens the database, checks if a user with the same username and password exist,
        if no then it sends an error message to the client,
        if yes then: 1- assign this username to this client
                     2- send a login authorization message to the client
                     3- send the contacts of this user to the client user
        """
        with connect("messaging.db") as connection:
            cursor = connection.cursor()
            # Selects all rows where the values of the columns "username" and "password" are the same as those that the user is trying to login with .
            cursor.execute("SELECT * FROM Users WHERE username = ? AND password = ?", (username, password))
            # first get the first row from the previously executes SELECT command in sql
            # if a rows is selected(first row not None) then this mean that there a user with this username and password
            if cursor.fetchone():
                # Adds a new row to the self.clients dictionary where the key is the username and the value is the current connected client
                self.clients[username] = client
                # call the send_to_client function and send a login authorization message to the client
                self.send_to_client(f"login_confirmed:{username}", client, "string")
                # call the self.select_contacts_and_send function that will send all the contacts usernames of this user
                contacts_usernames= self.select_contacts(username, client)
                self.send_to_client(contacts_usernames, client, "list")
            # else if no rows are selected(first row is None) then this mean no user in the database have the same username and password
            else:
                # call a function to send an error message to the client to tell him that this username and password combination doesn't exist
                self.send_to_client("error_message:Username or password are not correct", client, "string")

    def logout(self,username, client):
        """
        This function handles user logout.
        It just removes the user from self.clients and send a logout confirmation to the client
        """
        self.clients.pop(username)
        self.send_to_client(f"logout_confirmed", client, "string")

    def select_contacts(self, username, client):
        """
        Extracts all the usernames of users who are contacts with a specific user and add them to a list then return it.
        this means that every single user in the messages table who had any message sent or received to or from that specific user is included in the list of usernames.
        """
        with connect("messaging.db") as connection:
            cursor = connection.cursor()
            # Selects all user ids where the value of the "username" column is the same as that of the current client.
            cursor.execute("SELECT id FROM Users WHERE username = ?", (username,))
            # select the first and only row and column from this list of tuples that was extracted from the database,
            # and store it into a username_id variable
            username_id = cursor.fetchone()[0]
            # select sender_id and recipient_id columns of all Messages rows where the sender_id or the recipient_id is equal to the current sender_id
            cursor.execute("SELECT sender_id, recipient_id FROM Messages WHERE sender_id = ? OR recipient_id = ? ",(username_id, username_id))
            # store all the messages rows in a variable
            messages_with_client = cursor.fetchall()
            # create a list that will store all contact usernames
            contacts_usernames = []
            # if there are selected rows(messages_with_client is not none)
            if messages_with_client:
                # iterate over every single message in the list
                for message in messages_with_client:
                    # if the first column(sender_id) value of this row is not the id of the current user
                    if message[0] != username_id:
                        # we select the username from the Users table who have the same id as the current row
                        cursor.execute("SELECT username FROM Users WHERE id = ?", (message[0],))
                        # select the first and only row and column from this list of tuples that was extracted from the database,
                        # and store it into a id_username variable
                        id_username = cursor.fetchone()[0]
                        # check if this username is  not already inside the list of contacts_usernames to avoid duplicates,
                        if id_username not in contacts_usernames:
                            # add the username to the list of contacts_usernames
                            contacts_usernames.append(id_username)
                    # else if the second column(recipient_id) value of this row is not the id of the current user
                    elif message[1] != username_id:
                        # we select the username from the Users table who have the same id as the current row
                        cursor.execute("SELECT username FROM Users WHERE id = ?", (message[1],))
                        # select the first and only row and column from this list of tuples that was extracted from the database,
                        # and store it into a id_username variable
                        id_username = cursor.fetchone()[0]
                        # check if this username is  not already inside the list of contacts_usernames to avoid duplicates,
                        if id_username not in contacts_usernames:
                            # add the username to the list of contacts_usernames
                            contacts_usernames.append(id_username)
            # return the list of contacts_usernames
            return contacts_usernames

    def file_send_to_server(self, file_name, file_size, client):
        """
        This function is responsible for receiving a file message from a client
        """
        file_size = int(file_size)
        file_path = os.path.join(self.files_dir, file_name)
        with open(file_path, "wb") as file:
            received = 0
            # keep receiving chunks until the total received chunked are grater than or equal to the file size
            while received < file_size:
                # makes sure the chunk size is 4096 bytes or lower
                chunk_size = min(4096, file_size - received)
                # receive the file chunk
                data = client.recv(chunk_size)
                # write the file chunk
                file.write(data)
                received += chunk_size

    def username_check(self, username, client):
        """
        This function checks if a username exists in the database or not and sends a response back to the client
        """
        with connect("messaging.db") as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
            if cursor.fetchone():
                self.send_to_client(f"username_exist_message:{username}", client, "string")
            else:
                self.send_to_client(f"username_dont_exist_message:user dont exist:{username}", client, "string")

    def select_messages_from_db(self, current_client, other_client, json = False):
        """
        Select all messages between two users then either return then as a list of dictionaries (table) or a JSON formatted list of dictionaries (JSON table).
        """
        with connect("messaging.db") as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM Users WHERE username = ?", (current_client,))
            current_client_id = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM Users WHERE username = ?", (other_client,))
            other_client_id = cursor.fetchone()[0]
            cursor.execute("SELECT * FROM Messages WHERE (sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?) ORDER BY date_time ", (current_client_id, other_client_id, other_client_id, current_client_id))
            messages = cursor.fetchall()


        messages_rows_as_dictionaries_list = []
        for message in messages:

            messages_rows_as_dictionaries_list.append({
                "sender": message[1],
                "receiver": message[2],
                "date_time": message[3],
                "message": message[4],
                "message_type": message[5]
            })

        for dictionary in messages_rows_as_dictionaries_list:
            if dictionary["sender"] == current_client_id:
                dictionary["sender"] = current_client
            else:
                dictionary["sender"] = other_client

            if dictionary["receiver"] == other_client_id:
                dictionary["receiver"] = other_client
            else:
                dictionary["receiver"] = current_client
        # if Jsont is true then return the table In a JSON format (Not in a JSON format)
        if json:
            messages_json= dumps(messages_rows_as_dictionaries_list)
            return messages_json
        # if Jsont is true then return the table (Not in a JSON format)
        else:
            return messages_rows_as_dictionaries_list

    def insert_message_to_db(self, sender, reciver, text, message_type):
        """
        This function is responsible for inserting a new message into the database
        """
        with connect("messaging.db") as connection:
            cursor = connection.cursor()
            # Fetches the id or the sender user
            cursor.execute("SELECT id FROM Users WHERE username = ?", (sender,))
            sender_id = cursor.fetchone()[0]
            # fetches the id of the reciver user
            cursor.execute("SELECT id FROM Users WHERE username = ?", (reciver,))
            reciver_id = cursor.fetchone()[0]
            # insert he message sender_id, recipient_id, message and message type row into the Messages table in the database
            cursor.execute("INSERT INTO Messages (sender_id, recipient_id, message, message_type) VALUES (?, ?, ?, ?)", (sender_id, reciver_id, text, message_type))
            connection.commit()

    def start_server(self):
        """
        This function starts the server and make it constantly look for connection requests from client servers.
        Then it create and start a thread for each client server.
        This allows the server to send and receive messages from multiple client servers at once without clients effecting each other messages.
        """
        # Start the server
        self.server.listen()
        # Prepare the server to accept a new client as long as the server is running.
        while True:
            # Get the values of the client socket object(client) and the client private IP address (address).
            client, address = self.server.accept()
            print(f"client with ip address of {address} have connected to the server")
            # Create and start a new thread for the client,
            # and assign this thread to a function that will handle all received messages from the client
            Thread(target=self.handle_receive_from_client, args = (client,)).start()


if __name__=='__main__':
    # Create a server object
    server=Server()

    




