from tkinter import *
from socket import *
from threading import *
import os
from json import *
from datetime import *


class Client:
    def __init__(self):
        """
        initiate some important object variables
        """
        # encoding format
        self.format = 'utf-8'
        # Fetch the IP address from the current server machine.
        # NOTE: if the client machine is not the same as the server machine then this have to be changed to the private ip address of the server
        # Moreover both the client and the server have to be connected to the same network
        self.server_ip = gethostbyname(gethostname())
        # Create a TCP internet socket.
        self.client = socket(AF_INET, SOCK_STREAM)
        # connect the sockets to  the server
        self.client.connect((self.server_ip, 8000))
        # loge din user username
        self.username = ""
        self.conversations = {}
        self.current_conversation_name = None
        self.current_contact = None
        self.current_user_contacts = None
        # current directory of the client.py file
        self.main_directory = os.path.dirname(os.path.realpath(__file__))
        self.temp_conversation_name = None
        # start a thread to constantly recieve requests from the server
        Thread(target=self.handle_receive_from_server).start()

    def send_to_server(self, message, type):
        """
        This function is responsible for sending string and file messages to the server.
        same sending functionality that is explained in server.py send_to_client function
        """
        if type == "string":
            message = message.encode(self.format)
            message_length = str(len(message)).encode(self.format)
            message_length += b' ' * (64 - len(message_length))
            self.client.send(message_length)
            self.client.send(message)
        elif type == "file":
            path, file_name = message.split("\x1f")
            file_size = os.path.getsize(path)
            self.send_to_server(f"file_send_to_server:{file_name}:{str(file_size)}", "string")
            with open(path, 'rb') as file:
                data = file.read()
                self.client.sendall(data)

    def receive_from_server(self):
        """
        Handles receiving string messages from the server in the same way (explained in server.py receive_from_client function )that the server handles receiving string messages from the client
        """
        message_length = int(self.client.recv(64).decode(self.format))
        if message_length:
            message = self.client.recv(message_length).decode(self.format)
            return message
        return None

    def handle_receive_from_server(self):
        """
        Handles various request types that are received from the server in the same way (explained in server.py handle_receive_from_client function )that the server handles various request types that are received from the server
        """
        while True:
            message = self.receive_from_server()
            if message.startswith("registration_confirmed"):
                """
                handles confirmed registration requests and loads sucess message
                """
                ui.login_or_register_ui()
                ui.alert(message)
            elif message.startswith("login_confirmed"):
                """
                handles confirmed login request requests:
                loging in the user
                create a file that will store his recived files (if it doesn't exist)
                receive a list of usrnames who are contacts of the current user
                load the contacts GUI page
                """
                username = message[16:]
                self.username = username
                os.makedirs(f"{self.username}_files", exist_ok=True)
                self.main_directory = os.path.dirname(os.path.realpath(__file__))
                self.files_dir = os.path.join(self.main_directory, f"{self.username}_files")
                """
                receive the usernames of the contacts of the user
                """
                # an array that will store all the byte packets to keep track of the order or received messages
                all_packets_array = bytearray()
                data_sent = False
                while not data_sent:
                    # prepare to receive a max of 4096 bytes of data
                    data = self.client.recv(4096)
                    # extend the capacity of the byte array to be able to store the data of the new coming packet
                    all_packets_array.extend(data)
                    # makes sure that the array length is not smaller than the length of the end byte tag
                    if len(all_packets_array) >= 6:
                        # check if the array ends with the end byte tag
                        if all_packets_array[-6:] == b"<DONE>":
                            # remove the end byte tag
                            all_packets_array = all_packets_array[:-6]
                            # stop the loop
                            data_sent = True

                # converted to bytes, decode, convert back to normal format
                contacts_json = bytes(all_packets_array).decode(self.format)
                self.current_user_contacts = loads(contacts_json)


                ui.contacts()
            elif message.startswith("logout_confirmed"):
                """
                handles confirmed logout requests, logs the our out, and loads the login or register page
                """
                self.username = ""
                self.conversations = {}
                self.current_conversation_name = None
                self.current_contact = None
                self.current_user_contacts = None
                self.temp_conversation_name = None
                ui.login_or_register_ui()
            elif message.startswith("username_exist_message"):
                """
                Handles receiving a username_exist message from the server that approved the existence of a username in the database
                change the current conversation and contact names to accommodate with this username
                send a chat_messages_request to the server
                """
                contact_username = message[23:]
                conversation_name = self.generate_conversation_name(self.username, contact_username)
                self.current_conversation_name = conversation_name
                self.current_contact = contact_username
                self.send_to_server(f"chat_messages_request:{self.username}:{contact_username}", "string")
            elif message.startswith("username_dont_exist_message"):
                """
                handles receiving a username_dont_exist message from the server, loads an error message in the UI to inform the user
                """
                message = message[28:]
                username_dont_exist_message, username = message.split(":")
                ui.alert(username_dont_exist_message)
            elif message.startswith("error_message"):
                """
                handles receiving an error message from the server and displays it in the UI for the user to see it
                """
                error_message = message[14:]
                ui.alert(error_message)
            elif message.startswith("temp_client_username_update"):
                """
                handles changing the temp_client_username variable when requested by the server
                """
                message = message[28:]
                username_1, username_2 = message.split(":")
                conversation_name = self.generate_conversation_name(username_1, username_2)
                self.temp_conversation_name = conversation_name
            elif message.startswith("messages_table"):
                """
                handles receiving table messages from the server
                """
                all_packets_array = bytearray()
                data_sent = False
                while not data_sent:
                    data = self.client.recv(4096)
                    all_packets_array.extend(data)
                    if len(all_packets_array) >= 6:
                        if all_packets_array[-6:] == b"<DONE>":
                            all_packets_array = all_packets_array[:-6]
                            data_sent = True

                # converted to bytes, decode, convert back to normal format
                conversation_json = bytes(all_packets_array).decode(self.format)
                conversation_not_json = loads(conversation_json)


                if self.temp_conversation_name == self.current_conversation_name:

                    self.conversations[self.current_conversation_name] = conversation_not_json
                    ui.contact(self.current_conversation_name, self.current_contact)
            elif message.startswith("messages_files"):
                """
                handles receiving files messages from the server in the same way (explained in server.py file_send_to_server function ) that the server handles recieving file messages taht are send from the client
                """
                message = message[15:]
                file_name, file_size = message.split("\x1f")
                file_size = int(file_size)
                file_path = os.path.join(f"{self.username}_files", file_name)
                # only write the reception file bytes if these two variables are equal, else don't because this indicates that the user is not currently opening this conversation
                if self.temp_conversation_name == self.current_conversation_name:
                    with open(file_path, "wb") as file:
                        received = 0
                        while received < file_size:
                            remaining = file_size - received
                            data = self.client.recv(min(4096, remaining))
                            file.write(data)
                            actual_received = len(data)
                            received += actual_received
                else:
                    received = 0
                    while received < file_size:
                        remaining = file_size - received
                        data = self.client.recv(min(4096, remaining))
                        actual_received = len(data)
                        received += actual_received

    def generate_conversation_name(self, username_1, username_2):
        """
        Responsible for generatign a conversatin name between two clients when needed.
        client names are ordred alphabetically in the conversation name
        """
        users_unsorted = [username_1, username_2]
        users_sorted = sorted(users_unsorted)
        return f"{users_sorted[0]}-{users_sorted[1]}"

