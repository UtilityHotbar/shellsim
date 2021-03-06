import cmd
import time
import random
import re
import types
import external_module_repo
import ast
import operator as op
import json
import os
import pickle

try:
    import sqlitedict
except ImportError:
    os.system('pip3 install sqlitedict')
    import sqlitedict


operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
             ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
             ast.USub: op.neg, ast.Not: op.not_}

permitted_functions = {'len': len, 'type': type, 'int': int}

class Computer(cmd.Cmd):
    def __init__(self, users=None, drive=None, save_location="main_save.save"):
            self.name = 'DoorOSMachine'
            self.specs = {'OS': 'doorOS==3.1', 'defender': None}

            if not drive:
                with open('dooros_filesystem.json', 'r') as f:
                    self.filesystem = json.load(f)
            else:
                self.filesystem = drive
            self.speed = 0.1
            self.save_location = save_location

            # Current working directory path and directory contents
            self.cwd = '/'

            # Current users
            if not users:
                print('NEW USER LOGIN')
                user_name = input('Create username: ')
                password = input('Create password: ')
                self.users = {'root': {'password': 'toor', 'permissions': 'root'},
                              user_name: {'password': password, 'permissions': 'sudo'}}
            else:
                self.users = users
            self.curr_user = 'root'
            self.prompt = '(INVALID ACCESS) '

            # System variables
            self.forbidden_chars = ['/', ' ', '>', '*', '\\', '?', '{', '}']
            self.null_output = 'NUL'
            self.variables = {}
            self.permitted_internal_functions = {'parse_path': self.parse_path}
            self.permitted_internal_variables = ['complex_commands']
            self.complex_commands = ['lined']  # For these commands, don't split arguments
            self.curr_processes = ['shell']
            self.curr_connections = []

            # Stdio
            self.output = None
            self.redirect_output = False
            self.output_buffer = []
            self.output_mode = 'echo'
            self.output_location = None
            self.input_stream = []
            super().__init__()

    def emptyline(self):
        return

    def eval_expr(self, expr):
        return self.eval_(ast.parse(expr.encode('unicode_escape'), mode='eval').body)

    def eval_(self, node):
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            return operators[type(node.op)](self.eval_(node.left), self.eval_(node.right))
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
            return operators[type(node.op)](self.eval_(node.operand))
        elif isinstance(node, ast.Slice):
            if node.lower:
                lower = self.eval_(node.lower)
            else:
                lower = 0
            if node.upper:
                upper = self.eval_(node.upper)
            else:
                upper = '$'
            return [lower, upper]
        elif isinstance(node, ast.Subscript):
            root_string = self.eval_(node.value)
            target_range = self.eval_(node.slice)
            if type(target_range) == int:
                return root_string[target_range]
            elif type(target_range) == list:
                if target_range[1] != '$':
                    return root_string[target_range[0]:target_range[1]]
                else:
                    return root_string[target_range[0]:]
        elif isinstance(node, ast.Compare):
            curr_left = self.eval_(node.left)
            if len(node.ops) == 1:
                curr_right = self.eval_(node.comparators[0])
            else:
                curr_right = self.eval_(ast.Compare(left=node.comparators[0], ops=node.ops[1:], comparators=node.comparators[1:]))
                if curr_right == False:
                    return False
                else:
                    curr_right = self.eval_(node.comparators[1])
            curr_op = node.ops[0]
            if isinstance(curr_op, ast.Lt):
                return curr_left < curr_right
            elif isinstance(curr_op, ast.LtE):
                return curr_left <= curr_right
            elif isinstance(curr_op, ast.Gt):
                return curr_left > curr_right
            elif isinstance(curr_op, ast.GtE):
                return curr_left >= curr_right
            elif isinstance(curr_op, ast.Eq):
                return curr_left == curr_right
            elif isinstance(curr_op, ast.NotEq):
                return curr_left != curr_right
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                function_namespace = 'foreign'
                function_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                function_namespace = node.func.value.id
                function_name = node.func.attr
            else:
                function_namespace = 'INVALID'
                function_name = 'ERROR'
            argvalues = []
            for arg in node.args:
                argvalues.append(self.eval_(arg))
            if function_namespace == 'self':
                if function_name in self.permitted_internal_functions:
                    return self.permitted_internal_functions[function_name](*argvalues)
            else:
                if function_name in permitted_functions:
                    return permitted_functions[function_name](*argvalues)
                print(f'Unknown function {function_name} detected.')
                return 'EVALUATION_ERROR'
        else:
            ast.dump(node)
            print(f'Evaluation of node {ast.dump(node)} failed')
            raise TypeError(node)

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
            username = self.request_input('Username: ')
            password = self.request_input('Password: ')
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

    def evaluate_expressions(self, line: str, force_evaluate=False):
        variable_expression = re.compile(r'\$\w+')
        internal_code_expression = re.compile(r'\${([^}]+)}')
        arithmetic_expression = re.compile(r'\(\(\s*(.+)\s*\)\)')
        while re.search(internal_code_expression, line):
            internal_line = re.search(internal_code_expression, line)
            self.onecmd(internal_line.group(1))
            if type(self.output) == str:
                output = '"'+self.output+'"'
            else:
                output = str(self.output)
            line = line.replace(internal_line.group(0), output)
            self.output = None
        for variable in re.findall(variable_expression, line):
            try:
                target = self.variables[variable]
                if type(target) == str:
                    target = '"'+target+'"'
                line = line.replace(variable, str(target))
            except KeyError:
                print(f'Error - Variable {variable} not found.')
                return self.error_break('VARIABLE_NOT_FOUND_ERROR')
        while True:
            findmath = re.search(arithmetic_expression, line)
            if findmath:
                try:
                    line = line.replace(findmath.group(0), str(self.eval_expr(findmath.group(1))))
                except KeyboardInterrupt:
                    print(f'Error - Evaluation of expression {findmath.group(1)} failed.')
                    return self.error_break('EVALUATION_ERROR')
            else:
                break
        if force_evaluate:
            return self.eval_expr(line)
        else:
            return line

    def parseline(self, line: str):
        line = line.strip()
        preline = ''
        if line.startswith('raw'):
            skiparea = re.search(r'"(.+)"', line)
            if skiparea:
                preline = line.split(skiparea.group(0))[0]+skiparea.group(1)
                line = line.split(skiparea.group(0))[1]
        line = line.split(';')
        self.cmdqueue += line[1:]
        line = line[0].strip()
        line = self.evaluate_expressions(line)
        if not line.startswith('let'):
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
        return super().parseline(preline+line)

    def request_input(self, prompt='Enter input'):
        if not self.input_stream:
            return input(prompt)
        else:
            return self.input_stream.pop(0)

    def error_break(self, error_code='ERROR'):
        # Just halt everything, make sure errors don't propagate
        self.cmdqueue = []
        self.output_mode = 'echo'
        self.output_location = None
        self.input_stream = []
        self.output = f'Process terminated with error code {error_code}'
        return error_code

    def save(self):
        with open(self.save_location, 'wb') as f:
            pickle.dump(self, f)

    def flush(self):
        # If there is output either print it, add it to the next command in the command queue,
        # or stream it to a file
        if self.output_mode == 'echo':
            if not self.redirect_output:
                print(self.output)
            else:
                self.output_buffer.append(self.output)
            self.output = None
        elif self.output_mode == 'pipe':
            next_commands = [_.strip() for _ in self.cmdqueue[0].split('|')]
            # Newlines are the dividers for primitive stdin implementation as well as argument dividing
            if next_commands[0].startswith('run') or next_commands[0].startswith('read'):
                self.input_stream += self.output.split('\n')
            else:
                if not True in [True for _ in self.complex_commands if next_commands[0].startswith(_)]:
                    added_arguments = ' '.join(self.output.split('\n'))
                else:
                    added_arguments = self.output
                if '>' in next_commands[0]:
                    target_split = next_commands[0].split('>')
                    next_commands[0] = target_split[0] + ' ' + added_arguments + '>' + target_split[1]
                elif '>>' in next_commands[0]:
                    target_split = next_commands[0].split('>>')
                    next_commands[0] = target_split[0] + ' ' + added_arguments + '>>' + target_split[1]
                else:
                    next_commands[0] = next_commands[0] + ' ' + added_arguments
            self.cmdqueue[0] = '|'.join([next_commands[0]] + next_commands[1:])
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
                                if addition_dir[file_name]:
                                    addition_dir[file_name] += '\n'+self.output
                                else:
                                    addition_dir[file_name] = self.output
                        elif self.output_mode == 'file_overwrite':
                            if addition_dir[file_name] != '%SPECIAL_NULL_FILE%':
                                addition_dir[file_name] = self.output
                    except KeyError:
                        addition_dir[file_name] = self.output
                else:
                    print('Error - destination is not a directory')
                    stop = self.error_break('INVALID_PATH_ERROR')
            self.output = None

    def postcmd(self, stop, line: str) -> bool:
        if stop is None:
            stop = ''
        if stop.endswith('ERROR'):
            self.error_break(stop)
        if self.output:
            self.flush()
            self.output_mode = 'echo'
            self.output = None
        if stop == 'EXIT':
            self.error_break()
            return True
        else:
            return False

    def find_file(self, name, folder):
        results = []
        name = re.compile(name.replace('.', '\.').replace('*', '.+').replace('?', '.'))
        for file in folder:
            if re.fullmatch(name, file):
                results.append(file)
        return results

    def do_echo(self, args):
        """Echo input to output: echo INPUT"""
        self.output = args

    def do_raw(self, args):
        """Echo raw input to output: raw INPUT"""
        self.output = args

    def do_read(self, args):
        """Read in input stdin or user to variable: read VAR_NAME"""
        args = [x.strip() for x in args.split()]
        name = re.match(r'(\w+)', args[0]).group(1)
        prompt = None
        if len(args) > 1:
            prompt = ' '.join(args[1:])
        self.variables['$'+name] = self.request_input(prompt)

    def do_declare(self, args):
        """Declare string variable: declare VAR_NAME=VALUE"""
        args = [x.strip() for x in args.split('=')]
        name = re.match(r'(\w+)', args[0]).group(1)
        value = args[1]
        self.variables['$'+name] = value

    def do_let(self, args):
        """Declare variable as result of expression: declare VAR_NAME=EXPR"""
        args = [x.strip() for x in args.split('=')]
        name = re.match(r'(\w+)', args[0]).group(1)
        value = args[1]
        self.variables['$'+name] = self.eval_expr(value)

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
            condstring = expr.group(1).replace('-gt', '>').replace('-lt', '<').replace('-n', '0 <').replace('-z','0 ==').replace('! ', 'not ').replace('&&', 'and').replace('||', 'or')
            is_dir = re.search(is_directory_expression, condstring)
            if is_dir:
                condstring = condstring.replace(is_dir.group(0), f'(type(self.parse_path("{is_dir.group(1)}")) == dict)')
            is_file = re.search(is_file_expression, condstring)
            if is_file:
                condstring = condstring.replace(is_file.group(0), f'(type(self.parse_path("{is_file.group(1)}")) == str)')
            is_notempty = re.search(is_notempty_expression, condstring)
            if is_notempty:
                condstring = condstring.replace(is_notempty.group(0),
                                                f'(len(self.parse_path("{is_notempty.group(1)}")) > 0) and (type(self.parse_path("{is_notempty.group(1)}")) == str)')
            result = self.evaluate_expressions(condstring, force_evaluate=True)
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
            return
        elif target_file == '%SPECIAL_NULL_FILE%':
            return
        elif target_file == '%SPECIAL_PROCESS_FILE%':
            self.curr_processes.append(file_name)
            getattr(self, f'do_{file_name}')('', origin='internal')
            return
        body = target_file.split('\n')
        pointer = 0
        return_stack = []
        delete_next = False
        while True:
            line = body[pointer]
            specials = ['if', 'goto', 'return', '#', 'pullfromqueue', ':']
            if not (True in [True for _ in specials if line.startswith(_)]):
                if '|' in line:
                    if line.startswith('raw') and not re.search(r'".*|.*".*(|)', line).group(1):  # If there is a raw input line and there are no pipes after the quotes
                        pass
                    else:
                        body.insert(pointer+1, 'pullfromqueue')
                        delete_next = True
                self.postcmd(self.onecmd(line), line)
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
                pointer = body.index(':'+line.split()[1].strip())
            elif line.startswith('return'):
                pointer = return_stack.pop(-1)
            elif line.startswith('pullfromqueue'):
                body.insert(pointer+1, self.cmdqueue.pop(0))
                delete_next = True
            if delete_next:
                body.pop(pointer)
                delete_next = False
            else:
                pointer += 1
            if pointer > len(body)-1:
                break

    def do_cat(self, args):
        """Concatenate file contents: cat FILE_NAME1 FILE_NAME2 etc."""
        files = args.split(' ')
        output = []
        for file in files:
            file_path = '/'.join(file.split('/')[:-1])
            file_name = file.split('/')[-1]
            try:
                attempt = self.parse_path(file_path)
                if type(attempt) == dict:
                    for located in self.find_file(file_name, attempt):
                        output.append(attempt[located])
            except KeyError:
                print(f'Error - File {file_name} not found.')
                return 'FILE_NOT_FOUND_ERROR'
        self.output = '\n'.join(output)

    def do_cd(self, args):
        """Change current working directory: cd DIR_PATH"""
        attempt = self.parse_path(args, return_path=True)
        if type(attempt) == tuple:
            empty, self.cwd = attempt

    def do_ls(self, args):
        """List items in directory: ls / ls DIR_PATH"""
        if args:
            print(self.parse_path(args))
            target_dir = self.parse_path(args)
            if type(target_dir) == dict:
                self.output = ' '.join([item for item in target_dir if item[0] != '.'])
        else:
            print(self.parse_path(self.cwd))
            self.output = ' '.join(self.parse_path(self.cwd))

    def do_mkdir(self, args):
        """Make directory: mkdir DIR_NAME"""
        if args:
            dir_path = '/'.join(args.split('/')[:-1])
            dir_name = args.split('/')[-1]
            try:
                attempt = self.parse_path(dir_path)
                if type(attempt) == dict:
                    if self.check_invalid_name(dir_name):
                        print('Error - Invalid character in directory name.')
                        return 'INVALID_NAME_ERROR'
                    else:
                        try:
                            a = attempt[dir_name]
                            print(f'Error - Directory {dir_name} already exists.')
                            return 'DIRECTORY_EXISTS_ERROR'
                        except KeyError:
                            attempt[dir_name] = {}

            except KeyError:
                print(f'Error - File {args} not found.')
                return 'FILE_NOT_FOUND_ERROR'

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
        """Create new file: touch FILE_PATH"""
        file_path = '/'.join(args.split('/')[:-1])
        file_name = args.split('/')[-1]
        if self.check_invalid_name(file_name):
            print('Error - Invalid character in file name.')
            return 'FILENAME_ERROR'
        else:
            attempt = self.parse_path(file_path)
            if type(attempt) == dict:
                try:
                    a = attempt[file_name]
                except KeyError:
                    attempt[file_name] = ''
                    print(attempt)

    def do_rm(self, args):
        """Delete file: rm FILE_PATH"""
        file_path = '/'.join(args.split('/')[:-1])
        file_name = args.split('/')[-1]
        try:
            attempt, path = self.parse_path(file_path, return_path=True)
            if type(attempt) == dict:
                for located in self.find_file(file_name, attempt):
                    del attempt[located]
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
            password = self.request_input('Enter password: ')
            if password == self.users[self.curr_user]['password']:
                old_user = self.curr_user
                self.curr_user = 'root'
                done = self.onecmd(args)
                self.curr_user = old_user
            else:
                print('Error - Incorrect password.')
                done = 'INCORRECT_PASSWORD_ERROR'
        elif self.users[self.curr_user]['permissions'] == 'root':
            done = self.onecmd(args)
        else:
            print('Error - You don\'t have permission to perform this command')
            done = 'PERMISSION_ERROR'
        return done

    def do_sysvar(self, args):
        """Modify system variables: sysvar VAR_NAME CMD(add/del/mod/get) NEW_VAL"""
        if self.users[self.curr_user]['permissions'] == 'root':
            args = args.split()
            newval = ''
            try:
                variable = args[0]
                request = args[1]
            except IndexError:
                print('Error - Please specify enough arguments.')
                return 'INVALID_ARGUMENT_ERROR'
            if len(args) > 2:
                newval = ' '.join(args[2:])
            if variable in self.permitted_internal_variables:
                curr_val = getattr(self, variable)
                if request == 'get':
                    self.output = f'{variable} = {getattr(self, variable)}'
                elif type(curr_val) == list:
                    if request == 'add':
                        curr_val.append(self.eval_expr(newval))
                        setattr(self, variable, curr_val)
                    elif request == 'del':
                        curr_val.remove(self.eval_expr(newval))
                        setattr(self, variable, curr_val)
                    elif request == 'mod':
                        setattr(self, variable, [self.eval_expr(_) for _ in newval.split(',')])
                else:
                    if request == 'mod':
                        setattr(self, variable, self.eval_expr(newval))

            else:
                print('Error - Invalid or unmodifiable internal variable specified.')
                return 'INVALID_SYSTEM_VARIABLE_ERROR'
        else:
            print('Error - You don\'t have permission to perform this command')
            return 'PERMISSION_ERROR'

    def do_pkgman(self, args):
        """Manage external packages: pkgman get / remove PKG_1 PKG_2 etc."""
        args = args.split()
        cmd = args[0]
        packages = args[1:]
        for arg in packages:
            if cmd == 'get':
                try:
                    func = external_module_repo.module_directory[arg]
                    setattr(self, 'do_'+arg, types.MethodType(func, self))
                    try:
                        script = external_module_repo.startup_script_directory[arg]
                        attempt = self.parse_path('/tmp')
                        if type(attempt) == str:
                            self.onecmd('mkdir /tmp')
                            attempt = self.parse_path('/tmp')
                        attempt[arg+'_setup.sh'] = script
                        self.onecmd(f'sudo run /tmp/{arg}_setup.sh')
                    except KeyboardInterrupt:
                        print(f'No startup script for module {arg} found or startup script failed')
                except KeyboardInterrupt:
                    print(f'Error - Module {arg} not found.')
                    return 'MODULE_NOT_FOUND_ERROR'
            elif cmd == 'remove':
                delattr(self, 'do_'+arg)

    def do_ps(self, args):
        activeps = ''
        for index, process in enumerate(self.curr_processes):
            activeps += f'{index} {process}'
        self.output = activeps

    def do_kill(self, args):
        try:
            self.curr_processes.pop(int(args))
            if 'shell' not in self.curr_processes:
                return 'EXIT'
        except ValueError:
            print(f'Error - Invalid process id {args}')
            return 'INVALID_PID_ERROR'
        except IndexError:
            print(f'Error - Invalid process id {args}')
            return 'INVALID_PID_ERROR'

    def do_grep(self, args):
        args = args.split()
        location = args[0]
        searchstring = re.compile(args[1])
        attempt = self.parse_path(location)
        results = []
        if type(attempt) == dict:
            for item in attempt:
                if type(item) == str:
                    for line in item.split('\n'):
                        if re.match(searchstring, line):
                            results.append(line)
        elif type(attempt) == str:
            for line in attempt.split('\n'):
                if re.match(searchstring, line):
                    results.append(line)
        self.output = '\n'.join(results)

    def do_lined(self, args):
        """Basic line editor: lined"""
        argqueue = [_.strip() for _ in args.split('\n') if _ != '']
        arg_expression = re.compile(r'^(\d*,?\d*)(\S+)')
        document = []
        mode = 'wait'
        scope = [0, 0]
        prompt = ''
        while True:
            try:
                if document:
                    document = '\n'.join(document).split('\n')
                if not argqueue:
                    cmd = self.request_input(prompt)
                else:
                    cmd = argqueue.pop(0)
                if mode == 'wait':
                    argmatch = re.match(arg_expression, cmd)
                    curr_scope = argmatch.group(1)
                    instruction = argmatch.group(2)
                    curr_scope = curr_scope.replace('$', '-1')
                    # First try to see if target is just a single line number, then try treating it as range
                    try:
                        scope = [int(curr_scope), int(curr_scope)]
                    except ValueError:
                        if scope == ',':
                            scope = [0, -1]
                        elif scope:
                            scope = [int(curr_scope.split(',')[0]), int(curr_scope.split(',')[1])]
                        # Else, scope is preserved from last line
                    # for index, item in enumerate(scope):
                    #     if item < 0:
                    #         scope[index] = 0
                    #     if item > len(document)-1:
                    #         scope[index] = len(document)
                    curr_key = instruction[0]
                    if curr_key == 'a':
                        mode = 'append'
                    elif curr_key == 'l':
                        if not document:
                            continue
                        output = []
                        for index, item in enumerate(scope):
                            if item == -1:
                                scope[index] = len(document)-1
                        i = scope[0]
                        while True:
                            output.append(document[i].replace('$', '\$')+'$')
                            i += 1
                            if i > scope[1]:
                                break
                        self.output = '\n'.join(output)
                        self.flush()
                    elif curr_key == 'w':
                        try:
                            dest = cmd.split()[1]
                            file_path = '/'.join(dest.split('/')[:-1])
                            file_name = dest.split('/')[-1]
                            attempt = self.parse_path(file_path)
                            if (attempt[file_name] != '%SPECIAL_NULL_FILE%') and (type(attempt) == dict) and (type(attempt[file_name]) == str):
                               attempt[file_name] = '\n'.join(document)
                        except IndexError:
                            continue
                        except KeyError:
                            attempt[file_name] = '\n'.join(document)
                        self.output = (len('\n'.join(document)))
                        self.flush()
                    elif curr_key == 'i':
                        mode = 'insert'
                    elif curr_key == 'd':
                        document = document[:scope[0]]+document[scope[1]:]
                        scope = [scope[0], scope[0]]
                    elif curr_key == 'c':
                        document = document[:scope[0]] + document[scope[1]:]
                        scope = [scope[0], scope[0]]
                        mode = 'append'
                    elif curr_key == 's':
                        if not document:
                            continue
                        instruction = instruction.split('/')
                        for index, item in enumerate(scope):
                            if item == -1:
                                scope[index] = len(document)-1
                        i = scope[0]
                        while True:
                            document[i] = re.sub(re.compile(instruction[1]), instruction[2], document[i])
                            i += 1
                            if i > scope[1]:
                                break
                    elif curr_key == 'p':
                        if not document:
                            continue
                        output = []
                        for index, item in enumerate(scope):
                            if item == -1:
                                scope[index] = len(document)-1
                        i = scope[0]
                        while True:
                            output.append(document[i])
                            i += 1
                            if i > scope[1]:
                                break
                        self.output = '\n'.join(output)
                        self.flush()
                    elif curr_key == 'g':
                        ops = cmd.split('/')
                        pattern = ops[1]
                        subcmdlist = '/'.join(ops[2:]).split('\\')
                        foundlines = []
                        for index, line in enumerate(document):
                            if re.match(re.compile(pattern), line):
                                foundlines.append(index)
                        for index in foundlines:
                            print([str(index)+x for x in subcmdlist])
                            argqueue += [str(index)+x for x in subcmdlist]
                    elif curr_key == 'P':
                        prompt = '> '
                    elif curr_key == '!':
                        self.redirect_output = True
                        self.onecmd(cmd[1:])
                        document.append('\n'.join(self.output_buffer))
                        self.output_buffer = []
                        self.redirect_output = False
                    elif curr_key == 'q':
                        return '\n'.join(document)
                elif mode == 'append':
                    if cmd != '.':
                        document.insert(scope[0]+1, cmd)
                        scope = [scope[0]+1, scope[0]+1]
                    else:
                        mode = 'wait'
                elif mode == 'insert':
                    if cmd != '.':
                        if document:
                            if scope[0] > 0:
                                document.insert(scope[0]-1, cmd)
                            else:
                                document = [cmd]+document
                            scope = [scope[0] + 1, scope[0] + 1]
                        else:
                            document = [cmd]
                    else:
                        mode = 'wait'
            except KeyboardInterrupt:
                continue

    def do_shutdown(self, args):
        """Shutdown computer: shutdown"""
        self.save()
        return 'EXIT'

    def parse_path(self, path, return_path=False):
        curr_dir = self.filesystem
        if len(path) > 0:
            if not path[0] == '/':
                path = self.cwd+path
        else:
            path = self.cwd
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
    import local_web_network
    universityserver = Computer(
        users={'root': {'password': 'ModifiedRootPasswordToDeterIntrusion', 'permissions': 'root'},
               'admin': {'password': 'ThisIsALongConvolutedAndProbablySecurePassword', 'permissions': 'sudo'}},
        drive={
            "bin": {
                ".server": {
                    "blacklist.txt": "",
                    "content.txt": "NOVOGROD UNIVERSITY   <br>"
                                   "----------------------<br>"
                                   "A leading provider of <br>"
                                   "excellent technical   <br>"
                                   "and social education, <br>"
                                   "Novogrod University is<br>"
                                   "committed to student  <br>"
                                   "welfare and excellence<br>"
                                   ".",
                    "wait_time.txt": "0",
                    "message_handler.sh":
                        "read msg\n"
                        "let senderaddr = int($msg[8:11])\n"
                        "let content = $msg[12:]\n"
                        "if [ ! ${grep /bin/.server/blacklist.txt $senderaddr} ] ? : goto END\n"
                        "if [ $content != 'FETCH_CONTENT' ] ? goto END\n"
                        "nd $senderaddr \"\" -f /bin/.server/content.txt -t 0\n"
                        ":END"
                }
            },
            "users": {
                "admin": {}
            },
            "dev": {
                "null": "%SPECIAL_NULL_FILE%",
                "urandom": "%SPECIAL_RANDOM_FILE%",
            },
            "tmp": {

            }
        },
        save_location='uni_admin_comp.pickle'
    )
    universityserver.onecmd('pkgman get server')
    universityserver.onecmd('pkgman get nd')
    universityserver.onecmd('run /bin/server')

    peter = local_web_network.make_basic_computer('peter', 'password', {
        'jobs.txt': 'Update student records\nMark term 3 exams\nSubmit national safety report'})
    ivan = local_web_network.make_basic_computer('ivan', 'scidept1981', {
        '3a_grades.txt': 'Tanya Novikova 31\nEkaterina Mikhailovna 57\nSavva Bogdanov 62\nMikhail Simonov 20\nZoya Pavlova 40\nKonstantin Frolov 42\nLev Kuznetsov 45\nOnisim Volkov 47\nStegnov Denisovich 42\nYeltsov Sergeyevich 50',
        '3b_grades.txt': 'Aptekar Artur Pavlovich 40\nKalganov Tikhonovich 31\nLuski Valerianovich 52\nDaniltsin Konstantinovich 44\nRozhkov Yermolayevich 67\nYugantsev Yaroslavovich 40\nLipin Yegorovich 41\nTurbin Vyacheslavovich 48'})
    try:
        with open('main_save.save') as f:
            test = pickle.load(f)
    except FileNotFoundError:
        test = Computer()
    local_web_network.Router(test, peter, ivan, universityserver)
    test.startup()


if __name__ == '__main__':
    main()
