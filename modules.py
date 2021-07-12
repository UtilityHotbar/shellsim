def do_greet(self, args):
    """Greet name with welcome message: greet NAME"""
    self.output = 'Welcome ' + args


module_directory = {'greet': do_greet}
startup_script_directory = {}
