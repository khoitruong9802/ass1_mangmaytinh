import sys, socket
from threading import Thread
import json

SERVER_HOST = "localhost"
SERVER_PORT = 12345

active_clients = {}
db = {}

with open("db.json", "r") as file:
    db = json.load(file)


class Server:	
	
	LOGIN = 'LOGIN'
	LOGOUT = 'LOGOUT'
	REG = 'REG'
	PUBLISH = 'PUBLISH'
	FETCH = 'FETCH'


	LOGIN_SUCCESS = 0
	USER_PASS_INVALID = 1
	REG_OK = 2
	OK = 4
	FETCH_OK = 5
	FETCH_FAIL = 6

	def __init__(self, active_clients, db):
		self.active_clients = active_clients
		self.db = db
		self.runn = Thread(target=self.command_line_interface, args=()).start()

	def command_line_interface(self):
		print('At any time, you can run "help" command to read syntax')
		while True:
			command = input('>')
			self.execute_command(command)

	def execute_command(self, command):
		if len(command) == 0:
			return
		command = command.split(' ')
		if command[0] == 'exit':
			pass
		if command[0] == 'help':
			print('Command syntax:')
			print('listhost (list all hostname connect to server)')
			print('discover (discover the list of local files of all host)')
			print('discover hostname (discover the list of local files of the host named hostname)')
			print("ping hostname (live check the host named hostname)")
			# print('exit (if you want to stop server)')

		elif command[0] == 'discover':
			if len(command) == 1:
				for client in self.active_clients:
					print(f'{self.active_clients[client]["files"]}')
			elif len(command) == 2:
				try:
					print(f'{self.active_clients[command[1]]["files"]}')
				except:
					print('Hostname can not found')
			else:
				print('Command invalid!')

		elif command[0] == 'ping':
			if len(command) == 2:
				try:
					print(f'{self.active_clients[command[1]]["username"]} user is online')
				except:
					print('This user is offline or not existent')
			else:
				print('Command invalid!')

		elif command[0] == 'listhost':
			if len(command) == 1:
				for client in self.active_clients:
					print(f'{client}')
			else:
				print('Command invalid!')
		
		else:
			print('Command invalid!')


	def main(self):
		Server_Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		Server_Socket.bind((SERVER_HOST, SERVER_PORT))
		Server_Socket.listen(5)        
		# print(f'server socket = {Server_Socket}')
		# Receive client info (address,port) through RTSP/TCP session
		while True:
			client = {}
			client['Socket'] = Server_Socket.accept()
			#print(f"connect from {client['Socket'][1]}")
			Thread(target=self.recvRequest, args=(client, )).start()
			

	def recvRequest(self, client):
		connSocket = client['Socket'][0]
		while True:            
			try:
				data = connSocket.recv(256)
				if data:
					# print("Data received:\n" + data.decode("utf-8"))
					self.processRequest(data.decode("utf-8"), client)
			except:
				print(f"{client['username']} has logged out")
				del self.active_clients[client['username']]
				break

	def processRequest(self, data, client):
		# print('check process request running')
		# Get the request type
		request = data.split('\n')
		requestType = request[0]

		# Process LOGIN request
		if requestType == self.LOGIN:
			info = request[1].split("-")
			username = info[0]
			password = info[1]
			if (self.validate_login(username, password) == 1):
				client['username'] = username
				
				#get client_listen_port
				client['listen_socket'] = info[2]
				client['files'] = []
				
				#get client_friend from database
				self.replyRequest(self.LOGIN_SUCCESS, client, '')
				self.active_clients[username] = client
			else:
				self.replyRequest(self.USER_PASS_INVALID, client, '')

		elif requestType == self.REG:
			info = request[1].split("-")
			username = info[0]
			password = info[1]

			file_path = 'db.json'
			try:
				with open(file_path, 'r') as json_file:
					existing_data = json.load(json_file)
			except FileNotFoundError:
				existing_data = {}

			new_data = {
				username: {
					'password': password
				}
			}
			existing_data.update(new_data)
			with open(file_path, 'w') as json_file:
				json.dump(existing_data, json_file, indent=4)

			with open("db.json", "r") as file:
				self.db = json.load(file)

			self.replyRequest(self.REG_OK, client, '')

		elif requestType == self.PUBLISH:
			info = request[1].split("-")
			for fname in info:
				client['files'].append(fname)

		elif requestType == self.FETCH:
			info = request[1].split("-")
			fname = info[0]

			for client_name in self.active_clients:
				for file_name in self.active_clients[client_name]['files']:
					if file_name == fname:
						print(f'find sutable file in {self.active_clients[client_name]["listen_socket"]}')
						self.replyRequest(self.FETCH_OK, client, self.active_clients[client_name]["listen_socket"])
						return
			
			self.replyRequest(self.FETCH_FAIL, client, '')

		elif requestType == self.LOGOUT:
			self.active_clients.pop(client['username'])
			self.replyRequest(self.OK, client, '')
			client['Socket'][0].close()
			

	def replyRequest(self, code, client, mes):
		if code == self.LOGIN_SUCCESS:
			reply = 'LOGIN_SUCCESS' 
			connSocket = client['Socket'][0]
			connSocket.send(reply.encode())
		
		elif code == self.USER_PASS_INVALID:
			reply = f'USER_PASS_INVALID\n'
			connSocket = client['Socket'][0]
			connSocket.send(reply.encode())

		elif code == self.REG_OK:
			reply = f'REG_OK\n'
			connSocket = client['Socket'][0]
			connSocket.send(reply.encode())

		elif code == self.FETCH_OK:
			reply = f'FETCH_OK\n{mes}'
			connSocket = client['Socket'][0]
			connSocket.send(reply.encode())

		elif code == self.FETCH_FAIL:
			reply = f'FETCH_FAIL'
			connSocket = client['Socket'][0]
			connSocket.send(reply.encode())

		elif code == self.OK:
			reply = f"OK\n"
			connSocket = client['Socket'][0]
			connSocket.send(reply.encode())
	
	def validate_login(self, username, password):
		try:
			if self.db[username]['password'] == password:
				return 1
			else: 
				return -1
		except:
			return -1

if __name__ == "__main__":
	(Server(active_clients, db)).main()


