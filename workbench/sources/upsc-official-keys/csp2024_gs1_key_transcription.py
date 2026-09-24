# UPSC CSP-2024 GS Paper I official key (dated 21-05-2025 scan), 4 series. X = dropped.
A=("D A D A C B A B A B A A D C D " "B D B C X C A D A A A D A C A " "B D A B D A D C D C D C D D B "
   "C B C D A A X D B B A X B A C " "D A C C B D A C D A D A B D C " "D D C A C C D C B C D B A C D " "A D A B C C D D B B")
B=("D C D D B C B C D A B D A B D " "A D C D C A A D C D B D B C X " "D A D A C B A B A B C A D A A "
   "A D A C A A D A B C C D D B B " "C D C B C D B A C D D A C C B " "D A C D A A X D B B A X B A C " "D A B D C D D C A C")
C=("A D A B C C D D B B C D C B C " "D B A C D D A B D C D D C A C " "D A C C B D A C D A A X D B B "
   "A X B A C D C D D B C B C D A " "B D A B D A D C D C C A D A A " "A D A C A A A D C D B D B C X " "D A D A C B A B A B")
D=("D A B D C D D C A C D A C C B " "D A C D A C D C B C D B A C D " "A X D B B A X B A C A D A B C "
   "C D D B B D A D A C B A B A B " "C A D A A A D A C A A A D C D " "B D B C X D C D D B C B C D A " "B D A B D A D C D C")
KEY={s:dict(enumerate(v.split(),1)) for s,v in zip('ABCD',(A,B,C,D))}
for s in KEY: assert len(KEY[s])==100,(s,len(KEY[s]))
