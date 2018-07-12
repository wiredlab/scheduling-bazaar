import bz2
import gzip
import zipfile



# Compressed file reader
# adapted from:
#   https://stackoverflow.com/a/13045892

class CompressedFile(object):
    magic = None
    file_type = None
    mime_type = None

    def __init__(self, filename):
        # f is an open file or file like object
        self.filename = filename
        self.accessor = self.open()

    @classmethod
    def is_magic(self, data):
        return data.startswith(self.magic)

    def open(self):
        return None


class ZIPFile(CompressedFile):
    magic = b'\x50\x4b\x03\x04'
    file_type = 'zip'
    mime_type = 'compressed/zip'

    def open(self):
        return zipfile.ZipFile(self.filename)


class BZ2File(CompressedFile):
    magic = b'\x42\x5a\x68'
    file_type = 'bz2'
    mime_type = 'compressed/bz2'

    def open(self):
        return bz2.BZ2File(self.filename)


class GZFile(CompressedFile):
    magic = b'\x1f\x8b\x08'
    file_type = 'gz'
    mime_type = 'compressed/gz'

    def open(self):
        return gzip.GzipFile(self.filename)


class UnknownFile(CompressedFile):
    magic = b''
    file_type = '???'
    mime_type = 'unknown'

    def open(self):
        return open(self.filename)

# factory function to create a suitable instance for accessing files
def open_compressed(filename):
    with open(filename, 'rb') as f:
        start_of_file = f.read(1024)

    for cls in (ZIPFile, BZ2File, GZFile, UnknownFile):
        if cls.is_magic(start_of_file):
            return cls(filename).open()
    return None

