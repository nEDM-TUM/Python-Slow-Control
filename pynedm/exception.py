class PynEDMException(Exception):
    """
    General exception for :mod:`pynedm`
    """

class CommandCollision(PynEDMException):
    """
    :func:`pynedm.utils.listen` was called on a database where particular commands
    were already being used. 
    """

class PynEDMNoFile(PynEDMException):
    """
    File does not exist.	
    """

