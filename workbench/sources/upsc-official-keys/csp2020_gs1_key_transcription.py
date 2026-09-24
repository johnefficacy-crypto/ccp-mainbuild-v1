# UPSC CS(P) 2020 GS Paper I official key, transcribed from UPSC scan (4 series). X = dropped.
A=("B B D D B D D D A C B A D A D D D D D C B B A C C A X A A A "
   "C B B D D C D B C D C D D D B A C A A D B X A D B C B B B B "
   "C A D B A B A C D C B A C A A D A A D D A A D A A A A D C A "
   "C D B B C D A B C C")
B=("C D D D B A C A A D C B B D D C D B C D B A D A D D D D D C "
   "B B D D B D D D A C B B A C C A X A A A C D B B C D A B C C "
   "A A D A A A A D C A C A D B A B A C D C B X A D B C B B B B "
   "B A C A A D A A D D")
C=("C D B B C D A B C C A A D A A A A D C A B A C A A D A A D D "
   "C A D B A B A C D C B X A D B C B B B B C D D D B A C A A D "
   "C B B D D C D B C D B B A C C A X A A A B A D A D D D D D C "
   "B B D D B D D D A C")
D=("B A C A A D A A D D C A D B A B A C D C A A D A A A A D C A "
   "B X A D B C B B B B C D B B C D A B C C B B D D B D D D A C "
   "B B A C C A X A A A B A D A D D D D D C C D D D B A C A A D "
   "C B B D D C D B C D")
KEY={s:dict(enumerate(v.split(),1)) for s,v in zip('ABCD',(A,B,C,D))}
for s in KEY: assert len(KEY[s])==100,(s,len(KEY[s]))
