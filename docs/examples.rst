Examples
========

Here are some realistic examples implemented with ``constrainedrandom``.

Load instruction
----------------

The following example makes use of all of ``constrainedrandom``'s features to randomise a fictional load instruction opcode.

..  code-block:: python

    from constrainedrandom import RandObj, Random

    class ldInstr(RandObj):
        '''
        A made-up load instruction has the following fields (starting at LSB):
        - imm0 (11 bits): immediate offset for memory address
        - src0 ( 5 bits): source register for memory address
        - dst0 ( 5 bits): destination register for load data
        - wb   ( 1 bit ): enable for writeback of the address to the src0 register.
        - enc  (10 bits): fixed encoding to signify this kind of load instruction.

        And the following rules:
        - If writeback (wb) is set, src0 is written back with memory offset. In
        this case, do not allow dst0 to be the same register as src0.
        - The sum of the current contents of src0 and imm0 should be word-aligned.
        - The sum of the current contents of src0 and imm0 should not overflow 32
        bits.
        '''
        ENC = 0xfa800000

        def __init__(self, random, *args, **kwargs):
            super().__init__(random, *args, **kwargs)

            self.add_rand_var('src0', bits=5, order=0)
            def read_model_for_src0_value():
                # Pretend getter for src0 current value
                return 0xfffffbcd
            self.add_rand_var('src0_value', fn=read_model_for_src0_value, order=0)
            self.add_rand_var('wb', bits=1, order=0)
            self.add_rand_var('dst0', bits=5, order=1)
            self.add_rand_var('imm0', bits=11, order=2)
            def wb_dst_src(wb, dst0, src0):
                if wb:
                    return dst0 != src0
                return True
            self.add_multi_var_constraint(wb_dst_src, ('wb', 'dst0', 'src0'))
            def sum_src0_imm0(src0_value, imm0):
                address = src0_value + imm0
                return (address & 3 == 0) and (address < 0xffffffff)
            self.add_multi_var_constraint(sum_src0_imm0, ('src0_value', 'imm0'))

        def post_randomize(self):
            self.opcode = self.get_opcode()

        def get_opcode(self):
            opcode = self.ENC
            opcode = opcode | self.imm0
            opcode = opcode | (self.src0 << 11)
            opcode = opcode | (self.dst0 << 5)
            opcode = opcode | (self.wb << 5)
            return opcode


    if __name__ == "__main__":
        # Use a seed of 0 so our results are repeatable
        random = Random(0)
        ld_instr = ldInstr(random)
        # Produce 5 random valid opcodes for this load instruction
        for _ in range(5):
            ld_instr.randomize()
            print(hex(ld_instr.opcode))

The user is free to either inherit from ``RandObj`` (for more complex cases like this one above), or just to instance it directly and use it (for more straightforward cases like those in :doc:`howto` and in the ``tests/`` directory).

In local testing, the instruction above can be randomized at a rate of approximately 2000Hz, which is 'fast enough' for most pre-silicon verification simulations.