import cmd
import time
import random
import re
import types
import modules
import pickle


class Computer(cmd.Cmd):
    def __init__(self, users=None, drive=None):
        self.name = 'DoorOSMachine'
        self.specs = {'OS': 'doorOS==3.1', 'defender': None}
        if not drive:
            self.filesystem = {'welcome.txt': 'Hey there. Thanks for using doorOS. We hope you love us and our product!'}
        else:
            self.filesystem = drive
        self.speed = 0.1

        # Current working directory path and directory contents
        self.cwd = '/'
        self.curr_dir = self.filesystem

        # Current users
        if not users:
            print('NEW USER LOGIN')
            user_name = input('Create username: ')
            password = input('Create password: ')
            self.users = {'root': {'password': 'toor', 'permissions': 'root'},
                          user_name: {'password': password, 'permissions': 'sudo'}}
        else:
            self.users = users
        self.curr_user = None
        self.prompt = '(INVALID ACCESS) '

        # System variables
        self.forbidden_chars = ['/', ' ', '>']
        self.null_output = 'NUL'
        self.variables = {}

        # Stdio
        self.output = None
        self.output_mode = 'echo'
        self.output_location = None
        self.input_stream = []
        super().__init__()

    def delay_print(self, *args):
        print(' '.join(args))
        time.sleep(self.speed)

    def check_invalid_name(self, string):
        if True in [True for char in self.forbidden_chars if char in string]:
            return True

    def startup(self):
        self.delay_print('Initialising BIOS...')
        self.delay_print(f'Booting {" v.".join(self.specs["OS"].split("=="))}...')
        while True:
            username = input('Username: ')
            password = input('Password: ')
            try:
                if password == self.users[username]['password']:
                    if username == 'root':
                        print('Error - Cannot login as root. Please try again.')
                        continue
                    self.curr_user = username
                    break
            except KeyError:
                print('Invalid username or password. Please try again.')
        self.prompt = f'{self.curr_user}@{self.name} $ '
        self.cmdloop()

    def evaluate_expressions(self, line: str):
        variable_expression = re.compile(r'\$\S+')
        arithmetic_expression = re.compile(r'\(\(\s*(.+)\s*\)\)')
        for variable in re.findall(variable_expression, line):
            try:
                line = line.replace(variable, str(self.variables[variable]))
            except KeyError:
                print(f'Error - Variable {variable} not found.')
                return self.error_break('VARIABLE_NOT_FOUND_ERROR')
        while True:
            findmath = re.search(arithmetic_expression, line)
            if findmath:
                try:
                    line = line.replace(findmath.group(0), str(eval(findmath.group(1))))
                except:
                    print(f'Error - Evaluation of expression {findmath.group(1)} failed.')
                    return self.error_break('EVALUATION_ERROR')
            else:
                break
        return line

    def parseline(self, line: str):
        line = line.split(';')
        self.cmdqueue += line[1:]
        line = line[0]
        if '|' in line:
            line = line.split('|')
            self.cmdqueue.append('|'.join(line[1:]))
            self.output_mode = 'pipe'
            line = line[0]
        # Streaming output to file is always the last thing so its ok to check it after checking for pipes?
        elif '>>' in line:
            line = line.split('>>')
            self.output_mode = 'file'
            self.output_location = line[1].strip()
            line = line[0]
        elif '>' in line:
            line = line.split('>')
            self.output_mode = 'file_overwrite'
            self.output_location = line[1].strip()
            line = line[0]
        return super().parseline(self.evaluate_expressions(line))

    def request_input(self, prompt='Enter input'):
        if not self.input_stream:
            return input(prompt)
        else:
            return self.input_stream.pop()

    def error_break(self, error_code='ERROR'):
        # Just halt everything, make sure errors don't propagate
        self.cmdqueue = []
        self.output_mode = 'echo'
        self.output_location = None
        self.input_stream = None
        self.output = f'Process terminated with error code {error_code}'
        return error_code

    def save(self):
        with open('save.pickle', 'wb') as f:
            pickle.dump((self.users, self.filesystem), f)

    def postcmd(self, stop, line: str) -> bool:
        if stop is None:
            stop = ''
        if stop.endswith('ERROR'):
            self.error_break(stop)
        if self.output:
            # If there is output either print it, add it to the next command in the command queue,
            # or stream it to a file
            if self.output_mode == 'echo':
                print(self.output)
                self.output = None
            elif self.output_mode == 'pipe':
                next_commands = [_.strip() for _ in self.cmdqueue[0].split('|')]
                # Newlines are the dividers for primitive stdin implementation as well as argument dividing
                if next_commands[0].startswith('run') or next_commands[0].startswith('read'):
                    self.input_stream += self.output.split('\n')
                else:
                    added_arguments = ' '.join(self.output.split('\n'))
                    if '>' in next_commands[0]:
                        target_split = next_commands[0].split('>')
                        next_commands[0] = target_split[0] + ' ' + added_arguments + '>' + target_split[1]
                    elif '>>' in next_commands[0]:
                        target_split = next_commands[0].split('>>')
                        next_commands[0] = target_split[0] + ' ' + added_arguments + '>>' + target_split[1]
                    else:
                        next_commands[0] = next_commands[0] + ' ' + added_arguments
                self.cmdqueue[0] = '|'.join([next_commands[0]]+next_commands[1:])
                self.output_mode = 'echo'
                self.output = None
            elif self.output_mode == 'file' or self.output_mode == 'file_overwrite':
                file_path = '/'.join(self.output_location.split('/')[:-1])
                file_name = self.output_location.split('/')[-1]
                if file_name != self.null_output:
                    addition_dir = self.parse_path(file_path)
                    if type(addition_dir) == dict:
                        try:
                            if self.output_mode == 'file':
                                if addition_dir[file_name] != '%SPECIAL_NULL_FILE%':
                                    addition_dir[file_name] += self.output
                            elif self.output_mode == 'file_overwrite':
                                if addition_dir[file_name] != '%SPECIAL_NULL_FILE%':
                                    addition_dir[file_name] = self.output
                        except KeyError:
                            addition_dir[file_name] = self.output
                    else:
                        print('Error - destination is not a directory')
                        stop = self.error_break('INVALID_PATH_ERROR')
                self.output_mode = 'echo'
                self.output = None
        if stop == 'EXIT':
            self.error_break()
            return True
        else:
            return False

    def do_echo(self, args):
        """Echo input to output: echo INPUT"""
        self.output = args

    def do_read(self, args):
        """Read in input stdin or user to variable: read VAR_NAME"""
        self.variables['$'+args] = self.request_input()

    def do_declare(self, args):
        """Declare string variable: declare VAR_NAME=VALUE"""
        args = [x.strip() for x in args.split('=')]
        name = args[0]
        value = args[1]
        self.variables['$'+name] = value

    def do_let(self, args):
        """Declare variable as product of expression: declare VAR_NAME=EXPR"""
        args = [x.strip() for x in args.split('=')]
        name = args[0]
        value = args[1]
        self.variables['$'+name] = eval(value)

    def do_if(self, line, return_result=False):
        """Conditional execution: if [ COND ] ? TRUE_STATEMENT : FALSE_STATEMENT"""
        conditional_expression = re.compile(r'\[\s+(.+)\s+\]')
        is_directory_expression = re.compile(r'-d\s+(.+)')
        is_file_expression = re.compile(r'-e\s+(.+)')
        is_notempty_expression = re.compile(r'-s\s+(.+)')
        expr = re.search(conditional_expression, line)
        if not expr:
            print('Error - if statement does not contain condition.')
            return 'NO_CONDITION_ERROR'
        else:
            condstring = expr.group(1).replace('-gt', '>').replace('-lt', '<').replace('-n', '0 <').replace('-z',
                                                                                                            '0 ==').replace(
                '!', 'not').replace('&&', 'and').replace('||', 'or')
            is_dir = re.search(is_directory_expression, condstring)
            if is_dir:
                condstring = condstring.replace(is_dir.group(0), f'(type(self.parse_path({is_dir.group(1)})) == dict)')
            is_file = re.search(is_file_expression, condstring)
            if is_file:
                condstring = condstring.replace(is_file.group(0), f'(type(self.parse_path({is_file.group(1)})) == str)')
            is_notempty = re.search(is_notempty_expression, condstring)
            if is_notempty:
                condstring = condstring.replace(is_notempty.group(0),
                                                f'((len(self.parse_path({is_notempty.group(1)})) > 0) and (type(self.parse_path({is_notempty.group(1)})) == str))')
            condstring = self.evaluate_expressions(condstring)
            result = eval(condstring)
            targets = [_.strip() for _ in line.split('?')[1].split(':')]
            # Just return the result if instructed, otherwise execute then and else
            if return_result:
                return result
            else:
                if result:
                    self.cmdqueue.insert(0, targets[0])
                elif (not result) and (len(targets)>1):
                    self.cmdqueue.insert(0, targets[1])

    def do_run(self, args):
        """Run shell script: run FILE_PATH"""
        file_path = '/'.join(args.split('/')[:-1])
        file_name = args.split('/')[-1]
        attempt = self.parse_path(file_path)

        if type(attempt) == dict:
            try:
                target_file = attempt[file_name]
            except KeyError:
                print(f'Error - file {file_name} not found.')
                return 'FILE_NOT_FOUND_ERROR'
        if target_file == '%SPECIAL_RANDOM_FILE%':
            self.output = random.random()
        newlines_or_semicolons = re.compile(r'(\\n|;)')
        body = re.split(newlines_or_semicolons, target_file)
        pointer = 0
        return_stack = []
        delete_next = False
        print(body)
        while True:
            line = body[pointer]
            print(line)
            specials = ['if', 'goto', 'return']
            if not (True in [True for _ in specials if line.startswith(_)]):
                self.onecmd(line)
            elif line.startswith('if'):
                result = self.do_if(line[2:].strip(), return_result=True)
                targets = [_.strip() for _ in line.split('?')[1].split(':')]
                if result:
                    body.insert(pointer+1, targets[0])
                    delete_next = True
                elif (not result) and len(targets)>1:
                    body.insert(pointer+1, targets[1])
                    delete_next = True
            elif line.startswith('goto'):
                return_stack.append(pointer)
                pointer = body.index(line.split()[1].strip())
            elif line.startswith('return'):
                pointer = return_stack.pop(-1)
            if delete_next:
                body.remove(pointer)
            pointer += 1
            if pointer > len(body)-1:
                break

    def do_cat(self, args):
        """View contents of file: cat FILE_NAME"""
        files = args.split(' ')
        output = []
        for file in files:
            file_path = '/'.join(file.split('/')[:-1])
            file_name = file.split('/')[-1]
            try:
                attempt = self.parse_path(file_path)
                if type(attempt) == dict:
                    output.append(attempt[file_name])
            except KeyError:
                print(f'Error - File {file_name} not found.')
                return 'FILE_NOT_FOUND_ERROR'
        self.output = ' '.join(output)

    def do_cd(self, args):
        """Change current working directory: cd DIR_PATH"""
        attempt = self.parse_path(args, return_path=True)
        if type(attempt) == tuple:
            self.curr_dir, self.cwd = attempt

    def do_ls(self, args):
        """List items in directory: ls / ls DIR_PATH"""
        if args:
            target_dir = self.parse_path(args)
            if type(target_dir) == dict:
                self.output = ' '.join([item for item in target_dir if item[0] != '.'])
        else:
            self.output = ' '.join(self.curr_dir)

    def do_mkdir(self, args):
        """Make directory: mkdir DIR_NAME"""
        if args:
            if self.check_invalid_name(args):
                print('Error - Invalid character in directory name.')
                return 'INVALID_NAME_ERROR'
            else:
                self.curr_dir[args] = {}

    def do_rmdir(self, args):
        """Remove directory: rmdir DIR_NAME"""
        if args:
            print(self.parse_path(args))
            if self.parse_path(args) == {}:
                self.parse_path(args+'/..').pop(args.split('/')[-1])
            else:
                print('Error - target directory is not empty.')
                return 'NOT_EMPTY_DIRECTORY_ERROR'

    def do_pwd(self, args):
        """Print current working directory: pwd"""
        self.output = self.cwd

    def do_touch(self, args):
        """Create new file: touch FILENAME"""
        file_path = '/'.join(args.split('/')[:-1])
        file_name = args.split('/')[-1]
        if self.check_invalid_name(file_name):
            print('Error - Invalid character in file name.')
            return 'FILENAME_ERROR'
        else:
            attempt = self.parse_path(file_path)
            if type(attempt) == dict:
                attempt[file_name] = ''

    def do_del(self, args):
        """Delete file: del FILENAME"""
        file_path = '/'.join(args.split('/')[:-1])
        file_name = args.split('/')[-1]
        try:
            attempt, path = self.parse_path(file_path, return_path=True)
            if type(attempt) == dict:
                del [file_name]
        except KeyError:
            print(f'Error - File {args} not found.')
            return 'FILE_NOT_FOUND_ERROR'

    def do_user(self, args):
        """Manage users: user add/del/mod USERNAME OPTIONS"""
        if self.users[self.curr_user]['permissions'] != 'root':
            print('Error - You don\'t have permission to perform this command')
            return 'PERMISSION_ERROR'
        else:
            args = args.split()
            if len(args) < 2:
                print('Error - Insufficient arguments')
                return 'ARGUMENT_LENGTH_ERROR'
            if self.check_invalid_name(args[1]):
                print('Error - Username invalid')
                return 'INVALID_NAME_ERROR'
            if args[0] == 'add':
                try:
                    password = args[2]
                except IndexError:
                    password = self.request_input(f'Enter password for user {args[1]}')
                self.users[args[1]] = {'password': password, 'permissions': 'sudo'}
                self.output = f'Created user {args[1]} with password {password}.'
            elif args[0] == 'del':
                try:
                    del self.users[args[1]]
                    self.output = f'Deleted user {args[1]}.'
                except KeyError:
                    print(f'Error - User {args[1]} not found.')
                    return 'USER_NOT_FOUND_ERROR'
            elif args[0] == 'mod':
                try:
                    target = self.users[args[1]]
                    if args[2] == '+':
                        target['permissions'] = 'sudo'
                    elif args[2] == '-':
                        target['permissions'] = 'user'
                    self.output = f'Modified permissions for user {args[1]}.'
                except KeyError:
                    print(f'Error - User {args[1]} not found.')
                    return 'USER_NOT_FOUND_ERROR'
                except IndexError:
                    print('Error - Please specify the operation you wish to perform.')
                    return 'ARGUMENT_LENGTH_ERROR'

    def do_sudo(self, args):
        """Execute command as superuser: sudo COMMAND"""
        if self.users[self.curr_user]['permissions'] == 'sudo':
            old_user = self.curr_user
            self.curr_user = 'root'
            self.onecmd(args)
            self.curr_user = old_user

    def do_pkgman(self, args):
        args = args.split()
        cmd = args[0]
        packages = args[1:]
        for arg in packages:
            if cmd == 'get':
                try:
                    func = modules.module_directory[arg]
                    setattr(self, 'do_'+arg, types.MethodType(func, self))
                except KeyError:
                    print(f'Error - Module {arg} not found.')
                    return 'MODULE_NOT_FOUND_ERROR'
            elif cmd == 'remove':
                delattr(self, 'do_'+arg)

    def do_shutdown(self, args):
        """Shutdown computer: shutdown"""
        self.save()
        return 'EXIT'

    def parse_path(self, path, return_path=False):
        curr_dir = self.curr_dir
        tempcwd = self.cwd
        if path == '':
            pass
        elif path[0] == '/':
            curr_dir = self.filesystem
            path = path[1:]
            tempcwd = '/'
        path = path.split('/')
        for item in path:
            if item == '.' or item == '':
                continue
            elif item == '..':
                tempcwd = '/'+'/'.join(tempcwd.split('/')[:-1])
                curr_dir = self.parse_path(tempcwd)
            else:
                try:
                    if type(curr_dir[item]) != dict:
                        print(f'Error - directory {item} is not a directory.')
                        return 'INVALID_PATH_ERROR'
                    curr_dir = curr_dir[item]
                    tempcwd += item
                except KeyError:
                    print(f'Error - directory {item} does not exist.')
                    return 'INVALID_PATH_ERROR'
        if return_path:
            return curr_dir, tempcwd
        else:
            return curr_dir


def main():
    try:
        with open('save.pickle', 'rb') as f:
            users, drive = pickle.load(f)
    except FileNotFoundError:
        users, drive = None, None
    test = Computer(users=users, drive=drive)
    test.startup()


if __name__ == '__main__':
    main()