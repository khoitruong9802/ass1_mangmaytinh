import socket
from threading import Thread
import os
from shutil import copyfile
from pathlib import Path

SERVER_HOST = 'localhost'
SERVER_PORT = 12345

MY_HOST = socket.gethostname()
MY_PORT = 0

my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

class Client:

    LOGIN = 0
    REG = 1
    PUBLISH = 2
    LOGOUT = 3
    FETCH = 4
	
    def __init__(self):
        self.username = ''
        self.running = True
        self.is_login = False
        self.my_socket = my_socket
        self.server_socket = server_socket
        self.data_dir_path = 'client_repo'

        self.connect_from_peer = []
        self.my_repo = []

        self.connect_to_server()
        self.command_line = Thread(target=self.command_line_interface, args=()).start()

    def command_line_interface(self):
        print('At any time, you can run "help" command to read syntax')
        while self.running:
            if self.is_login == False:
                command = input('login> ')
                self.execute_command('authen', command)
            else:
                command = input(f'{self.username}> ')
                self.execute_command('run', command)

    def execute_command(self, command_type, command):
        if len(command) == 0:
            return
        command = command.split(' ')
        if command[0] == 'exit':
            self.running = False
            return
        if command[0] == 'help':
            print('Command syntax:')
            print('login username password (login if you have an account)')
            print("reg username password (register if you don't have an account)")
            # print('logout (logout if you want to change account)')
            # print('exit (if you want to exit program)')
            print('publish lname fname (publish file to server)')
            print('fetch fname (fetch some copy of the target file)')
            return

        if command_type == 'authen':
            if command[0] == 'login':
                if (len(command) == 3):
                    self.user_login(command[1], command[2])
                else:
                    print('Command invalid!')
            elif command[0] == 'reg':
                if (len(command) == 3):
                    self.user_reg(command[1], command[2])
                else:
                    print('Command invalid!')
            else:
                print('Command invalid!')
        elif command_type == 'run':
            if command[0] == 'publish':
                if (len(command) == 3):
                    self.publish_file(command[1], command[2])
                else:
                    print('Command invalid!')
            elif command[0] == 'fetch':
                if (len(command) == 2):
                    self.fetch_file(command[1])
                else:
                    print('Command invalid!')
            else:
                print('Command invalid!')
        else:
            print('Command invalid!')
    

    def connect_to_server(self):
        try:
            self.server_socket.connect((SERVER_HOST, SERVER_PORT))
            self.my_socket.bind((MY_HOST, MY_PORT))
            # print(f'connect_to_server, mysocket = {self.my_socket}')
            self.my_socket.listen(10)
        except:
            pass

    def send_request(self, requestCode, data):
        if requestCode == self.LOGIN:
            request = "LOGIN" + "\n" + data
            self.server_socket.send(request.encode())        
        elif requestCode == self.REG:
            request = "REG" + "\n" + data
            self.server_socket.send(request.encode())
        elif requestCode == self.PUBLISH:
            request = "PUBLISH" + "\n" + data
            self.server_socket.send(request.encode())
        elif requestCode == self.FETCH:
            request = "FETCH" + "\n" + data
            self.server_socket.send(request.encode())
        elif requestCode == self.LOGOUT:
            request = "LOGOUT" + "\n" + data
            self.server_socket.send(request.encode())

    def recv_reply(self):
        response = self.server_socket.recv(1024).decode()
        return response.split("\n")

    def user_reg(self, username, password):
        self.send_request(self.REG, f'{username}-{password}')

        response = self.recv_reply()
        if response[0] == "REG_OK":
            print('Register account successfully')
        else:
            print('Register account fail')

    def user_login(self, username, password):
        self.send_request(self.LOGIN, f'{username}-{password}-{self.my_socket.getsockname()}')

        response = self.recv_reply()
        if response[0] == "USER_PASS_INVALID":
            print('Username or Password invalid')
        else:
            print("Login success")
            self.is_login = True
            self.username = username

            fnames = ''
            if not os.path.exists(self.data_dir_path):
                os.makedirs(self.data_dir_path)
                print(f"Directory '{self.data_dir_path}' created successfully.")
            else:
                print(f"Directory '{self.data_dir_path}' already exists.\nAuto publish all file in local repository")
                file_names = os.listdir(self.data_dir_path)
                for file_name in file_names:
                    self.my_repo.append(file_name)
                    fnames = fnames + file_name + '-'
                
                self.send_request(self.PUBLISH, f'{fnames[:-1]}')

            Thread(target=self.accept_transfer_file).start()

    def accept_transfer_file(self):
        while self.is_login == True:
            try:
                peer = self.my_socket.accept()
                # print("Successfull")
                self.connect_from_peer.append(peer)
                Thread(target=self.recv_msg, args=(peer, )).start()
            except:
                # print("Close listen socket")
                pass

    def recv_msg(self, conn):
        while True:
            try:
                data = conn[0].recv(1024)
                print(data.decode())
                # Read File in binary
                file = open(f'{self.data_dir_path}\\{data.decode()}', 'rb')
                line = file.read(1024)
                # Keep sending data to the client
                while(line):
                    conn[0].send(line)
                    line = file.read(1024)
                
                file.close()
                print('File has been transferred successfully.')

                conn[0].close()
            except:
                print('Stop file transfer')
                break

        # print('Register new account with syntax (reg yourname username password)')
        # request = input()
        # self.send_request(self.REG, request)

    def publish_file(self, lname, fname):
        source = Path(lname)
        try:
            copyfile(source, f'client_repo\\{fname}')
            self.send_request(self.PUBLISH, f'{fname}')
            self.my_repo.append(fname)
        except:
            print('File path is invalid!!!!!')
        print(self.my_repo)

    def fetch_file(self, fname):
        for file in self.my_repo:
            if file == fname:
                print('You have this file')
                return
            
        self.send_request(self.FETCH, f'{fname}')

        response = self.recv_reply()
        if response[0] == 'FETCH_FAIL':
            print('No suitable file is found!')
            return
        
        if response[0] == 'FETCH_OK':
            print(response[1])
            addr = response[1].split("'")

            host = addr[1]
            port = int(addr[2][2:-1])
            try:
                sock = socket.socket()
                # Connect socket to the host and port
                sock.connect((host, port))
                print('Connection Established.')
                # Send a greeting to the server
                sock.send(fname.encode())

                self.data_dir_path = 'client_repo'
                # Write File in binary
                file = open(f'{self.data_dir_path}\\{fname}', 'wb')

                # Keep receiving data from the server
                line = sock.recv(1024)

                while(line):
                    file.write(line)
                    line = sock.recv(1024)

                print('File has been received successfully. File is stored in client_repo folder')

                file.close()
                sock.close()
                print('Connection Closed.')
                self.my_repo.append(fname)
            except:
                print('File transfer fail')

if __name__ == '__main__':
    App = Client()

    
