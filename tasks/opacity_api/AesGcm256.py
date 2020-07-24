from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
from .Constants import Constants

class AesGcm256:

    @staticmethod
    def encryptString(message, key):
        messageBytes = bytes(message, "utf-8")

        #key = AESGCM.generate_key(bit_length=256)
        encryptedMessage = AesGcm256.encrypt(messageBytes, key)

        return encryptedMessage

    @staticmethod
    def encrypt(messageBytes, key):
        aesgcm = AESGCM(key)
        nonce = os.urandom(16)
        encryptedBytes = aesgcm.encrypt(nonce=nonce, data=messageBytes, associated_data=None)
        encryptedBytes += nonce

        return encryptedBytes

    @staticmethod
    def decrypt(messageBytes, key):
        overhead = Constants.BLOCK_OVERHEAD
        raw = messageBytes[0:len(messageBytes)-overhead]
        tag = messageBytes[len(raw):len(raw)+Constants.TAG_BYTE_LENGTH]
        iv = messageBytes[len(raw)+len(tag):len(messageBytes)]

        aesgcm = AESGCM(key)
        decryptedBytes = aesgcm.decrypt(nonce=iv, data=raw+tag, associated_data=None)
        return decryptedBytes