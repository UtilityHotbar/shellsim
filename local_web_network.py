from main import Computer
import json
import threading

class Router:
    def __init__(self, *connections):
        self.connections = {}
        i = 0
        for var in connections:
            self.connections[100+i] = var
            i += 1
        print(self.connections)
        for id in self.connections:
            self.connections[id].curr_connections.append(self)

    def send_message(self, sender, recipient, content):
        self.connections[recipient].input_stream.append(f'MSGFROM {list(self.connections.keys())[list(self.connections.values()).index(sender)]}:{content}')
        if 'server' in self.connections[recipient].curr_processes:
            serverResponse = threading.Thread(target=self.connections[recipient].do_server, args=('respond', 'internal'))
            serverResponse.start()

    def query_address(self, sender):
        return list(self.connections.keys())[list(self.connections.values()).index(sender)]

    def establish_connection(self, originator, recipient, data_stream=None):
        try:
            getattr(self.connections[recipient], 'do_slink')  # Check if recipient has slink installed
            self.connections[recipient].input_stream=data_stream
            return self.connections[recipient]
        except AttributeError:
            return False


def make_basic_computer(name, pwd, extra_files):
    users = {'root': {'password': 'toor', 'permissions': 'root'}, name: {'password': pwd, 'permissions': 'sudo'}}
    with open('dooros_filesystem.json', 'r') as f:
        file_system = json.load(f)
    file_system['users'][name] = extra_files
    return Computer(users=users, drive=file_system, save_location=f'{name}_{pwd}_computer.save')

