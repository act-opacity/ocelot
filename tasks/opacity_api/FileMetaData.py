from .Constants import Constants

class FileMetaData:

    def __init__(self, fileData):
        self.name = fileData["name"]
        self.type = fileData["type"]
        self.size = fileData["size"]
        self.p = FileMetaOptions()

    def getDict(self):
        temp = self.__dict__.copy()
        temp["p"] = self.p.__dict__
        return temp


class FileMetaOptions:

    def __init__(self):
        self.blockSize = Constants.DEFAULT_BLOCK_SIZE
        self.partSize = 10485760  # should be Constants.DEFAULT_PART_SIZE but they are 2 different numbers
