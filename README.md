# shellsim
A self-contained simulation of a bash-like shell, with scripting, piping, streaming functionality and internal filesystem.

## Commands

### Basic commands
* Change current working directory: cd DIR_PATH
* List items in directory: ls / ls DIR_PATH
* Make directory: mkdir DIR_NAME
* Remove directory: rmdir DIR_NAME
* Print current working directory: pwd
* Create new file: touch FILE_PATH
* Delete file: rm FILE_PATH
* Manage users: user add/del/mod USERNAME OPTIONS
* Execute command as superuser: sudo COMMAND

### File handling
* Echo input to output: echo INPUT
* Concatenate file contents: cat FILE_NAME1 FILE_NAME2 etc.

### Variables and scripting
* Declare string variable: declare VAR_NAME=VALUE
* Declare variable as result of expression: declare VAR_NAME=EXPR
* Read in input stdin or user to variable: read VAR_NAME
* Conditional execution: if [ COND ] ? TRUE_STATEMENT : FALSE_STATEMENT
* Run shell script: run FILE_PATH

### Package management
* Manage external packages: pkgman get / remove PKG_1 PKG_2 etc.
> Pkgman works by checking the `module_directory` object in `modules.py`. Functions there with a corresponding name will be added as attributes of the `Computer` object callable as commands in the shell. `pkgman remove` will delete the attribute, thus unlinking the function.

## Advanced Features
### Piping
`COMMAND 1 | COMMAND 2` will supply the output of command 1 as arguments for command 2. Newlines are treated as argument separators. In the case of scripts, arguments are stored in an input stream which can be read from using the `read` command.

### Streaming
`COMMAND 1 > FILE_NAME.txt` will stream the output of command 1 to file_name.txt. `>` overwrites existing file content, `>>` appends to existing file content.

### Script flow
* `goto LABEL` will goto the line with the label `:LABEL`, pushing the current position onto the `return` stack. Useable in shell scripts only.
* `return` will return to the position in the script after your last `goto` statement. Useable in shell scripts only.

### Filename matching
`rm` and `cat` support filename matching. `*` to match anything, `?` to match a single character, `[abc]` to match any character in `abc`, `[^abc]` to match any character not in `abc`.
