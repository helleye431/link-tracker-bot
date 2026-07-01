class DataProcessingError(Exception):
    pass


class MessageDeserializationError(DataProcessingError):
    pass
