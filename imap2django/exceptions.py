class Imap2DjangoException(Exception):
    pass

class ParsingError(Imap2DjangoException):
    pass

class NormalizationError(Imap2DjangoException):
    pass

class StorageError(Imap2DjangoException):
    pass

class ThreadingError(Imap2DjangoException):
    pass

