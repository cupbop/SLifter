from sir.operand import Operand

class UnsupportedOperatorException(Exception):
    pass

class InvalidTypeException(Exception):
    pass

class Instruction:
    def __init__(self, id, opcodes, operands):
        self.id = id
        self.opcodes = opcodes
        self.operands = operands
        self.TwinIdx = ""
        self.TrueBranch = None
        self.FalseBranch = None
        
    def GetArgsAndRegs(self):
        regs = []
        args = []
        for operand in self.operands:
            if operand.IsReg:
                regs.append(operand)
            if operand.IsArg:
                args.append(operand)

        return args, regs

    def IsExit(self):
        return self.opcodes[0] == "EXIT"

    def IsBranch(self):
        return self.opcodes[0] == "ISETP"

    def IsBinary(self):
        return self.opcodes[0] == "FFMA" or self.opcodes[0] == "FADD" or self.opcodes[0] == "XMAD" or self.opcodes[0] == "SHL" or self.opcodes[0] == "SHR" or self.opcodes[0] == "S2R"
    
    def IsNOP(self):
        return self.opcodes[0] == "NOP"

    def IsAddrCompute(self):
        if self.opcodes[0] == "IADD":
            # Check operands
            if len(self.operands) == 3:
                operand = self.operands[2]
                # Check function argument operand
                return operand.IsArg

        return False

    def IsLoad(self):
        return self.opcodes[0] == "LDG"

    def IsStore(self):
        return self.opcodes[0] == "STG"

    # Set all operands as skipped
    def SetSkip(self):
        for Operand in self.operands:
            Operand.Skipped = True
            
    def ResolveType(self):
        if not self.DirectlySolveType():
            if not self.PartialSolveType():
                raise UnsupportedOperatorException

    # Collect registers used in instructions
    def GetRegs(self, Regs, lifter):
        # Check twin instruction case
        TwinIdx = self.TwinIdx
        
        for Operand in self.operands:
            if Operand.IsReg:
                if TwinIdx.find(Operand.Reg) == 0:
                    if not Operand.TypeDesc == "NOTYPE":
                        RegName = TwinIdx + Operand.TypeDesc
                        Regs[RegName] = Operand
                else:
                    if not Operand.TypeDesc == "NOTYPE":
                        Regs[Operand.GetIRRegName(lifter)] = Operand
        
    # Get def operand
    def GetDef(self):
        return self.operands[0]

    # Get use operand
    def GetUses(self):
        Uses = []
        for i in range(1, len(self.operands)):
            Uses.append(self.operands[i])

        return Uses

    # Check and update the use operand's type from the givenn operand
    def CheckAndUpdateUseType(self, Def):
        for i in range(1, len(self.operands)):
            CurrOperand = self.operands[i]
            if CurrOperand.Name == Def.Name:
                CurrOperand.SetTypeDesc(Def.TypeDesc)
                return True

        return False
    
    # Check and update the def operand's type from the given operands
    def CheckAndUpdateDefType(self, Uses):
        Def = self.operands[0]
        for i in range(len(Uses)):
            CurrUse = Uses[i]
            if CurrUse.IsReg and Def.IsReg and CurrUse.Reg == Def.Reg: # CurrUse.Name == Def.Name:
                Def.SetTypeDesc(CurrUse.TypeDesc)
                return True

        return False
    
    # Directly resolve the type description, this is mainly working for binary operation
    def DirectlySolveType(self):
        TypeDesc = None
        if self.opcodes[0] == "FFMA":
            TypeDesc = "Float32"
        elif self.opcodes[0] == "FADD":
            TypeDesc = "Float32"
        elif self.opcodes[0] == "XMAD":
            TypeDesc = "INT"
        elif self.opcodes[0] == "SHL":
            TypeDesc = "INT"
        elif self.opcodes[0] == "SHR":
            TypeDesc = "INT"
        elif self.opcodes[0] == "S2R":
            TypeDesc = "INT"
        elif self.opcodes[0] == "ISETP":
            TypeDesc = "INT"
        else:
            return False
        
        for operand in self.operands:
            operand.SetTypeDesc(TypeDesc)

        return True
    
    def PartialSolveType(self):
        if self.opcodes[0] == "LDG":
            TypeDesc = self.operands[0].GetTypeDesc()
            if TypeDesc != None:
                self.operands[1].SetTypeDesc(TypeDesc + "_PTR")
            else:
                TypeDesc = self.operands[1].GetTypeDesc()
                if TypeDesc != None:
                    self.operands[0].SetTypeDesc(TypeDesc.replace('_PTR', ""))
                else:
                    raise InvalidTypeException
        elif self.opcodes[0] == "STG":
            TypeDesc = self.operands[1].GetTypeDesc()
            if TypeDesc != None:
                self.operands[0].SetTypeDesc(TypeDesc + "_PTR")
            else:
                TypeDesc = self.operands[0].GetTypeDesc()
                if TypeDesc != None:
                    self.operands[0].SetTypeDesc(TypeDesc.replace('_PTR', ""))
                else:
                    raise InvalidTypeException
        elif self.opcodes[0] == 'IADD':
            TypeDesc = self.operands[0].GetTypeDesc()
            if TypeDesc != None:
                self.operands[1].SetTypeDesc("Int32") # The integer offset
                self.operands[2].SetTypeDesc(TypeDesc)
        else:
            return False

        return True

    def Lift(self, lifter, IRBuilder, IRRegs, IRArgs):
        if self.opcodes[0] == "EXIT":
            IRBuilder.ret_void()
        elif self.opcodes[0] == "FADD":
            Res = self.operands[0]
            Op1 = self.operands[1]
            Op2 = self.operands[2]
            if Res.IsReg and Op1.IsReg and Op2.IsReg:
                IRRes = IRRegs[Res.GetIRRegName(lifter)]
                IROp1 = IRRegs[Op1.GetIRRegName(lifter)]
                IROp2 = IRRegs[Op2.GetIRRegName(lifter)]
            
                # Load operands
                Load1 = IRBuilder.load(IROp1, "load")
                Load2 = IRBuilder.load(IROp2, "load")

                # FADD instruction
                IRVal = IRBuilder.add(Load1, Load2, "fadd")

                # Store result
                IRBuilder.store(IRVal, IRRes)
                
        elif self.opcodes[0] == "SHL":
            ResOp = self.operands[0]
            Op1 = self.operands[1]

            if ResOp.IsReg and Op1.IsReg:
                IRRes = IRRegs[ResOp.GetIRRegName(lifter)]
                IROp1 = IRRegs[Op1.GetIRRegName(lifter)]

                # Load value
                Load1 = IRBuilder.load(IROp1, "loadval")

                # Add 0
                IRVal = IRBuilder.add(Load1, lifter.ir.Constant(lifter.ir.IntType(32), 0), "add")

                # Store result
                IRBuilder.store(IRVal, IRRes)
                
        elif self.opcodes[0] == "IADD":
            ResOp = self.operands[0]
            Op1 = self.operands[1]
            Op2 = self.operands[2]

            if Op1.IsReg and Op2.IsArg:
                IRRes = IRRegs[ResOp.GetIRRegName(lifter)];
                IROp1 = IRRegs[Op1.GetIRRegName(lifter)]
                IROp2 = IRArgs[Op2.ArgOffset]

                # Load values
                Indices = []
                Load1 = IRBuilder.load(IROp1, "offset")
                Indices.append(Load1)
                Load2 = IRBuilder.load(IROp2, "ptr")
                
                # Add operands
                IRVal = IRBuilder.gep(Load2, Indices, "addr")

                # Store the value
                IRBuilder.store(IRVal, IRRes)
                
        elif self.opcodes[0] == "S2R":
            ResOp = self.operands[0]
            ValOp = self.operands[1]
            if ValOp.IsThreadIdx and ResOp.IsReg:
                IRResOp = IRRegs[ResOp.GetIRRegName(lifter)]
                
                # Call thread idx operation
                IRVal = IRBuilder.call(lifter.GetThreadIdx, [], "ThreadIdx")

                # Store the result
                IRBuilder.store(IRVal, IRResOp)
                
        elif self.opcodes[0] == "LDG":
            PtrOp = self.operands[1]
            ValOp = self.operands[0]
            if PtrOp.IsReg and ValOp.IsReg:
                IRPtrOp = IRRegs[PtrOp.GetIRRegName(lifter)]
                IRValOp = IRRegs[ValOp.GetIRRegName(lifter)]

                # Load operands
                LoadPtr = IRBuilder.load(IRPtrOp, "loadptr")

                # Load instruction
                IRRes = IRBuilder.load(LoadPtr, "load_inst")

                # Store the result
                IRBuilder.store(IRRes, IRValOp)
        elif self.opcodes[0] == "STG":
            PtrOp = self.operands[0]
            ValOp = self.operands[1]
            if PtrOp.IsReg and ValOp.IsReg:
                IRPtrOp = IRRegs[PtrOp.GetIRRegName(lifter)]
                IRValOp = IRRegs[ValOp.GetIRRegName(lifter)]

                # Load operands
                Addr = IRBuilder.load(IRPtrOp, "loadptr")
                Val = IRBuilder.load(IRValOp, "loadval")

                # Store instruction
                IRBuilder.store(Val, Addr)

    # Lift branch instruction
    def LiftBranch(self, lifter, IRBuilder, IRRegs, IRArgs, TrueBr, FalseBr):
        if self.opcodes[0] == "ISETP":
            Val1Op = self.operands[2]
            Val2Op = self.operands[3]

            # Check register or arguments
            IRVal1 = None
            IRVal2 = None
            if Val1Op.IsReg:
                IRVal1 = IRRegs[Val1Op.GetIRRegName(lifter)]
            elif Val1Op.IsArg:
                IRVal1 = IRArgs[Val1Op.ArgOffset]

            if Val2Op.IsReg:
                IRVal2 = IRRegs[Val2Op.GEtIRRegName(lifter)]
            elif Val2Op.IsArg:
                IRVal2 = IRArgs[Val2Op.ArgOffset]

            if not IRVal1 == None and not IRVal2 == None:
                Val1 = IRBuilder.load(IRVal1, "val1")
                Val2 = IRBuilder.load(IRVal2, "val2")

                # Calculate condition
                Cmp = IRBuilder.icmp_signed(lifter.GetCmpOp(self.opcodes[1]), Val1, Val2, "cmp")
                
                # Branch instruction
                IRBuilder.cbranch(Cmp, TrueBr, FalseBr)
            
    def dump(self):
        print("inst: ", self.id, self.opcodes)
        for operand in self.operands:
            operand.dump()
        
