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

## Lined (LINe EDitor)
Based on the `ed` editor. Commands should be issued in the format `A,BcP` where `A,B` is a line range (defaults to the last line you added), `c` is the command and `P` the arguments. If you use `,` in place of `A,B` the range is the entire document. If you just use a single line number it will only target that single line. `cat file.txt | lined` will push all commands in `file.txt` to lined.

Supports the following commands:
* `a`: Append after line, switch to insert mode (Treat all commands as lines to be inserted until lined receives a single `.`)
* `i`: Insert before line, switch to insert mode
* `c`: Change
* `d`: Delete
* `l`: List
* `w filename`: Write to `filename`, outputing number of characters written on successful write
* `!command`: Run `command` in shell and add output to document
* `s/re/new`: Substitute everything in range based on regular expression `re` with the text `new`
* `g/re/p`: Global search for all lines that match regex `re`, issuing command string `p`. Command strings can be separated by `\` for multiple commands (Commands that insert lines or delete them will mess up under the current implementation)
* `q`: Quit
