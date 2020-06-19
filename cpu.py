import sys
from datetime import datetime

HLT = 0b00000001    # Exit emulator
LDI = 0b10000010    # Set value of register
PRN = 0b01000111    # Print value at register
MUL = 0b10100010    # Multiply values of two registers
PUSH = 0b01000101   # Push value in given register on stack
POP = 0b01000110    # Pop value at top of stack into given register
CALL = 0b01010000   # Call subroutine at address stored in register
RET = 0b00010001    # Return from subroutine by popping PC from stack
ADD = 0b10100000    # Add the value of two registers and store in register A
CMP = 0b10100111    # Compare the values of two registers and set the flag
JMP = 0b01010100    # Set the PC (jump) to the address in the given register
JEQ = 0b01010101    # If the equal flag is true, jump to address in register
JNE = 0b01010110    # If the equal flag is false, jump to address in register
ST = 0b10000100     # Store value in register B in address of register A
PRA = 0b01001000    # Print ASCII character corresponding to vaue in register
IRET = 0b00010011   # Return from an interrupt handler

class CPU:
    """Main CPU class."""

    def __init__(self):
        """Construct a new CPU."""
        # holds 256 bytes of memory
        self.ram = [0] * 256
        # 8 general-purpose registers + stack pointer
        self.reg = [0] * 7 + [0xF4]
        # program counter, special-purpose register
        self.pc = 0

        self.running = False

        self.fl = 0b00000000

        self.allow_interrupt = True

    def handle_hlt(self, a, b):
        self.running = False

    def handle_ldi(self, a, b):
        self.reg[a] = b

    def handle_prn(self, a, b):
        print(self.reg[a])

    def handle_mul(self, a, b):
        self.alu('MUL', a, b)

    def handle_push(self, a, b):
        self.reg[7] -= 1
        self.ram_write(self.reg[7], self.reg[a])
    
    def handle_pop(self, a, b):
        self.reg[a] = self.ram_read(self.reg[7])
        self.reg[7] += 1
    
    def handle_call(self, a, b):
        self.reg[7] -= 1
        self.ram_write(self.reg[7], self.pc + 2)
        self.pc = self.reg[a]
    
    def handle_ret(self, a, b):
        self.pc = self.ram_read(self.reg[7])
        self.reg[7] += 1
    
    def handle_add(self, a, b):
        self.alu('ADD', a, b)
    
    def handle_cmp(self, a, b):
        self.alu('CMP', a, b)
    
    def handle_jmp(self, a, b):
        self.pc = self.reg[a]
    
    def handle_jeq(self, a, b):
        if self.fl & 0b00000001:
            self.pc = self.reg[a]
        else:
            self.pc += 2

    def handle_jne(self, a, b):
        if (self.fl & 0b00000001) == 0:
            self.pc = self.reg[a]
        else:
            self.pc += 2
    
    def handle_st(self, a, b):
        self.ram_write(self.reg[a], self.reg[b])

    def handle_pra(self, a, b):
        print(chr(self.reg[a]))
    
    def handle_iret(self, a, b):
        # Pop registers, fl, pc off stack
        for i in range(7):
            self.reg[6 - i] = self.ram_read(self.reg[7])
            self.reg[7] += 1
        
        self.fl = self.ram_read(self.reg[7])
        self.reg[7] += 1

        self.pc = self.ram_read(self.reg[7])
        self.reg[7] += 1

        # Re-enable interrupts
        self.allow_interrupt = True

    def ext_interrupt(self):
        self.allow_interrupt = False
        # Clear bit in IS register
        self.reg[6] = 0
        # Push pc, fl, registers onto stack
        self.reg[7] -= 1
        self.ram_write(self.reg[7], self.pc)

        self.reg[7] -= 1
        self.ram_write(self.reg[7], self.fl)

        for i in range(7):
            self.reg[7] -= 1
            self.ram_write(self.reg[7], self.reg[i])
            
        # Set pc to handler address
        self.pc = self.ram_read(0xF8) 
        # Interrupt handler in interrupt vector table at address 0xF8

    def exec(self, instruction, a=None, b=None):
        # set up branch table
        dispatch = {
            HLT: self.handle_hlt,
            LDI: self.handle_ldi,
            PRN: self.handle_prn,
            MUL: self.handle_mul,
            PUSH: self.handle_push,
            POP: self.handle_pop,
            CALL: self.handle_call,
            RET: self.handle_ret,
            ADD: self.handle_add,
            CMP: self.handle_cmp,
            JMP: self.handle_jmp,
            JEQ: self.handle_jeq,
            JNE: self.handle_jne,
            ST: self.handle_st,
            PRA: self.handle_pra,
            IRET: self.handle_iret
        }
        
        dispatch[instruction](a, b)

    def load(self, file_path: str):
        """Load a program into memory."""
        address = 0

        with open(file_path) as file:
            for line in file:
                if line == '\n' or line[0] == '#':
                    continue
                else:
                    self.ram[address] = int(line.split()[0], 2)

                address += 1

    def alu(self, op, reg_a, reg_b):
        """ALU operations."""
        # arithmetic logic unit

        if op == "ADD":
            self.reg[reg_a] += self.reg[reg_b]
        #elif op == "SUB": etc
        elif op == "MUL":
            self.reg[reg_a] *= self.reg[reg_b]
        elif op == "CMP":
            if self.reg[reg_a] < self.reg[reg_b]:
                self.fl = 0b00000100

            if self.reg[reg_a] > self.reg[reg_b]:
                self.fl = 0b00000010

            if self.reg[reg_a] == self.reg[reg_b]:
                self.fl = 0b00000001
        else:
            raise Exception("Unsupported ALU operation")

    def trace(self):
        """
        Handy function to print out the CPU state. You might want to call this
        from run() if you need help debugging.
        """

        print(f"TRACE: %02X | %02X %02X %02X |" % (
            self.pc,
            self.fl,
            #self.ie,
            self.ram_read(self.pc),
            self.ram_read(self.pc + 1),
            self.ram_read(self.pc + 2)
        ), end='')

        for i in range(8):
            print(" %02X" % self.reg[i], end='')

        print()

    def run(self):
        """Run the CPU."""
        self.running = True
        start_time = datetime.now()

        while self.running:
            # read the memory address stored in register PC
            # then store in ir, the instruction register
            ir = self.ram_read(self.pc)

            # read bytes at PC+1 and PC+2 in case instruction needs them
            operand_a = self.ram_read(self.pc + 1)
            operand_b = self.ram_read(self.pc + 2)

            if self.allow_interrupt:
                current_time = datetime.now()
                elapsed = current_time - start_time

                if elapsed.total_seconds() >= 1:
                    self.reg[6] = self.reg[6] | 0b00000001 # set timer bit to true
                    start_time = datetime.now()
                    
                # interrupt mask and interrupt status
                masked_interrupts = self.reg[5] & self.reg[6] 

                for i in range(8):
                    # right shift interrupts down by i, 
                    # then mask with 1 to see if that bit was set
                    interrupt_happened = ((masked_interrupts >> i) & 1) == 1

                    if interrupt_happened:
                        self.ext_interrupt()

                        ir = self.ram_read(self.pc)

                        operand_a = self.ram_read(self.pc + 1)
                        operand_b = self.ram_read(self.pc + 2)

            try:
                self.exec(ir, operand_a, operand_b)

                if ((ir & 0b00010000) >> 4) == 0:
                    n_operands = (ir & 0b11000000) >> 6
                    n_move_pc = n_operands + 1
                    self.pc += n_move_pc
            except:
                print(f'Unknown instruction {bin(ir)} at address {self.pc}')
                sys.exit(1)

    def ram_read(self, address: int):
        """Return the value stored at the address."""
        return self.ram[address]
    
    def ram_write(self, address: int, data):
        self.ram[address] = data