import base64, bitcoinlib, json, math, mimetypes, requests, shutil, os, web3, posixpath
from random import randint
from time import sleep
from pathlib import Path
from joblib import Parallel, delayed
from Crypto.Hash import keccak
from tasks.opacity_api.AccountStatus import AccountStatus
from tasks.opacity_api.AesGcm256 import AesGcm256
from tasks.opacity_api.Constants import Constants
from tasks.opacity_api.FileMetaData import FileMetaData
from tasks.opacity_api.FolderMetaData import FolderMetaData, FolderMetaFolder, FolderMetaFile, FolderMetaFileVersion
from tasks.opacity_api.Helper import Helper

# location on host to save downloads until completely downloaded
IN_PROGRESS_DOWNLOADS = os.environ.get('IN_PROGRESS_DOWNLOADS')

class Opacity:
    _baseUrl = "https://broker-1.opacitynodes.com:3000/api/v1/"
    _privateKey = ""
    _chainCode = ""
    _masterKey = None
    _status = None
    _metaData = FolderMetaData()

    def __init__(self, account_handle):
        if len(account_handle) != 128:
            raise AttributeError("The Account handle should have the length of 128")

        self._privateKey = account_handle[0:64]
        self._chainCode = account_handle[64:128]
        private_key_bytes = bytearray.fromhex(self._privateKey)
        chain_code_bytes = bytearray.fromhex(self._chainCode)
        new_key = bitcoinlib.keys.Key(import_key=private_key_bytes, is_private=True, compressed=True)
        self._masterKey = bitcoinlib.keys.HDKey(key=new_key.private_byte, chain=chain_code_bytes)

    def checkAccountStatus(self):
        requestBody = dict()
        requestBody["timestamp"] = Helper.GetUnixMilliseconds()
        rawPayload = Helper.GetJson(requestBody)

        payload = self.signPayloadDict(rawPayload)
        payloadJson = Helper.GetJson(payload)

        with requests.Session() as s:
            response = s.post(self._baseUrl + "account-data", data=payloadJson)

        if response.status_code == 404:
            raise AttributeError("The provided account handle is invalid!")
        else:
            accountData = response.content.decode("utf-8")
            return AccountStatus.ToObject(accountData)

    def signPayloadDict(self, requestBodyJson):
        # hash the payload
        msgBytes = bytearray(requestBodyJson, "utf-8")
        msgHashHex = keccak.new(data=msgBytes, digest_bits=256).hexdigest()
        msgHash = bytearray.fromhex(msgHashHex)

        # create the signature
        privKey = web3.Account.from_key(self._privateKey)
        signature = privKey.signHash(msgHash)

        # signatureFinal = format(signature.r, 'x') + format(signature.s, 'x')
        signatureFinal = signature.signature.hex()[2:130]
        if len(signatureFinal) != 128:
            raise Exception("signature doesn't have the length of 128")

        # get public key as hex
        pubHex = self._masterKey.public_compressed_hex

        newDict = dict()
        newDict["requestBody"] = requestBodyJson
        newDict["signature"] = signatureFinal
        newDict["publicKey"] = pubHex
        newDict["hash"] = msgHashHex

        return newDict

    def SignPayloadForm(self, requestBodyJson, extraPayload):
        # hash the payload
        msgBytes = bytearray(requestBodyJson, "utf-8")
        msgHashHex = keccak.new(data=msgBytes, digest_bits=256).hexdigest()
        msgHash = bytearray.fromhex(msgHashHex)

        # create the signature
        privKey = web3.Account.from_key(self._privateKey)
        signature = privKey.signHash(msgHash)
        signatureFinal = signature.signature.hex()[2:130]
        if (len(signatureFinal) != 128):
            raise Exception("signature doesn't have length of 128")

        # get public key as hex
        pubHex = self._masterKey.public_compressed_hex

        newDict = dict()
        newDict["requestBody"] = (None, requestBodyJson, "text/plain; charset=utf-8")
        newDict['signature'] = (None, signatureFinal, "text/plain; charset=utf-8")
        newDict['publicKey'] = (None, pubHex, "text/plain; charset=utf-8")

        for payloadKey, payloadValue in extraPayload.items():
            newDict[payloadKey] = payloadValue

        return newDict

    def AddFileToFolderMetaData(self, folder, fileOrFolder, isFile=False, isFolder=False):
        metadata = self.getFolderData(folder=folder)
        keyString = metadata["keyString"]
        folderMetaData = metadata["metadata"]

        if isFile:
            folderMetaData.files.append(fileOrFolder)
        elif isFolder:
            folderMetaData.folders.append(fileOrFolder)
        else:
            raise EnvironmentError("neither file nor folder")

        folderMetaDataString = folderMetaData.toString()
        encryptedFolderMetaData = AesGcm256.encryptString(folderMetaDataString, bytearray.fromhex(keyString))
        encryptedFolderMetaDataBase64 = base64.b64encode(encryptedFolderMetaData).decode("utf-8")
        AesGcm256.decrypt(encryptedFolderMetaData, bytearray.fromhex(keyString))
        metaReqDict = {
            "timestamp": Helper.GetUnixMilliseconds(),
            "metadataKey": metadata["metadataKey"],
            "metadata": encryptedFolderMetaDataBase64
        }

        metaReqDictJson = Helper.GetJson(metaReqDict)
        payload = self.signPayloadDict(metaReqDictJson)
        payloadJson = Helper.GetJson(payload)

        try:
            with requests.Session() as s:
                response = s.post(self._baseUrl + "metadata/set", data=payloadJson)
        except:
            raise

        return response

    def GetFolderMetaData(self, metaDataKey, keyString):
        timestamp = Helper.GetUnixMilliseconds()
        payload = dict({
            "timestamp": timestamp,
            "metadataKey": metaDataKey
        })
        payloadJson = Helper.GetJson(payload)
        payloadMeta = self.signPayloadDict(payloadJson)
        payloadMetaJson = Helper.GetJson(payloadMeta)

        with requests.Session() as s:
            response = s.post(self._baseUrl + "metadata/get", data=payloadMetaJson)

        resultMetaDataEncrypted = response.content.decode("utf-8")
        resultMetaDataEncryptedJson = json.loads(resultMetaDataEncrypted)
        stringbytes = bytes(resultMetaDataEncryptedJson["metadata"], "utf-8")
        stringDecoded = base64.b64decode(stringbytes)
        decryptedMetaData = AesGcm256.decrypt(stringDecoded, bytearray.fromhex(keyString))
        metaData = decryptedMetaData.decode("utf-8")
        metaData = json.loads(metaData)
        folderMetaData = FolderMetaData.ToObject(metaData)
        return folderMetaData

    def getFolderData(self, folder, recreate_if_nonexistent=True):
        folderKey = Helper.getFolderHDKey(self._masterKey, folder)
        metaDataKey = Helper.getMetaDataKey(folderKey)
        keyString = keccak.new(data=bytearray(folderKey.private_hex, "utf-8"), digest_bits=256).hexdigest()
        try:
            folderMetaData = self.GetFolderMetaData(metaDataKey, keyString)
            self._metaData = folderMetaData
        except TypeError as e:
            print(f"Error: {e}")
            print(f"Folder does not exist; must have been deleted already")
            if recreate_if_nonexistent:
                folderMetaData = FolderMetaData()
            else:
                return False
        return {"metadata": folderMetaData, "keyString": keyString, "metadataKey": metaDataKey}

    def download(self, fileHandle, savingPath, fileName):
        # Create directory structure, including all parents, as needed
        Path(savingPath).mkdir(parents=True, exist_ok=True)
        self.downloadFile(fileHandle, savingPath, fileName)

    def downloadFile(self, fileHandle, savingPath, fileName):
        fileId = fileHandle[:64]
        fileKey = fileHandle[64:]
        key = bytearray.fromhex(fileKey)
        payloadJson = json.dumps({"fileID": fileId})

        with requests.Session() as s:
            response = s.post(self._baseUrl + "download", data=payloadJson)

        url = response.content.decode()
        # check for good response data
        temp_url = json.loads(url)
        if isinstance(temp_url, dict) and "fileDownloadUrl" in temp_url:
            url = temp_url["fileDownloadUrl"]
        else:
            raise ValueError('Requested file appears to be nonexistent within Opacity storage for your account. Failed to download.')
        # Get file metadata
        with requests.Session() as s:
            response = s.get(url + "/metadata")
        encryptedMetaData = response.content
        # Decrypt file metadata
        decryptedMetaData = AesGcm256.decrypt(encryptedMetaData, key)
        metaData = json.loads(decryptedMetaData)
        # prepare for download
        uploadSize = Helper.GetUploadSize(metaData["size"])
        partSize = 5245440  # 80 * (Constants.DEFAULT_BLOCK_SIZE + Constants.BLOCK_OVERHEAD)
        parts = int(uploadSize / partSize) + 1
        # create temp directory where specific file will be saved
        temp_download_dir = os.path.join(IN_PROGRESS_DOWNLOADS, fileId)
        Path(temp_download_dir).mkdir(parents=True, exist_ok=True)

        ''' Downloading all parts '''
        
        fileUrl = url + "/file"

        print("Downloading file: {}".format(fileName))
        # start_time = time.time()
        # downloadPart() retrieves all file parts and saves in temp directory
        Parallel(n_jobs=5)(
            delayed(self.downloadPart)(partNumber, parts, partSize, uploadSize, fileUrl, temp_download_dir) for partNumber in
            range(parts))
        # print("--- %s seconds with parallel n = 5---" % (time.time() - start_time))

        ''' Decrypt the chunks and restore the file '''
        chunkSize = metaData["p"]["blockSize"] + Constants.BLOCK_OVERHEAD
        chunksAmount = int(uploadSize / chunkSize) + 1

        # create complete file name, including path
        file_name = os.path.join(savingPath, fileName)

        # Remove (Overwrite) local file at same location if it exists
        if os.path.isfile(file_name):
            os.remove(file_name)

        # Assemble and write final file
        with open(file_name, 'ab+') as saveFile:
            fileIndex = 0
            seek = 0
            for chunkIndex in range(chunksAmount):
                chunkRawBytes = None
                with open(os.path.join(temp_download_dir, str(fileIndex) + ".part"), 'rb') as partFile:
                    partFile.seek(seek)
                    toReadBytes = chunkSize
                    # if the bytes to read exceed the file in the next iteration of the for loop
                    # you need to go to the next partFile -> seek from start
                    if seek + toReadBytes >= os.path.getsize(partFile.name):
                        toReadBytes = os.path.getsize(partFile.name) - seek
                        seek = 0
                        fileIndex = fileIndex + 1
                    else:
                        seek = seek + chunkSize
                    chunkRawBytes = partFile.read(toReadBytes)
                decryptedChunk = AesGcm256.decrypt(chunkRawBytes, key)
                saveFile.write(decryptedChunk)
        # file has been saved to permanent directory
        # now cleanup temp download directory and contents
        shutil.rmtree(temp_download_dir)
        print("Finished download of {}".format(fileName))

    def downloadPart(self, partNumber, endPartNumber, partSize, uploadSize, url, folderPath):
        print("Downloading part {:d} out of {:d}".format(partNumber + 1, endPartNumber))
        byteFrom = partNumber * partSize
        byteTo = (partNumber + 1) * partSize - 1
        if (byteTo > uploadSize - 1):
            byteTo = uploadSize - 1
        fileBytes = None

        with requests.Session() as s:
            temp = "bytes={}-{}".format(byteFrom, byteTo)
            s.headers.update({"range": temp})
            response = s.get(url=url)
            fileBytes = response.content

        fileToWriteTo = os.path.join(folderPath, str(partNumber) + ".part")

        with open(fileToWriteTo, 'wb') as file:
            file.write(fileBytes)

    def rename_file(self, folder, file_handle, new_file_name):
        if len(file_handle) == 128:
            # only rename the file and set metadata
            metadata = self.getFolderData(folder)
            for file in metadata["metadata"].files:
                for version in file.versions:
                    if version.handle == file_handle:
                        previous_name = file.name
                        file.name = new_file_name
                        break
            self.setMetadata(metadata)
            print(f"Successfully renamed file from '{previous_name}' to '{new_file_name}'")

    def setMetadata(self, metadata):
        keyString = metadata["keyString"]
        folderMetaDataString = metadata["metadata"].toString()
        encryptedFolderMetaData = AesGcm256.encryptString(folderMetaDataString, bytearray.fromhex(keyString))
        encryptedFolderMetaDataBase64 = base64.b64encode(encryptedFolderMetaData).decode("utf-8")
        AesGcm256.decrypt(encryptedFolderMetaData, bytearray.fromhex(keyString))

        metaReqDict = {
            "timestamp": Helper.GetUnixMilliseconds(),
            "metadataKey": metadata["metadataKey"],
            "metadata": encryptedFolderMetaDataBase64
        }

        metaReqDictJson = Helper.GetJson(metaReqDict)
        payload = self.signPayloadDict(metaReqDictJson)
        payloadJson = Helper.GetJson(payload)

        with requests.Session() as s:
            response = s.post(self._baseUrl + "metadata/set", data=payloadJson)

        folderMetaData = self.decryptMetaData(response, keyString)
        metadata["metadata"] = folderMetaData

        return metadata

    def decryptMetaData(self, metadataResponse, keyString):
        resultMetaDataEncrypted = metadataResponse.content.decode("utf-8")
        resultMetaDataEncryptedJson = json.loads(resultMetaDataEncrypted)
        stringbytes = bytes(resultMetaDataEncryptedJson["metadata"], "utf-8")
        stringDecoded = base64.b64decode(stringbytes)
        decryptedMetaData = AesGcm256.decrypt(stringDecoded, bytearray.fromhex(keyString))
        metaData = decryptedMetaData.decode("utf-8")
        metaData = json.loads(metaData)
        folderMetaData = FolderMetaData.ToObject(metaData)
        return folderMetaData

    def createMetadata(self, folder):
        dictionary = self.createMetadatakeyAndKeystring(folder=folder)
        requestBody = dict()
        requestBody["timestamp"] = Helper.GetUnixMilliseconds()
        requestBody["metadataKey"] = dictionary["metadataKey"]
        rawPayload = Helper.GetJson(requestBody)
        payload = self.signPayloadDict(rawPayload)
        payloadJson = Helper.GetJson(payload)

        with requests.Session() as s:
            response = s.post(self._baseUrl + "metadata/create", data=payloadJson)

        if response.status_code == 403:
            print("The folder: {} already exists! -> Will use that folder instead".format(folder))
            return {"metadataKey": dictionary["metadataKey"], "addFolder": False}
        else:
            # set empty foldermetadata
            newfolderMetadata = FolderMetaData()
            newfolderMetadata.name = os.path.basename(folder)
            newfolderMetadata.created = Helper.GetUnixMilliseconds()
            newfolderMetadata.modified = Helper.GetUnixMilliseconds()
            dictionary["metadata"] = newfolderMetadata
            self.setMetadata(dictionary)
            return {"metadataKey": dictionary["metadataKey"], "addFolder": True}

    def createMetadatakeyAndKeystring(self, folder):
        folder = folder
        folderKey = Helper.getFolderHDKey(self._masterKey, folder)
        metaDataKey = Helper.getMetaDataKey(folderKey)
        keyString = keccak.new(data=bytearray(folderKey.private_hex, "utf-8"), digest_bits=256).hexdigest()
        return {"metadataKey": metaDataKey, "keyString": keyString}

    def move_file(self, file_handle, fromFolder, toFolder):
        if len(file_handle) == 128:
            print("moving file")
            fromFolderMetadata = self.getFolderData(fromFolder)
            toFolderMetadata = self.getFolderData(toFolder)
            file_list = []
            for file in fromFolderMetadata["metadata"].files:
                for version in file.versions:
                    if version.handle == file_handle:
                        # add file metadata to the moveto folder
                        toFolderMetadata["metadata"].files.append(file)
                    else:
                        # don't add back file being moved
                        file_list.append(file)
            # overwrite existing metadata for files
            fromFolderMetadata["metadata"].files = file_list
            # make it so
            self.setMetadata(fromFolderMetadata)
            self.setMetadata(toFolderMetadata)
            print("Successfully moved the folder from '{}' to '{}'".format(fromFolder, toFolder))
        elif not file_handle:
            # must be local file only
            print("no file handle passed in. exiting")
        else:
            raise Exception("Please provide a file handle with the length of 128 characters")