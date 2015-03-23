"""Coordinates data reading, translation and analysis.
"""

import os
import logging
import imp
import ipc
import time

class Worker(object):
    """Coordinates data reading, translation and analysis.

    This is the main class of the backend of Hummingbird. It uses a light source
    dependent translator to read and translate the data into a common format. It
    then runs whatever analysis algorithms are specified in the user provided
    configuration file.

    Args:
        config_file (str): The configuration file to load.
    """
    state = None
    conf = None
    def __init__(self, config_file):
        if(config_file is None):
            # Try to load an example configuration file
            config_file = os.path.abspath(os.path.dirname(__file__)+
                                          "/../../examples/cxitut13/conf.py")
            logging.warning("No configuration file given! "
                            "Loading example configuration from %s",
                            (config_file))
        self._config_file = config_file
        # self.backend_conf = imp.load_source('backend_conf', config_file)
        self.load_conf()
        Worker.state['_config_file'] = config_file
        Worker.state['_config_dir'] = os.path.dirname(config_file)
        if(not ipc.mpi.is_master()):
            self.translator = init_translator(Worker.state)
        print 'Starting backend...'

    def load_conf(self):
        """Load or reload the configuration file."""
        Worker.conf = imp.load_source('backend_conf', self._config_file)
        if(Worker.state is None):
            Worker.state = Worker.conf.state
        else:
            # Only copy the keys that exist in the newly loaded state
            for k in Worker.conf.state:
                Worker.state[k] = Worker.conf.state[k]

    def start(self):
        """Start the event loop."""
        Worker.state['running'] = True
        self.event_loop()

    def event_loop(self):
        """The event loop.

        While ``state['running']`` is True, it will get events
        from the translator and process them as fast as possible.
        """
        while(True):
            try:
                while(Worker.state['running']):
                    if(ipc.mpi.is_master()):
                        ipc.mpi.master_loop()
                    else:
                        evt = self.translator.nextEvent()
                        ipc.set_current_event(evt)
                        Worker.conf.onEvent(evt)
            except KeyboardInterrupt:
                try:
                    print "Hit Ctrl+c again in the next second to quit..."
                    time.sleep(1)
                    print "Reloading configuration file."
                    self.load_conf()
                except KeyboardInterrupt:
                    print "Exiting..."
                    break


def init_translator(state):
    """Initialize the translator, depending on the state['Facility']."""
    if('Facility' not in state):
        raise ValueError("You need to set the 'Facility' in the configuration")
    elif(state['Facility'] == 'LCLS'):
        from backend.lcls import LCLSTranslator
        return LCLSTranslator(state)
    elif(state['Facility'] == 'dummy'):
        from backend.dummy import DummyTranslator
        return DummyTranslator(state)
    else:
        raise ValueError('Facility %s not supported' % (state['Facility']))
