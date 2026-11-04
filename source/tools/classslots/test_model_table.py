"""Static and emulated checks of the model table move against the pristine 1.130 client (skipped when it is absent)."""
import re
import struct
import unittest

import model_table as table
import patch_class_slots as slots
import test_class_slots

GETTER = 0x433F24


class ModelTableTests(unittest.TestCase):
    offset = test_class_slots.ClassSlotPatchTests.offset

    @classmethod
    def setUpClass(cls):
        if not test_class_slots.PRISTINE.is_file():
            raise unittest.SkipTest('Pristine 1.130 game.dll is not available')
        cls.original = slots.patch(test_class_slots.PRISTINE.read_bytes())[0]
        cls.moved = table.widen(cls.original)
        pe = struct.unpack_from('<I', cls.moved, 60)[0]
        count = struct.unpack_from('<H', cls.moved, pe+6)[0]
        at = pe+24+struct.unpack_from('<H', cls.moved, pe+20)[0]+40*(count-1)
        cls.name, cls.size, cls.rva, cls.raw_size = struct.unpack_from('<8sIII', cls.moved, at)

    def test_new_section_is_wide_and_has_no_file_bytes(self):
        self.assertEqual(self.name, b'.models\0')
        self.assertEqual(self.size, 32768*0x1D0)
        self.assertEqual(self.raw_size, 0)
        self.assertEqual(len(self.moved), len(self.original))

    def test_only_the_listed_sites_change(self):
        self.assertEqual(len(table.REFERENCES), 63)
        expected = {self.offset(self.original, at)+i for at in table.CAP_SITES for i in range(1, 3)}
        expected |= {self.offset(self.original, at)+i for at, _ in table.REFERENCES for i in range(4)}
        pe = struct.unpack_from('<I', self.moved, 60)[0]
        count = struct.unpack_from('<H', self.moved, pe+6)[0]
        header = pe+24+struct.unpack_from('<H', self.moved, pe+20)[0]+40*count
        changed = {i for i, (a, b) in enumerate(zip(self.original, self.moved)) if a != b and i >= header}
        self.assertLessEqual(changed, expected)

    def test_refuses_a_moved_or_unknown_client(self):
        with self.assertRaises(ValueError):
            table.widen(self.moved)
        broken = bytearray(self.original)
        broken[self.offset(self.original, table.REFERENCES[0][0])] ^= 1
        with self.assertRaises(ValueError):
            table.widen(bytes(broken))

    def test_the_cap_reader_pattern_sees_the_new_ceiling(self):
        caps = [struct.unpack('<I', m[1])[0] for m in re.finditer(rb'\x85\xc0\x7c.\x3d(....)\x7d.\x69\xc0\xd0\x01\x00\x00', self.moved, re.S)]
        self.assertEqual(caps, [32768])

    def test_getter_returns_the_new_array(self):
        try:
            from unicorn import UC_ARCH_X86, UC_MODE_32, Uc
            from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP
        except ImportError:
            self.skipTest('unicorn is not installed')
        code = self.moved[self.offset(self.moved, GETTER):self.offset(self.moved, GETTER)+0x20]
        for model, expected in ((10000, slots.BASE+self.rva+10000*0x1D0), (2500, slots.BASE+self.rva+2500*0x1D0)):
            emu = Uc(UC_ARCH_X86, UC_MODE_32)
            emu.mem_map(0x433000, 0x2000)
            emu.mem_write(GETTER, code)
            emu.mem_map(0x100000, 0x2000)
            emu.mem_write(0x100800, struct.pack('<I', 0xDEAD000))
            emu.reg_write(UC_X86_REG_ESP, 0x100800)
            emu.reg_write(UC_X86_REG_EAX, model)
            emu.emu_start(GETTER, 0xDEAD000)
            self.assertEqual(emu.reg_read(UC_X86_REG_EAX), expected)


if __name__ == '__main__':
    unittest.main()
