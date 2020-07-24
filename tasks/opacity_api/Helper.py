from .Constants import Constants
import Crypto.Random
from Crypto.Hash import keccak
import math
import json
import time
import bitcoinlib
import Crypto

class Helper:

    @staticmethod
    def GetUnixMilliseconds():
        return int(time.time()*1000)

    @staticmethod
    def GetUploadSize(size):
        blocksize = Constants.DEFAULT_BLOCK_SIZE
        blockCount = math.ceil(size / blocksize)
        return size + blockCount * Constants.BLOCK_OVERHEAD

    @staticmethod
    def GetEndIndex(uploadSize, fileMetaOptions):
        blockSize = fileMetaOptions.blockSize
        partSize = fileMetaOptions.partSize
        chunkSize = blockSize + Constants.BLOCK_OVERHEAD
        chunkCount = int(uploadSize / chunkSize)
        chunksPerPart = int(partSize / chunkSize) + 1
        endIndex = int(chunkCount / chunksPerPart) + 1
        return endIndex

    @staticmethod
    def getMetaDataKey(folderKey):
        hash = keccak.new(data=bytes(folderKey.public_hex, "utf-8"), digest_bits=256).hexdigest()
        return hash

    @staticmethod
    def getFolderHDKey(key, folder):
        return Helper.generateSubHDKey(key, "folder: " + folder)

    @staticmethod
    def getFileHDKey(key, file):
        return Helper.generateSubHDKey(key, "file: " + file)

    @staticmethod
    def generateSubHDKey(key, pathString):
        hash = keccak.new(data=bytes(pathString, "utf-8"), digest_bits=256).hexdigest()
        path = Helper.hashToPath(hash, prefix=True)
        subKey = key.subkey_for_path(path)
        return subKey

    @staticmethod
    def hashToPath(hash, prefix=False):
        if((len(hash) % 4) != 0):
            raise Exception("hash must be multiple of ? bytes")

        groups = [hash[i:i+4] for i in range(0,len(hash), 4)]
        numberedGroups = [str(int(hexNumber, 16)) for hexNumber in groups]
        result = ("m/" if prefix else "") + "'/".join(numberedGroups) + "'"
        return result

    @staticmethod
    def GenerateFileKeys():
        arr = Crypto.Random.get_random_bytes(64)
        return arr

    @staticmethod
    def GetPartial(fileInfo, partSize, currentIndex):
        remaining = fileInfo["size"] - (currentIndex * partSize)
        uploadSize = min(partSize, remaining)
        with open(fileInfo["fullName"], "rb") as input_file:
            input_file.seek(partSize*currentIndex)
            part = input_file.read(uploadSize)
        return part

    @staticmethod
    def GetJson(dictionary):
        return json.dumps(dictionary, separators=(',', ':'))
