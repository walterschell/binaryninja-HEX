from binaryninja import *
import struct
def view2str(bv):
    """
    Buffers all data from a binary view to a string
    :param bv: BinaryView to read from
    :return: string of the data underlying bv
    """
    size = len(bv)
    txt = bv.read(0, size)
    return txt

class HexRegion:
    """
    Contigous region of memory.
    """
    def __init__(self, start_address):
        self.start_address = start_address
        self.data = ''
    
    def append(self, data):
        self.data += data
    @property
    def end_address(self):
        return self.start_address + len(self.data)

    def __contains__(self, addr):
        if addr >= self.start_address and addr < self.end_address:
            return True
        return False

    def __getitem__(self, addr):
        if isinstance(addr, slice):
            if not addr.start in self:
                raise Exception('Invalid Address for region')
            return self.data[addr.start - self.start_address: addr.stop - self.start_address]
    
        if not addr in self:
            raise Exception('Invalid Address %x for region %s' % (addr,self))
        return self.data[addr - self.start_address]
    def __str__(self):
        return '[0x%x, 0x%x)' % (self.start_address, self.end_address)

class HexData:
    def __init__(self, data):
        self.regions = []
        self.max_addr = 0
        lines = data.split('\n')
        base_addr = 0
        last_region = None
        for line in lines:
            line = line.rstrip()
            #print '->%s<-' % line
            start = line[0]
            if start != ':':
               raise Exception('Invalid character "%s" (Expected ":"' % start)
            size = int(line[1:3], 16)
            if len(line) != 2*size + 11:
                   raise Exception('Invalid line size %d (Expected %d)' % (len(line), 2*size+11))
            addr = int(line[3:7], 16)
            rec_type = int(line[7:9], 16)
            rec_data_text = line[9:9+(2 * size)]
               
            rec_data = ''

            for i in range(size):
                rec_data += chr(int(rec_data_text[2*i:2*i+2], 16))

            #Data Bytes   
            if rec_type == 0:
                real_addr = base_addr + addr
                self.max_addr = max(self.max_addr, real_addr + size)
                if last_region is None:
                    last_region = HexRegion(real_addr)
                    self.regions.append(last_region)

                if last_region.end_address != real_addr:
                    last_region = HexRegion(real_addr)
                    self.regions.append(last_region)
                last_region.append(rec_data)
                
            #EOF
            elif rec_type == 1:
                break             
                
            #Extended Linear Address
            elif rec_type == 4:
                base_addr, = struct.unpack('!H', rec_data)
                base_addr <<= 16
                print 'New Base Addr: 0x%x' % base_addr
        #regions aren't nessicarily in order in file
        self.regions.sort(key=lambda x: x.start_address)
        for region in self.regions:
            print region
    def __contains__(self, addr):
        for region in self.regions:
            if addr in region:
                return True

        return False

    def __len__(self):
        return self.max_addr

    def get_next_valid_offset(self, addr):
        result = None
        for i, region in enumerate(self.regions[:-1]):
            if addr in region:
                result = addr
                break
            if addr > region.end_address and addr < self.regions[i+1].start_address:
                result = self.regions[i+1].start_address
                break
        if result is None:
            print 'No valid offset from 0x%x' % addr
        else:
            print 'Next valid offset from 0x%x: 0x%x' % (addr, result)
        return result


    def __getitem__(self, addr):
        if isinstance(addr, slice):
            for region in self.regions:
                if addr.start in region:
                    return region[addr]
            raise Exception('Invalid Address: 0x%x' % addr.start)
    
        for region in self.regions:
            if addr in region:
                return region[addr]
        raise Exception('Invalid Address: %0x' % addr)
class HEXView(BinaryView):
    """
    Used for the Intel-HEX format
    """
    name = "Intel-HEX"
    long_name = "Intel-HEX"

    def __init__(self, data):
        BinaryView.__init__(self, parent_view=data, file_metadata=data.file)
        self.data = HexData(view2str(data))

    @classmethod
    def is_valid_for_data(cls, data):
        print 'Trying Intel-Hex'
        try:
            HexData(view2str(data))
            return True
        except Exception as e:
            print 'Exception: %s' % e
        return False


    def perform_read(self, addr, length):
        try:
            result = self.data[addr: addr + length]
            return result
        except:
            return None

    def perform_is_valid_offset(self, addr):
        return addr in self.data

    def perform_is_executable(self):
        return True

    def perform_get_length(self):
        return len(self.data)

    def perform_get_next_valid_offset(self, addr):
        return self.data.get_next_valid_offset(addr)

def init_module():
    HEXView.register()

init_module()