import json

class FolderMetaFileVersion:

    def __init__(self, size=None, handle=None, modified=None, created=None):
        self.size = size
        self.handle = handle
        self.modified = modified
        self.created = created

class FolderMetaFile:

    def __init__(self):
        self.name = None
        self.tags = []
        self.versions = []  # List[FolderMetaFileVersion]

class FolderMetaFolder:

    def __init__(self, name=None, handle=None):
        self.name = name
        self.handle = handle


class FolderMetaData:

    def __init__(self):
        self.name = None
        self.created = None
        self.modified = None
        self.files = []  # List[FolderMetaFile]
        self.folders = []  # List[FolderMetaFolder]
        self.tags = []

    def toString(self):
        newList = list()
        newList.append(self.name)

        files = []

        for file in self.files:
            fileAsList = list()
            fileAsList.append(file.name)
            fileAsList.append(file.created)
            fileAsList.append(file.modified)

            versionsList = []
            for version in file.versions:
                versionAsList = list()
                versionAsList.append(version.handle)
                versionAsList.append(version.size)
                versionAsList.append(version.created)
                versionAsList.append(version.modified)
                versionsList.append(versionAsList)

            fileAsList.append(versionsList)
            files.append(fileAsList)

        newList.append(files)

        folders = []
        for folder in self.folders:
            folderAsList = list()
            folderAsList.append(folder.name)
            folderAsList.append(folder.handle)
            folders.append(folderAsList)

        newList.append(folders)

        newList.append(self.created)
        newList.append(self.modified)

        newListAsString = json.dumps(newList, separators=(',', ':'))

        return newListAsString

    @staticmethod
    def ToObject(data):
        folderMetaData = FolderMetaData()

        folderMetaData.name = str(data[0])
        folderMetaData.created = int(data[3])
        folderMetaData.modified = int(data[4])

        for file in data[1]:
            folderMetaFile = FolderMetaFile()
            folderMetaFile.name = str(file[0])
            folderMetaFile.created = int(file[1])
            folderMetaFile.modified = int(file[2])

            for version in file[3]:
                folderMetaFileVersion = FolderMetaFileVersion()
                folderMetaFileVersion.handle = str(version[0])
                folderMetaFileVersion.size = int(version[1])
                folderMetaFileVersion.created = int(version[2])
                folderMetaFileVersion.modified = int(version[3])

                folderMetaFile.versions.append(folderMetaFileVersion)

            folderMetaData.files.append(folderMetaFile)

        for folder in data[2]:
            folderMetaFolder = FolderMetaFolder(folder[0],folder[1])
            folderMetaData.folders.append(folderMetaFolder)

        return folderMetaData

