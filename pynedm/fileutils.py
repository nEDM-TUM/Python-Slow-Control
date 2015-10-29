from cloudant.resource import Resource
from .exception import PynEDMNoFile
import traceback

__all__ = [ "AttachmentFile" ]

class AttachmentFile(Resource):
    """
    Provides a file-like object for handling document attachments without
    downloading them.

    Returned by :func:`pynedm.utils.ProcessObject.open_file`
    """
    def __init__(self,req):
        self.req = req
        self.curr_pos = 0
        try:
            self.head_info = self.req.head()
            self.head_info.raise_for_status()
            self.total_length = int(self.head_info.headers['content-length'])
        except Exception as e:
            raise PynEDMNoFile(str(e))

    def seek(self, seekpos, whence=0):
        """
        Seek to a position in the file

        :param seekpos: seek position
        :type seekpos: int
        :param whence: direction (0 - from beginning, 1 - relative to current position, 2 - from end)
        :type seekpos: int
        """
        if whence == 1:
            seekpos += self.curr_pos
        elif whence == 2:
            seekpos = self.total_length - seekpos

        if seekpos > self.total_length:
            seekpos = self.total_length
        self.curr_pos = seekpos

    def tell(self):
        """
        Get the current position

        :returns: int - current position
        """
        return self.curr_pos

    def read(self, numbytes=-1):
        """
        Read number of bytes from current position

        :param numbytes: number of bytes to read (< 0 reads remaining bytes)
        :type numbytes: int
        """
        if numbytes < 0:
            numbytes = self.total_length
        to = self.curr_pos + numbytes - 1
        if to >= self.total_length:
            to = self.total_length-1
        if self.curr_pos >= to:
            return None
        try:
            t = self.req.get(headers={
              "Range" : "bytes={}-{}".format(self.curr_pos, to)
            })
            t.raise_for_status()
            self.seek(to+1)
            return t.content
        except Exception as e:
            raise PynEDMNoFile(str(e))

    def __enter__(self):
        """
        Allow 'with' calls.
        """
        return self

    def __exit__(self, *args):
        """
        Allow 'with' calls.
        """

    def iterate(self, chunk_size):
        """
        Iterates from this current position to the end of the file

        :param chunk_size: number of bytes in chunk to yield
        :type chunk_size: int
        """
        while True:
            ri = self.read(chunk_size)
            if ri is None: break
            yield ri