class UI:
    """
    This class is only responsible of handeling all UI related tasks
    """

    def __init__(self):
        self.ui = Tk()
        # set the size of the ui
        self.ui.geometry("400x300")
        # give a title for the window (the name of the application)
        self.ui.title("NetChat")
        # creates a client object
        self.client = Client()
        self.alert_label = Label(self.ui, text="", fg="red")
        # loads the login or register ui
        self.login_or_register_ui()

    def login_or_register_ui(self):
        """
        Clear previous GUI and prompts the client to either login or register
        """
        self.clear_window()
        self.ui.title("NetChat")
        login = Button(self.ui, command=self.login_ui, text="Login")
        login.pack()
        register = Button(self.ui, command=self.register_ui, text="Register")
        register.pack()

    def register_ui(self):
        """
        Clear previous GUI and prompts the client to enter his a username and password for registration
        """
        self.clear_window()
        back = Button(self.ui, command=self.login_or_register_ui, text="Back")
        back.pack()

        username_label = Label(self.ui, text="Username:")
        username_label.pack()
        username = Entry(self.ui)
        username.pack()

        password_label = Label(self.ui, text="Password:")
        password_label.pack()
        password = Entry(self.ui)
        password.pack()
        # after submission a registration request will be sent to the server
        submit = Button(self.ui, command=lambda: self.client.send_to_server(f"register:{username.get().lower()}:{password.get()}", "string"), text="Register")
        submit.pack()

    def login_ui(self):
        """
        Clear previous GUI and prompts the client to enter his username and password for login
        """
        self.clear_window()

        back = Button(self.ui, command=self.login_or_register_ui, text="Back")
        back.pack()

        username_label = Label(self.ui, text="Username:")
        username_label.pack()
        username = Entry(self.ui)
        username.pack()

        password_label = Label(self.ui, text="Password:")
        password_label.pack()
        password = Entry(self.ui)
        password.pack()
        # sends a login request to the server after submitting
        submit = Button(self.ui, command=lambda: self.client.send_to_server(f"login:{username.get().lower()}:{password.get()}", "string"), text="Login")
        submit.pack()

    def alert(self, alert):
        """
        This function is responsible for displaying any success or error messages on any current window tab when called
        """
        if self.alert_label:
            self.alert_label.destroy()

        self.alert_label = Label(self.ui, text=alert, fg="red")
        self.alert_label.pack()

    def contacts(self):
        """
        after login the user is redirected to this page
        here he can logout, search for a user, or select one of his contacts
        """
        self.client.current_conversation_name = None
        self.clear_window()
        self.ui.title(self.client.username)
        # sends a logout request to the server
        logout = Button(self.ui, command=lambda: self.client.send_to_server(f"logout:{self.client.username}", "string"), text="Logout")
        logout.pack()

        client_username_search_label = Label(self.ui, text="Search for a username:")
        client_username_search_label.pack()
        client_username_search = Entry(self.ui)
        client_username_search.pack()
        # prevents the user from inputting his own username, but if other username is entered then a username_exist request is sent to the server to find out if the username actually exist in the database
        search = Button(self.ui, command=lambda: self.alert("You cannot send a message to your self") if client_username_search.get() == self.client.username else self.client.send_to_server(f"username_exist:{client_username_search.get().lower()}", "string"), text="Search")
        search.pack()

        password_label = Label(self.ui, text="My contacts:")
        password_label.pack()

        if self.client.current_user_contacts is None:
            pass
        else:
            contacts_buttons = {}
            for contact in self.client.current_user_contacts:
                # almost same functionality as the  search Button
                contacts_buttons[contact] = Button(self.ui, command=lambda: self.client.send_to_server(f"username_exist:{contact}", "string"), text=contact)
                contacts_buttons[contact].pack()

    def contact(self, conversation_name, contact_name ):
        """
        Responsible for:
        1-displaying messages between users
        2-Identifying who is the sender
        3-displaying the message and time it was sent
        4-Allowing users to send a text or a file message
        """
        self.clear_window()
        # create a canvas to allow scrolling
        canvas= Canvas(self.ui, scrollregion=(0,0,2000,5000))

        # create a frame to house all ui elements
        frame = Frame(canvas)
        # create a scrollable windows for the frame
        canvas.create_window((0, 0), window=frame, anchor='nw')

        # button that allow user to go back to the contacts page
        back = Button(frame, command=self.contacts, text="back")
        back.pack()

        # display the current contact name
        contact = Label(frame, text=contact_name)
        contact.pack()

        """
        Display all messages between users
        """
        messages_label = Label(frame, text="Messages:")
        messages_label.pack()
        messages = self.client.conversations[conversation_name]
        if messages is None:
            pass
        else:
            for message in messages:
                if message["sender"] == contact_name:
                    sender_label = Label(frame, text=message["sender"], fg="purple")
                    sender_label.pack()

                    message_label = Label(frame, text=message["message"], fg="purple")
                    message_label.pack()

                    date_time_label = Label(frame, text=message["date_time"], fg="purple")
                    date_time_label.pack()
                else:
                    sender_label = Label(frame, text=message["sender"], fg="blue")
                    sender_label.pack()

                    message_label = Label(frame, text=message["message"], fg="blue")
                    message_label.pack()

                    date_time_label = Label(frame, text=message["date_time"], fg="blue")
                    date_time_label.pack()

        ## send text message
        text_label = Label(frame, text="send text message:")
        text_label.pack()
        message_text = Entry(frame)
        message_text.pack()
        # send a new message request and adds the contact to the current contacts if he is not added there
        send_text = Button(frame, command=lambda: (self.client.send_to_server(f'new_message\x1ftext_message\x1f{self.client.username}\x1f{contact_name}\x1f{message_text.get()}', "string"), self.client.current_user_contacts.append(contact_name) if contact_name not in self.client.current_user_contacts else None),text="Send_text")
        send_text.pack()

        ## send file message
        ## !!! THIS FIELD ONLY ACCEPTS AN ABSOLUTE PATH OF THE FILE !!!
        file_label = Label(frame, text="send file message:")
        file_label.pack()
        message_file = Entry(frame)
        message_file.pack()
        #first send the file to the server (a unique file server is created using date_time so it doesnt clash with other file names, moreover the special seperator \x1f is used to prevent errors)
        #Then send a new message request
        send_file = Button(frame, command=lambda time = datetime.now(): (self.client.send_to_server(f"{message_file.get()}\x1f{self.client.username}-{contact_name}_{time.strftime("%Y-%m-%d_%H-%M-%S")}_{os.path.basename(message_file.get())}","file"), self.client.send_to_server(f'new_message\x1ffile_message\x1f{self.client.username}\x1f{contact_name}\x1f{self.client.username}-{contact_name}_{time.strftime("%Y-%m-%d_%H-%M-%S")}_{os.path.basename(message_file.get())}', "string")), text="Send_file")
        send_file.pack()

        canvas.pack(expand=True, fill="both")
        # allow scrolling with mouse wheel
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(-int(event.delta / 60), "units"))

    def update_messages(self, sender, message):
        """
        Responsible for displaying new messages in real time
        """
        sender_label = Label(self.ui, text=sender)
        sender_label.pack()

        message_label = Label(self.ui, text=message)
        message_label.pack()

        date_time_label = Label(self.ui, text=f"{datetime.now()}")
        date_time_label.pack()

    def clear_window(self):
        """
        destroy all UI elements
        """
        for widget in self.ui.winfo_children():
            widget.destroy()

    def start(self):
        """
        Start the UI loop
        """
        self.ui.mainloop()


if __name__ == '__main__':
    # creates a UI Object
    ui=UI()
    # calls the start() function to keep the ui running at all times
    ui.start()