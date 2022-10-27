import argparse
import socket
import shlex
import subprocess
import sys
import textwrap
import threading



class NetCat:
    def __init__(self, args, buffer=None):
        self.args = args
        self.buffer = buffer
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    def run(self):
        if self.args.listen:
            self.listen()
        else:
            self.send()
    def send(self):
        self.socket.connect((self.args.target, self.args.port))
        if self.buffer:
            self.socket.send(self.buffer)
        
        try:
            while True:
                recv_len = 1
                response = ''
                while recv_len:
                    data = self.socket.recv(4096)
                    recv_len = len(data)
                    response += data.decode()
                    if recv_len < 4096:
                        break
                if response:
                    if 'OFP:' in response:
                        print(response, end=' ')
                    else:
                        print(response)
                    buffer = input()
                    if 'exit' == buffer.lower():
                        sys.exit()
                    buffer += '\n'
                    self.socket.send(buffer.encode())
        except KeyboardInterrupt:
            print('User terminated.')
            self.socket.close()
            sys.exit()

    def listen(self):
        self.socket.bind((self.args.target, self.args.port))
        self.socket.listen(5)
        while True:
            client_socket, _ = self.socket.accept()
            client_thread = threading.Thread(
                target=self.handle, args=(client_socket,)
            )
            client_thread.start()
    
    def handle(self, client_socket):
        if self.args.execute:
            output = execute(self.args.execute)
            client_socket.send(output.encode())

        elif self.args.upload:
            file_buffer = b''
            while True:
                data = client_socket.recv(4096)
                if data:
                    file_buffer += data.decode()
                else:
                    break
        elif self.args.command:
            cmd_buffer = b''
            while True:
                try:
                    client_socket.send(b'OFP: #>')
                    while '\n' not in cmd_buffer.decode():
                        cmd_buffer += client_socket.recv(64)
                    response = execute(cmd_buffer.decode())
                    if response:
                        client_socket.send(response.encode())
                    cmd_buffer = b''
                except Exception as e:
                    print(f'Server killed {e}')
                    self.socket.close()
                    sys.exit()
        else:
            echo_buffer = b''
            #print(echo_buffer.decode())
            while True:
                client_socket.send(b'OFP: echo>')
                while '\n' not in echo_buffer.decode():
                    echo_buffer += client_socket.recv(64)
                echo_buffer = echo_buffer.strip()
                print(echo_buffer.decode())
                echo_buffer = b''

def execute(cmd):
    cmd = cmd.strip()
    if not cmd:
        return
    try:
        output = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
        #print(type(output))
    except subprocess.CalledProcessError as e:
        output = bytes(f'Eror code: {e.returncode}\n', 'utf-8')
    return output.decode()

if __name__=='__main__':
    parser = argparse.ArgumentParser(
        description='NetCat Replacement Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''Example:
            netcat.py -t IP -p PORT -l -c # Command Shell
            netcat.py -t IP -p PORT -l -u=file_path #Upload to file
            netcat.py -t IP -p PORT -l -e=\"cat /etc/passwd\" # Execute command
            echo 'ABC' | ./netcat.py -t IP -p PORT # echo text to server port PORT
            netcat.py -t IP -p PORT # Connect to server 
        '''))
    parser.add_argument('-c', '--command', action='store_true', help='Command shell')
    parser.add_argument('-e', '--execute', help='Execute a command')
    parser.add_argument('-l', '--listen', action='store_true', help='Listen')
    parser.add_argument('-p', '--port', type=int, default=5555, help='Specified port')
    parser.add_argument('-t', '--target',default='127.0.0.1', help='Specified IP')
    parser.add_argument('-u', '--upload', help='Upload file')

    args = parser.parse_args()
    if args.listen:
        buffer = ''
    else:
        buffer = sys.stdin.read()
    
    nc = NetCat(args, buffer.encode())
    nc.run()




            

    