# Messaging application

Video demo: https://www.youtube.com/watch?v=OjKrU9_MJPE
## Overview
A client-server messaging application allowing users on the same
network connection to instantly send and receive text and file messages in real-time.

## Tools & Technologies
- Python 3.12
- TKinter library
- Threading
- SQLite3
- Sockets library

## Features
- GUI built with TKinter that allows users to easily interact with the application
- User authentication
- User searching and contacts management.
- Utilizing the Sockets library to enable Sending text and file messages with TCP protocol
- SQLite3 Database for storing users and messages
- Multithreading to handle continuous requests on client and server side without freezing the interface.

## Prerequisites
 - Python 3.12 

## Structure
 - [server.py](server.py): Responsible for handling data, processing messages, and connected clients
 - [client.py](client.py): Includes GUI logic and manages client-sided network communications

## How to run
1. Clone the repository by running `git clone https://github.com/Abdullahmohammadaref/messaging_application`.
2. Run `python server.py` then open two more terminals and run `python client.py` on each one of them.

The previous steps are for running the whole application on one machine. To allow 
different devices to communicate on the same network `py server.py` should be running 
on any machine connected to network, and other client machines can run `py client.py`.

!!IMPORTANT!!
However, The `server_ip` variable in the `__init__` function inside the `Client` class in [client.py](client.py) for each client machine should be changed to the
private ip address of the machine that will be running the [server.py](server.py) file if communication will be across multiple machines.

Note: To find
the private IP address simply open command prompt in the machine that will
run [server.py](server.py) then run `ipconfig`. Depending on whether the machine is using
Wi-Fi or Ethernet the private IP address will be displayed under the ”Default
Gateway” option.
