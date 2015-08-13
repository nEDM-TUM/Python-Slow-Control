from cloudant.resource import Resource
from .exception import PynEDMNoFile
import traceback

class AttachmentFile(Resource):
    def __init__(self,req):
        self.req = req
        self.curr_pos = 0
        try:
            self.head_info = self.req.head()
            self.head_info.raise_for_status()
            self.total_length = int(self.head_info.headers['content-length'])
        except Exception as e:
            raise PynEDMNoFile(str(e))

    def seek(self, seekpos):
        """
        Seek to a position
        """
        if seekpos >= self.total_length:
            seekpos = self.total_length - 1
        self.curr_pos = seekpos

    def read(self, numbytes=-1):
        """
        Read number of bytes from current position
        """
        if numbytes < 0:
            numbytes = self.total_length
        to = self.curr_pos + numbytes - 1
        if to >= self.total_length:
            to = self.total_length-1
        if self.curr_pos == to:
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

    def iterate(self, chunk_size):
        """
        Iterates from this current position to the end of the file
        """
        while True:
            ri = self.read(chunk_size)
            if ri is None: break
            yield ri
