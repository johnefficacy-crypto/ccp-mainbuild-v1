# QRE-GIR-A — general-intelligence-reasoning — SME review sheet (360 Q)

Levels {'L1': 26, 'L2': 96, 'L3': 118, 'L4': 120} · key positions {'A': 90, 'B': 90, 'C': 90, 'D': 90} · microtopics covered 24/24
Status `ai_drafted` / `draft`. ⚠ = verify_fact (statute / rate / threshold — check against current official text).


---

## GRA-001 · L1 · easy · Linear row — single row, one direction · foundation

Five persons – D, E, F, G and H – sit in a straight row, all facing north.

- E sits second to the left of D.
- Only two persons sit between F and G, and F is to the right of G.
- As many persons sit to the right of F as to the left of E.

Who sits third from the left end?

- **A.** D ✅
- **B.** H  _(error: off by one position)_
- **C.** G  _(error: off by one position)_
- **D.** E  _(error: not at that position)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only two persons sit between F and G, and F is to the right of G.' and 'E sits second to the left of D.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – E; 2nd from the left end – G; 3rd from the left end – D; 4th from the left end – H; 5th from the left end – F.
4. 3rd from the left end is occupied by D.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Check which end the count starts from.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-002 · L1 · easy · Linear row — single row, one direction · foundation

Five persons – L, M, N, P and Q – sit in a straight row, all facing north.

- N sits third to the left of M.
- N does not sit at either extreme end.
- P sits third to the left of L.

Who sits second to the left of M?

- **A.** Q ✅
- **B.** P  _(error: not at the required position)_
- **C.** N  _(error: counted one place too far)_
- **D.** L  _(error: counted one place short)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'N sits third to the left of M.' and 'P sits third to the left of L.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – P; 2nd from the left end – N; 3rd from the left end – Q; 4th from the left end – L; 5th from the left end – M.
4. M is at 5th from the left end; the person asked for is at 3rd from the left end, i.e. Q.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-003 · L2 · medium · Linear row — single row, one direction · foundation

Six persons – J, K, L, M, N and P – sit in a straight row, all facing north.

- Only one person sits between J and K, and J is to the right of K.
- L does not sit adjacent to M.
- K sits third to the left of P.
- Only three persons sit between J and L, and J is to the right of L.

Who sits second to the left of M?

- **A.** K  _(error: counted one place short)_
- **B.** N ✅
- **C.** L  _(error: counted one place too far)_
- **D.** P  _(error: direction reversed (to the right of instead of to the left of))_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only three persons sit between J and L, and J is to the right of L.' and 'K sits third to the left of P.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – L; 2nd from the left end – N; 3rd from the left end – K; 4th from the left end – M; 5th from the left end – J; 6th from the left end – P.
4. M is at 4th from the left end; the person asked for is at 2nd from the left end, i.e. N.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-004 · L2 · medium · Linear row — single row, one direction · foundation

Six persons – A, B, C, D, E and F – sit in a straight row, all facing north.

- As many persons sit to the right of A as to the left of C.
- D sits third to the left of E.
- E sits second to the left of F.
- A sits somewhere to the right of E.

How many persons sit between A and B?

- **A.** Three  _(error: counted both named persons)_
- **B.** Two  _(error: counted one of the two named persons)_
- **C.** One ✅
- **D.** Four  _(error: counted from the wrong end)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'D sits third to the left of E.' and 'E sits second to the left of F.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – D; 2nd from the left end – C; 3rd from the left end – B; 4th from the left end – E; 5th from the left end – A; 6th from the left end – F.
4. A is at 5th from the left end and B at 3rd from the left end; 1 position(s) lie strictly between them.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Between' excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-005 · L2 · medium · Linear row — single row, one direction · foundation

Six persons – J, K, L, M, N and P – sit in a straight row, all facing north.

- P sits immediately to the right of N.
- L sits second to the left of K.
- M sits immediately to the right of K.
- M sits immediately to the left of N.

What is the position of K from the left end of the row?

- **A.** 5th from the left end  _(error: off by two positions)_
- **B.** 4th from the left end  _(error: counted from the opposite end)_
- **C.** 2nd from the left end  _(error: off by one position)_
- **D.** 3rd from the left end ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L sits second to the left of K.' and 'M sits immediately to the left of N.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – L; 2nd from the left end – J; 3rd from the left end – K; 4th from the left end – M; 5th from the left end – N; 6th from the left end – P.
4. K is at 3rd from the left end.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-006 · L3 · hard · Linear row — single row, one direction · officer

Seven persons – D, E, F, G, H, J and K – sit in a straight row, all facing north.

- H sits fourth to the right of D.
- E sits adjacent to G.
- K sits immediately to the right of H.
- J sits third to the right of E.

Which of the following statements is true?

- **A.** Only two persons sit between F and J.  _(error: false in the solved arrangement)_
- **B.** H sits immediately to the right of K.  _(error: false in the solved arrangement)_
- **C.** G sits somewhere to the right of K.  _(error: false in the solved arrangement)_
- **D.** H sits somewhere to the right of G. ✅

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'H sits fourth to the right of D.' and 'J sits third to the right of E.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – D; 2nd from the left end – F; 3rd from the left end – G; 4th from the left end – E; 5th from the left end – H; 6th from the left end – K; 7th from the left end – J.
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-007 · L3 · hard · Linear row — single row, one direction · officer

Six persons – K, L, M, N, P and Q – sit in a straight row, all facing north. Each of them is from a different city among Bhopal, Chennai, Delhi, Indore, Jaipur and Patna.

- Only three persons sit between P and the one from Bhopal, and P is to the right of the one from Bhopal.
- Q sits fourth to the left of N.
- Q sits third to the left of K.
- Only two persons sit between the one from Patna and Q.
- As many persons sit to the right of the one from Indore as to the left of the one from Delhi.
- The one from Indore sits immediately to the left of L.
- Only one person sits between the one from Chennai and Q, and the one from Chennai is to the right of Q.

Who sits immediately to the right of the one from Indore?

- **A.** M  _(error: counted one place too far)_
- **B.** N  _(error: not at the required position)_
- **C.** L ✅
- **D.** K  _(error: not at the required position)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 city assignments leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Q sits fourth to the left of N.' and 'Q sits third to the left of K.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – Q (Indore); 2nd from the left end – L (Bhopal); 3rd from the left end – M (Chennai); 4th from the left end – K (Patna); 5th from the left end – N (Jaipur); 6th from the left end – P (Delhi).
4. The one from Indore is at 1st from the left end; the person asked for is at 2nd from the left end, i.e. L.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-008 · L4 · hard · Linear row — single row, one direction · officer

Eight persons – K, L, M, N, P, Q, R and S – sit in a straight row, all facing north. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- M sits third to the left of K.
- Only two persons sit between L and N, and L is to the right of N.
- M sits fourth to the left of the one who likes Apple.
- R does not sit adjacent to S.
- Only five persons sit between R and P, and R is to the right of P.
- The one who likes Papaya sits second to the left of M.
- As many persons sit to the right of M as to the left of K.
- The one who likes Mango sits fourth to the right of N.
- The one who likes Orange sits fourth to the right of the one who likes Guava.
- Only one person sits between the one who likes Guava and P, and the one who likes Guava is to the right of P.
- K sits fourth to the right of the one who likes Cherry.
- Only one person sits between R and the one who likes Litchi, and R is to the right of the one who likes Litchi.

Who sits immediately to the left of S?

- **A.** M  _(error: counted one place too far)_
- **B.** N  _(error: not at the required position)_
- **C.** K  _(error: direction reversed (to the right of instead of to the left of))_
- **D.** L ✅

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only five persons sit between R and P, and R is to the right of P.' and 'M sits third to the left of K.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – N (Papaya); 2nd from the left end – P (Cherry); 3rd from the left end – M (Banana); 4th from the left end – L (Guava); 5th from the left end – S (Mango); 6th from the left end – K (Litchi); 7th from the left end – Q (Apple); 8th from the left end – R (Orange).
4. S is at 5th from the left end; the person asked for is at 4th from the left end, i.e. L.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-009 · L4 · hard · Linear row — single row, one direction · officer

Eight persons – K, L, M, N, P, Q, R and S – sit in a straight row, all facing north. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- M sits third to the left of K.
- Only two persons sit between L and N, and L is to the right of N.
- M sits fourth to the left of the one who likes Apple.
- R does not sit adjacent to S.
- Only five persons sit between R and P, and R is to the right of P.
- The one who likes Papaya sits second to the left of M.
- As many persons sit to the right of M as to the left of K.
- The one who likes Mango sits fourth to the right of N.
- The one who likes Orange sits fourth to the right of the one who likes Guava.
- Only one person sits between the one who likes Guava and P, and the one who likes Guava is to the right of P.
- K sits fourth to the right of the one who likes Cherry.
- Only one person sits between R and the one who likes Litchi, and R is to the right of the one who likes Litchi.

Which fruit does N like?

- **A.** Cherry  _(error: attribute of P, a neighbour of N)_
- **B.** Apple  _(error: attribute of Q)_
- **C.** Papaya ✅
- **D.** Orange  _(error: attribute of R)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only five persons sit between R and P, and R is to the right of P.' and 'M sits third to the left of K.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – N (Papaya); 2nd from the left end – P (Cherry); 3rd from the left end – M (Banana); 4th from the left end – L (Guava); 5th from the left end – S (Mango); 6th from the left end – K (Litchi); 7th from the left end – Q (Apple); 8th from the left end – R (Orange).
4. N likes Papaya in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-010 · L4 · hard · Linear row — single row, one direction · officer

Eight persons – K, L, M, N, P, Q, R and S – sit in a straight row, all facing north. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- M sits third to the left of K.
- Only two persons sit between L and N, and L is to the right of N.
- M sits fourth to the left of the one who likes Apple.
- R does not sit adjacent to S.
- Only five persons sit between R and P, and R is to the right of P.
- The one who likes Papaya sits second to the left of M.
- As many persons sit to the right of M as to the left of K.
- The one who likes Mango sits fourth to the right of N.
- The one who likes Orange sits fourth to the right of the one who likes Guava.
- Only one person sits between the one who likes Guava and P, and the one who likes Guava is to the right of P.
- K sits fourth to the right of the one who likes Cherry.
- Only one person sits between R and the one who likes Litchi, and R is to the right of the one who likes Litchi.

How many persons sit between N and R?

- **A.** Eight  _(error: counted both named persons)_
- **B.** Six ✅
- **C.** Five  _(error: counted one short)_
- **D.** Seven  _(error: counted one of the two named persons)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only five persons sit between R and P, and R is to the right of P.' and 'M sits third to the left of K.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – N (Papaya); 2nd from the left end – P (Cherry); 3rd from the left end – M (Banana); 4th from the left end – L (Guava); 5th from the left end – S (Mango); 6th from the left end – K (Litchi); 7th from the left end – Q (Apple); 8th from the left end – R (Orange).
4. N is at 1st from the left end and R at 8th from the left end; 6 position(s) lie strictly between them.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Between' excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-011 · L4 · hard · Linear row — single row, one direction · officer

Eight persons – K, L, M, N, P, Q, R and S – sit in a straight row, all facing north. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- M sits third to the left of K.
- Only two persons sit between L and N, and L is to the right of N.
- M sits fourth to the left of the one who likes Apple.
- R does not sit adjacent to S.
- Only five persons sit between R and P, and R is to the right of P.
- The one who likes Papaya sits second to the left of M.
- As many persons sit to the right of M as to the left of K.
- The one who likes Mango sits fourth to the right of N.
- The one who likes Orange sits fourth to the right of the one who likes Guava.
- Only one person sits between the one who likes Guava and P, and the one who likes Guava is to the right of P.
- K sits fourth to the right of the one who likes Cherry.
- Only one person sits between R and the one who likes Litchi, and R is to the right of the one who likes Litchi.

Which of the following statements is true?

- **A.** Only three persons sit between the one who likes Cherry and N.  _(error: false in the solved arrangement)_
- **B.** The one who likes Papaya does not sit at either extreme end.  _(error: false in the solved arrangement)_
- **C.** The one who likes Litchi does not sit at either extreme end. ✅
- **D.** Only three persons sit between K and the one who likes Orange.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only five persons sit between R and P, and R is to the right of P.' and 'M sits third to the left of K.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – N (Papaya); 2nd from the left end – P (Cherry); 3rd from the left end – M (Banana); 4th from the left end – L (Guava); 5th from the left end – S (Mango); 6th from the left end – K (Litchi); 7th from the left end – Q (Apple); 8th from the left end – R (Orange).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-012 · L4 · hard · Linear row — single row, one direction · officer

Eight persons – K, L, M, N, P, Q, R and S – sit in a straight row, all facing north. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- M sits third to the left of K.
- Only two persons sit between L and N, and L is to the right of N.
- M sits fourth to the left of the one who likes Apple.
- R does not sit adjacent to S.
- Only five persons sit between R and P, and R is to the right of P.
- The one who likes Papaya sits second to the left of M.
- As many persons sit to the right of M as to the left of K.
- The one who likes Mango sits fourth to the right of N.
- The one who likes Orange sits fourth to the right of the one who likes Guava.
- Only one person sits between the one who likes Guava and P, and the one who likes Guava is to the right of P.
- K sits fourth to the right of the one who likes Cherry.
- Only one person sits between R and the one who likes Litchi, and R is to the right of the one who likes Litchi.

Who likes Papaya?

- **A.** L  _(error: no clue links this person to that attribute)_
- **B.** N ✅
- **C.** P  _(error: neighbour of the correct person)_
- **D.** Q  _(error: no clue links this person to that attribute)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only five persons sit between R and P, and R is to the right of P.' and 'M sits third to the left of K.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – N (Papaya); 2nd from the left end – P (Cherry); 3rd from the left end – M (Banana); 4th from the left end – L (Guava); 5th from the left end – S (Mango); 6th from the left end – K (Litchi); 7th from the left end – Q (Apple); 8th from the left end – R (Orange).
4. N likes Papaya.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Attribute clues often name the attribute, not the person; resolve them only after positions are fixed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-013 · L4 · hard · Linear row — single row, one direction · officer

Seven persons – E, F, G, H, J, K and L – sit in a straight row, all facing north. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal and Marketing.

- L sits third to the right of J.
- The one who works in HR sits immediately to the right of J.
- H sits fourth to the right of E.
- Only two persons sit between the one who works in Admin and E, and the one who works in Admin is to the right of E.
- The one who works in Marketing sits second to the right of E.
- As many persons sit to the right of G as to the left of the one who works in Legal.
- E sits second to the right of G.
- Only one person sits between J and K.
- The one who works in IT sits immediately to the right of the one who works in Finance.

Who sits third to the right of the one who works in Audit?

- **A.** G  _(error: direction reversed (to the left of instead of to the right of))_
- **B.** E  _(error: not at the required position)_
- **C.** H ✅
- **D.** F  _(error: counted one place short)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 dept assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'H sits fourth to the right of E.' and 'L sits third to the right of J.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – G (Finance); 2nd from the left end – J (IT); 3rd from the left end – E (HR); 4th from the left end – K (Audit); 5th from the left end – L (Marketing); 6th from the left end – F (Admin); 7th from the left end – H (Legal).
4. The one who works in Audit is at 4th from the left end; the person asked for is at 7th from the left end, i.e. H.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-014 · L4 · hard · Linear row — single row, one direction · officer

Seven persons – E, F, G, H, J, K and L – sit in a straight row, all facing north. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal and Marketing.

- L sits third to the right of J.
- The one who works in HR sits immediately to the right of J.
- H sits fourth to the right of E.
- Only two persons sit between the one who works in Admin and E, and the one who works in Admin is to the right of E.
- The one who works in Marketing sits second to the right of E.
- As many persons sit to the right of G as to the left of the one who works in Legal.
- E sits second to the right of G.
- Only one person sits between J and K.
- The one who works in IT sits immediately to the right of the one who works in Finance.

How many persons sit to the right of F?

- **A.** None  _(error: missed the extreme position)_
- **B.** One ✅
- **C.** Two  _(error: included the person named)_
- **D.** Five  _(error: counted to the left of instead of to the right of)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 dept assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'H sits fourth to the right of E.' and 'L sits third to the right of J.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – G (Finance); 2nd from the left end – J (IT); 3rd from the left end – E (HR); 4th from the left end – K (Audit); 5th from the left end – L (Marketing); 6th from the left end – F (Admin); 7th from the left end – H (Legal).
4. F is at 6th from the left end; 1 position(s) lie beyond it in that direction.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Count only the persons beyond the one named, in the stated direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-015 · L4 · hard · Linear row — single row, one direction · officer

Seven persons – E, F, G, H, J, K and L – sit in a straight row, all facing north. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal and Marketing.

- L sits third to the right of J.
- The one who works in HR sits immediately to the right of J.
- H sits fourth to the right of E.
- Only two persons sit between the one who works in Admin and E, and the one who works in Admin is to the right of E.
- The one who works in Marketing sits second to the right of E.
- As many persons sit to the right of G as to the left of the one who works in Legal.
- E sits second to the right of G.
- Only one person sits between J and K.
- The one who works in IT sits immediately to the right of the one who works in Finance.

Which of the following statements is NOT true?

- **A.** As many persons sit to the right of H as to the left of L. ✅
- **B.** As many persons sit to the right of L as to the left of E.  _(error: this statement is true in the solved arrangement)_
- **C.** G sits fourth to the left of the one who works in Marketing.  _(error: this statement is true in the solved arrangement)_
- **D.** Only two persons sit between the one who works in IT and L.  _(error: this statement is true in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 dept assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'H sits fourth to the right of E.' and 'L sits third to the right of J.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – G (Finance); 2nd from the left end – J (IT); 3rd from the left end – E (HR); 4th from the left end – K (Audit); 5th from the left end – L (Marketing); 6th from the left end – F (Admin); 7th from the left end – H (Legal).
4. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-016 · L1 · easy · Linear row — facing both directions · foundation

Five persons – P, Q, R, S and T – sit in a straight row. Some of them face north and the others face south.

- R sits immediately to the left of S.
- Q and T face the same direction.
- The immediate neighbours of S face opposite directions.
- P sits immediately to the left of R.
- P and R face opposite directions.
- Q faces south.
- T sits second to the right of S.

Who sit at the two extreme ends of the row?

- **A.** R and T  _(error: one person taken from the second position)_
- **B.** R and Q  _(error: second-from-end persons)_
- **C.** P and Q  _(error: one person taken from the second position)_
- **D.** P and T ✅

**Working**

1. Exhaustive enumeration over 120 seat/position orders × 30 facing patterns leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — West to east: P (faces south); R (faces north); S (faces north); Q (faces south); T (faces south).
3. Extreme ends: P and T.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Ends are fixed by the solved order, whatever the facings.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-017 · L2 · medium · Linear row — facing both directions · foundation

Five persons – M, N, P, Q and R – sit in a straight row. Some of them face north and the others face south.

- Both immediate neighbours of R face north.
- N sits third to the right of R.
- P sits second to the left of M.
- The persons at the two extreme ends face the same direction.
- R sits third to the left of N.

Who sits immediately to the right of Q?

- **A.** P  _(error: not at that position)_
- **B.** N  _(error: treated Q as facing north (viewer's right))_
- **C.** R  _(error: counted one place off)_
- **D.** M ✅

**Working**

1. Exhaustive enumeration over 120 seat/position orders × 30 facing patterns leaves exactly one arrangement that satisfies all 5 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — West to east: P (faces north); R (faces north); M (faces north); Q (faces south); N (faces north).
3. Q faces south, so Q's right is towards the west; counting 1 place(s) that way gives M.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Right and left are taken from the reference person's own facing; a south-facing person's right is the viewer's left.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-018 · L2 · medium · Linear row — facing both directions · foundation

Six persons – D, E, F, G, H and J – sit in a straight row. Some of them face north and the others face south.

- F and G face the same direction.
- Exactly two persons face north.
- H sits third to the left of E.
- G sits second to the right of D.
- G sits at one of the extreme ends.
- H sits immediately to the right of F.
- D and H face the same direction.

How many persons face north?

- **A.** Two ✅
- **B.** One  _(error: off by one)_
- **C.** Four  _(error: counted south-facing persons)_
- **D.** Three  _(error: off by one)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 62 facing patterns leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'G sits at one of the extreme ends.'; then place the others by elimination.
3. Solved arrangement — West to east: G (faces north); E (faces south); D (faces south); F (faces north); H (faces south); J (faces south).
4. North-facing: F, G.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Fix every person's facing before counting.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-019 · L2 · medium · Linear row — facing both directions · foundation

Six persons – P, Q, R, S, T and U – sit in a straight row. Some of them face north and the others face south.

- P sits second to the right of U.
- Both immediate neighbours of T face south.
- R sits second to the right of Q.
- S sits immediately to the left of P.
- Q sits third to the right of P.
- Exactly two persons face north.

Who sits immediately to the left of S?

- **A.** U  _(error: treated S as facing north (viewer's left))_
- **B.** R  _(error: counted one place off)_
- **C.** Q  _(error: not at that position)_
- **D.** P ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 62 facing patterns leaves exactly one arrangement that satisfies all 6 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — West to east: U (faces north); S (faces south); P (faces north); R (faces south); T (faces south); Q (faces south).
3. S faces south, so S's left is towards the east; counting 1 place(s) that way gives P.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Right and left are taken from the reference person's own facing; a south-facing person's right is the viewer's left.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-020 · L2 · medium · Linear row — facing both directions · foundation

Six persons – K, L, M, N, P and Q – sit in a straight row. Some of them face north and the others face south.

- Both immediate neighbours of Q face south.
- M sits second to the right of N.
- L faces south.
- M sits immediately to the right of P.
- N sits immediately to the right of Q.
- N sits second to the left of K.

What is the position of N with respect to M?

- **A.** Second to the right  _(error: measured from the viewer's side / reversed)_
- **B.** Second to the left ✅
- **C.** Third to the left  _(error: counted one place extra)_
- **D.** Immediately to the left  _(error: counted one place short)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 62 facing patterns leaves exactly one arrangement that satisfies all 6 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — West to east: P (faces north); M (faces south); Q (faces north); N (faces south); L (faces south); K (faces north).
3. M faces south; from M's own right-left, N is second to the left.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Use the reference person's facing, not the viewer's.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-021 · L3 · hard · Linear row — facing both directions · officer

Seven persons – L, M, N, P, Q, R and S – sit in a straight row. Some of them face north and the others face south.

- M faces south.
- P sits third to the left of Q.
- L sits third to the right of Q.
- S sits immediately to the left of Q.
- N sits third to the right of S.
- N faces south.
- L and P face the same direction.
- The immediate neighbours of Q face opposite directions.
- Both immediate neighbours of M face south.

Who sits immediately to the left of N?

- **A.** L  _(error: treated N as facing north (viewer's left))_
- **B.** R ✅
- **C.** M  _(error: not at that position)_
- **D.** Q  _(error: counted one place off)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 126 facing patterns leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — West to east: L (faces south); N (faces south); R (faces north); Q (faces south); S (faces south); M (faces south); P (faces south).
3. N faces south, so N's left is towards the east; counting 1 place(s) that way gives R.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Right and left are taken from the reference person's own facing; a south-facing person's right is the viewer's left.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-022 · L3 · hard · Linear row — facing both directions · officer

Six persons – E, F, G, H, J and K – sit in a straight row. Some of them face north and the others face south. Each of them plays a different game among Badminton, Chess, Football, Kabaddi, Tennis and Volleyball.

- The one who plays Kabaddi and G face opposite directions.
- J does not play Volleyball.
- J sits third to the right of G.
- G faces north.
- Only one person sits between the one who plays Kabaddi and G.
- H does not play Volleyball.
- H sits immediately to the right of G.
- The one who plays Football sits second to the right of F.
- K sits immediately to the right of the one who plays Tennis.
- H faces north.
- E does not play Football.
- Only three persons sit between the one who plays Badminton and H.
- G does not play Tennis.
- G does not play Badminton.
- H does not play Tennis.
- Exactly three persons face north.

Which of the following statements is true?

- **A.** The one who plays Kabaddi faces north.  _(error: false in the solved arrangement)_
- **B.** Only four persons sit between F and H.  _(error: false in the solved arrangement)_
- **C.** The one who plays Chess faces north. ✅
- **D.** The one who plays Football faces south.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 62 facing patterns × 720 sport assignments leaves exactly one arrangement that satisfies all 16 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — West to east: G (faces north, Football); H (faces north, Chess); F (faces south, Kabaddi); J (faces north, Tennis); K (faces south, Volleyball); E (faces south, Badminton).
3. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-023 · L4 · hard · Linear row — facing both directions · officer

Eight persons – K, L, M, N, P, Q, R and S – sit in a straight row. Some of them face north and the others face south.

- N and P face opposite directions.
- L sits second to the right of M.
- Only one person sits between K and R.
- P and Q face the same direction.
- Only one person sits between M and R.
- N and R face opposite directions.
- L faces north.
- K sits immediately to the right of P.
- N sits third to the left of L.
- S sits third to the right of M.
- The persons at the two extreme ends face the same direction.
- S faces north.

Who sits immediately to the left of Q?

- **A.** L ✅
- **B.** M  _(error: treated Q as facing north (viewer's left))_
- **C.** K  _(error: not at that position)_
- **D.** S  _(error: counted one place off)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person sits between K and R.' and 'Only one person sits between M and R.'; then place the others by elimination.
3. Solved arrangement — West to east: K (faces north); P (faces south); R (faces south); N (faces north); M (faces north); Q (faces south); L (faces north); S (faces north).
4. Q faces south, so Q's left is towards the east; counting 1 place(s) that way gives L.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Right and left are taken from the reference person's own facing; a south-facing person's right is the viewer's left.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-024 · L4 · hard · Linear row — facing both directions · officer

Eight persons – K, L, M, N, P, Q, R and S – sit in a straight row. Some of them face north and the others face south.

- N and P face opposite directions.
- L sits second to the right of M.
- Only one person sits between K and R.
- P and Q face the same direction.
- Only one person sits between M and R.
- N and R face opposite directions.
- L faces north.
- K sits immediately to the right of P.
- N sits third to the left of L.
- S sits third to the right of M.
- The persons at the two extreme ends face the same direction.
- S faces north.

What is the position of L with respect to R?

- **A.** Third to the left  _(error: counted one place short)_
- **B.** Fourth to the right  _(error: measured from the viewer's side / reversed)_
- **C.** Fourth to the left ✅
- **D.** Fifth to the left  _(error: counted one place extra)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person sits between K and R.' and 'Only one person sits between M and R.'; then place the others by elimination.
3. Solved arrangement — West to east: K (faces north); P (faces south); R (faces south); N (faces north); M (faces north); Q (faces south); L (faces north); S (faces north).
4. R faces south; from R's own right-left, L is fourth to the left.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Use the reference person's facing, not the viewer's.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-025 · L4 · hard · Linear row — facing both directions · officer

Eight persons – K, L, M, N, P, Q, R and S – sit in a straight row. Some of them face north and the others face south.

- N and P face opposite directions.
- L sits second to the right of M.
- Only one person sits between K and R.
- P and Q face the same direction.
- Only one person sits between M and R.
- N and R face opposite directions.
- L faces north.
- K sits immediately to the right of P.
- N sits third to the left of L.
- S sits third to the right of M.
- The persons at the two extreme ends face the same direction.
- S faces north.

How many persons face north?

- **A.** Four  _(error: off by one)_
- **B.** Five ✅
- **C.** Six  _(error: off by one)_
- **D.** Three  _(error: counted south-facing persons)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person sits between K and R.' and 'Only one person sits between M and R.'; then place the others by elimination.
3. Solved arrangement — West to east: K (faces north); P (faces south); R (faces south); N (faces north); M (faces north); Q (faces south); L (faces north); S (faces north).
4. North-facing: K, L, M, N, S.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Fix every person's facing before counting.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-026 · L4 · hard · Linear row — facing both directions · officer

Eight persons – K, L, M, N, P, Q, R and S – sit in a straight row. Some of them face north and the others face south.

- N and P face opposite directions.
- L sits second to the right of M.
- Only one person sits between K and R.
- P and Q face the same direction.
- Only one person sits between M and R.
- N and R face opposite directions.
- L faces north.
- K sits immediately to the right of P.
- N sits third to the left of L.
- S sits third to the right of M.
- The persons at the two extreme ends face the same direction.
- S faces north.

Which of the following statements is true?

- **A.** Q sits at one of the extreme ends.  _(error: false in the solved arrangement)_
- **B.** P and R face the same direction. ✅
- **C.** P and R face opposite directions.  _(error: false in the solved arrangement)_
- **D.** K and P face the same direction.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person sits between K and R.' and 'Only one person sits between M and R.'; then place the others by elimination.
3. Solved arrangement — West to east: K (faces north); P (faces south); R (faces south); N (faces north); M (faces north); Q (faces south); L (faces north); S (faces north).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-027 · L4 · hard · Linear row — facing both directions · officer

Eight persons – K, L, M, N, P, Q, R and S – sit in a straight row. Some of them face north and the others face south.

- N and P face opposite directions.
- L sits second to the right of M.
- Only one person sits between K and R.
- P and Q face the same direction.
- Only one person sits between M and R.
- N and R face opposite directions.
- L faces north.
- K sits immediately to the right of P.
- N sits third to the left of L.
- S sits third to the right of M.
- The persons at the two extreme ends face the same direction.
- S faces north.

How many persons sit between Q and R?

- **A.** One  _(error: counted one short)_
- **B.** Three  _(error: counted one of the two named persons)_
- **C.** Four  _(error: counted both named persons)_
- **D.** Two ✅

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person sits between K and R.' and 'Only one person sits between M and R.'; then place the others by elimination.
3. Solved arrangement — West to east: K (faces north); P (faces south); R (faces south); N (faces north); M (faces north); Q (faces south); L (faces north); S (faces north).
4. 2 person(s) sit strictly between them.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Between' excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-028 · L4 · hard · Linear row — facing both directions · officer

Seven persons – M, N, P, Q, R, S and T – sit in a straight row. Some of them face north and the others face south. Each of them is from a different city among Bhopal, Chennai, Delhi, Indore, Jaipur, Kochi and Patna.

- The one from Indore and T face the same direction.
- Only one person sits between the one from Delhi and R.
- Only two persons sit between S and T.
- P sits second to the left of the one from Kochi.
- The immediate neighbours of the one from Chennai face opposite directions.
- R is not from Kochi.
- M is not from Indore.
- Q and R face opposite directions.
- P sits adjacent to T.
- The one from Jaipur sits immediately to the left of P.
- Q faces south.
- Q sits adjacent to S.
- The one from Chennai and Q face the same direction.
- Q sits third to the right of R.
- N is not from Indore.
- N and P face the same direction.
- M is not from Bhopal.
- S sits second to the right of M.

Who sits third to the left of the one from Jaipur?

- **A.** N  _(error: counted one place off)_
- **B.** M ✅
- **C.** P  _(error: not at that position)_
- **D.** R  _(error: treated Q as facing north (viewer's left))_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 126 facing patterns × 5,040 city assignments leaves exactly one arrangement that satisfies all 18 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only two persons sit between S and T.' and 'P sits adjacent to T.'; then place the others by elimination.
3. Solved arrangement — West to east: R (faces north, Indore); T (faces north, Bhopal); P (faces south, Delhi); Q (faces south, Jaipur); S (faces north, Kochi); N (faces south, Chennai); M (faces south, Patna).
4. Q faces south, so Q's left is towards the east; counting 3 place(s) that way gives M.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Right and left are taken from the reference person's own facing; a south-facing person's right is the viewer's left.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-029 · L4 · hard · Linear row — facing both directions · officer

Seven persons – M, N, P, Q, R, S and T – sit in a straight row. Some of them face north and the others face south. Each of them is from a different city among Bhopal, Chennai, Delhi, Indore, Jaipur, Kochi and Patna.

- The one from Indore and T face the same direction.
- Only one person sits between the one from Delhi and R.
- Only two persons sit between S and T.
- P sits second to the left of the one from Kochi.
- The immediate neighbours of the one from Chennai face opposite directions.
- R is not from Kochi.
- M is not from Indore.
- Q and R face opposite directions.
- P sits adjacent to T.
- The one from Jaipur sits immediately to the left of P.
- Q faces south.
- Q sits adjacent to S.
- The one from Chennai and Q face the same direction.
- Q sits third to the right of R.
- N is not from Indore.
- N and P face the same direction.
- M is not from Bhopal.
- S sits second to the right of M.

Who is from Kochi?

- **A.** N  _(error: neighbour of the correct person)_
- **B.** T  _(error: no clue links this person to that attribute)_
- **C.** S ✅
- **D.** Q  _(error: neighbour of the correct person)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 126 facing patterns × 5,040 city assignments leaves exactly one arrangement that satisfies all 18 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only two persons sit between S and T.' and 'P sits adjacent to T.'; then place the others by elimination.
3. Solved arrangement — West to east: R (faces north, Indore); T (faces north, Bhopal); P (faces south, Delhi); Q (faces south, Jaipur); S (faces north, Kochi); N (faces south, Chennai); M (faces south, Patna).
4. S is from Kochi.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Attribute clues often name the attribute, not the person; resolve them only after positions are fixed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-030 · L4 · hard · Linear row — facing both directions · officer

Seven persons – M, N, P, Q, R, S and T – sit in a straight row. Some of them face north and the others face south. Each of them is from a different city among Bhopal, Chennai, Delhi, Indore, Jaipur, Kochi and Patna.

- The one from Indore and T face the same direction.
- Only one person sits between the one from Delhi and R.
- Only two persons sit between S and T.
- P sits second to the left of the one from Kochi.
- The immediate neighbours of the one from Chennai face opposite directions.
- R is not from Kochi.
- M is not from Indore.
- Q and R face opposite directions.
- P sits adjacent to T.
- The one from Jaipur sits immediately to the left of P.
- Q faces south.
- Q sits adjacent to S.
- The one from Chennai and Q face the same direction.
- Q sits third to the right of R.
- N is not from Indore.
- N and P face the same direction.
- M is not from Bhopal.
- S sits second to the right of M.

Which of the following statements is NOT true?

- **A.** M sits second to the left of R. ✅
- **B.** P and Q face the same direction.  _(error: this statement is true in the solved arrangement)_
- **C.** S sits second to the left of P.  _(error: this statement is true in the solved arrangement)_
- **D.** Exactly three persons face north.  _(error: this statement is true in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 126 facing patterns × 5,040 city assignments leaves exactly one arrangement that satisfies all 18 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only two persons sit between S and T.' and 'P sits adjacent to T.'; then place the others by elimination.
3. Solved arrangement — West to east: R (faces north, Indore); T (faces north, Bhopal); P (faces south, Delhi); Q (faces south, Jaipur); S (faces north, Kochi); N (faces south, Chennai); M (faces south, Patna).
4. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-031 · L1 · easy · Circular arrangement — facing centre · foundation

Five persons – E, F, G, H and J – sit around a circular table, all facing the centre.

- F is not an immediate neighbour of H.
- E sits immediately to the left of H.
- J sits second to the right of H.

Who sits immediately to the right of G?

- **A.** H  _(error: direction reversed)_
- **B.** J ✅
- **C.** F  _(error: counted one seat too far)_
- **D.** E  _(error: not at that seat)_

**Working**

1. Exhaustive enumeration over 24 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'E sits immediately to the left of H.' and 'J sits second to the right of H.'; then place the others by elimination.
3. Solved arrangement — Clockwise from E: E; F; J; G; H.
4. G faces the centre, so G's right runs anticlockwise; 1 seat(s) that way is J.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-032 · L1 · easy · Circular arrangement — facing centre · foundation

Five persons – D, E, F, G and H – sit around a circular table, all facing the centre.

- G sits immediately to the right of H.
- F sits immediately to the right of D.
- H sits second to the right of F.

What is the position of F with respect to G?

- **A.** Second to the right ✅
- **B.** Third to the right  _(error: counted one seat extra)_
- **C.** Second to the left  _(error: direction reversed)_
- **D.** Immediately to the right  _(error: counted one seat short)_

**Working**

1. Exhaustive enumeration over 24 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'F sits immediately to the right of D.' and 'G sits immediately to the right of H.'; then place the others by elimination.
3. Solved arrangement — Clockwise from D: D; G; H; E; F.
4. G faces the centre; counted from G's own right/left, F is second to the right.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Positions are always read from the reference person's facing.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-033 · L2 · medium · Circular arrangement — facing centre · foundation

Six persons – J, K, L, M, N and P – sit around a circular table, all facing the centre.

- L sits immediately to the left of P.
- P sits second to the left of J.
- M sits immediately to the left of L.
- N is an immediate neighbour of P.

Who sits opposite M?

- **A.** N ✅
- **B.** K  _(error: not opposite)_
- **C.** J  _(error: seat next to the opposite seat)_
- **D.** P  _(error: seat next to the opposite seat)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L sits immediately to the left of P.' and 'M sits immediately to the left of L.'; then place the others by elimination.
3. Solved arrangement — Clockwise from J: J; N; P; L; M; K.
4. The seat 3 places away from M in either direction is N's.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Opposite means exactly half-way round the table.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-034 · L2 · medium · Circular arrangement — facing centre · foundation

Six persons – E, F, G, H, J and K – sit around a circular table, all facing the centre.

- H sits second to the right of F.
- G sits immediately to the right of J.
- K sits second to the left of J.

Who sits second to the left of H?

- **A.** G  _(error: direction reversed)_
- **B.** K  _(error: counted one seat short)_
- **C.** F ✅
- **D.** E  _(error: counted one seat too far)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'G sits immediately to the right of J.' and 'H sits second to the right of F.'; then place the others by elimination.
3. Solved arrangement — Clockwise from E: E; G; J; H; K; F.
4. H faces the centre, so H's left runs clockwise; 2 seat(s) that way is F.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-035 · L2 · medium · Circular arrangement — facing centre · foundation

Six persons – E, F, G, H, J and K – sit around a circular table, all facing the centre.

- E is an immediate neighbour of F.
- Only one person sits between H and F when counted from the left of H.
- J sits immediately to the left of E.
- K sits immediately to the left of H.

How many persons sit between F and K when counted from the left of F?

- **A.** None  _(error: counted from the other side)_
- **B.** Four ✅
- **C.** Five  _(error: counted one named person)_
- **D.** Three  _(error: counted one short)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'J sits immediately to the left of E.' and 'K sits immediately to the left of H.'; then place the others by elimination.
3. Solved arrangement — Clockwise from E: E; J; G; H; K; F.
4. Moving to F's left, 4 person(s) are passed before reaching K.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** The count depends on the side; the other side gives n − 2 − m.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-036 · L3 · hard · Circular arrangement — facing centre · officer

Seven persons – D, E, F, G, H, J and K – sit around a circular table, all facing the centre.

- K sits immediately to the right of H.
- H sits second to the left of G.
- D sits third to the right of G.
- F sits immediately to the right of E.

What is the position of E with respect to G?

- **A.** Second to the right  _(error: counted one seat extra)_
- **B.** Immediately to the right ✅
- **C.** Immediately to the left  _(error: direction reversed)_
- **D.** Second to the left  _(error: reversed and off by one)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'D sits third to the right of G.' and 'F sits immediately to the right of E.'; then place the others by elimination.
3. Solved arrangement — Clockwise from D: D; F; E; G; K; H; J.
4. G faces the centre; counted from G's own right/left, E is immediately to the right.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Positions are always read from the reference person's facing.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-037 · L3 · hard · Circular arrangement — facing centre · officer

Six persons – J, K, L, M, N and P – sit around a circular table, all facing the centre. Each of them owns a car of a different colour among black, blue, grey, silver, white and yellow.

- K sits immediately to the left of L.
- The owner of the silver car is an immediate neighbour of N.
- The owner of the black car sits immediately to the left of K.
- N is not an immediate neighbour of the owner of the white car.
- The owner of the black car sits immediately to the right of the owner of the silver car.
- The owner of the grey car sits immediately to the right of the owner of the blue car.
- J sits immediately to the left of P.
- The owner of the blue car sits opposite M.

Who sits second to the right of the owner of the yellow car?

- **A.** J ✅
- **B.** P  _(error: counted one seat too far)_
- **C.** M  _(error: direction reversed)_
- **D.** L  _(error: counted one seat short)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders × 720 car assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'J sits immediately to the left of P.' and 'K sits immediately to the left of L.'; then place the others by elimination.
3. Solved arrangement — Clockwise from J: J (grey); L (blue); K (yellow); N (black); M (silver); P (white).
4. K faces the centre, so K's right runs anticlockwise; 2 seat(s) that way is J.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-038 · L4 · hard · Circular arrangement — facing centre · officer

Eight persons – A, B, C, D, E, F, G and H – sit around a circular table, all facing the centre. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- Only two persons sit between C and B when counted from the right of C.
- E sits immediately to the right of B.
- Only two persons sit between the one who likes Mango and F when counted from the left of the one who likes Mango.
- The one who likes Banana sits third to the left of B.
- A sits third to the left of D.
- Only one person sits between B and D when counted from the right of B.
- B does not like Orange.
- F does not like Apple.
- The one who likes Cherry sits third to the right of H.
- The one who likes Litchi sits second to the right of A.
- The one who likes Apple sits second to the right of E.
- The one who likes Guava sits immediately to the right of the one who likes Litchi.

Who sits second to the right of F?

- **A.** D  _(error: direction reversed)_
- **B.** C  _(error: counted one seat short)_
- **C.** G ✅
- **D.** A  _(error: counted one seat too far)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'A sits third to the left of D.' and 'E sits immediately to the right of B.'; then place the others by elimination.
3. Solved arrangement — Clockwise from A: A (Mango); G (Cherry); C (Banana); F (Orange); H (Apple); D (Guava); E (Litchi); B (Papaya).
4. F faces the centre, so F's right runs anticlockwise; 2 seat(s) that way is G.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-039 · L4 · hard · Circular arrangement — facing centre · officer

Eight persons – A, B, C, D, E, F, G and H – sit around a circular table, all facing the centre. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- Only two persons sit between C and B when counted from the right of C.
- E sits immediately to the right of B.
- Only two persons sit between the one who likes Mango and F when counted from the left of the one who likes Mango.
- The one who likes Banana sits third to the left of B.
- A sits third to the left of D.
- Only one person sits between B and D when counted from the right of B.
- B does not like Orange.
- F does not like Apple.
- The one who likes Cherry sits third to the right of H.
- The one who likes Litchi sits second to the right of A.
- The one who likes Apple sits second to the right of E.
- The one who likes Guava sits immediately to the right of the one who likes Litchi.

Which fruit does D like?

- **A.** Orange  _(error: attribute of F)_
- **B.** Guava ✅
- **C.** Apple  _(error: attribute of H, a neighbour of D)_
- **D.** Litchi  _(error: attribute of E, a neighbour of D)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'A sits third to the left of D.' and 'E sits immediately to the right of B.'; then place the others by elimination.
3. Solved arrangement — Clockwise from A: A (Mango); G (Cherry); C (Banana); F (Orange); H (Apple); D (Guava); E (Litchi); B (Papaya).
4. D likes Guava in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-040 · L4 · hard · Circular arrangement — facing centre · officer

Eight persons – A, B, C, D, E, F, G and H – sit around a circular table, all facing the centre. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- Only two persons sit between C and B when counted from the right of C.
- E sits immediately to the right of B.
- Only two persons sit between the one who likes Mango and F when counted from the left of the one who likes Mango.
- The one who likes Banana sits third to the left of B.
- A sits third to the left of D.
- Only one person sits between B and D when counted from the right of B.
- B does not like Orange.
- F does not like Apple.
- The one who likes Cherry sits third to the right of H.
- The one who likes Litchi sits second to the right of A.
- The one who likes Apple sits second to the right of E.
- The one who likes Guava sits immediately to the right of the one who likes Litchi.

Who sits opposite F?

- **A.** B ✅
- **B.** C  _(error: not opposite)_
- **C.** A  _(error: seat next to the opposite seat)_
- **D.** E  _(error: seat next to the opposite seat)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'A sits third to the left of D.' and 'E sits immediately to the right of B.'; then place the others by elimination.
3. Solved arrangement — Clockwise from A: A (Mango); G (Cherry); C (Banana); F (Orange); H (Apple); D (Guava); E (Litchi); B (Papaya).
4. The seat 4 places away from F in either direction is B's.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Opposite means exactly half-way round the table.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-041 · L4 · hard · Circular arrangement — facing centre · officer

Eight persons – A, B, C, D, E, F, G and H – sit around a circular table, all facing the centre. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- Only two persons sit between C and B when counted from the right of C.
- E sits immediately to the right of B.
- Only two persons sit between the one who likes Mango and F when counted from the left of the one who likes Mango.
- The one who likes Banana sits third to the left of B.
- A sits third to the left of D.
- Only one person sits between B and D when counted from the right of B.
- B does not like Orange.
- F does not like Apple.
- The one who likes Cherry sits third to the right of H.
- The one who likes Litchi sits second to the right of A.
- The one who likes Apple sits second to the right of E.
- The one who likes Guava sits immediately to the right of the one who likes Litchi.

How many persons sit between B and E when counted from the left of B?

- **A.** Seven  _(error: counted one named person)_
- **B.** Six ✅
- **C.** Five  _(error: counted one short)_
- **D.** None  _(error: counted from the other side)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'A sits third to the left of D.' and 'E sits immediately to the right of B.'; then place the others by elimination.
3. Solved arrangement — Clockwise from A: A (Mango); G (Cherry); C (Banana); F (Orange); H (Apple); D (Guava); E (Litchi); B (Papaya).
4. Moving to B's left, 6 person(s) are passed before reaching E.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** The count depends on the side; the other side gives n − 2 − m.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-042 · L4 · hard · Circular arrangement — facing centre · officer

Eight persons – A, B, C, D, E, F, G and H – sit around a circular table, all facing the centre. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- Only two persons sit between C and B when counted from the right of C.
- E sits immediately to the right of B.
- Only two persons sit between the one who likes Mango and F when counted from the left of the one who likes Mango.
- The one who likes Banana sits third to the left of B.
- A sits third to the left of D.
- Only one person sits between B and D when counted from the right of B.
- B does not like Orange.
- F does not like Apple.
- The one who likes Cherry sits third to the right of H.
- The one who likes Litchi sits second to the right of A.
- The one who likes Apple sits second to the right of E.
- The one who likes Guava sits immediately to the right of the one who likes Litchi.

Which of the following statements is true?

- **A.** C is not an immediate neighbour of F.  _(error: false in the solved arrangement)_
- **B.** B sits immediately to the left of E. ✅
- **C.** B sits immediately to the left of H.  _(error: false in the solved arrangement)_
- **D.** E sits immediately to the right of G.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'A sits third to the left of D.' and 'E sits immediately to the right of B.'; then place the others by elimination.
3. Solved arrangement — Clockwise from A: A (Mango); G (Cherry); C (Banana); F (Orange); H (Apple); D (Guava); E (Litchi); B (Papaya).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-043 · L4 · hard · Circular arrangement — facing centre · officer

Seven persons – M, N, P, Q, R, S and T – sit around a circular table, all facing the centre. Each of them teaches a different subject among Chemistry, Civics, Economics, Geography, History, Physics and Zoology.

- The one who teaches Zoology sits third to the left of T.
- Only two persons sit between M and the one who teaches Civics when counted from the left of M.
- The one who teaches Physics sits second to the left of T.
- Q sits immediately to the right of M.
- N is not an immediate neighbour of the one who teaches Economics.
- R sits second to the left of P.
- Only one person sits between R and the one who teaches History when counted from the left of R.
- S sits second to the right of N.
- Only two persons sit between the one who teaches Geography and the one who teaches Civics when counted from the right of the one who teaches Geography.

Who sits immediately to the left of the one who teaches Geography?

- **A.** M ✅
- **B.** T  _(error: direction reversed)_
- **C.** N  _(error: not at that seat)_
- **D.** P  _(error: counted one seat too far)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 5,040 subject assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Q sits immediately to the right of M.' and 'R sits second to the left of P.'; then place the others by elimination.
3. Solved arrangement — Clockwise from M: M (Physics); P (Zoology); S (Economics); R (Civics); N (Chemistry); T (History); Q (Geography).
4. Q faces the centre, so Q's left runs clockwise; 1 seat(s) that way is M.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-044 · L4 · hard · Circular arrangement — facing centre · officer

Seven persons – M, N, P, Q, R, S and T – sit around a circular table, all facing the centre. Each of them teaches a different subject among Chemistry, Civics, Economics, Geography, History, Physics and Zoology.

- The one who teaches Zoology sits third to the left of T.
- Only two persons sit between M and the one who teaches Civics when counted from the left of M.
- The one who teaches Physics sits second to the left of T.
- Q sits immediately to the right of M.
- N is not an immediate neighbour of the one who teaches Economics.
- R sits second to the left of P.
- Only one person sits between R and the one who teaches History when counted from the left of R.
- S sits second to the right of N.
- Only two persons sit between the one who teaches Geography and the one who teaches Civics when counted from the right of the one who teaches Geography.

What is the position of S with respect to N?

- **A.** Third to the left  _(error: reversed and off by one)_
- **B.** Third to the right  _(error: counted one seat extra)_
- **C.** Second to the right ✅
- **D.** Second to the left  _(error: direction reversed)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 5,040 subject assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Q sits immediately to the right of M.' and 'R sits second to the left of P.'; then place the others by elimination.
3. Solved arrangement — Clockwise from M: M (Physics); P (Zoology); S (Economics); R (Civics); N (Chemistry); T (History); Q (Geography).
4. N faces the centre; counted from N's own right/left, S is second to the right.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Positions are always read from the reference person's facing.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-045 · L4 · hard · Circular arrangement — facing centre · officer

Seven persons – M, N, P, Q, R, S and T – sit around a circular table, all facing the centre. Each of them teaches a different subject among Chemistry, Civics, Economics, Geography, History, Physics and Zoology.

- The one who teaches Zoology sits third to the left of T.
- Only two persons sit between M and the one who teaches Civics when counted from the left of M.
- The one who teaches Physics sits second to the left of T.
- Q sits immediately to the right of M.
- N is not an immediate neighbour of the one who teaches Economics.
- R sits second to the left of P.
- Only one person sits between R and the one who teaches History when counted from the left of R.
- S sits second to the right of N.
- Only two persons sit between the one who teaches Geography and the one who teaches Civics when counted from the right of the one who teaches Geography.

Which of the following statements is NOT true?

- **A.** The one who teaches Chemistry sits second to the right of Q.  _(error: this statement is true in the solved arrangement)_
- **B.** The one who teaches Civics sits immediately to the left of S.  _(error: this statement is true in the solved arrangement)_
- **C.** The one who teaches Physics sits third to the left of N.  _(error: this statement is true in the solved arrangement)_
- **D.** The one who teaches Chemistry sits third to the left of S. ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 5,040 subject assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Q sits immediately to the right of M.' and 'R sits second to the left of P.'; then place the others by elimination.
3. Solved arrangement — Clockwise from M: M (Physics); P (Zoology); S (Economics); R (Civics); N (Chemistry); T (History); Q (Geography).
4. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-046 · L1 · easy · Circular arrangement — mixed facing · foundation

Five persons – A, B, C, D and E – sit around a circular table. Some of them face the centre and the others face away from the centre.

- C sits second to the left of E.
- B is an immediate neighbour of E.
- E faces the centre.
- A and B face opposite directions.
- D sits immediately to the right of C.
- D faces the centre.
- C sits immediately to the left of B.

How many persons face the centre?

- **A.** Two  _(error: counted those facing outside)_
- **B.** Four  _(error: off by one)_
- **C.** Three ✅
- **D.** Five  _(error: off by two)_

**Working**

1. Exhaustive enumeration over 24 seat/position orders × 30 facing patterns leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'B is an immediate neighbour of E.'; then place the others by elimination.
3. Solved arrangement — Clockwise from A: A [faces outside]; E [faces centre]; B [faces centre]; C [faces outside]; D [faces centre].
4. Facing the centre: B, D, E.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Fix every facing before counting.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-047 · L2 · medium · Circular arrangement — mixed facing · foundation

Five persons – J, K, L, M and N – sit around a circular table. Some of them face the centre and the others face away from the centre.

- Both immediate neighbours of L face the centre.
- K faces away from the centre.
- Both immediate neighbours of N face the centre.
- N sits second to the left of M.

Who sits second to the left of K?

- **A.** M  _(error: not at that seat)_
- **B.** N ✅
- **C.** L  _(error: treated K as facing the centre)_
- **D.** J  _(error: counted one seat short)_

**Working**

1. Exhaustive enumeration over 24 seat/position orders × 30 facing patterns leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from J: J [faces centre]; K [faces outside]; M [faces centre]; L [faces centre]; N [faces centre].
3. K faces away from the centre, so K's left runs anticlockwise; 2 seat(s) that way is N.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-048 · L2 · medium · Circular arrangement — mixed facing · foundation

Six persons – E, F, G, H, J and K – sit around a circular table. Some of them face the centre and the others face away from the centre.

- F sits second to the left of G.
- G faces away from the centre.
- E is an immediate neighbour of H.
- F sits immediately to the left of K.
- E sits second to the right of J.
- E faces away from the centre.
- G sits second to the left of H.
- J sits immediately to the right of G.

Who sits immediately to the right of E?

- **A.** F ✅
- **B.** K  _(error: counted one seat too far)_
- **C.** H  _(error: treated E as facing the centre)_
- **D.** G  _(error: not at that seat)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders × 62 facing patterns leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'E is an immediate neighbour of H.'; then place the others by elimination.
3. Solved arrangement — Clockwise from E: E [faces outside]; F [faces centre]; K [faces outside]; G [faces outside]; J [faces outside]; H [faces outside].
4. E faces away from the centre, so E's right runs clockwise; 1 seat(s) that way is F.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-049 · L2 · medium · Circular arrangement — mixed facing · foundation

Six persons – L, M, N, P, Q and R – sit around a circular table. Some of them face the centre and the others face away from the centre.

- Exactly three persons face the centre.
- M sits second to the left of Q.
- Only one person sits between R and M when counted from the left of R.
- L sits immediately to the right of Q.
- P is an immediate neighbour of Q.
- M faces the centre.
- Only one person sits between N and L when counted from the right of N.
- Only one person sits between P and N when counted from the right of P.

What is the position of Q with respect to L?

- **A.** Immediately to the left ✅
- **B.** Immediately to the right  _(error: direction reversed)_
- **C.** Second to the right  _(error: reversed and off by one)_
- **D.** Second to the left  _(error: counted one seat extra)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders × 62 facing patterns leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'P is an immediate neighbour of Q.'; then place the others by elimination.
3. Solved arrangement — Clockwise from L: L [faces centre]; Q [faces centre]; P [faces outside]; M [faces centre]; N [faces outside]; R [faces outside].
4. L faces the centre; counted from L's own right/left, Q is immediately to the left.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Positions are always read from the reference person's facing.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-050 · L2 · medium · Circular arrangement — mixed facing · foundation

Six persons – L, M, N, P, Q and R – sit around a circular table. Some of them face the centre and the others face away from the centre.

- Q sits second to the left of M.
- Only one person sits between L and M when counted from the right of L.
- M sits immediately to the right of R.
- L sits second to the right of Q.
- N sits second to the right of R.
- R sits second to the left of P.
- Both immediate neighbours of L face the centre.

Who sits opposite L?

- **A.** Q  _(error: seat next to the opposite seat)_
- **B.** M  _(error: seat next to the opposite seat)_
- **C.** R ✅
- **D.** N  _(error: not opposite)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders × 62 facing patterns leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from L: L [faces centre]; P [faces centre]; Q [faces centre]; R [faces outside]; M [faces outside]; N [faces centre].
3. The seat 3 places away from L in either direction is R's.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Opposite means exactly half-way round the table.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-051 · L3 · hard · Circular arrangement — mixed facing · officer

Seven persons – E, F, G, H, J, K and L – sit around a circular table. Some of them face the centre and the others face away from the centre.

- K sits second to the left of H.
- G sits immediately to the right of L.
- J sits third to the left of K.
- K sits immediately to the right of F.
- F sits third to the left of E.
- Both immediate neighbours of E face away from the centre.
- E sits immediately to the left of G.

Who sits immediately to the right of J?

- **A.** H  _(error: treated J as facing the centre)_
- **B.** E ✅
- **C.** G  _(error: counted one seat too far)_
- **D.** F  _(error: not at that seat)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 126 facing patterns leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from E: E [faces outside]; G [faces outside]; L [faces centre]; K [faces centre]; F [faces centre]; H [faces outside]; J [faces outside].
3. J faces away from the centre, so J's right runs clockwise; 1 seat(s) that way is E.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-052 · L3 · hard · Circular arrangement — mixed facing · officer

Six persons – M, N, P, Q, R and S – sit around a circular table. Some of them face the centre and the others face away from the centre. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Kochi and Patna.

- The one from Kochi is an immediate neighbour of the one from Bhopal.
- R is not from Agra.
- The immediate neighbours of R face opposite directions.
- The one from Delhi sits second to the left of S.
- The immediate neighbours of Q face opposite directions.
- Q is an immediate neighbour of S.
- N sits second to the right of the one from Bhopal.
- Q sits second to the right of R.
- R is not from Chennai.
- S is not from Kochi.
- N is not from Chennai.
- M sits second to the right of P.
- Both immediate neighbours of the one from Delhi face the centre.

Which of the following statements is true?

- **A.** R and the one from Chennai face the same direction. ✅
- **B.** The one from Delhi sits immediately to the left of Q.  _(error: false in the solved arrangement)_
- **C.** N sits immediately to the left of the one from Delhi.  _(error: false in the solved arrangement)_
- **D.** M and the one from Agra face the same direction.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders × 62 facing patterns × 720 city assignments leaves exactly one arrangement that satisfies all 13 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Q is an immediate neighbour of S.'; then place the others by elimination.
3. Solved arrangement — Clockwise from M: M [faces outside] (Kochi); Q [faces centre] (Bhopal); S [faces centre] (Chennai); R [faces centre] (Patna); P [faces outside] (Delhi); N [faces centre] (Agra).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-053 · L4 · hard · Circular arrangement — mixed facing · officer

Eight persons – J, K, L, M, N, P, Q and R – sit around a circular table. Some of them face the centre and the others face away from the centre.

- The immediate neighbours of L face opposite directions.
- N and Q face the same direction.
- Only two persons sit between R and N when counted from the left of R.
- P sits third to the left of M.
- R sits third to the left of L.
- R sits immediately to the right of M.
- Q faces the centre.
- L sits immediately to the left of J.
- L faces the centre.
- P sits third to the right of K.
- K faces the centre.

Who sits second to the left of J?

- **A.** P ✅
- **B.** R  _(error: treated J as facing the centre)_
- **C.** L  _(error: counted one seat short)_
- **D.** N  _(error: counted one seat too far)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from J: J [faces outside]; K [faces centre]; R [faces centre]; M [faces centre]; Q [faces centre]; N [faces centre]; P [faces centre]; L [faces centre].
3. J faces away from the centre, so J's left runs anticlockwise; 2 seat(s) that way is P.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-054 · L4 · hard · Circular arrangement — mixed facing · officer

Eight persons – J, K, L, M, N, P, Q and R – sit around a circular table. Some of them face the centre and the others face away from the centre.

- The immediate neighbours of L face opposite directions.
- N and Q face the same direction.
- Only two persons sit between R and N when counted from the left of R.
- P sits third to the left of M.
- R sits third to the left of L.
- R sits immediately to the right of M.
- Q faces the centre.
- L sits immediately to the left of J.
- L faces the centre.
- P sits third to the right of K.
- K faces the centre.

What is the position of R with respect to K?

- **A.** Second to the left  _(error: counted one seat extra)_
- **B.** Immediately to the right  _(error: direction reversed)_
- **C.** Immediately to the left ✅
- **D.** Second to the right  _(error: reversed and off by one)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from J: J [faces outside]; K [faces centre]; R [faces centre]; M [faces centre]; Q [faces centre]; N [faces centre]; P [faces centre]; L [faces centre].
3. K faces the centre; counted from K's own right/left, R is immediately to the left.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Positions are always read from the reference person's facing.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-055 · L4 · hard · Circular arrangement — mixed facing · officer

Eight persons – J, K, L, M, N, P, Q and R – sit around a circular table. Some of them face the centre and the others face away from the centre.

- The immediate neighbours of L face opposite directions.
- N and Q face the same direction.
- Only two persons sit between R and N when counted from the left of R.
- P sits third to the left of M.
- R sits third to the left of L.
- R sits immediately to the right of M.
- Q faces the centre.
- L sits immediately to the left of J.
- L faces the centre.
- P sits third to the right of K.
- K faces the centre.

How many persons face the centre?

- **A.** One  _(error: counted those facing outside)_
- **B.** Seven ✅
- **C.** Six  _(error: off by one)_
- **D.** Eight  _(error: off by one)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from J: J [faces outside]; K [faces centre]; R [faces centre]; M [faces centre]; Q [faces centre]; N [faces centre]; P [faces centre]; L [faces centre].
3. Facing the centre: K, L, M, N, P, Q, R.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Fix every facing before counting.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-056 · L4 · hard · Circular arrangement — mixed facing · officer

Eight persons – J, K, L, M, N, P, Q and R – sit around a circular table. Some of them face the centre and the others face away from the centre.

- The immediate neighbours of L face opposite directions.
- N and Q face the same direction.
- Only two persons sit between R and N when counted from the left of R.
- P sits third to the left of M.
- R sits third to the left of L.
- R sits immediately to the right of M.
- Q faces the centre.
- L sits immediately to the left of J.
- L faces the centre.
- P sits third to the right of K.
- K faces the centre.

How many persons sit between Q and L when counted from the left of Q?

- **A.** Three  _(error: counted one named person)_
- **B.** Four  _(error: counted from the other side)_
- **C.** Two ✅
- **D.** One  _(error: counted one short)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from J: J [faces outside]; K [faces centre]; R [faces centre]; M [faces centre]; Q [faces centre]; N [faces centre]; P [faces centre]; L [faces centre].
3. Moving to Q's left, 2 person(s) are passed before reaching L.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** The count depends on the side; the other side gives n − 2 − m.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-057 · L4 · hard · Circular arrangement — mixed facing · officer

Eight persons – J, K, L, M, N, P, Q and R – sit around a circular table. Some of them face the centre and the others face away from the centre.

- The immediate neighbours of L face opposite directions.
- N and Q face the same direction.
- Only two persons sit between R and N when counted from the left of R.
- P sits third to the left of M.
- R sits third to the left of L.
- R sits immediately to the right of M.
- Q faces the centre.
- L sits immediately to the left of J.
- L faces the centre.
- P sits third to the right of K.
- K faces the centre.

Which of the following statements is true?

- **A.** L is an immediate neighbour of N.  _(error: false in the solved arrangement)_
- **B.** J sits second to the right of R. ✅
- **C.** L sits second to the right of R.  _(error: false in the solved arrangement)_
- **D.** L and P face opposite directions.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from J: J [faces outside]; K [faces centre]; R [faces centre]; M [faces centre]; Q [faces centre]; N [faces centre]; P [faces centre]; L [faces centre].
3. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-058 · L4 · hard · Circular arrangement — mixed facing · officer

Seven persons – L, M, N, P, Q, R and S – sit around a circular table. Some of them face the centre and the others face away from the centre. Each of them plays a different game among Chess, Cricket, Football, Hockey, Kabaddi, Tennis and Volleyball.

- P sits third to the left of N.
- The one who plays Tennis and Q face opposite directions.
- P does not play Kabaddi.
- L and P face the same direction.
- The one who plays Cricket faces the centre.
- P sits immediately to the left of the one who plays Chess.
- Q does not play Football.
- S faces the centre.
- Only two persons sit between R and the one who plays Tennis when counted from the right of R.
- P does not play Football.
- S does not play Football.
- N does not play Kabaddi.
- M faces the centre.
- Exactly four persons face the centre.
- Q sits second to the right of L.
- The one who plays Football sits third to the left of the one who plays Volleyball.
- N and P face the same direction.

Who sits third to the left of the one who plays Kabaddi?

- **A.** S  _(error: treated L as facing the centre)_
- **B.** R ✅
- **C.** M  _(error: not at that seat)_
- **D.** P  _(error: counted one seat short)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 126 facing patterns × 5,040 sport assignments leaves exactly one arrangement that satisfies all 17 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from L: L [faces outside] (Kabaddi); N [faces outside] (Tennis); Q [faces centre] (Cricket); S [faces centre] (Volleyball); R [faces centre] (Chess); P [faces outside] (Hockey); M [faces centre] (Football).
3. L faces away from the centre, so L's left runs anticlockwise; 3 seat(s) that way is R.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-059 · L4 · hard · Circular arrangement — mixed facing · officer

Seven persons – L, M, N, P, Q, R and S – sit around a circular table. Some of them face the centre and the others face away from the centre. Each of them plays a different game among Chess, Cricket, Football, Hockey, Kabaddi, Tennis and Volleyball.

- P sits third to the left of N.
- The one who plays Tennis and Q face opposite directions.
- P does not play Kabaddi.
- L and P face the same direction.
- The one who plays Cricket faces the centre.
- P sits immediately to the left of the one who plays Chess.
- Q does not play Football.
- S faces the centre.
- Only two persons sit between R and the one who plays Tennis when counted from the right of R.
- P does not play Football.
- S does not play Football.
- N does not play Kabaddi.
- M faces the centre.
- Exactly four persons face the centre.
- Q sits second to the right of L.
- The one who plays Football sits third to the left of the one who plays Volleyball.
- N and P face the same direction.

Who plays Tennis?

- **A.** L  _(error: neighbour of the correct person)_
- **B.** R  _(error: no clue links this person to that attribute)_
- **C.** Q  _(error: neighbour of the correct person)_
- **D.** N ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 126 facing patterns × 5,040 sport assignments leaves exactly one arrangement that satisfies all 17 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from L: L [faces outside] (Kabaddi); N [faces outside] (Tennis); Q [faces centre] (Cricket); S [faces centre] (Volleyball); R [faces centre] (Chess); P [faces outside] (Hockey); M [faces centre] (Football).
3. N plays Tennis.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Attribute clues often name the attribute, not the person; resolve them only after positions are fixed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-060 · L4 · hard · Circular arrangement — mixed facing · officer

Seven persons – L, M, N, P, Q, R and S – sit around a circular table. Some of them face the centre and the others face away from the centre. Each of them plays a different game among Chess, Cricket, Football, Hockey, Kabaddi, Tennis and Volleyball.

- P sits third to the left of N.
- The one who plays Tennis and Q face opposite directions.
- P does not play Kabaddi.
- L and P face the same direction.
- The one who plays Cricket faces the centre.
- P sits immediately to the left of the one who plays Chess.
- Q does not play Football.
- S faces the centre.
- Only two persons sit between R and the one who plays Tennis when counted from the right of R.
- P does not play Football.
- S does not play Football.
- N does not play Kabaddi.
- M faces the centre.
- Exactly four persons face the centre.
- Q sits second to the right of L.
- The one who plays Football sits third to the left of the one who plays Volleyball.
- N and P face the same direction.

Which of the following statements is NOT true?

- **A.** Only one person sits between P and L when counted from the right of P.  _(error: this statement is true in the solved arrangement)_
- **B.** Only one person sits between P and S when counted from the left of P.  _(error: this statement is true in the solved arrangement)_
- **C.** Only two persons sit between N and M when counted from the right of N. ✅
- **D.** Only two persons sit between M and S when counted from the right of M.  _(error: this statement is true in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 126 facing patterns × 5,040 sport assignments leaves exactly one arrangement that satisfies all 17 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from L: L [faces outside] (Kabaddi); N [faces outside] (Tennis); Q [faces centre] (Cricket); S [faces centre] (Volleyball); R [faces centre] (Chess); P [faces outside] (Hockey); M [faces centre] (Football).
3. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-061 · L1 · easy · Square and rectangular arrangement · foundation

Four persons – J, K, L and M – sit around a square table, one at each corner, all facing the centre.

- K sits immediately to the right of J.
- M sits immediately to the left of J.

Which of the following statements is true?

- **A.** L sits immediately to the left of M. ✅
- **B.** J sits immediately to the left of M.  _(error: false in the solved arrangement)_
- **C.** K is an immediate neighbour of M.  _(error: false in the solved arrangement)_
- **D.** M sits immediately to the right of J.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 6 seat/position orders leaves exactly one arrangement that satisfies all 2 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'K sits immediately to the right of J.' and 'M sits immediately to the left of J.'; then place the others by elimination.
3. Solved arrangement — Clockwise from J: J; M; L; K.
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-062 · L2 · medium · Square and rectangular arrangement · foundation

Six persons – K, L, M, N, P and Q – sit around a rectangular table: two sit on each of the longer sides and one sits at each of the shorter sides, all facing the centre.

- M sits immediately to the right of N.
- N sits second to the right of P.
- N sits on one of the longer sides of the table.
- P sits on one of the longer sides of the table.
- P sits immediately to the right of Q.
- P sits immediately to the left of L.

Who sits second to the left of Q?

- **A.** K  _(error: counted one seat short)_
- **B.** N  _(error: counted one seat too far)_
- **C.** L  _(error: direction reversed)_
- **D.** M ✅

**Working**

1. Exhaustive enumeration over 360 seat/position orders leaves exactly one arrangement that satisfies all 6 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'M sits immediately to the right of N.' and 'N sits second to the right of P.'; then place the others by elimination.
3. Solved arrangement — Clockwise from K: K [shorter side]; M [longer side]; N [longer side]; L [shorter side]; P [longer side]; Q [longer side].
4. Q faces the centre, so Q's left runs clockwise; 2 seat(s) that way is M.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-063 · L2 · medium · Square and rectangular arrangement · foundation

Six persons – E, F, G, H, J and K – sit around a rectangular table: two sit on each of the longer sides and one sits at each of the shorter sides, all facing the centre.

- G sits immediately to the right of E.
- G is an immediate neighbour of K.
- F is not an immediate neighbour of H.
- K sits on one of the longer sides of the table.
- H sits second to the left of G.
- E sits on one of the longer sides of the table.

What is the position of G with respect to K?

- **A.** Immediately to the right  _(error: direction reversed)_
- **B.** Second to the left  _(error: counted one seat extra)_
- **C.** Immediately to the left ✅
- **D.** Second to the right  _(error: reversed and off by one)_

**Working**

1. Exhaustive enumeration over 360 seat/position orders leaves exactly one arrangement that satisfies all 6 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'G sits immediately to the right of E.' and 'H sits second to the left of G.'; then place the others by elimination.
3. Solved arrangement — Clockwise from G: G [shorter side]; E [longer side]; H [longer side]; J [shorter side]; F [longer side]; K [longer side].
4. K faces the centre; counted from K's own right/left, G is immediately to the left.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Positions are always read from the reference person's facing.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-064 · L2 · medium · Square and rectangular arrangement · foundation

Eight persons – D, E, F, G, H, J, K and L – sit around a square table: four sit at the four corners and four sit one at the middle of each side, all facing the centre.

- F sits third to the left of J.
- Only two persons sit between F and K when counted from the left of F.
- L sits third to the left of H.
- H sits immediately to the right of G.
- D sits immediately to the left of J.
- J sits at one of the corners.

Who sits opposite H?

- **A.** D  _(error: seat next to the opposite seat)_
- **B.** E  _(error: not opposite)_
- **C.** L  _(error: seat next to the opposite seat)_
- **D.** J ✅

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders leaves exactly one arrangement that satisfies all 6 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'D sits immediately to the left of J.' and 'F sits third to the left of J.'; then place the others by elimination.
3. Solved arrangement — Clockwise from J: J [corner]; D [middle of side]; E [corner]; F [middle of side]; H [corner]; G [middle of side]; K [corner]; L [middle of side].
4. The seat 4 places away from H in either direction is J's.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Opposite means exactly half-way round the table.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-065 · L2 · medium · Square and rectangular arrangement · foundation

Eight persons – L, M, N, P, Q, R, S and T – sit around a square table: four sit at the four corners and four sit one at the middle of each side, all facing the centre.

- M sits immediately to the left of L.
- Q sits third to the right of M.
- L sits third to the right of P.
- S sits at the middle of one of the sides.
- T sits immediately to the left of R.
- P sits opposite S.

Who sits second to the right of S?

- **A.** M  _(error: direction reversed)_
- **B.** R  _(error: counted one seat too far)_
- **C.** Q  _(error: counted one seat short)_
- **D.** T ✅

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders leaves exactly one arrangement that satisfies all 6 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L sits third to the right of P.' and 'M sits immediately to the left of L.'; then place the others by elimination.
3. Solved arrangement — Clockwise from L: L [corner]; M [middle of side]; N [corner]; P [middle of side]; R [corner]; T [middle of side]; Q [corner]; S [middle of side].
4. S faces the centre, so S's right runs anticlockwise; 2 seat(s) that way is T.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-066 · L3 · hard · Square and rectangular arrangement · officer

Eight persons – P, Q, R, S, T, U, V and W – sit around a square table: four sit at the four corners and four sit one at the middle of each side. Those at the corners face the centre and those at the middle of the sides face away from the centre.

- Only two persons sit between P and V when counted from the right of P.
- W sits third to the left of U.
- T sits at the middle of one of the sides.
- R sits second to the left of V.
- Q sits third to the left of V.
- T sits immediately to the right of P.
- T sits second to the left of W.

Who sits third to the right of V?

- **A.** Q  _(error: treated V as facing the centre)_
- **B.** P ✅
- **C.** W  _(error: counted one seat too far)_
- **D.** T  _(error: counted one seat short)_

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only two persons sit between P and V when counted from the right of P.' and 'Q sits third to the left of V.'; then place the others by elimination.
3. Solved arrangement — Clockwise from P: P [faces centre, corner]; W [faces outside, middle of side]; Q [faces centre, corner]; R [faces outside, middle of side]; S [faces centre, corner]; V [faces outside, middle of side]; U [faces centre, corner]; T [faces outside, middle of side].
4. V faces away from the centre, so V's right runs clockwise; 3 seat(s) that way is P.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-067 · L3 · hard · Square and rectangular arrangement · officer

Six persons – K, L, M, N, P and Q – sit around a rectangular table: two sit on each of the longer sides and one sits at each of the shorter sides, all facing the centre. Each of them likes a different fruit among Banana, Cherry, Guava, Litchi, Mango and Orange.

- L does not like Mango.
- The one who likes Litchi sits second to the left of K.
- Only one person sits between N and the one who likes Orange when counted from the right of N.
- P does not like Banana.
- The one who likes Cherry sits second to the left of M.
- The one who likes Litchi sits on one of the longer sides of the table.
- L is an immediate neighbour of M.
- P sits second to the left of the one who likes Mango.
- M sits at one of the shorter sides of the table.
- N sits immediately to the left of K.

Who sits immediately to the right of the one who likes Mango?

- **A.** L  _(error: counted one seat too far)_
- **B.** Q  _(error: direction reversed)_
- **C.** K ✅
- **D.** M  _(error: not at that seat)_

**Working**

1. Exhaustive enumeration over 360 seat/position orders × 720 fruit assignments leaves exactly one arrangement that satisfies all 10 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'N sits immediately to the left of K.' and 'M sits at one of the shorter sides of the table.'; then place the others by elimination.
3. Solved arrangement — Clockwise from M: M [shorter side] (Banana); L [longer side] (Orange); K [longer side] (Cherry); N [shorter side] (Mango); Q [longer side] (Litchi); P [longer side] (Guava).
4. N faces the centre, so N's right runs anticlockwise; 1 seat(s) that way is K.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-068 · L4 · hard · Square and rectangular arrangement · officer

Eight persons – P, Q, R, S, T, U, V and W – sit around a square table: four sit at the four corners and four sit one at the middle of each side. Those at the corners face the centre and those at the middle of the sides face away from the centre. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- The one who works in Audit sits immediately to the left of Q.
- T does not work in Legal.
- The one who works in Marketing sits opposite V.
- The one who works in IT sits third to the left of T.
- S is an immediate neighbour of W.
- Only one person sits between R and S when counted from the right of R.
- Q sits third to the right of U.
- V sits third to the right of R.
- The one who works in Finance sits third to the left of the one who works in HR.
- The one who works in Sales sits immediately to the right of the one who works in Audit.
- The one who works in Finance sits second to the right of V.
- P sits at one of the corners.

Who sits third to the left of T?

- **A.** S  _(error: treated T as facing the centre)_
- **B.** R ✅
- **C.** W  _(error: counted one seat too far)_
- **D.** U  _(error: counted one seat short)_

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person sits between R and S when counted from the right of R.' and 'Q sits third to the right of U.'; then place the others by elimination.
3. Solved arrangement — Clockwise from P: P [faces centre, corner] (Legal); T [faces outside, middle of side] (Admin); Q [faces centre, corner] (HR); V [faces outside, middle of side] (Audit); S [faces centre, corner] (Sales); W [faces outside, middle of side] (Finance); R [faces centre, corner] (IT); U [faces outside, middle of side] (Marketing).
4. T faces away from the centre, so T's left runs anticlockwise; 3 seat(s) that way is R.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-069 · L4 · hard · Square and rectangular arrangement · officer

Eight persons – P, Q, R, S, T, U, V and W – sit around a square table: four sit at the four corners and four sit one at the middle of each side. Those at the corners face the centre and those at the middle of the sides face away from the centre. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- The one who works in Audit sits immediately to the left of Q.
- T does not work in Legal.
- The one who works in Marketing sits opposite V.
- The one who works in IT sits third to the left of T.
- S is an immediate neighbour of W.
- Only one person sits between R and S when counted from the right of R.
- Q sits third to the right of U.
- V sits third to the right of R.
- The one who works in Finance sits third to the left of the one who works in HR.
- The one who works in Sales sits immediately to the right of the one who works in Audit.
- The one who works in Finance sits second to the right of V.
- P sits at one of the corners.

In which department does W work?

- **A.** Finance ✅
- **B.** Sales  _(error: attribute of S, a neighbour of W)_
- **C.** IT  _(error: attribute of R, a neighbour of W)_
- **D.** Admin  _(error: attribute of T)_

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person sits between R and S when counted from the right of R.' and 'Q sits third to the right of U.'; then place the others by elimination.
3. Solved arrangement — Clockwise from P: P [faces centre, corner] (Legal); T [faces outside, middle of side] (Admin); Q [faces centre, corner] (HR); V [faces outside, middle of side] (Audit); S [faces centre, corner] (Sales); W [faces outside, middle of side] (Finance); R [faces centre, corner] (IT); U [faces outside, middle of side] (Marketing).
4. W works in Finance in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-070 · L4 · hard · Square and rectangular arrangement · officer

Eight persons – P, Q, R, S, T, U, V and W – sit around a square table: four sit at the four corners and four sit one at the middle of each side. Those at the corners face the centre and those at the middle of the sides face away from the centre. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- The one who works in Audit sits immediately to the left of Q.
- T does not work in Legal.
- The one who works in Marketing sits opposite V.
- The one who works in IT sits third to the left of T.
- S is an immediate neighbour of W.
- Only one person sits between R and S when counted from the right of R.
- Q sits third to the right of U.
- V sits third to the right of R.
- The one who works in Finance sits third to the left of the one who works in HR.
- The one who works in Sales sits immediately to the right of the one who works in Audit.
- The one who works in Finance sits second to the right of V.
- P sits at one of the corners.

Three of the following four are alike in a certain way based on their positions in the arrangement and so form a group. Which one does not belong to that group?

- **A.** R  _(error: belongs to the group (facing the centre))_
- **B.** T ✅
- **C.** Q  _(error: belongs to the group (facing the centre))_
- **D.** P  _(error: belongs to the group (facing the centre))_

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person sits between R and S when counted from the right of R.' and 'Q sits third to the right of U.'; then place the others by elimination.
3. Solved arrangement — Clockwise from P: P [faces centre, corner] (Legal); T [faces outside, middle of side] (Admin); Q [faces centre, corner] (HR); V [faces outside, middle of side] (Audit); S [faces centre, corner] (Sales); W [faces outside, middle of side] (Finance); R [faces centre, corner] (IT); U [faces outside, middle of side] (Marketing).
4. R, Q, P are all facing the centre; T is not.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Look for the positional property the three share, not for the letters' alphabetical pattern.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-071 · L4 · hard · Square and rectangular arrangement · officer

Eight persons – P, Q, R, S, T, U, V and W – sit around a square table: four sit at the four corners and four sit one at the middle of each side. Those at the corners face the centre and those at the middle of the sides face away from the centre. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- The one who works in Audit sits immediately to the left of Q.
- T does not work in Legal.
- The one who works in Marketing sits opposite V.
- The one who works in IT sits third to the left of T.
- S is an immediate neighbour of W.
- Only one person sits between R and S when counted from the right of R.
- Q sits third to the right of U.
- V sits third to the right of R.
- The one who works in Finance sits third to the left of the one who works in HR.
- The one who works in Sales sits immediately to the right of the one who works in Audit.
- The one who works in Finance sits second to the right of V.
- P sits at one of the corners.

What is the position of V with respect to W?

- **A.** Third to the right  _(error: reversed and off by one)_
- **B.** Second to the right  _(error: direction reversed)_
- **C.** Second to the left ✅
- **D.** Third to the left  _(error: counted one seat extra)_

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person sits between R and S when counted from the right of R.' and 'Q sits third to the right of U.'; then place the others by elimination.
3. Solved arrangement — Clockwise from P: P [faces centre, corner] (Legal); T [faces outside, middle of side] (Admin); Q [faces centre, corner] (HR); V [faces outside, middle of side] (Audit); S [faces centre, corner] (Sales); W [faces outside, middle of side] (Finance); R [faces centre, corner] (IT); U [faces outside, middle of side] (Marketing).
4. W faces away from the centre; counted from W's own right/left, V is second to the left.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Positions are always read from the reference person's facing.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-072 · L4 · hard · Square and rectangular arrangement · officer

Eight persons – P, Q, R, S, T, U, V and W – sit around a square table: four sit at the four corners and four sit one at the middle of each side. Those at the corners face the centre and those at the middle of the sides face away from the centre. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- The one who works in Audit sits immediately to the left of Q.
- T does not work in Legal.
- The one who works in Marketing sits opposite V.
- The one who works in IT sits third to the left of T.
- S is an immediate neighbour of W.
- Only one person sits between R and S when counted from the right of R.
- Q sits third to the right of U.
- V sits third to the right of R.
- The one who works in Finance sits third to the left of the one who works in HR.
- The one who works in Sales sits immediately to the right of the one who works in Audit.
- The one who works in Finance sits second to the right of V.
- P sits at one of the corners.

Which of the following statements is true?

- **A.** Only two persons sit between S and the one who works in Audit when counted from the right of S.  _(error: false in the solved arrangement)_
- **B.** Only one person sits between R and the one who works in Sales when counted from the left of R.  _(error: false in the solved arrangement)_
- **C.** Only two persons sit between P and the one who works in Finance when counted from the left of P.  _(error: false in the solved arrangement)_
- **D.** Only one person sits between W and the one who works in Audit when counted from the left of W. ✅

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person sits between R and S when counted from the right of R.' and 'Q sits third to the right of U.'; then place the others by elimination.
3. Solved arrangement — Clockwise from P: P [faces centre, corner] (Legal); T [faces outside, middle of side] (Admin); Q [faces centre, corner] (HR); V [faces outside, middle of side] (Audit); S [faces centre, corner] (Sales); W [faces outside, middle of side] (Finance); R [faces centre, corner] (IT); U [faces outside, middle of side] (Marketing).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-073 · L4 · hard · Square and rectangular arrangement · officer

Eight persons – B, C, D, E, F, G, H and J – sit around a square table: four sit at the four corners and four sit one at the middle of each side. Some of them face the centre and the others face away from the centre.

- B sits opposite E.
- H sits second to the right of E.
- C sits at one of the corners.
- J sits second to the left of G.
- C sits immediately to the left of F.
- G faces away from the centre.
- E sits second to the right of C.
- J sits immediately to the right of B.
- E and H face opposite directions.
- C sits third to the right of D.
- H sits immediately to the right of J.

Who sits third to the right of C?

- **A.** J  _(error: treated C as facing the centre)_
- **B.** D ✅
- **C.** E  _(error: counted one seat short)_
- **D.** H  _(error: counted one seat too far)_

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'B sits opposite E.' and 'C sits at one of the corners.'; then place the others by elimination.
3. Solved arrangement — Clockwise from B: B [faces centre, corner]; G [faces outside, middle of side]; C [faces outside, corner]; F [faces outside, middle of side]; E [faces outside, corner]; D [faces centre, middle of side]; H [faces centre, corner]; J [faces centre, middle of side].
4. C faces away from the centre, so C's right runs clockwise; 3 seat(s) that way is D.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-074 · L4 · hard · Square and rectangular arrangement · officer

Eight persons – B, C, D, E, F, G, H and J – sit around a square table: four sit at the four corners and four sit one at the middle of each side. Some of them face the centre and the others face away from the centre.

- B sits opposite E.
- H sits second to the right of E.
- C sits at one of the corners.
- J sits second to the left of G.
- C sits immediately to the left of F.
- G faces away from the centre.
- E sits second to the right of C.
- J sits immediately to the right of B.
- E and H face opposite directions.
- C sits third to the right of D.
- H sits immediately to the right of J.

How many persons face the centre?

- **A.** Three  _(error: off by one)_
- **B.** Four ✅
- **C.** Six  _(error: off by two)_
- **D.** Five  _(error: off by one)_

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'B sits opposite E.' and 'C sits at one of the corners.'; then place the others by elimination.
3. Solved arrangement — Clockwise from B: B [faces centre, corner]; G [faces outside, middle of side]; C [faces outside, corner]; F [faces outside, middle of side]; E [faces outside, corner]; D [faces centre, middle of side]; H [faces centre, corner]; J [faces centre, middle of side].
4. Facing the centre: B, D, H, J.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Fix every facing before counting.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-075 · L4 · hard · Square and rectangular arrangement · officer

Eight persons – B, C, D, E, F, G, H and J – sit around a square table: four sit at the four corners and four sit one at the middle of each side. Some of them face the centre and the others face away from the centre.

- B sits opposite E.
- H sits second to the right of E.
- C sits at one of the corners.
- J sits second to the left of G.
- C sits immediately to the left of F.
- G faces away from the centre.
- E sits second to the right of C.
- J sits immediately to the right of B.
- E and H face opposite directions.
- C sits third to the right of D.
- H sits immediately to the right of J.

Which of the following statements is NOT true?

- **A.** Both immediate neighbours of F face the centre. ✅
- **B.** The immediate neighbours of E face opposite directions.  _(error: this statement is true in the solved arrangement)_
- **C.** Both immediate neighbours of F face away from the centre.  _(error: this statement is true in the solved arrangement)_
- **D.** Both immediate neighbours of J face the centre.  _(error: this statement is true in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders × 254 facing patterns leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'B sits opposite E.' and 'C sits at one of the corners.'; then place the others by elimination.
3. Solved arrangement — Clockwise from B: B [faces centre, corner]; G [faces outside, middle of side]; C [faces outside, corner]; F [faces outside, middle of side]; E [faces outside, corner]; D [faces centre, middle of side]; H [faces centre, corner]; J [faces centre, middle of side].
4. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-076 · L1 · easy · Floor puzzle · foundation

Five persons – B, C, D, E and F – live on the five floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 5.

- F lives on floor 4.
- F lives three floors above D.
- C lives two floors below E.

Who lives on floor 5?

- **A.** B  _(error: not at that position)_
- **B.** E ✅
- **C.** F  _(error: off by one position)_
- **D.** D  _(error: counted from the opposite end)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'F lives three floors above D.' and 'C lives two floors below E.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – D; Floor 2 – B; Floor 3 – C; Floor 4 – F; Floor 5 – E.
4. Floor 5 is occupied by E.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Check which end the count starts from.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-077 · L1 · easy · Floor puzzle · foundation

Five persons – A, B, C, D and E – live on the five floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 5.

- Only two persons live between A and E, and A lives above E.
- C and E live on adjacent floors.
- D lives three floors above B.

On which floor does B live?

- **A.** Floor 1 ✅
- **B.** Floor 5  _(error: counted from the opposite end)_
- **C.** Floor 3  _(error: off by two positions)_
- **D.** Floor 2  _(error: off by one position)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'D lives three floors above B.' and 'Only two persons live between A and E, and A lives above E.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – B; Floor 2 – E; Floor 3 – C; Floor 4 – D; Floor 5 – A.
4. B is at Floor 1.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-078 · L2 · medium · Floor puzzle · foundation

Six persons – K, L, M, N, P and Q – live on the six floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 6.

- Only two persons live between K and M, and K lives above M.
- Only one person lives between L and Q, and L lives above Q.
- P lives four floors above M.

Who lives on the floor immediately below K?

- **A.** P  _(error: direction reversed (above instead of below))_
- **B.** L  _(error: counted one place too far)_
- **C.** M  _(error: not at the required position)_
- **D.** N ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'P lives four floors above M.' and 'Only two persons live between K and M, and K lives above M.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – Q; Floor 2 – M; Floor 3 – L; Floor 4 – N; Floor 5 – K; Floor 6 – P.
4. K is at Floor 5; the person asked for is at Floor 4, i.e. N.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-079 · L2 · medium · Floor puzzle · foundation

Six persons – J, K, L, M, N and P – live on the six floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 6.

- K lives four floors below N.
- N lives three floors above L.
- J and N live on adjacent floors.
- The number of persons living above L is the same as the number of persons living below P.

How many persons live between K and N?

- **A.** Three ✅
- **B.** Four  _(error: counted one of the two named persons)_
- **C.** Two  _(error: counted one short)_
- **D.** Five  _(error: counted both named persons)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'K lives four floors below N.' and 'N lives three floors above L.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – M; Floor 2 – K; Floor 3 – L; Floor 4 – P; Floor 5 – J; Floor 6 – N.
4. K is at Floor 2 and N at Floor 6; 3 position(s) lie strictly between them.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Between' excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-080 · L2 · medium · Floor puzzle · foundation

Six persons – E, F, G, H, J and K – live on the six floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 6.

- H lives on the floor immediately above K.
- G lives on an odd-numbered floor.
- E lives on the floor immediately below G.
- J lives four floors below G.

How many persons live above G?

- **A.** Two  _(error: included the person named)_
- **B.** One ✅
- **C.** Four  _(error: counted below instead of above)_
- **D.** None  _(error: missed the extreme position)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'J lives four floors below G.' and 'E lives on the floor immediately below G.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – J; Floor 2 – K; Floor 3 – H; Floor 4 – E; Floor 5 – G; Floor 6 – F.
4. G is at Floor 5; 1 position(s) lie beyond it in that direction.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Count only the persons beyond the one named, in the stated direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-081 · L3 · hard · Floor puzzle · officer

Seven persons – P, Q, R, S, T, U and V – live on the seven floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 7.

- Only two persons live between R and S, and R lives above S.
- The number of persons living above S is the same as the number of persons living below V.
- S lives on the floor immediately above Q.
- T lives on the floor immediately above P.

Which of the following statements is true?

- **A.** P lives three floors below R.  _(error: false in the solved arrangement)_
- **B.** V lives two floors below P.  _(error: false in the solved arrangement)_
- **C.** S lives three floors above U.  _(error: false in the solved arrangement)_
- **D.** T lives two floors below V. ✅

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only two persons live between R and S, and R lives above S.' and 'S lives on the floor immediately above Q.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – Q; Floor 2 – S; Floor 3 – P; Floor 4 – T; Floor 5 – R; Floor 6 – V; Floor 7 – U.
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-082 · L3 · hard · Floor puzzle · officer

Six persons – D, E, F, G, H and J – live on the six floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 6. Each of them owns a car of a different colour among black, blue, grey, red, silver and yellow.

- The owner of the red car lives on an odd-numbered floor.
- G does not own the red car.
- The owner of the black car lives on a floor somewhere above H.
- J lives three floors above E.
- The owner of the blue car lives three floors above G.
- The owner of the yellow car lives four floors above D.
- G does not own the silver car.

Who lives on the floor immediately below the owner of the black car?

- **A.** H ✅
- **B.** J  _(error: direction reversed (above instead of below))_
- **C.** E  _(error: counted one place too far)_
- **D.** D  _(error: not at the required position)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 car assignments leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'J lives three floors above E.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – G (grey); Floor 2 – D (silver); Floor 3 – E (red); Floor 4 – H (blue); Floor 5 – F (black); Floor 6 – J (yellow).
4. The owner of the black car is at Floor 5; the person asked for is at Floor 4, i.e. H.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-083 · L4 · hard · Floor puzzle · officer

Eight persons – K, L, M, N, P, Q, R and S – live on the eight floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 8. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore, Jaipur, Kochi and Patna.

- Only three persons live between the one from Agra and the one from Indore, and the one from Agra lives above the one from Indore.
- S is not from Chennai.
- Only one person lives between P and N, and P lives above N.
- The one from Delhi lives three floors above L.
- R lives three floors above N.
- The one from Patna lives five floors below P.
- The one from Kochi lives two floors above L.
- Only two persons live between N and S.
- The one from Chennai lives four floors below Q.
- L lives three floors above K.
- Only two persons live between the one from Bhopal and P.

Who lives two floors below L?

- **A.** N  _(error: counted one place short)_
- **B.** K  _(error: counted one place too far)_
- **C.** M ✅
- **D.** R  _(error: direction reversed (above instead of below))_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 city assignments leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L lives three floors above K.' and 'R lives three floors above N.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – S (Patna); Floor 2 – K (Indore); Floor 3 – M (Bhopal); Floor 4 – N (Chennai); Floor 5 – L (Jaipur); Floor 6 – P (Agra); Floor 7 – R (Kochi); Floor 8 – Q (Delhi).
4. L is at Floor 5; the person asked for is at Floor 3, i.e. M.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-084 · L4 · hard · Floor puzzle · officer

Eight persons – K, L, M, N, P, Q, R and S – live on the eight floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 8. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore, Jaipur, Kochi and Patna.

- Only three persons live between the one from Agra and the one from Indore, and the one from Agra lives above the one from Indore.
- S is not from Chennai.
- Only one person lives between P and N, and P lives above N.
- The one from Delhi lives three floors above L.
- R lives three floors above N.
- The one from Patna lives five floors below P.
- The one from Kochi lives two floors above L.
- Only two persons live between N and S.
- The one from Chennai lives four floors below Q.
- L lives three floors above K.
- Only two persons live between the one from Bhopal and P.

Which city is N from?

- **A.** Chennai ✅
- **B.** Jaipur  _(error: attribute of L, a neighbour of N)_
- **C.** Bhopal  _(error: attribute of M, a neighbour of N)_
- **D.** Kochi  _(error: attribute of R)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 city assignments leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L lives three floors above K.' and 'R lives three floors above N.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – S (Patna); Floor 2 – K (Indore); Floor 3 – M (Bhopal); Floor 4 – N (Chennai); Floor 5 – L (Jaipur); Floor 6 – P (Agra); Floor 7 – R (Kochi); Floor 8 – Q (Delhi).
4. N is from Chennai in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-085 · L4 · hard · Floor puzzle · officer

Eight persons – K, L, M, N, P, Q, R and S – live on the eight floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 8. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore, Jaipur, Kochi and Patna.

- Only three persons live between the one from Agra and the one from Indore, and the one from Agra lives above the one from Indore.
- S is not from Chennai.
- Only one person lives between P and N, and P lives above N.
- The one from Delhi lives three floors above L.
- R lives three floors above N.
- The one from Patna lives five floors below P.
- The one from Kochi lives two floors above L.
- Only two persons live between N and S.
- The one from Chennai lives four floors below Q.
- L lives three floors above K.
- Only two persons live between the one from Bhopal and P.

How many persons live between K and Q?

- **A.** Four  _(error: counted one short)_
- **B.** Six  _(error: counted one of the two named persons)_
- **C.** Five ✅
- **D.** Seven  _(error: counted both named persons)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 city assignments leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L lives three floors above K.' and 'R lives three floors above N.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – S (Patna); Floor 2 – K (Indore); Floor 3 – M (Bhopal); Floor 4 – N (Chennai); Floor 5 – L (Jaipur); Floor 6 – P (Agra); Floor 7 – R (Kochi); Floor 8 – Q (Delhi).
4. K is at Floor 2 and Q at Floor 8; 5 position(s) lie strictly between them.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Between' excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-086 · L4 · hard · Floor puzzle · officer

Eight persons – K, L, M, N, P, Q, R and S – live on the eight floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 8. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore, Jaipur, Kochi and Patna.

- Only three persons live between the one from Agra and the one from Indore, and the one from Agra lives above the one from Indore.
- S is not from Chennai.
- Only one person lives between P and N, and P lives above N.
- The one from Delhi lives three floors above L.
- R lives three floors above N.
- The one from Patna lives five floors below P.
- The one from Kochi lives two floors above L.
- Only two persons live between N and S.
- The one from Chennai lives four floors below Q.
- L lives three floors above K.
- Only two persons live between the one from Bhopal and P.

Which of the following statements is true?

- **A.** M lives four floors above K.  _(error: false in the solved arrangement)_
- **B.** P lives four floors above K. ✅
- **C.** N lives three floors above L.  _(error: false in the solved arrangement)_
- **D.** L lives three floors below S.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 city assignments leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L lives three floors above K.' and 'R lives three floors above N.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – S (Patna); Floor 2 – K (Indore); Floor 3 – M (Bhopal); Floor 4 – N (Chennai); Floor 5 – L (Jaipur); Floor 6 – P (Agra); Floor 7 – R (Kochi); Floor 8 – Q (Delhi).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-087 · L4 · hard · Floor puzzle · officer

Eight persons – K, L, M, N, P, Q, R and S – live on the eight floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 8. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore, Jaipur, Kochi and Patna.

- Only three persons live between the one from Agra and the one from Indore, and the one from Agra lives above the one from Indore.
- S is not from Chennai.
- Only one person lives between P and N, and P lives above N.
- The one from Delhi lives three floors above L.
- R lives three floors above N.
- The one from Patna lives five floors below P.
- The one from Kochi lives two floors above L.
- Only two persons live between N and S.
- The one from Chennai lives four floors below Q.
- L lives three floors above K.
- Only two persons live between the one from Bhopal and P.

On which floor does L live?

- **A.** Floor 4  _(error: counted from the opposite end)_
- **B.** Floor 6  _(error: off by one position)_
- **C.** Floor 5 ✅
- **D.** Floor 7  _(error: off by two positions)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 city assignments leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L lives three floors above K.' and 'R lives three floors above N.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – S (Patna); Floor 2 – K (Indore); Floor 3 – M (Bhopal); Floor 4 – N (Chennai); Floor 5 – L (Jaipur); Floor 6 – P (Agra); Floor 7 – R (Kochi); Floor 8 – Q (Delhi).
4. L is at Floor 5.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-088 · L4 · hard · Floor puzzle · officer

Seven persons – P, Q, R, S, T, U and V – live on the seven floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 7. Each of them plays a different game among Badminton, Chess, Cricket, Football, Kabaddi, Tennis and Volleyball.

- Only four persons live between T and P, and T lives above P.
- Only four persons live between the one who plays Chess and T.
- The one who plays Volleyball lives two floors below T.
- Only two persons live between T and U.
- The one who plays Kabaddi lives on the floor immediately below R.
- P lives on a floor somewhere above the one who plays Tennis.
- The one who plays Cricket lives three floors above V.
- T lives four floors above the one who plays Badminton.
- S lives on an even-numbered floor.

Who lives two floors below the one who plays Volleyball?

- **A.** U  _(error: counted one place short)_
- **B.** T  _(error: direction reversed (above instead of below))_
- **C.** P  _(error: counted one place too far)_
- **D.** V ✅

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 sport assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only four persons live between T and P, and T lives above P.' and 'Only two persons live between T and U.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – Q (Tennis); Floor 2 – P (Chess); Floor 3 – V (Badminton); Floor 4 – U (Kabaddi); Floor 5 – R (Volleyball); Floor 6 – S (Cricket); Floor 7 – T (Football).
4. The one who plays Volleyball is at Floor 5; the person asked for is at Floor 3, i.e. V.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-089 · L4 · hard · Floor puzzle · officer

Seven persons – P, Q, R, S, T, U and V – live on the seven floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 7. Each of them plays a different game among Badminton, Chess, Cricket, Football, Kabaddi, Tennis and Volleyball.

- Only four persons live between T and P, and T lives above P.
- Only four persons live between the one who plays Chess and T.
- The one who plays Volleyball lives two floors below T.
- Only two persons live between T and U.
- The one who plays Kabaddi lives on the floor immediately below R.
- P lives on a floor somewhere above the one who plays Tennis.
- The one who plays Cricket lives three floors above V.
- T lives four floors above the one who plays Badminton.
- S lives on an even-numbered floor.

Who plays Kabaddi?

- **A.** R  _(error: neighbour of the correct person)_
- **B.** V  _(error: neighbour of the correct person)_
- **C.** U ✅
- **D.** Q  _(error: no clue links this person to that attribute)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 sport assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only four persons live between T and P, and T lives above P.' and 'Only two persons live between T and U.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – Q (Tennis); Floor 2 – P (Chess); Floor 3 – V (Badminton); Floor 4 – U (Kabaddi); Floor 5 – R (Volleyball); Floor 6 – S (Cricket); Floor 7 – T (Football).
4. U plays Kabaddi.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Attribute clues often name the attribute, not the person; resolve them only after positions are fixed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-090 · L4 · hard · Floor puzzle · officer

Seven persons – P, Q, R, S, T, U and V – live on the seven floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 7. Each of them plays a different game among Badminton, Chess, Cricket, Football, Kabaddi, Tennis and Volleyball.

- Only four persons live between T and P, and T lives above P.
- Only four persons live between the one who plays Chess and T.
- The one who plays Volleyball lives two floors below T.
- Only two persons live between T and U.
- The one who plays Kabaddi lives on the floor immediately below R.
- P lives on a floor somewhere above the one who plays Tennis.
- The one who plays Cricket lives three floors above V.
- T lives four floors above the one who plays Badminton.
- S lives on an even-numbered floor.

Which of the following statements is NOT true?

- **A.** P lives three floors below R.  _(error: this statement is true in the solved arrangement)_
- **B.** S lives four floors above P.  _(error: this statement is true in the solved arrangement)_
- **C.** V lives four floors above T. ✅
- **D.** U lives three floors above Q.  _(error: this statement is true in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 sport assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only four persons live between T and P, and T lives above P.' and 'Only two persons live between T and U.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – Q (Tennis); Floor 2 – P (Chess); Floor 3 – V (Badminton); Floor 4 – U (Kabaddi); Floor 5 – R (Volleyball); Floor 6 – S (Cricket); Floor 7 – T (Football).
4. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-091 · L1 · easy · Floor and flat double-variable puzzle · foundation

Four persons – J, K, L and M – live in a two-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 2. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B.

- L lives on the lowermost floor.
- L and M live on the same floor.
- M lives in Flat B.
- K lives in Flat A.

Which of the following statements is true?

- **A.** J and L live on the same floor.  _(error: false in the solved arrangement)_
- **B.** K lives directly above L. ✅
- **C.** L lives on the topmost floor.  _(error: false in the solved arrangement)_
- **D.** L lives directly above M.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 24 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L and M live on the same floor.' and 'K lives in Flat A.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 2: A – K, B – J; floor 1: A – L, B – M.
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-092 · L2 · medium · Floor and flat double-variable puzzle · foundation

Six persons – A, B, C, D, E and F – live in a three-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 3. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B.

- D and E live on the same floor.
- B lives two floors above F.
- B lives in Flat A.
- C lives to the east of F on the same floor.
- B and E live in the same type of flat.

Who lives directly above C?

- **A.** D ✅
- **B.** A  _(error: not directly above)_
- **C.** E  _(error: same floor as the flat above, but the other type (diagonal))_
- **D.** F  _(error: neighbour on the same floor)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 5 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'C lives to the east of F on the same floor.' and 'B lives two floors above F.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 3: A – B, B – A; floor 2: A – E, B – D; floor 1: A – F, B – C.
4. C is in Flat B, floor 1; directly above is Flat B, floor 2 – D.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Directly above/below' keeps the same flat type (A over A, B over B).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-093 · L2 · medium · Floor and flat double-variable puzzle · foundation

Six persons – S, T, U, V, W and X – live in a three-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 3. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B.

- T and X live in the same type of flat.
- T lives directly above W.
- V lives on the lowermost floor.
- W lives in Flat B.
- S and X live on the same floor.

In which flat does W live?

- **A.** Flat B, floor 2  _(error: one floor too high)_
- **B.** Flat B, floor 1 ✅
- **C.** Flat A, floor 2  _(error: diagonal flat)_
- **D.** Flat A, floor 1  _(error: right floor, wrong flat type)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 5 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'T lives directly above W.' and 'S and X live on the same floor.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 3: A – S, B – X; floor 2: A – U, B – T; floor 1: A – V, B – W.
4. W – Flat B, floor 1.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Fix both variables — floor and flat type.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-094 · L2 · medium · Floor and flat double-variable puzzle · foundation

Six persons – S, T, U, V, W and X – live in a three-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 3. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B.

- V lives on a higher floor than X.
- S lives on a higher floor than W.
- W lives in Flat A.
- S lives in Flat A.
- T lives on the lowermost floor.
- T and V live on adjacent floors but in different types of flat.

Who lives on the same floor as W?

- **A.** S  _(error: lives directly above instead)_
- **B.** U  _(error: lives on another floor)_
- **C.** T  _(error: lives directly below instead)_
- **D.** V ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 6 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'T and V live on adjacent floors but in different types of flat.' and 'T lives on the lowermost floor.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 3: A – S, B – U; floor 2: A – W, B – V; floor 1: A – T, B – X.
4. W is in Flat A, floor 2; the other flat on that floor is V's.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Same floor ≠ same flat type.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-095 · L2 · medium · Floor and flat double-variable puzzle · foundation

Six persons – A, B, C, D, E and F – live in a three-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 3. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B.

- B lives directly above D.
- E lives directly above F.
- C lives in Flat A.
- A lives on a higher floor than D.
- D lives on an even-numbered floor.

How many persons live on floors above the floor of E?

- **A.** Two ✅
- **B.** Three  _(error: counted the other flat on the same floor)_
- **C.** Four  _(error: counted one floor extra)_
- **D.** One  _(error: counted floors, not persons)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 5 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'B lives directly above D.' and 'E lives directly above F.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 3: A – B, B – A; floor 2: A – D, B – E; floor 1: A – C, B – F.
4. E is on floor 2; 1 floor(s) above × 2 flats = 2.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Each floor holds two persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-096 · L3 · hard · Floor and flat double-variable puzzle · officer

Eight persons – D, E, F, G, H, J, K and L – live in a four-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 4. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B.

- E lives directly above D.
- G lives in Flat A.
- J lives directly above K.
- H lives in Flat A.
- H and K live on adjacent floors but in different types of flat.
- D lives directly above H.
- F lives three floors above H.

Who lives directly above L?

- **A.** E  _(error: not directly above)_
- **B.** H  _(error: neighbour on the same floor)_
- **C.** D  _(error: same floor as the flat above, but the other type (diagonal))_
- **D.** K ✅

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'F lives three floors above H.' and 'D lives directly above H.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 4: A – G, B – F; floor 3: A – E, B – J; floor 2: A – D, B – K; floor 1: A – H, B – L.
4. L is in Flat B, floor 1; directly above is Flat B, floor 2 – K.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Directly above/below' keeps the same flat type (A over A, B over B).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-097 · L3 · hard · Floor and flat double-variable puzzle · officer

Six persons – E, F, G, H, J and K – live in a three-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 3. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B. Each of them owns a car of a different colour among blue, green, grey, red, silver and white.

- H lives on the topmost floor.
- The owner of the silver car and J live on the same floor.
- K does not own the green car.
- K does not own the silver car.
- H lives in Flat B.
- H owns the red car.
- E lives in Flat B.
- The owner of the blue car lives on the lowermost floor.
- The owner of the white car lives to the east of the owner of the grey car on the same floor.
- G and the owner of the white car live on the same floor.

What is the colour of the car owned by K?

- **A.** silver  _(error: attribute of E, a neighbour of K)_
- **B.** white ✅
- **C.** grey  _(error: attribute of G, a neighbour of K)_
- **D.** red  _(error: attribute of H, a neighbour of K)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 car assignments leaves exactly one arrangement that satisfies all 10 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'H lives on the topmost floor.' and 'E lives in Flat B.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 3: A – F (green), B – H (red); floor 2: A – G (grey), B – K (white); floor 1: A – J (blue), B – E (silver).
4. K owns the white car in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-098 · L4 · hard · Floor and flat double-variable puzzle · officer

Eight persons – K, L, M, N, P, Q, R and S – live in a four-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 4. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- L and P do not live on the same floor.
- L lives on a higher floor than R.
- M does not work in IT.
- The one who works in IT lives on an odd-numbered floor.
- The one who works in Marketing and S live on the same floor.
- The one who works in Legal lives in Flat B of floor 2.
- P lives in Flat A.
- The one who works in HR lives directly above S.
- S lives directly above P.
- N does not work in Admin.
- K lives on an even-numbered floor.
- P works in Audit.
- M does not work in Finance.
- Q lives directly above L.
- The one who works in Admin lives to the east of M on the same floor.
- K lives in Flat A.

Who lives directly above R?

- **A.** N ✅
- **B.** K  _(error: not directly above)_
- **C.** P  _(error: same floor as the flat above, but the other type (diagonal))_
- **D.** M  _(error: neighbour on the same floor)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 16 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Q lives directly above L.' and 'S lives directly above P.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 4: A – K (HR), B – Q (Finance); floor 3: A – S (IT), B – L (Marketing); floor 2: A – P (Audit), B – N (Legal); floor 1: A – M (Sales), B – R (Admin).
4. R is in Flat B, floor 1; directly above is Flat B, floor 2 – N.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Directly above/below' keeps the same flat type (A over A, B over B).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-099 · L4 · hard · Floor and flat double-variable puzzle · officer

Eight persons – K, L, M, N, P, Q, R and S – live in a four-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 4. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- L and P do not live on the same floor.
- L lives on a higher floor than R.
- M does not work in IT.
- The one who works in IT lives on an odd-numbered floor.
- The one who works in Marketing and S live on the same floor.
- The one who works in Legal lives in Flat B of floor 2.
- P lives in Flat A.
- The one who works in HR lives directly above S.
- S lives directly above P.
- N does not work in Admin.
- K lives on an even-numbered floor.
- P works in Audit.
- M does not work in Finance.
- Q lives directly above L.
- The one who works in Admin lives to the east of M on the same floor.
- K lives in Flat A.

In which flat does M live?

- **A.** Flat A, floor 1 ✅
- **B.** Flat A, floor 2  _(error: one floor too high)_
- **C.** Flat B, floor 2  _(error: diagonal flat)_
- **D.** Flat B, floor 1  _(error: right floor, wrong flat type)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 16 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Q lives directly above L.' and 'S lives directly above P.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 4: A – K (HR), B – Q (Finance); floor 3: A – S (IT), B – L (Marketing); floor 2: A – P (Audit), B – N (Legal); floor 1: A – M (Sales), B – R (Admin).
4. M – Flat A, floor 1.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Fix both variables — floor and flat type.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-100 · L4 · hard · Floor and flat double-variable puzzle · officer

Eight persons – K, L, M, N, P, Q, R and S – live in a four-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 4. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- L and P do not live on the same floor.
- L lives on a higher floor than R.
- M does not work in IT.
- The one who works in IT lives on an odd-numbered floor.
- The one who works in Marketing and S live on the same floor.
- The one who works in Legal lives in Flat B of floor 2.
- P lives in Flat A.
- The one who works in HR lives directly above S.
- S lives directly above P.
- N does not work in Admin.
- K lives on an even-numbered floor.
- P works in Audit.
- M does not work in Finance.
- Q lives directly above L.
- The one who works in Admin lives to the east of M on the same floor.
- K lives in Flat A.

In which department does K work?

- **A.** Finance  _(error: attribute of Q, a neighbour of K)_
- **B.** HR ✅
- **C.** Legal  _(error: attribute of N)_
- **D.** IT  _(error: attribute of S, a neighbour of K)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 16 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Q lives directly above L.' and 'S lives directly above P.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 4: A – K (HR), B – Q (Finance); floor 3: A – S (IT), B – L (Marketing); floor 2: A – P (Audit), B – N (Legal); floor 1: A – M (Sales), B – R (Admin).
4. K works in HR in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-101 · L4 · hard · Floor and flat double-variable puzzle · officer

Eight persons – K, L, M, N, P, Q, R and S – live in a four-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 4. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- L and P do not live on the same floor.
- L lives on a higher floor than R.
- M does not work in IT.
- The one who works in IT lives on an odd-numbered floor.
- The one who works in Marketing and S live on the same floor.
- The one who works in Legal lives in Flat B of floor 2.
- P lives in Flat A.
- The one who works in HR lives directly above S.
- S lives directly above P.
- N does not work in Admin.
- K lives on an even-numbered floor.
- P works in Audit.
- M does not work in Finance.
- Q lives directly above L.
- The one who works in Admin lives to the east of M on the same floor.
- K lives in Flat A.

Who lives on the same floor as N?

- **A.** R  _(error: lives directly below instead)_
- **B.** K  _(error: lives on another floor)_
- **C.** P ✅
- **D.** L  _(error: lives directly above instead)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 16 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Q lives directly above L.' and 'S lives directly above P.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 4: A – K (HR), B – Q (Finance); floor 3: A – S (IT), B – L (Marketing); floor 2: A – P (Audit), B – N (Legal); floor 1: A – M (Sales), B – R (Admin).
4. N is in Flat B, floor 2; the other flat on that floor is P's.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Same floor ≠ same flat type.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-102 · L4 · hard · Floor and flat double-variable puzzle · officer

Eight persons – K, L, M, N, P, Q, R and S – live in a four-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 4. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- L and P do not live on the same floor.
- L lives on a higher floor than R.
- M does not work in IT.
- The one who works in IT lives on an odd-numbered floor.
- The one who works in Marketing and S live on the same floor.
- The one who works in Legal lives in Flat B of floor 2.
- P lives in Flat A.
- The one who works in HR lives directly above S.
- S lives directly above P.
- N does not work in Admin.
- K lives on an even-numbered floor.
- P works in Audit.
- M does not work in Finance.
- Q lives directly above L.
- The one who works in Admin lives to the east of M on the same floor.
- K lives in Flat A.

Which of the following statements is true?

- **A.** The one who works in Finance lives on the topmost floor. ✅
- **B.** The one who works in Sales lives on a higher floor than R.  _(error: false in the solved arrangement)_
- **C.** The one who works in Audit lives on the topmost floor.  _(error: false in the solved arrangement)_
- **D.** N lives on a higher floor than the one who works in Audit.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 16 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Q lives directly above L.' and 'S lives directly above P.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 4: A – K (HR), B – Q (Finance); floor 3: A – S (IT), B – L (Marketing); floor 2: A – P (Audit), B – N (Legal); floor 1: A – M (Sales), B – R (Admin).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-103 · L4 · hard · Floor and flat double-variable puzzle · officer

Six persons – K, L, M, N, P and Q – live in a three-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 3. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Kochi and Patna.

- L is not from Agra.
- L and the one from Kochi live in the same type of flat.
- The one from Delhi lives directly above M.
- The one from Chennai lives in Flat A.
- L and P live on the same floor.
- The one from Chennai lives on an even-numbered floor.
- M and Q live on adjacent floors but in different types of flat.
- The one from Delhi and the one from Bhopal live on the same floor.
- Q lives on a higher floor than K.
- M is not from Chennai.

Who is from Kochi?

- **A.** K  _(error: neighbour of the correct person)_
- **B.** N  _(error: neighbour of the correct person)_
- **C.** M ✅
- **D.** L  _(error: neighbour of the correct person)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 city assignments leaves exactly one arrangement that satisfies all 10 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L and P live on the same floor.' and 'M and Q live on adjacent floors but in different types of flat.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 3: A – Q (Bhopal), B – N (Delhi); floor 2: A – K (Chennai), B – M (Kochi); floor 1: A – P (Agra), B – L (Patna).
4. M is from Kochi.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Attribute clues often name the attribute, not the person; resolve them only after positions are fixed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-104 · L4 · hard · Floor and flat double-variable puzzle · officer

Six persons – K, L, M, N, P and Q – live in a three-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 3. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Kochi and Patna.

- L is not from Agra.
- L and the one from Kochi live in the same type of flat.
- The one from Delhi lives directly above M.
- The one from Chennai lives in Flat A.
- L and P live on the same floor.
- The one from Chennai lives on an even-numbered floor.
- M and Q live on adjacent floors but in different types of flat.
- The one from Delhi and the one from Bhopal live on the same floor.
- Q lives on a higher floor than K.
- M is not from Chennai.

How many persons live on floors above the floor of K?

- **A.** Two ✅
- **B.** Three  _(error: counted the other flat on the same floor)_
- **C.** Four  _(error: counted one floor extra)_
- **D.** One  _(error: counted floors, not persons)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 city assignments leaves exactly one arrangement that satisfies all 10 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L and P live on the same floor.' and 'M and Q live on adjacent floors but in different types of flat.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 3: A – Q (Bhopal), B – N (Delhi); floor 2: A – K (Chennai), B – M (Kochi); floor 1: A – P (Agra), B – L (Patna).
4. K is on floor 2; 1 floor(s) above × 2 flats = 2.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Each floor holds two persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-105 · L4 · hard · Floor and flat double-variable puzzle · officer

Six persons – K, L, M, N, P and Q – live in a three-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 3. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Kochi and Patna.

- L is not from Agra.
- L and the one from Kochi live in the same type of flat.
- The one from Delhi lives directly above M.
- The one from Chennai lives in Flat A.
- L and P live on the same floor.
- The one from Chennai lives on an even-numbered floor.
- M and Q live on adjacent floors but in different types of flat.
- The one from Delhi and the one from Bhopal live on the same floor.
- Q lives on a higher floor than K.
- M is not from Chennai.

Which of the following statements is NOT true?

- **A.** L and Q live on adjacent floors but in different types of flat. ✅
- **B.** The one from Chennai and P live in the same type of flat.  _(error: this statement is true in the solved arrangement)_
- **C.** The one from Patna and the one from Kochi live in the same type of flat.  _(error: this statement is true in the solved arrangement)_
- **D.** The one from Kochi and Q do not live on the same floor.  _(error: this statement is true in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 city assignments leaves exactly one arrangement that satisfies all 10 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'L and P live on the same floor.' and 'M and Q live on adjacent floors but in different types of flat.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 3: A – Q (Bhopal), B – N (Delhi); floor 2: A – K (Chennai), B – M (Kochi); floor 1: A – P (Agra), B – L (Patna).
4. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-106 · L1 · easy · Box and stack puzzle · foundation

Five boxes – P, Q, R, S and T – are placed one above another in a single stack. Position 1 is at the bottom and position 5 is at the top.

- Box Q is placed immediately below box S.
- Box P is placed immediately below box Q.
- Only three boxes are placed between box T and box R, and box T is above box R.

Which box is placed third from the bottom?

- **A.** Q ✅
- **B.** R  _(error: not at that position)_
- **C.** P  _(error: off by one position)_
- **D.** S  _(error: off by one position)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only three boxes are placed between box T and box R, and box T is above box R.' and 'Box P is placed immediately below box Q.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – R; 2nd from the bottom – P; 3rd from the bottom – Q; 4th from the bottom – S; 5th from the bottom – T.
4. 3rd from the bottom is occupied by Q.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Check which end the count starts from.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-107 · L1 · easy · Box and stack puzzle · foundation

Five boxes – A, B, C, D and E – are placed one above another in a single stack. Position 1 is at the bottom and position 5 is at the top.

- Box B is not placed adjacent to box C.
- Box C is placed immediately above box E.
- Only one box is placed between box C and box D, and box C is above box D.
- The number of boxes above box A is the same as the number of boxes below box B.

Which box is placed immediately above box D?

- **A.** B  _(error: direction reversed (below instead of above))_
- **B.** E ✅
- **C.** C  _(error: counted one place too far)_
- **D.** A  _(error: not at the required position)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one box is placed between box C and box D, and box C is above box D.' and 'Box C is placed immediately above box E.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – B; 2nd from the bottom – D; 3rd from the bottom – E; 4th from the bottom – C; 5th from the bottom – A.
4. Box D is at 2nd from the bottom; the person asked for is at 3rd from the bottom, i.e. E.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-108 · L2 · medium · Box and stack puzzle · foundation

Six boxes – A, B, C, D, E and F – are placed one above another in a single stack. Position 1 is at the bottom and position 6 is at the top.

- The number of boxes above box A is the same as the number of boxes below box B.
- The number of boxes above box D is the same as the number of boxes below box E.
- Box C is placed somewhere above box A.
- Box D and box F are placed one directly on the other.
- Only three boxes are placed between box B and box C.

How many boxes are placed between box A and box D?

- **A.** One  _(error: counted one short)_
- **B.** Two ✅
- **C.** Four  _(error: counted both named persons)_
- **D.** Three  _(error: counted one of the two named persons)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 5 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only three boxes are placed between box B and box C.' and 'The number of boxes above box A is the same as the number of boxes below box B.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – A; 2nd from the bottom – C; 3rd from the bottom – E; 4th from the bottom – D; 5th from the bottom – F; 6th from the bottom – B.
4. Box A is at 1st from the bottom and box D at 4th from the bottom; 2 position(s) lie strictly between them.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Between' excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-109 · L2 · medium · Box and stack puzzle · foundation

Six boxes – M, N, P, Q, R and S – are placed one above another in a single stack. Position 1 is at the bottom and position 6 is at the top.

- Box M is placed neither at the top nor at the bottom.
- Only two boxes are placed between box N and box R.
- Only one box is placed between box P and box S.
- Box Q is placed immediately below box N.
- Box P is placed immediately above box R.

How many boxes are placed above box R?

- **A.** One ✅
- **B.** None  _(error: missed the extreme position)_
- **C.** Two  _(error: included the person named)_
- **D.** Four  _(error: counted below instead of above)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 5 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Box P is placed immediately above box R.' and 'Box Q is placed immediately below box N.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – Q; 2nd from the bottom – N; 3rd from the bottom – M; 4th from the bottom – S; 5th from the bottom – R; 6th from the bottom – P.
4. Box R is at 5th from the bottom; 1 position(s) lie beyond it in that direction.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Count only the persons beyond the one named, in the stated direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-110 · L2 · medium · Box and stack puzzle · foundation

Six boxes – S, T, U, V, W and X – are placed one above another in a single stack. Position 1 is at the bottom and position 6 is at the top.

- Box U is placed immediately above box W.
- Box W and box X are placed one directly on the other.
- Box X is placed immediately above box T.
- Only four boxes are placed between box S and box T.

At which position from the bottom is box S placed?

- **A.** 5th from the bottom  _(error: off by one position)_
- **B.** 6th from the bottom ✅
- **C.** 4th from the bottom  _(error: off by two positions)_
- **D.** 1st from the bottom  _(error: counted from the opposite end)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only four boxes are placed between box S and box T.' and 'Box U is placed immediately above box W.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – T; 2nd from the bottom – X; 3rd from the bottom – W; 4th from the bottom – U; 5th from the bottom – V; 6th from the bottom – S.
4. Box S is at 6th from the bottom.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-111 · L3 · hard · Box and stack puzzle · officer

Seven boxes – D, E, F, G, H, J and K – are placed one above another in a single stack. Position 1 is at the bottom and position 7 is at the top.

- Only two boxes are placed between box K and box F, and box K is above box F.
- The number of boxes above box E is the same as the number of boxes below box F.
- Box H is placed somewhere above box J.
- Box J is placed neither at the top nor at the bottom.
- The number of boxes above box J is the same as the number of boxes below box D.
- Box G is placed immediately below box K.

Which of the following statements is true?

- **A.** The number of boxes above box G is the same as the number of boxes below box J.  _(error: false in the solved arrangement)_
- **B.** Only two boxes are placed between box F and box G, and box F is above box G.  _(error: false in the solved arrangement)_
- **C.** Only three boxes are placed between box K and box J, and box K is above box J.  _(error: false in the solved arrangement)_
- **D.** Only two boxes are placed between box E and box K, and box E is above box K. ✅

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders leaves exactly one arrangement that satisfies all 6 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only two boxes are placed between box K and box F, and box K is above box F.' and 'Box G is placed immediately below box K.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – F; 2nd from the bottom – J; 3rd from the bottom – G; 4th from the bottom – K; 5th from the bottom – H; 6th from the bottom – D; 7th from the bottom – E.
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-112 · L3 · hard · Box and stack puzzle · officer

Six boxes – D, E, F, G, H and J – are placed one above another in a single stack. Position 1 is at the bottom and position 6 is at the top. Each box is of a different colour among black, green, orange, pink, red and yellow.

- The green box and box H are placed one directly on the other.
- Box E is placed immediately below box D.
- The number of boxes above box D is the same as the number of boxes below the red box.
- The number of boxes above the black box is the same as the number of boxes below the orange box.
- Box D is not pink.
- Box J is placed immediately below box H.
- The black box is placed immediately below the orange box.
- Only three boxes are placed between box F and box D, and box F is above box D.

Which box is placed immediately above the pink box?

- **A.** D ✅
- **B.** H  _(error: not at the required position)_
- **C.** F  _(error: not at the required position)_
- **D.** G  _(error: counted one place too far)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 boxcol assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only three boxes are placed between box F and box D, and box F is above box D.' and 'Box E is placed immediately below box D.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – E (pink); 2nd from the bottom – D (yellow); 3rd from the bottom – G (black); 4th from the bottom – J (orange); 5th from the bottom – H (red); 6th from the bottom – F (green).
4. The pink box is at 1st from the bottom; the person asked for is at 2nd from the bottom, i.e. D.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-113 · L4 · hard · Box and stack puzzle · officer

Eight boxes – A, B, C, D, E, F, G and H – are placed one above another in a single stack. Position 1 is at the bottom and position 8 is at the top. Each box is of a different colour among black, blue, green, orange, pink, red, white and yellow.

- Only one box is placed between box B and box C.
- Only two boxes are placed between box C and box H.
- The yellow box is placed at an odd-numbered position.
- Box D is not black.
- The number of boxes above the white box is the same as the number of boxes below the green box.
- Only three boxes are placed between the orange box and box C.
- Box B is placed somewhere above box E.
- Box D is placed immediately below box G.
- The green box is placed immediately below box B.
- Only one box is placed between the pink box and the red box, and the pink box is above the red box.
- The number of boxes above box D is the same as the number of boxes below box H.
- Only six boxes are placed between box A and box E.

Which box is placed immediately below box G?

- **A.** C  _(error: direction reversed (above instead of below))_
- **B.** D ✅
- **C.** E  _(error: counted one place too far)_
- **D.** A  _(error: not at the required position)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 boxcol assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only six boxes are placed between box A and box E.' and 'Box D is placed immediately below box G.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – E (red); 2nd from the bottom – D (blue); 3rd from the bottom – G (pink); 4th from the bottom – C (white); 5th from the bottom – F (green); 6th from the bottom – B (black); 7th from the bottom – H (yellow); 8th from the bottom – A (orange).
4. Box G is at 3rd from the bottom; the person asked for is at 2nd from the bottom, i.e. D.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-114 · L4 · hard · Box and stack puzzle · officer

Eight boxes – A, B, C, D, E, F, G and H – are placed one above another in a single stack. Position 1 is at the bottom and position 8 is at the top. Each box is of a different colour among black, blue, green, orange, pink, red, white and yellow.

- Only one box is placed between box B and box C.
- Only two boxes are placed between box C and box H.
- The yellow box is placed at an odd-numbered position.
- Box D is not black.
- The number of boxes above the white box is the same as the number of boxes below the green box.
- Only three boxes are placed between the orange box and box C.
- Box B is placed somewhere above box E.
- Box D is placed immediately below box G.
- The green box is placed immediately below box B.
- Only one box is placed between the pink box and the red box, and the pink box is above the red box.
- The number of boxes above box D is the same as the number of boxes below box H.
- Only six boxes are placed between box A and box E.

What is the colour of box H?

- **A.** yellow ✅
- **B.** red  _(error: attribute of E)_
- **C.** orange  _(error: attribute of A, a neighbour of H)_
- **D.** black  _(error: attribute of B, a neighbour of H)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 boxcol assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only six boxes are placed between box A and box E.' and 'Box D is placed immediately below box G.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – E (red); 2nd from the bottom – D (blue); 3rd from the bottom – G (pink); 4th from the bottom – C (white); 5th from the bottom – F (green); 6th from the bottom – B (black); 7th from the bottom – H (yellow); 8th from the bottom – A (orange).
4. Box H is yellow in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-115 · L4 · hard · Box and stack puzzle · officer

Eight boxes – A, B, C, D, E, F, G and H – are placed one above another in a single stack. Position 1 is at the bottom and position 8 is at the top. Each box is of a different colour among black, blue, green, orange, pink, red, white and yellow.

- Only one box is placed between box B and box C.
- Only two boxes are placed between box C and box H.
- The yellow box is placed at an odd-numbered position.
- Box D is not black.
- The number of boxes above the white box is the same as the number of boxes below the green box.
- Only three boxes are placed between the orange box and box C.
- Box B is placed somewhere above box E.
- Box D is placed immediately below box G.
- The green box is placed immediately below box B.
- Only one box is placed between the pink box and the red box, and the pink box is above the red box.
- The number of boxes above box D is the same as the number of boxes below box H.
- Only six boxes are placed between box A and box E.

How many boxes are placed between box C and box D?

- **A.** One ✅
- **B.** Three  _(error: counted both named persons)_
- **C.** Four  _(error: counted from the wrong end)_
- **D.** Two  _(error: counted one of the two named persons)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 boxcol assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only six boxes are placed between box A and box E.' and 'Box D is placed immediately below box G.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – E (red); 2nd from the bottom – D (blue); 3rd from the bottom – G (pink); 4th from the bottom – C (white); 5th from the bottom – F (green); 6th from the bottom – B (black); 7th from the bottom – H (yellow); 8th from the bottom – A (orange).
4. Box C is at 4th from the bottom and box D at 2nd from the bottom; 1 position(s) lie strictly between them.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Between' excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-116 · L4 · hard · Box and stack puzzle · officer

Eight boxes – A, B, C, D, E, F, G and H – are placed one above another in a single stack. Position 1 is at the bottom and position 8 is at the top. Each box is of a different colour among black, blue, green, orange, pink, red, white and yellow.

- Only one box is placed between box B and box C.
- Only two boxes are placed between box C and box H.
- The yellow box is placed at an odd-numbered position.
- Box D is not black.
- The number of boxes above the white box is the same as the number of boxes below the green box.
- Only three boxes are placed between the orange box and box C.
- Box B is placed somewhere above box E.
- Box D is placed immediately below box G.
- The green box is placed immediately below box B.
- Only one box is placed between the pink box and the red box, and the pink box is above the red box.
- The number of boxes above box D is the same as the number of boxes below box H.
- Only six boxes are placed between box A and box E.

Which of the following statements is true?

- **A.** The black box is not placed adjacent to the yellow box.  _(error: false in the solved arrangement)_
- **B.** Only one box is placed between box B and the green box.  _(error: false in the solved arrangement)_
- **C.** The white box is placed at an even-numbered position. ✅
- **D.** The green box is placed at an even-numbered position.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 boxcol assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only six boxes are placed between box A and box E.' and 'Box D is placed immediately below box G.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – E (red); 2nd from the bottom – D (blue); 3rd from the bottom – G (pink); 4th from the bottom – C (white); 5th from the bottom – F (green); 6th from the bottom – B (black); 7th from the bottom – H (yellow); 8th from the bottom – A (orange).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-117 · L4 · hard · Box and stack puzzle · officer

Eight boxes – A, B, C, D, E, F, G and H – are placed one above another in a single stack. Position 1 is at the bottom and position 8 is at the top. Each box is of a different colour among black, blue, green, orange, pink, red, white and yellow.

- Only one box is placed between box B and box C.
- Only two boxes are placed between box C and box H.
- The yellow box is placed at an odd-numbered position.
- Box D is not black.
- The number of boxes above the white box is the same as the number of boxes below the green box.
- Only three boxes are placed between the orange box and box C.
- Box B is placed somewhere above box E.
- Box D is placed immediately below box G.
- The green box is placed immediately below box B.
- Only one box is placed between the pink box and the red box, and the pink box is above the red box.
- The number of boxes above box D is the same as the number of boxes below box H.
- Only six boxes are placed between box A and box E.

Which box is red?

- **A.** A  _(error: no clue links this person to that attribute)_
- **B.** F  _(error: no clue links this person to that attribute)_
- **C.** D  _(error: neighbour of the correct person)_
- **D.** E ✅

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 boxcol assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only six boxes are placed between box A and box E.' and 'Box D is placed immediately below box G.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – E (red); 2nd from the bottom – D (blue); 3rd from the bottom – G (pink); 4th from the bottom – C (white); 5th from the bottom – F (green); 6th from the bottom – B (black); 7th from the bottom – H (yellow); 8th from the bottom – A (orange).
4. Box E is red.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Attribute clues often name the attribute, not the person; resolve them only after positions are fixed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-118 · L4 · hard · Box and stack puzzle · officer

Seven boxes – A, B, C, D, E, F and G – are placed one above another in a single stack. Position 1 is at the bottom and position 7 is at the top. Each box contains a different item among books, clocks, cups, lamps, pens, shoes and toys.

- Box E is placed immediately above box B.
- Only three boxes are placed between box B and box F.
- Only two boxes are placed between the box containing pens and box G, and the box containing pens is above box G.
- Only one box is placed between box G and box B, and box G is above box B.
- Only two boxes are placed between the box containing shoes and the box containing cups, and the box containing shoes is above the box containing cups.
- Box D is placed immediately above the box containing clocks.
- The number of boxes above box E is the same as the number of boxes below the box containing toys.
- Only four boxes are placed between box C and the box containing lamps, and box C is above the box containing lamps.

Which box is placed immediately below the box containing clocks?

- **A.** E ✅
- **B.** D  _(error: direction reversed (above instead of below))_
- **C.** A  _(error: not at the required position)_
- **D.** B  _(error: counted one place too far)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 item assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one box is placed between box G and box B, and box G is above box B.' and 'Box E is placed immediately above box B.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – A (books); 2nd from the bottom – B (lamps); 3rd from the bottom – E (cups); 4th from the bottom – G (clocks); 5th from the bottom – D (toys); 6th from the bottom – F (shoes); 7th from the bottom – C (pens).
4. The box containing clocks is at 4th from the bottom; the person asked for is at 3rd from the bottom, i.e. E.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-119 · L4 · hard · Box and stack puzzle · officer

Seven boxes – A, B, C, D, E, F and G – are placed one above another in a single stack. Position 1 is at the bottom and position 7 is at the top. Each box contains a different item among books, clocks, cups, lamps, pens, shoes and toys.

- Box E is placed immediately above box B.
- Only three boxes are placed between box B and box F.
- Only two boxes are placed between the box containing pens and box G, and the box containing pens is above box G.
- Only one box is placed between box G and box B, and box G is above box B.
- Only two boxes are placed between the box containing shoes and the box containing cups, and the box containing shoes is above the box containing cups.
- Box D is placed immediately above the box containing clocks.
- The number of boxes above box E is the same as the number of boxes below the box containing toys.
- Only four boxes are placed between box C and the box containing lamps, and box C is above the box containing lamps.

How many boxes are placed above box B?

- **A.** One  _(error: counted below instead of above)_
- **B.** Four  _(error: missed the extreme position)_
- **C.** Five ✅
- **D.** Six  _(error: included the person named)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 item assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one box is placed between box G and box B, and box G is above box B.' and 'Box E is placed immediately above box B.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – A (books); 2nd from the bottom – B (lamps); 3rd from the bottom – E (cups); 4th from the bottom – G (clocks); 5th from the bottom – D (toys); 6th from the bottom – F (shoes); 7th from the bottom – C (pens).
4. Box B is at 2nd from the bottom; 5 position(s) lie beyond it in that direction.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Count only the persons beyond the one named, in the stated direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-120 · L4 · hard · Box and stack puzzle · officer

Seven boxes – A, B, C, D, E, F and G – are placed one above another in a single stack. Position 1 is at the bottom and position 7 is at the top. Each box contains a different item among books, clocks, cups, lamps, pens, shoes and toys.

- Box E is placed immediately above box B.
- Only three boxes are placed between box B and box F.
- Only two boxes are placed between the box containing pens and box G, and the box containing pens is above box G.
- Only one box is placed between box G and box B, and box G is above box B.
- Only two boxes are placed between the box containing shoes and the box containing cups, and the box containing shoes is above the box containing cups.
- Box D is placed immediately above the box containing clocks.
- The number of boxes above box E is the same as the number of boxes below the box containing toys.
- Only four boxes are placed between box C and the box containing lamps, and box C is above the box containing lamps.

Which of the following statements is NOT true?

- **A.** The number of boxes above box G is the same as the number of boxes below box E. ✅
- **B.** Only four boxes are placed between box C and box B, and box C is above box B.  _(error: this statement is true in the solved arrangement)_
- **C.** The number of boxes above box C is the same as the number of boxes below box A.  _(error: this statement is true in the solved arrangement)_
- **D.** Only two boxes are placed between box G and box A, and box G is above box A.  _(error: this statement is true in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 item assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one box is placed between box G and box B, and box G is above box B.' and 'Box E is placed immediately above box B.'; then place the others by elimination.
3. Solved arrangement — Bottom (position 1) upwards: 1st from the bottom – A (books); 2nd from the bottom – B (lamps); 3rd from the bottom – E (cups); 4th from the bottom – G (clocks); 5th from the bottom – D (toys); 6th from the bottom – F (shoes); 7th from the bottom – C (pens).
4. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-121 · L1 · easy · Category and attribute matching puzzle · foundation

Four friends – Aman, Chitra, Dev and Harsh – are being described. Each of them likes a different fruit among Apple, Banana, Guava and Litchi. Each of them is from a different city among Agra, Indore, Kochi and Patna.

- Either Chitra or Harsh is from Patna.
- The one who likes Guava is from Kochi.
- The one who likes Banana is from Agra.
- Aman likes Litchi.
- Either Dev or Harsh likes Banana.
- Dev is from Kochi.

Which fruit does the one from Patna like?

- **A.** Banana  _(error: belongs to Harsh)_
- **B.** Guava  _(error: belongs to Dev)_
- **C.** Litchi  _(error: belongs to Aman)_
- **D.** Apple ✅

**Working**

1. Exhaustive enumeration over 1 seat/position orders × 24 fruit assignments × 24 city assignments leaves exactly one arrangement that satisfies all 6 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Aman (Litchi, Indore); Chitra (Apple, Patna); Dev (Guava, Kochi); Harsh (Banana, Agra).
3. the one from Patna is Chitra, who likes Apple.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Chain the two attributes through the person; do not pair attributes directly from one clue.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-122 · L1 · easy · Category and attribute matching puzzle · foundation

Four friends – Ekta, Gopal, Hina and Jaya – are being described. Each of them plays a different game among Badminton, Football, Hockey and Tennis. Each of them is from a different city among Bhopal, Chennai, Delhi and Patna.

- Ekta does not play Tennis.
- Hina is not from Chennai.
- The one who plays Tennis is neither from Delhi nor from Patna.
- Hina does not play Football.
- The one who plays Football is from Delhi.
- Jaya does not play Tennis.
- Jaya is from Bhopal.
- The one who plays Badminton is not from Patna.

Which game does Gopal play?

- **A.** Badminton  _(error: attribute of Jaya)_
- **B.** Football  _(error: attribute of Ekta)_
- **C.** Tennis ✅
- **D.** Hockey  _(error: attribute of Hina)_

**Working**

1. Exhaustive enumeration over 1 seat/position orders × 24 sport assignments × 24 city assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Ekta (Football, Delhi); Gopal (Tennis, Chennai); Hina (Hockey, Patna); Jaya (Badminton, Bhopal).
3. Gopal plays Tennis in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-123 · L2 · medium · Category and attribute matching puzzle · foundation

Five friends – Ekta, Firoz, Gopal, Hina and Karan – are being described. Each of them likes a different fruit among Guava, Litchi, Mango, Orange and Papaya. Each of them is from a different city among Agra, Bhopal, Jaipur, Kochi and Patna.

- The one who likes Guava is neither from Jaipur nor from Agra.
- Either Karan or Firoz likes Papaya.
- Either Firoz or Ekta likes Orange.
- The one who likes Orange is neither from Jaipur nor from Bhopal.
- Either Ekta or Hina likes Mango.
- Either Karan or Ekta likes Litchi.
- Gopal is not from Kochi.
- The one who likes Litchi is from Agra.
- The one who likes Papaya is from Bhopal.
- Either Karan or Firoz is from Agra.

Which city is the one who likes Mango from?

- **A.** Kochi  _(error: belongs to Ekta)_
- **B.** Jaipur ✅
- **C.** Bhopal  _(error: belongs to Firoz)_
- **D.** Patna  _(error: belongs to Gopal)_

**Working**

1. Exhaustive enumeration over 1 seat/position orders × 120 fruit assignments × 120 city assignments leaves exactly one arrangement that satisfies all 10 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Ekta (Orange, Kochi); Firoz (Papaya, Bhopal); Gopal (Guava, Patna); Hina (Mango, Jaipur); Karan (Litchi, Agra).
3. the one who likes Mango is Hina, who is from Jaipur.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Chain the two attributes through the person; do not pair attributes directly from one clue.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-124 · L2 · medium · Category and attribute matching puzzle · foundation

Five friends – Aman, Chitra, Dev, Gauri and Harsh – are being described. Each of them plays a different game among Badminton, Chess, Hockey, Kabaddi and Tennis. Each of them works in a different department among Admin, Audit, Finance, HR and Legal.

- Either Gauri or Dev works in Audit.
- Either Dev or Chitra works in Finance.
- The one who plays Badminton does not work in Legal and does not work in Finance.
- Aman does not work in HR.
- The one who plays Tennis does not work in Legal.
- The one who plays Chess does not work in Admin and does not work in Finance.
- Harsh does not work in Admin.
- Either Harsh or Gauri works in Admin.
- The one who plays Tennis does not work in Finance and does not work in Audit.
- The one who plays Hockey works in Admin.

Who works in HR?

- **A.** Dev  _(error: no clue links this person to that attribute)_
- **B.** Aman  _(error: no clue links this person to that attribute)_
- **C.** Harsh ✅
- **D.** Chitra  _(error: no clue links this person to that attribute)_

**Working**

1. Exhaustive enumeration over 1 seat/position orders × 120 sport assignments × 120 dept assignments leaves exactly one arrangement that satisfies all 10 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Aman (Chess, Legal); Chitra (Kabaddi, Finance); Dev (Badminton, Audit); Gauri (Hockey, Admin); Harsh (Tennis, HR).
3. Harsh works in HR.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Attribute clues often name the attribute, not the person; resolve them only after positions are fixed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-125 · L2 · medium · Category and attribute matching puzzle · foundation

Five friends – Ekta, Firoz, Gopal, Jaya and Karan – are being described. Each of them teaches a different subject among Botany, Chemistry, Civics, Geography and Physics. Each of them is from a different city among Chennai, Indore, Jaipur, Kochi and Patna.

- Ekta is not from Chennai.
- Either Karan or Gopal teaches Chemistry.
- Ekta does not teach Botany.
- Either Firoz or Ekta is from Indore.
- Either Firoz or Ekta is from Chennai.
- Ekta does not teach Geography.
- The one who teaches Physics is from Kochi.
- Firoz does not teach Botany.
- The one who teaches Botany is neither from Jaipur nor from Kochi.
- Either Firoz or Karan is from Patna.

Which subject does the one from Chennai teach?

- **A.** Geography ✅
- **B.** Physics  _(error: belongs to Jaya)_
- **C.** Chemistry  _(error: belongs to Gopal)_
- **D.** Civics  _(error: belongs to Ekta)_

**Working**

1. Exhaustive enumeration over 1 seat/position orders × 120 subject assignments × 120 city assignments leaves exactly one arrangement that satisfies all 10 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Ekta (Civics, Indore); Firoz (Geography, Chennai); Gopal (Chemistry, Jaipur); Jaya (Physics, Kochi); Karan (Botany, Patna).
3. the one from Chennai is Firoz, who teaches Geography.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Chain the two attributes through the person; do not pair attributes directly from one clue.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-126 · L3 · hard · Category and attribute matching puzzle · officer

Six friends – Ekta, Firoz, Gopal, Hina, Jaya and Karan – are being described. Each of them likes a different fruit among Apple, Cherry, Guava, Litchi, Mango and Orange. Each of them is from a different city among Agra, Bhopal, Delhi, Jaipur, Kochi and Patna.

- The one who likes Orange is from Bhopal.
- Either Ekta or Karan is from Delhi.
- Either Karan or Jaya likes Orange.
- Ekta is not from Delhi.
- The one who likes Litchi is from Jaipur.
- The one who likes Apple is from Delhi.
- Either Ekta or Jaya likes Mango.
- Either Firoz or Ekta is from Patna.
- The one who likes Cherry is from Patna.
- Either Karan or Hina is from Agra.

Which fruit does the one from Bhopal like?

- **A.** Orange ✅
- **B.** Guava  _(error: belongs to Hina)_
- **C.** Apple  _(error: belongs to Karan)_
- **D.** Mango  _(error: belongs to Ekta)_

**Working**

1. Exhaustive enumeration over 1 seat/position orders × 720 fruit assignments × 720 city assignments leaves exactly one arrangement that satisfies all 10 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Ekta (Mango, Kochi); Firoz (Cherry, Patna); Gopal (Litchi, Jaipur); Hina (Guava, Agra); Jaya (Orange, Bhopal); Karan (Apple, Delhi).
3. the one from Bhopal is Jaya, who likes Orange.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Chain the two attributes through the person; do not pair attributes directly from one clue.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-127 · L3 · hard · Category and attribute matching puzzle · officer

Six persons – Bela, Chitra, Dev, Esha, Farid and Gauri – joined a company in six different years from 2016 to 2021, one person per year. Each of them works in a different department among Audit, Finance, HR, IT, Legal and Sales.

- The one who works in HR joined in the year immediately before Dev.
- Dev joined in the year immediately before Chitra.
- As many persons joined after Esha as before the one who works in IT.
- Chitra joined in the year immediately after the one who works in Sales.
- Farid joined exactly two years before Gauri.
- The one who works in Legal and Gauri joined in consecutive years.
- Farid does not work in Finance.
- Bela joined exactly two years after Esha.

Who joined in the year immediately after the one who works in HR?

- **A.** Dev ✅
- **B.** Esha  _(error: not at the required position)_
- **C.** Bela  _(error: direction reversed (before instead of after))_
- **D.** Chitra  _(error: counted one place too far)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 dept assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Bela joined exactly two years after Esha.' and 'Farid joined exactly two years before Gauri.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 2016 – Esha (Finance); 2017 – Farid (Audit); 2018 – Bela (Legal); 2019 – Gauri (HR); 2020 – Dev (Sales); 2021 – Chitra (IT).
4. The one who works in HR is at 2019; the person asked for is at 2020, i.e. Dev.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-128 · L4 · hard · Category and attribute matching puzzle · officer

Six persons – Bhumi, Charu, Tara, Uday, Vani and Yash – joined a company in six different years from 2016 to 2021, one person per year. Each of them likes a different fruit among Apple, Cherry, Guava, Litchi, Mango and Orange. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore and Jaipur.

- Vani does not like Cherry.
- Tara joined in the year immediately before Charu.
- The one who likes Guava is not from Delhi.
- The one who likes Apple is from Bhopal.
- Vani is not from Agra.
- Charu is not from Indore.
- Uday joined in an even-numbered year.
- As many persons joined after the one who likes Orange as before Bhumi.
- Charu does not like Guava.
- The one from Delhi joined in the year immediately before Vani.
- Tara joined exactly four years before Bhumi.
- As many persons joined after the one who likes Mango as before Uday.
- The one who likes Cherry is from Indore.
- The one who likes Orange is not from Agra.
- Uday is not from Chennai.
- Bhumi joined exactly two years after Yash.

Which fruit does Uday like?

- **A.** Cherry  _(error: attribute of Tara, a neighbour of Uday)_
- **B.** Litchi  _(error: attribute of Yash)_
- **C.** Guava  _(error: attribute of Vani)_
- **D.** Orange ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 fruit assignments × 720 city assignments leaves exactly one arrangement that satisfies all 16 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Tara joined exactly four years before Bhumi.' and 'Bhumi joined exactly two years after Yash.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 2016 – Uday (Orange, Jaipur); 2017 – Tara (Cherry, Indore); 2018 – Charu (Apple, Bhopal); 2019 – Yash (Litchi, Delhi); 2020 – Vani (Guava, Chennai); 2021 – Bhumi (Mango, Agra).
4. Uday likes Orange in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-129 · L4 · hard · Category and attribute matching puzzle · officer

Six persons – Bhumi, Charu, Tara, Uday, Vani and Yash – joined a company in six different years from 2016 to 2021, one person per year. Each of them likes a different fruit among Apple, Cherry, Guava, Litchi, Mango and Orange. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore and Jaipur.

- Vani does not like Cherry.
- Tara joined in the year immediately before Charu.
- The one who likes Guava is not from Delhi.
- The one who likes Apple is from Bhopal.
- Vani is not from Agra.
- Charu is not from Indore.
- Uday joined in an even-numbered year.
- As many persons joined after the one who likes Orange as before Bhumi.
- Charu does not like Guava.
- The one from Delhi joined in the year immediately before Vani.
- Tara joined exactly four years before Bhumi.
- As many persons joined after the one who likes Mango as before Uday.
- The one who likes Cherry is from Indore.
- The one who likes Orange is not from Agra.
- Uday is not from Chennai.
- Bhumi joined exactly two years after Yash.

Who likes Orange?

- **A.** Bhumi  _(error: no clue links this person to that attribute)_
- **B.** Tara  _(error: neighbour of the correct person)_
- **C.** Uday ✅
- **D.** Yash  _(error: no clue links this person to that attribute)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 fruit assignments × 720 city assignments leaves exactly one arrangement that satisfies all 16 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Tara joined exactly four years before Bhumi.' and 'Bhumi joined exactly two years after Yash.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 2016 – Uday (Orange, Jaipur); 2017 – Tara (Cherry, Indore); 2018 – Charu (Apple, Bhopal); 2019 – Yash (Litchi, Delhi); 2020 – Vani (Guava, Chennai); 2021 – Bhumi (Mango, Agra).
4. Uday likes Orange.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Attribute clues often name the attribute, not the person; resolve them only after positions are fixed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-130 · L4 · hard · Category and attribute matching puzzle · officer

Six persons – Bhumi, Charu, Tara, Uday, Vani and Yash – joined a company in six different years from 2016 to 2021, one person per year. Each of them likes a different fruit among Apple, Cherry, Guava, Litchi, Mango and Orange. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore and Jaipur.

- Vani does not like Cherry.
- Tara joined in the year immediately before Charu.
- The one who likes Guava is not from Delhi.
- The one who likes Apple is from Bhopal.
- Vani is not from Agra.
- Charu is not from Indore.
- Uday joined in an even-numbered year.
- As many persons joined after the one who likes Orange as before Bhumi.
- Charu does not like Guava.
- The one from Delhi joined in the year immediately before Vani.
- Tara joined exactly four years before Bhumi.
- As many persons joined after the one who likes Mango as before Uday.
- The one who likes Cherry is from Indore.
- The one who likes Orange is not from Agra.
- Uday is not from Chennai.
- Bhumi joined exactly two years after Yash.

Who joined exactly two years before Yash?

- **A.** Tara ✅
- **B.** Bhumi  _(error: direction reversed (after instead of before))_
- **C.** Uday  _(error: counted one place too far)_
- **D.** Charu  _(error: counted one place short)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 fruit assignments × 720 city assignments leaves exactly one arrangement that satisfies all 16 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Tara joined exactly four years before Bhumi.' and 'Bhumi joined exactly two years after Yash.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 2016 – Uday (Orange, Jaipur); 2017 – Tara (Cherry, Indore); 2018 – Charu (Apple, Bhopal); 2019 – Yash (Litchi, Delhi); 2020 – Vani (Guava, Chennai); 2021 – Bhumi (Mango, Agra).
4. Yash is at 2019; the person asked for is at 2017, i.e. Tara.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-131 · L4 · hard · Category and attribute matching puzzle · officer

Six persons – Bhumi, Charu, Tara, Uday, Vani and Yash – joined a company in six different years from 2016 to 2021, one person per year. Each of them likes a different fruit among Apple, Cherry, Guava, Litchi, Mango and Orange. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore and Jaipur.

- Vani does not like Cherry.
- Tara joined in the year immediately before Charu.
- The one who likes Guava is not from Delhi.
- The one who likes Apple is from Bhopal.
- Vani is not from Agra.
- Charu is not from Indore.
- Uday joined in an even-numbered year.
- As many persons joined after the one who likes Orange as before Bhumi.
- Charu does not like Guava.
- The one from Delhi joined in the year immediately before Vani.
- Tara joined exactly four years before Bhumi.
- As many persons joined after the one who likes Mango as before Uday.
- The one who likes Cherry is from Indore.
- The one who likes Orange is not from Agra.
- Uday is not from Chennai.
- Bhumi joined exactly two years after Yash.

Which of the following statements is true?

- **A.** Uday is not from Delhi. ✅
- **B.** Bhumi is not from Agra.  _(error: false in the solved arrangement)_
- **C.** Uday joined later than Yash.  _(error: false in the solved arrangement)_
- **D.** Vani does not like Guava.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 fruit assignments × 720 city assignments leaves exactly one arrangement that satisfies all 16 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Tara joined exactly four years before Bhumi.' and 'Bhumi joined exactly two years after Yash.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 2016 – Uday (Orange, Jaipur); 2017 – Tara (Cherry, Indore); 2018 – Charu (Apple, Bhopal); 2019 – Yash (Litchi, Delhi); 2020 – Vani (Guava, Chennai); 2021 – Bhumi (Mango, Agra).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-132 · L4 · hard · Category and attribute matching puzzle · officer

Six persons – Bhumi, Charu, Tara, Uday, Vani and Yash – joined a company in six different years from 2016 to 2021, one person per year. Each of them likes a different fruit among Apple, Cherry, Guava, Litchi, Mango and Orange. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore and Jaipur.

- Vani does not like Cherry.
- Tara joined in the year immediately before Charu.
- The one who likes Guava is not from Delhi.
- The one who likes Apple is from Bhopal.
- Vani is not from Agra.
- Charu is not from Indore.
- Uday joined in an even-numbered year.
- As many persons joined after the one who likes Orange as before Bhumi.
- Charu does not like Guava.
- The one from Delhi joined in the year immediately before Vani.
- Tara joined exactly four years before Bhumi.
- As many persons joined after the one who likes Mango as before Uday.
- The one who likes Cherry is from Indore.
- The one who likes Orange is not from Agra.
- Uday is not from Chennai.
- Bhumi joined exactly two years after Yash.

In which year did Tara join?

- **A.** 2016  _(error: off by one position)_
- **B.** 2017 ✅
- **C.** 2020  _(error: counted from the opposite end)_
- **D.** 2018  _(error: off by one position)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 fruit assignments × 720 city assignments leaves exactly one arrangement that satisfies all 16 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Tara joined exactly four years before Bhumi.' and 'Bhumi joined exactly two years after Yash.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 2016 – Uday (Orange, Jaipur); 2017 – Tara (Cherry, Indore); 2018 – Charu (Apple, Bhopal); 2019 – Yash (Litchi, Delhi); 2020 – Vani (Guava, Chennai); 2021 – Bhumi (Mango, Agra).
4. Tara is at 2017.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-133 · L4 · hard · Category and attribute matching puzzle · officer

Five persons – Aman, Chitra, Dev, Farid and Gauri – joined a company in five different years from 2019 to 2023, one person per year. Each of them plays a different game among Chess, Football, Hockey, Tennis and Volleyball. Each of them works in a different department among Admin, Finance, HR, Legal and Marketing.

- The one who works in HR joined exactly four years after Farid.
- Aman joined in the year immediately after Farid.
- Dev does not play Football.
- The one who plays Hockey works in Admin.
- Chitra joined exactly two years after Aman.
- Aman does not play Volleyball.
- Chitra and the one who plays Chess joined in consecutive years.
- The one who plays Football does not work in Legal.
- Aman and Dev joined in consecutive years.
- Aman does not work in Admin.
- The one who works in Admin joined exactly two years before the one who works in Marketing.
- The one who plays Tennis works in Finance.

Who joined exactly two years before the one who plays Chess?

- **A.** Farid ✅
- **B.** Aman  _(error: counted one place short)_
- **C.** Chitra  _(error: not at the required position)_
- **D.** Gauri  _(error: direction reversed (after instead of before))_

**Working**

1. Exhaustive enumeration over 120 seat/position orders × 120 sport assignments × 120 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Chitra joined exactly two years after Aman.' and 'Aman joined in the year immediately after Farid.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 2019 – Farid (Hockey, Admin); 2020 – Aman (Tennis, Finance); 2021 – Dev (Chess, Marketing); 2022 – Chitra (Volleyball, Legal); 2023 – Gauri (Football, HR).
4. The one who plays Chess is at 2021; the person asked for is at 2019, i.e. Farid.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-134 · L4 · hard · Category and attribute matching puzzle · officer

Five persons – Aman, Chitra, Dev, Farid and Gauri – joined a company in five different years from 2019 to 2023, one person per year. Each of them plays a different game among Chess, Football, Hockey, Tennis and Volleyball. Each of them works in a different department among Admin, Finance, HR, Legal and Marketing.

- The one who works in HR joined exactly four years after Farid.
- Aman joined in the year immediately after Farid.
- Dev does not play Football.
- The one who plays Hockey works in Admin.
- Chitra joined exactly two years after Aman.
- Aman does not play Volleyball.
- Chitra and the one who plays Chess joined in consecutive years.
- The one who plays Football does not work in Legal.
- Aman and Dev joined in consecutive years.
- Aman does not work in Admin.
- The one who works in Admin joined exactly two years before the one who works in Marketing.
- The one who plays Tennis works in Finance.

In which department does Dev work?

- **A.** Legal  _(error: attribute of Chitra, a neighbour of Dev)_
- **B.** HR  _(error: attribute of Gauri)_
- **C.** Marketing ✅
- **D.** Finance  _(error: attribute of Aman, a neighbour of Dev)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders × 120 sport assignments × 120 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Chitra joined exactly two years after Aman.' and 'Aman joined in the year immediately after Farid.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 2019 – Farid (Hockey, Admin); 2020 – Aman (Tennis, Finance); 2021 – Dev (Chess, Marketing); 2022 – Chitra (Volleyball, Legal); 2023 – Gauri (Football, HR).
4. Dev works in Marketing in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-135 · L4 · hard · Category and attribute matching puzzle · officer

Five persons – Aman, Chitra, Dev, Farid and Gauri – joined a company in five different years from 2019 to 2023, one person per year. Each of them plays a different game among Chess, Football, Hockey, Tennis and Volleyball. Each of them works in a different department among Admin, Finance, HR, Legal and Marketing.

- The one who works in HR joined exactly four years after Farid.
- Aman joined in the year immediately after Farid.
- Dev does not play Football.
- The one who plays Hockey works in Admin.
- Chitra joined exactly two years after Aman.
- Aman does not play Volleyball.
- Chitra and the one who plays Chess joined in consecutive years.
- The one who plays Football does not work in Legal.
- Aman and Dev joined in consecutive years.
- Aman does not work in Admin.
- The one who works in Admin joined exactly two years before the one who works in Marketing.
- The one who plays Tennis works in Finance.

Which of the following statements is NOT true?

- **A.** The one who works in Finance joined exactly three years before Gauri.  _(error: this statement is true in the solved arrangement)_
- **B.** The one who plays Football joined exactly three years after Aman.  _(error: this statement is true in the solved arrangement)_
- **C.** The one who works in Admin joined exactly three years before Dev. ✅
- **D.** Aman joined in the year immediately after the one who plays Hockey.  _(error: this statement is true in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders × 120 sport assignments × 120 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Chitra joined exactly two years after Aman.' and 'Aman joined in the year immediately after Farid.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 2019 – Farid (Hockey, Admin); 2020 – Aman (Tennis, Finance); 2021 – Dev (Chess, Marketing); 2022 – Chitra (Volleyball, Legal); 2023 – Gauri (Football, HR).
4. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-136 · L1 · easy · Clock-time scheduling puzzle · foundation

Five persons – Arjun, Bhumi, Tara, Yash and Zoya – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 10 a.m., 11 a.m., 12 noon, 2 p.m. and 3 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m.

- As many persons meet the counsellor after Yash as before Arjun.
- Tara meets the counsellor at some time after Arjun.
- Bhumi meets the counsellor exactly five hours after Zoya.

Who meets the counsellor at 10 a.m.?

- **A.** Arjun  _(error: off by one position)_
- **B.** Tara  _(error: not at that position)_
- **C.** Bhumi  _(error: counted from the opposite end)_
- **D.** Zoya ✅

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Bhumi meets the counsellor exactly five hours after Zoya.' and 'As many persons meet the counsellor after Yash as before Arjun.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 10 a.m. – Zoya; 11 a.m. – Arjun; 12 noon – Tara; 2 p.m. – Yash; 3 p.m. – Bhumi.
4. 10 a.m. is occupied by Zoya.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Check which end the count starts from.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-137 · L2 · medium · Clock-time scheduling puzzle · foundation

Five persons – Aman, Bela, Farid, Gauri and Harsh – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 10 a.m., 11 a.m., 12 noon, 2 p.m. and 3 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m.

- Only one person meets the counsellor between Gauri and Harsh.
- Farid meets the counsellor at 3 p.m.
- Aman and Farid do not have consecutive slots.
- Harsh meets the counsellor exactly two hours after Gauri.

Who meets the counsellor in the slot immediately after Bela?

- **A.** Harsh  _(error: not at the required position)_
- **B.** Gauri  _(error: not at the required position)_
- **C.** Aman  _(error: not at the required position)_
- **D.** Farid ✅

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Harsh meets the counsellor exactly two hours after Gauri.' and 'Farid meets the counsellor at 3 p.m.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 10 a.m. – Gauri; 11 a.m. – Aman; 12 noon – Harsh; 2 p.m. – Bela; 3 p.m. – Farid.
4. Bela is at 2 p.m.; the person asked for is at 3 p.m., i.e. Farid.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-138 · L2 · medium · Clock-time scheduling puzzle · foundation

Six persons – Deepa, Gopal, Hina, Ishaan, Jaya and Karan – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m. and 3 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m.

- Jaya has either the first or the last slot.
- Hina meets the counsellor exactly three hours after Gopal.
- Only one person meets the counsellor between Jaya and Karan.
- Deepa has either the first or the last slot.

At what time does Deepa meet the counsellor?

- **A.** 3 p.m.  _(error: counted from the opposite end)_
- **B.** 10 a.m.  _(error: off by one position)_
- **C.** 9 a.m. ✅
- **D.** 11 a.m.  _(error: off by two positions)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Hina meets the counsellor exactly three hours after Gopal.' and 'Only one person meets the counsellor between Jaya and Karan.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Deepa; 10 a.m. – Ishaan; 11 a.m. – Gopal; 12 noon – Karan; 2 p.m. – Hina; 3 p.m. – Jaya.
4. Deepa is at 9 a.m..

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-139 · L2 · medium · Clock-time scheduling puzzle · foundation

Six persons – Arjun, Charu, Uday, Vani, Yash and Zoya – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m. and 3 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m.

- Charu meets the counsellor exactly three hours before Uday.
- Only one person meets the counsellor between Uday and Zoya.
- Charu meets the counsellor exactly two hours before Arjun.
- Uday meets the counsellor exactly three hours before Yash.

Who meets the counsellor in the slot immediately before Yash?

- **A.** Charu  _(error: not at the required position)_
- **B.** Vani ✅
- **C.** Arjun  _(error: not at the required position)_
- **D.** Uday  _(error: not at the required position)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Charu meets the counsellor exactly three hours before Uday.' and 'Charu meets the counsellor exactly two hours before Arjun.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Charu; 10 a.m. – Zoya; 11 a.m. – Arjun; 12 noon – Uday; 2 p.m. – Vani; 3 p.m. – Yash.
4. Yash is at 3 p.m.; the person asked for is at 2 p.m., i.e. Vani.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-140 · L2 · medium · Clock-time scheduling puzzle · foundation

Six persons – Deepa, Ekta, Firoz, Gopal, Hina and Ishaan – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m. and 3 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m.

- As many persons meet the counsellor after Deepa as before Ishaan.
- Only two persons meet the counsellor between Deepa and Gopal.
- Ekta meets the counsellor in the slot immediately after Ishaan.
- Deepa meets the counsellor exactly two hours after Hina.

How many persons meet the counsellor between Deepa and Gopal?

- **A.** Two ✅
- **B.** Three  _(error: counted one of the two named persons)_
- **C.** Four  _(error: counted both named persons)_
- **D.** One  _(error: counted one short)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Deepa meets the counsellor exactly two hours after Hina.' and 'Ekta meets the counsellor in the slot immediately after Ishaan.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Hina; 10 a.m. – Firoz; 11 a.m. – Deepa; 12 noon – Ishaan; 2 p.m. – Ekta; 3 p.m. – Gopal.
4. Deepa is at 11 a.m. and Gopal at 3 p.m.; 2 position(s) lie strictly between them.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Between' excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-141 · L3 · hard · Clock-time scheduling puzzle · officer

Seven persons – Bela, Chitra, Dev, Esha, Farid, Gauri and Harsh – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m., 3 p.m. and 4 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m.

- Only two persons meet the counsellor between Chitra and Esha.
- Chitra meets the counsellor exactly two hours after Farid.
- Bela meets the counsellor after the lunch break.
- Only three persons meet the counsellor between Gauri and Harsh.
- As many persons meet the counsellor after Bela as before Harsh.

Who meets the counsellor exactly two hours after Farid?

- **A.** Harsh  _(error: counted one place short)_
- **B.** Bela  _(error: not at the required position)_
- **C.** Chitra ✅
- **D.** Dev  _(error: not at the required position)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders leaves exactly one arrangement that satisfies all 5 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Chitra meets the counsellor exactly two hours after Farid.' and 'As many persons meet the counsellor after Bela as before Harsh.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Esha; 10 a.m. – Farid; 11 a.m. – Harsh; 12 noon – Chitra; 2 p.m. – Bela; 3 p.m. – Dev; 4 p.m. – Gauri.
4. Farid is at 10 a.m.; the person asked for is at 12 noon, i.e. Chitra.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-142 · L3 · hard · Clock-time scheduling puzzle · officer

Six persons – Deepa, Ekta, Gopal, Hina, Jaya and Karan – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m. and 3 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m. Each of them is from a different city among Agra, Bhopal, Chennai, Indore, Kochi and Patna.

- The one from Agra meets the counsellor exactly two hours after Ekta.
- The one from Kochi meets the counsellor exactly two hours before the one from Indore.
- Only two persons meet the counsellor between the one from Patna and Jaya, with the one from Patna meeting later than Jaya.
- Deepa meets the counsellor exactly five hours before Karan.
- As many persons meet the counsellor after the one from Chennai as before Deepa.
- Gopal meets the counsellor exactly three hours after Jaya.

Who meets the counsellor exactly three hours before the one from Indore?

- **A.** Deepa  _(error: counted one place short)_
- **B.** Karan  _(error: direction reversed (after instead of before))_
- **C.** Gopal  _(error: not at the required position)_
- **D.** Ekta ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 city assignments leaves exactly one arrangement that satisfies all 6 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Deepa meets the counsellor exactly five hours before Karan.' and 'Gopal meets the counsellor exactly three hours after Jaya.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Ekta (Bhopal); 10 a.m. – Deepa (Kochi); 11 a.m. – Jaya (Agra); 12 noon – Hina (Indore); 2 p.m. – Gopal (Chennai); 3 p.m. – Karan (Patna).
4. The one from Indore is at 12 noon; the person asked for is at 9 a.m., i.e. Ekta.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-143 · L4 · hard · Clock-time scheduling puzzle · officer

Eight persons – Aman, Bela, Chitra, Dev, Esha, Farid, Gauri and Harsh – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m., 3 p.m., 4 p.m. and 5 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- Only one person meets the counsellor between Gauri and Aman, with Gauri meeting later than Aman.
- As many persons meet the counsellor after Dev as before Bela.
- Only four persons meet the counsellor between Gauri and Chitra, with Gauri meeting later than Chitra.
- Dev meets the counsellor exactly four hours after Bela.
- The one who works in Finance and Dev do not have consecutive slots.
- The one who works in Marketing has either the first or the last slot.
- The one who works in HR meets the counsellor in the slot immediately after the one who works in IT.
- The one who works in Admin meets the counsellor in the slot immediately before Esha.
- The one who works in Audit and Harsh have consecutive slots.
- Only five persons meet the counsellor between the one who works in Finance and the one who works in Marketing.
- Only one person meets the counsellor between the one who works in Sales and Esha.
- Only one person meets the counsellor between Chitra and Esha.

Who meets the counsellor exactly two hours before Esha?

- **A.** Farid  _(error: counted one place too far)_
- **B.** Aman  _(error: direction reversed (after instead of before))_
- **C.** Bela  _(error: counted one place short)_
- **D.** Chitra ✅

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Dev meets the counsellor exactly four hours after Bela.' and 'Only four persons meet the counsellor between Gauri and Chitra, with Gauri meeting later than Chitra.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Farid (Legal); 10 a.m. – Chitra (Finance); 11 a.m. – Bela (Admin); 12 noon – Esha (IT); 2 p.m. – Aman (HR); 3 p.m. – Dev (Sales); 4 p.m. – Gauri (Audit); 5 p.m. – Harsh (Marketing).
4. Esha is at 12 noon; the person asked for is at 10 a.m., i.e. Chitra.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-144 · L4 · hard · Clock-time scheduling puzzle · officer

Eight persons – Aman, Bela, Chitra, Dev, Esha, Farid, Gauri and Harsh – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m., 3 p.m., 4 p.m. and 5 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- Only one person meets the counsellor between Gauri and Aman, with Gauri meeting later than Aman.
- As many persons meet the counsellor after Dev as before Bela.
- Only four persons meet the counsellor between Gauri and Chitra, with Gauri meeting later than Chitra.
- Dev meets the counsellor exactly four hours after Bela.
- The one who works in Finance and Dev do not have consecutive slots.
- The one who works in Marketing has either the first or the last slot.
- The one who works in HR meets the counsellor in the slot immediately after the one who works in IT.
- The one who works in Admin meets the counsellor in the slot immediately before Esha.
- The one who works in Audit and Harsh have consecutive slots.
- Only five persons meet the counsellor between the one who works in Finance and the one who works in Marketing.
- Only one person meets the counsellor between the one who works in Sales and Esha.
- Only one person meets the counsellor between Chitra and Esha.

At what time does Bela meet the counsellor?

- **A.** 10 a.m.  _(error: off by one position)_
- **B.** 11 a.m. ✅
- **C.** 12 noon  _(error: off by one position)_
- **D.** 3 p.m.  _(error: counted from the opposite end)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Dev meets the counsellor exactly four hours after Bela.' and 'Only four persons meet the counsellor between Gauri and Chitra, with Gauri meeting later than Chitra.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Farid (Legal); 10 a.m. – Chitra (Finance); 11 a.m. – Bela (Admin); 12 noon – Esha (IT); 2 p.m. – Aman (HR); 3 p.m. – Dev (Sales); 4 p.m. – Gauri (Audit); 5 p.m. – Harsh (Marketing).
4. Bela is at 11 a.m..

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-145 · L4 · hard · Clock-time scheduling puzzle · officer

Eight persons – Aman, Bela, Chitra, Dev, Esha, Farid, Gauri and Harsh – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m., 3 p.m., 4 p.m. and 5 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- Only one person meets the counsellor between Gauri and Aman, with Gauri meeting later than Aman.
- As many persons meet the counsellor after Dev as before Bela.
- Only four persons meet the counsellor between Gauri and Chitra, with Gauri meeting later than Chitra.
- Dev meets the counsellor exactly four hours after Bela.
- The one who works in Finance and Dev do not have consecutive slots.
- The one who works in Marketing has either the first or the last slot.
- The one who works in HR meets the counsellor in the slot immediately after the one who works in IT.
- The one who works in Admin meets the counsellor in the slot immediately before Esha.
- The one who works in Audit and Harsh have consecutive slots.
- Only five persons meet the counsellor between the one who works in Finance and the one who works in Marketing.
- Only one person meets the counsellor between the one who works in Sales and Esha.
- Only one person meets the counsellor between Chitra and Esha.

In which department does Bela work?

- **A.** Admin ✅
- **B.** Legal  _(error: attribute of Farid)_
- **C.** Finance  _(error: attribute of Chitra, a neighbour of Bela)_
- **D.** IT  _(error: attribute of Esha, a neighbour of Bela)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Dev meets the counsellor exactly four hours after Bela.' and 'Only four persons meet the counsellor between Gauri and Chitra, with Gauri meeting later than Chitra.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Farid (Legal); 10 a.m. – Chitra (Finance); 11 a.m. – Bela (Admin); 12 noon – Esha (IT); 2 p.m. – Aman (HR); 3 p.m. – Dev (Sales); 4 p.m. – Gauri (Audit); 5 p.m. – Harsh (Marketing).
4. Bela works in Admin in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-146 · L4 · hard · Clock-time scheduling puzzle · officer

Eight persons – Aman, Bela, Chitra, Dev, Esha, Farid, Gauri and Harsh – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m., 3 p.m., 4 p.m. and 5 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- Only one person meets the counsellor between Gauri and Aman, with Gauri meeting later than Aman.
- As many persons meet the counsellor after Dev as before Bela.
- Only four persons meet the counsellor between Gauri and Chitra, with Gauri meeting later than Chitra.
- Dev meets the counsellor exactly four hours after Bela.
- The one who works in Finance and Dev do not have consecutive slots.
- The one who works in Marketing has either the first or the last slot.
- The one who works in HR meets the counsellor in the slot immediately after the one who works in IT.
- The one who works in Admin meets the counsellor in the slot immediately before Esha.
- The one who works in Audit and Harsh have consecutive slots.
- Only five persons meet the counsellor between the one who works in Finance and the one who works in Marketing.
- Only one person meets the counsellor between the one who works in Sales and Esha.
- Only one person meets the counsellor between Chitra and Esha.

Which of the following statements is true?

- **A.** Esha and the one who works in Admin do not have consecutive slots.  _(error: false in the solved arrangement)_
- **B.** Harsh meets the counsellor in the slot immediately before Chitra.  _(error: false in the solved arrangement)_
- **C.** The one who works in HR and Gauri do not have consecutive slots. ✅
- **D.** The one who works in Finance and Farid do not have consecutive slots.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Dev meets the counsellor exactly four hours after Bela.' and 'Only four persons meet the counsellor between Gauri and Chitra, with Gauri meeting later than Chitra.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Farid (Legal); 10 a.m. – Chitra (Finance); 11 a.m. – Bela (Admin); 12 noon – Esha (IT); 2 p.m. – Aman (HR); 3 p.m. – Dev (Sales); 4 p.m. – Gauri (Audit); 5 p.m. – Harsh (Marketing).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-147 · L4 · hard · Clock-time scheduling puzzle · officer

Eight persons – Aman, Bela, Chitra, Dev, Esha, Farid, Gauri and Harsh – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m., 3 p.m., 4 p.m. and 5 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m. Each of them works in a different department among Admin, Audit, Finance, HR, IT, Legal, Marketing and Sales.

- Only one person meets the counsellor between Gauri and Aman, with Gauri meeting later than Aman.
- As many persons meet the counsellor after Dev as before Bela.
- Only four persons meet the counsellor between Gauri and Chitra, with Gauri meeting later than Chitra.
- Dev meets the counsellor exactly four hours after Bela.
- The one who works in Finance and Dev do not have consecutive slots.
- The one who works in Marketing has either the first or the last slot.
- The one who works in HR meets the counsellor in the slot immediately after the one who works in IT.
- The one who works in Admin meets the counsellor in the slot immediately before Esha.
- The one who works in Audit and Harsh have consecutive slots.
- Only five persons meet the counsellor between the one who works in Finance and the one who works in Marketing.
- Only one person meets the counsellor between the one who works in Sales and Esha.
- Only one person meets the counsellor between Chitra and Esha.

How many persons meet the counsellor after Bela?

- **A.** Six  _(error: included the person named)_
- **B.** Four  _(error: missed the extreme position)_
- **C.** Two  _(error: counted before instead of after)_
- **D.** Five ✅

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 dept assignments leaves exactly one arrangement that satisfies all 12 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Dev meets the counsellor exactly four hours after Bela.' and 'Only four persons meet the counsellor between Gauri and Chitra, with Gauri meeting later than Chitra.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Farid (Legal); 10 a.m. – Chitra (Finance); 11 a.m. – Bela (Admin); 12 noon – Esha (IT); 2 p.m. – Aman (HR); 3 p.m. – Dev (Sales); 4 p.m. – Gauri (Audit); 5 p.m. – Harsh (Marketing).
4. Bela is at 11 a.m.; 5 position(s) lie beyond it in that direction.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Count only the persons beyond the one named, in the stated direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-148 · L4 · hard · Clock-time scheduling puzzle · officer

Seven persons – Arjun, Bhumi, Charu, Tara, Vani, Yash and Zoya – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m., 3 p.m. and 4 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore, Kochi and Patna.

- The one from Bhopal meets the counsellor exactly three hours before the one from Chennai.
- The one from Delhi meets the counsellor in the slot immediately before the one from Patna.
- Zoya meets the counsellor in the slot immediately after Yash.
- The one from Indore has neither the first nor the last slot.
- The one from Indore meets the counsellor in the slot immediately after Vani.
- The one from Kochi meets the counsellor exactly four hours before Arjun.
- Arjun and Charu do not have consecutive slots.
- Charu meets the counsellor exactly three hours after Bhumi.

Who is from Agra?

- **A.** Tara  _(error: neighbour of the correct person)_
- **B.** Bhumi  _(error: no clue links this person to that attribute)_
- **C.** Zoya  _(error: no clue links this person to that attribute)_
- **D.** Arjun ✅

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 city assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Charu meets the counsellor exactly three hours after Bhumi.' and 'Zoya meets the counsellor in the slot immediately after Yash.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Bhumi (Delhi); 10 a.m. – Yash (Patna); 11 a.m. – Zoya (Bhopal); 12 noon – Charu (Kochi); 2 p.m. – Vani (Chennai); 3 p.m. – Tara (Indore); 4 p.m. – Arjun (Agra).
4. Arjun is from Agra.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Attribute clues often name the attribute, not the person; resolve them only after positions are fixed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-149 · L4 · hard · Clock-time scheduling puzzle · officer

Seven persons – Arjun, Bhumi, Charu, Tara, Vani, Yash and Zoya – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m., 3 p.m. and 4 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore, Kochi and Patna.

- The one from Bhopal meets the counsellor exactly three hours before the one from Chennai.
- The one from Delhi meets the counsellor in the slot immediately before the one from Patna.
- Zoya meets the counsellor in the slot immediately after Yash.
- The one from Indore has neither the first nor the last slot.
- The one from Indore meets the counsellor in the slot immediately after Vani.
- The one from Kochi meets the counsellor exactly four hours before Arjun.
- Arjun and Charu do not have consecutive slots.
- Charu meets the counsellor exactly three hours after Bhumi.

Who meets the counsellor exactly two hours after Yash?

- **A.** Arjun  _(error: not at the required position)_
- **B.** Bhumi  _(error: not at the required position)_
- **C.** Charu ✅
- **D.** Zoya  _(error: counted one place short)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 city assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Charu meets the counsellor exactly three hours after Bhumi.' and 'Zoya meets the counsellor in the slot immediately after Yash.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Bhumi (Delhi); 10 a.m. – Yash (Patna); 11 a.m. – Zoya (Bhopal); 12 noon – Charu (Kochi); 2 p.m. – Vani (Chennai); 3 p.m. – Tara (Indore); 4 p.m. – Arjun (Agra).
4. Yash is at 10 a.m.; the person asked for is at 12 noon, i.e. Charu.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-150 · L4 · hard · Clock-time scheduling puzzle · officer

Seven persons – Arjun, Bhumi, Charu, Tara, Vani, Yash and Zoya – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m., 3 p.m. and 4 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m. Each of them is from a different city among Agra, Bhopal, Chennai, Delhi, Indore, Kochi and Patna.

- The one from Bhopal meets the counsellor exactly three hours before the one from Chennai.
- The one from Delhi meets the counsellor in the slot immediately before the one from Patna.
- Zoya meets the counsellor in the slot immediately after Yash.
- The one from Indore has neither the first nor the last slot.
- The one from Indore meets the counsellor in the slot immediately after Vani.
- The one from Kochi meets the counsellor exactly four hours before Arjun.
- Arjun and Charu do not have consecutive slots.
- Charu meets the counsellor exactly three hours after Bhumi.

Which of the following statements is NOT true?

- **A.** The one from Patna meets the counsellor in the slot immediately after the one from Delhi.  _(error: this statement is true in the solved arrangement)_
- **B.** The one from Delhi meets the counsellor exactly three hours before the one from Chennai. ✅
- **C.** Only one person meets the counsellor between the one from Chennai and the one from Bhopal.  _(error: this statement is true in the solved arrangement)_
- **D.** The one from Chennai meets the counsellor exactly three hours after the one from Bhopal.  _(error: this statement is true in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 city assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Charu meets the counsellor exactly three hours after Bhumi.' and 'Zoya meets the counsellor in the slot immediately after Yash.'; then place the others by elimination.
3. Solved arrangement — Earliest to latest: 9 a.m. – Bhumi (Delhi); 10 a.m. – Yash (Patna); 11 a.m. – Zoya (Bhopal); 12 noon – Charu (Kochi); 2 p.m. – Vani (Chennai); 3 p.m. – Tara (Indore); 4 p.m. – Arjun (Agra).
4. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-151 · L1 · easy · Day and week scheduling puzzle · foundation

Five persons – Arjun, Bhumi, Charu, Tara and Zoya – each give a talk on a different day of the same week, from Monday to Friday, one talk per day.

- Arjun gives a talk on Tuesday.
- Bhumi gives a talk three days before Zoya.
- Tara gives a talk on the day immediately after Zoya.

Who gives a talk on Thursday?

- **A.** Charu  _(error: off by one position)_
- **B.** Zoya ✅
- **C.** Tara  _(error: off by one position)_
- **D.** Arjun  _(error: counted from the opposite end)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Bhumi gives a talk three days before Zoya.' and 'Arjun gives a talk on Tuesday.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Bhumi; Tuesday – Arjun; Wednesday – Charu; Thursday – Zoya; Friday – Tara.
4. Thursday is occupied by Zoya.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Check which end the count starts from.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-152 · L1 · easy · Day and week scheduling puzzle · foundation

Five persons – Bela, Chitra, Esha, Farid and Gauri – each give a talk on a different day of the same week, from Monday to Friday, one talk per day.

- Gauri gives a talk on Friday.
- Farid gives a talk on the day immediately after Esha.
- Esha gives a talk two days after Bela.

On which day does Gauri give a talk?

- **A.** Friday ✅
- **B.** Thursday  _(error: off by one position)_
- **C.** Monday  _(error: counted from the opposite end)_
- **D.** Wednesday  _(error: off by two positions)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Esha gives a talk two days after Bela.' and 'Farid gives a talk on the day immediately after Esha.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Bela; Tuesday – Chitra; Wednesday – Esha; Thursday – Farid; Friday – Gauri.
4. Gauri is at Friday.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-153 · L2 · medium · Day and week scheduling puzzle · foundation

Six persons – Deepa, Ekta, Gopal, Hina, Ishaan and Jaya – each give a talk on a different day of the same week, from Monday to Saturday, one talk per day.

- Only three persons give talks between Ekta and Ishaan.
- Deepa gives a talk on the day immediately before Jaya.
- As many persons give talks after Gopal as before Ekta.
- Gopal gives a talk three days after Ekta.

Who gives a talk on the day immediately after Gopal?

- **A.** Ekta  _(error: not at the required position)_
- **B.** Ishaan ✅
- **C.** Deepa  _(error: not at the required position)_
- **D.** Jaya  _(error: direction reversed (before instead of after))_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Gopal gives a talk three days after Ekta.' and 'Only three persons give talks between Ekta and Ishaan.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Hina; Tuesday – Ekta; Wednesday – Deepa; Thursday – Jaya; Friday – Gopal; Saturday – Ishaan.
4. Gopal is at Friday; the person asked for is at Saturday, i.e. Ishaan.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-154 · L2 · medium · Day and week scheduling puzzle · foundation

Six persons – Arjun, Bhumi, Charu, Uday, Yash and Zoya – each give a talk on a different day of the same week, from Monday to Saturday, one talk per day.

- Charu gives a talk three days after Bhumi.
- As many persons give talks after Arjun as before Uday.
- Zoya gives a talk four days after Arjun.

How many persons give talks between Charu and Zoya?

- **A.** Two  _(error: counted one of the two named persons)_
- **B.** Three  _(error: counted both named persons)_
- **C.** Four  _(error: counted from the wrong end)_
- **D.** One ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Zoya gives a talk four days after Arjun.' and 'Charu gives a talk three days after Bhumi.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Bhumi; Tuesday – Arjun; Wednesday – Yash; Thursday – Charu; Friday – Uday; Saturday – Zoya.
4. Charu is at Thursday and Zoya at Saturday; 1 position(s) lie strictly between them.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Between' excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-155 · L2 · medium · Day and week scheduling puzzle · foundation

Seven persons – Deepa, Ekta, Firoz, Gopal, Hina, Jaya and Karan – each give a talk on a different day of the same week, from Monday to Sunday, one talk per day.

- As many persons give talks after Karan as before Firoz.
- Firoz gives a talk four days before Jaya.
- Deepa gives a talk two days before Ekta.
- Only four persons give talks between Hina and Firoz, with Hina coming after Firoz.

On which day does Deepa give a talk?

- **A.** Monday  _(error: off by one position)_
- **B.** Wednesday  _(error: off by one position)_
- **C.** Tuesday ✅
- **D.** Saturday  _(error: counted from the opposite end)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only four persons give talks between Hina and Firoz, with Hina coming after Firoz.' and 'Firoz gives a talk four days before Jaya.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Firoz; Tuesday – Deepa; Wednesday – Gopal; Thursday – Ekta; Friday – Jaya; Saturday – Hina; Sunday – Karan.
4. Deepa is at Tuesday.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-156 · L3 · hard · Day and week scheduling puzzle · officer

Seven persons – Aman, Bela, Chitra, Dev, Farid, Gauri and Harsh – each give a talk on a different day of the same week, from Monday to Sunday, one talk per day.

- Only four persons give talks between Harsh and Bela, with Harsh coming after Bela.
- Only one person gives a talk between Gauri and Aman, with Gauri coming after Aman.
- Harsh gives a talk two days after Dev.
- Farid gives a talk two days before Chitra.
- Aman gives a talk on a day after Wednesday.

Which of the following statements is true?

- **A.** Farid gives a talk two days before Bela.  _(error: false in the solved arrangement)_
- **B.** Gauri gives a talk three days after Harsh.  _(error: false in the solved arrangement)_
- **C.** Harsh gives a talk three days before Bela.  _(error: false in the solved arrangement)_
- **D.** Chitra gives a talk two days before Dev. ✅

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders leaves exactly one arrangement that satisfies all 5 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only four persons give talks between Harsh and Bela, with Harsh coming after Bela.' and 'Farid gives a talk two days before Chitra.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Farid; Tuesday – Bela; Wednesday – Chitra; Thursday – Aman; Friday – Dev; Saturday – Gauri; Sunday – Harsh.
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-157 · L3 · hard · Day and week scheduling puzzle · officer

Six persons – Kavya, Lalit, Nikhil, Om, Preeti and Rahul – each give a talk on a different day of the same week, from Monday to Saturday, one talk per day. Each of them teaches a different subject among Civics, Economics, Geography, History, Physics and Zoology.

- Only one person gives a talk between the one who teaches Physics and Om.
- Only three persons give talks between the one who teaches History and the one who teaches Civics, with the one who teaches History coming after the one who teaches Civics.
- Nikhil gives a talk either on Monday or on Saturday.
- Lalit gives a talk four days after Kavya.
- Only two persons give talks between the one who teaches Zoology and Preeti.
- The one who teaches Economics gives a talk on the day immediately before the one who teaches History.
- Preeti gives a talk two days before Rahul.

Who gives a talk two days before the one who teaches Zoology?

- **A.** Preeti  _(error: counted one place too far)_
- **B.** Rahul  _(error: counted one place short)_
- **C.** Om ✅
- **D.** Kavya  _(error: not at the required position)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 subject assignments leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Lalit gives a talk four days after Kavya.' and 'Preeti gives a talk two days before Rahul.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Nikhil (Civics); Tuesday – Kavya (Physics); Wednesday – Preeti (Geography); Thursday – Om (Economics); Friday – Rahul (History); Saturday – Lalit (Zoology).
4. The one who teaches Zoology is at Saturday; the person asked for is at Thursday, i.e. Om.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-158 · L4 · hard · Day and week scheduling puzzle · officer

Seven persons – Aman, Chitra, Dev, Esha, Farid, Gauri and Harsh – each give a talk on a different day of the same week, from Monday to Sunday, one talk per day. Each of them teaches a different subject among Botany, Chemistry, Civics, Economics, Geography, History and Zoology.

- Chitra gives a talk three days after Aman.
- As many persons give talks after the one who teaches Economics as before Chitra.
- The one who teaches Botany gives a talk three days before Farid.
- Harsh gives a talk five days before Chitra.
- Only one person gives a talk between the one who teaches Zoology and Dev.
- The one who teaches Geography gives a talk either on Monday or on Sunday.
- Only four persons give talks between Chitra and the one who teaches Civics.
- Only three persons give talks between the one who teaches History and Farid.
- Gauri does not teach Chemistry.

Who gives a talk two days after Aman?

- **A.** Harsh  _(error: direction reversed (before instead of after))_
- **B.** Dev  _(error: counted one place short)_
- **C.** Chitra  _(error: counted one place too far)_
- **D.** Esha ✅

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 subject assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Harsh gives a talk five days before Chitra.' and 'Chitra gives a talk three days after Aman.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Harsh (Civics); Tuesday – Gauri (Economics); Wednesday – Aman (History); Thursday – Dev (Botany); Friday – Esha (Chemistry); Saturday – Chitra (Zoology); Sunday – Farid (Geography).
4. Aman is at Wednesday; the person asked for is at Friday, i.e. Esha.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-159 · L4 · hard · Day and week scheduling puzzle · officer

Seven persons – Aman, Chitra, Dev, Esha, Farid, Gauri and Harsh – each give a talk on a different day of the same week, from Monday to Sunday, one talk per day. Each of them teaches a different subject among Botany, Chemistry, Civics, Economics, Geography, History and Zoology.

- Chitra gives a talk three days after Aman.
- As many persons give talks after the one who teaches Economics as before Chitra.
- The one who teaches Botany gives a talk three days before Farid.
- Harsh gives a talk five days before Chitra.
- Only one person gives a talk between the one who teaches Zoology and Dev.
- The one who teaches Geography gives a talk either on Monday or on Sunday.
- Only four persons give talks between Chitra and the one who teaches Civics.
- Only three persons give talks between the one who teaches History and Farid.
- Gauri does not teach Chemistry.

Which subject does Harsh teach?

- **A.** Economics  _(error: attribute of Gauri, a neighbour of Harsh)_
- **B.** Botany  _(error: attribute of Dev)_
- **C.** Civics ✅
- **D.** History  _(error: attribute of Aman)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 subject assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Harsh gives a talk five days before Chitra.' and 'Chitra gives a talk three days after Aman.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Harsh (Civics); Tuesday – Gauri (Economics); Wednesday – Aman (History); Thursday – Dev (Botany); Friday – Esha (Chemistry); Saturday – Chitra (Zoology); Sunday – Farid (Geography).
4. Harsh teaches Civics in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-160 · L4 · hard · Day and week scheduling puzzle · officer

Seven persons – Aman, Chitra, Dev, Esha, Farid, Gauri and Harsh – each give a talk on a different day of the same week, from Monday to Sunday, one talk per day. Each of them teaches a different subject among Botany, Chemistry, Civics, Economics, Geography, History and Zoology.

- Chitra gives a talk three days after Aman.
- As many persons give talks after the one who teaches Economics as before Chitra.
- The one who teaches Botany gives a talk three days before Farid.
- Harsh gives a talk five days before Chitra.
- Only one person gives a talk between the one who teaches Zoology and Dev.
- The one who teaches Geography gives a talk either on Monday or on Sunday.
- Only four persons give talks between Chitra and the one who teaches Civics.
- Only three persons give talks between the one who teaches History and Farid.
- Gauri does not teach Chemistry.

On which day does Chitra give a talk?

- **A.** Sunday  _(error: off by one position)_
- **B.** Friday  _(error: off by one position)_
- **C.** Tuesday  _(error: counted from the opposite end)_
- **D.** Saturday ✅

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 subject assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Harsh gives a talk five days before Chitra.' and 'Chitra gives a talk three days after Aman.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Harsh (Civics); Tuesday – Gauri (Economics); Wednesday – Aman (History); Thursday – Dev (Botany); Friday – Esha (Chemistry); Saturday – Chitra (Zoology); Sunday – Farid (Geography).
4. Chitra is at Saturday.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-161 · L4 · hard · Day and week scheduling puzzle · officer

Seven persons – Aman, Chitra, Dev, Esha, Farid, Gauri and Harsh – each give a talk on a different day of the same week, from Monday to Sunday, one talk per day. Each of them teaches a different subject among Botany, Chemistry, Civics, Economics, Geography, History and Zoology.

- Chitra gives a talk three days after Aman.
- As many persons give talks after the one who teaches Economics as before Chitra.
- The one who teaches Botany gives a talk three days before Farid.
- Harsh gives a talk five days before Chitra.
- Only one person gives a talk between the one who teaches Zoology and Dev.
- The one who teaches Geography gives a talk either on Monday or on Sunday.
- Only four persons give talks between Chitra and the one who teaches Civics.
- Only three persons give talks between the one who teaches History and Farid.
- Gauri does not teach Chemistry.

Which of the following statements is true?

- **A.** As many persons give talks after the one who teaches Geography as before Esha.  _(error: false in the solved arrangement)_
- **B.** Only four persons give talks between Chitra and the one who teaches Chemistry.  _(error: false in the solved arrangement)_
- **C.** Only three persons give talks between Farid and the one who teaches Economics.  _(error: false in the solved arrangement)_
- **D.** As many persons give talks after the one who teaches History as before Esha. ✅

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 subject assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Harsh gives a talk five days before Chitra.' and 'Chitra gives a talk three days after Aman.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Harsh (Civics); Tuesday – Gauri (Economics); Wednesday – Aman (History); Thursday – Dev (Botany); Friday – Esha (Chemistry); Saturday – Chitra (Zoology); Sunday – Farid (Geography).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-162 · L4 · hard · Day and week scheduling puzzle · officer

Seven persons – Aman, Chitra, Dev, Esha, Farid, Gauri and Harsh – each give a talk on a different day of the same week, from Monday to Sunday, one talk per day. Each of them teaches a different subject among Botany, Chemistry, Civics, Economics, Geography, History and Zoology.

- Chitra gives a talk three days after Aman.
- As many persons give talks after the one who teaches Economics as before Chitra.
- The one who teaches Botany gives a talk three days before Farid.
- Harsh gives a talk five days before Chitra.
- Only one person gives a talk between the one who teaches Zoology and Dev.
- The one who teaches Geography gives a talk either on Monday or on Sunday.
- Only four persons give talks between Chitra and the one who teaches Civics.
- Only three persons give talks between the one who teaches History and Farid.
- Gauri does not teach Chemistry.

How many persons give talks after Gauri?

- **A.** Four  _(error: missed the extreme position)_
- **B.** Five ✅
- **C.** One  _(error: counted before instead of after)_
- **D.** Six  _(error: included the person named)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 5,040 subject assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Harsh gives a talk five days before Chitra.' and 'Chitra gives a talk three days after Aman.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Harsh (Civics); Tuesday – Gauri (Economics); Wednesday – Aman (History); Thursday – Dev (Botany); Friday – Esha (Chemistry); Saturday – Chitra (Zoology); Sunday – Farid (Geography).
4. Gauri is at Tuesday; 5 position(s) lie beyond it in that direction.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Count only the persons beyond the one named, in the stated direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-163 · L4 · hard · Day and week scheduling puzzle · officer

Six persons – Deepa, Firoz, Hina, Ishaan, Jaya and Karan – each give a talk on a different day of the same week, from Monday to Saturday, one talk per day. Each of them plays a different game among Badminton, Chess, Cricket, Hockey, Kabaddi and Tennis.

- Only one person gives a talk between Ishaan and Firoz, with Ishaan coming after Firoz.
- Hina gives a talk on the day immediately before Deepa.
- As many persons give talks after Hina as before the one who plays Badminton.
- Only two persons give talks between Jaya and the one who plays Chess, with Jaya coming after the one who plays Chess.
- Deepa does not play Kabaddi.
- The one who plays Cricket gives a talk two days before Deepa.
- Jaya gives a talk on the day immediately after the one who plays Tennis.
- Karan does not play Cricket.

Who plays Cricket?

- **A.** Ishaan  _(error: neighbour of the correct person)_
- **B.** Hina  _(error: neighbour of the correct person)_
- **C.** Firoz  _(error: no clue links this person to that attribute)_
- **D.** Jaya ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 sport assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person gives a talk between Ishaan and Firoz, with Ishaan coming after Firoz.' and 'Hina gives a talk on the day immediately before Deepa.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Firoz (Chess); Tuesday – Karan (Badminton); Wednesday – Ishaan (Tennis); Thursday – Jaya (Cricket); Friday – Hina (Kabaddi); Saturday – Deepa (Hockey).
4. Jaya plays Cricket.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Attribute clues often name the attribute, not the person; resolve them only after positions are fixed.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-164 · L4 · hard · Day and week scheduling puzzle · officer

Six persons – Deepa, Firoz, Hina, Ishaan, Jaya and Karan – each give a talk on a different day of the same week, from Monday to Saturday, one talk per day. Each of them plays a different game among Badminton, Chess, Cricket, Hockey, Kabaddi and Tennis.

- Only one person gives a talk between Ishaan and Firoz, with Ishaan coming after Firoz.
- Hina gives a talk on the day immediately before Deepa.
- As many persons give talks after Hina as before the one who plays Badminton.
- Only two persons give talks between Jaya and the one who plays Chess, with Jaya coming after the one who plays Chess.
- Deepa does not play Kabaddi.
- The one who plays Cricket gives a talk two days before Deepa.
- Jaya gives a talk on the day immediately after the one who plays Tennis.
- Karan does not play Cricket.

Who gives a talk on the day immediately before the one who plays Kabaddi?

- **A.** Firoz  _(error: not at the required position)_
- **B.** Jaya ✅
- **C.** Ishaan  _(error: counted one place too far)_
- **D.** Deepa  _(error: direction reversed (after instead of before))_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 sport assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person gives a talk between Ishaan and Firoz, with Ishaan coming after Firoz.' and 'Hina gives a talk on the day immediately before Deepa.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Firoz (Chess); Tuesday – Karan (Badminton); Wednesday – Ishaan (Tennis); Thursday – Jaya (Cricket); Friday – Hina (Kabaddi); Saturday – Deepa (Hockey).
4. The one who plays Kabaddi is at Friday; the person asked for is at Thursday, i.e. Jaya.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-165 · L4 · hard · Day and week scheduling puzzle · officer

Six persons – Deepa, Firoz, Hina, Ishaan, Jaya and Karan – each give a talk on a different day of the same week, from Monday to Saturday, one talk per day. Each of them plays a different game among Badminton, Chess, Cricket, Hockey, Kabaddi and Tennis.

- Only one person gives a talk between Ishaan and Firoz, with Ishaan coming after Firoz.
- Hina gives a talk on the day immediately before Deepa.
- As many persons give talks after Hina as before the one who plays Badminton.
- Only two persons give talks between Jaya and the one who plays Chess, with Jaya coming after the one who plays Chess.
- Deepa does not play Kabaddi.
- The one who plays Cricket gives a talk two days before Deepa.
- Jaya gives a talk on the day immediately after the one who plays Tennis.
- Karan does not play Cricket.

Which of the following statements is NOT true?

- **A.** Only three persons give talks between Deepa and Karan, with Deepa coming after Karan.  _(error: this statement is true in the solved arrangement)_
- **B.** Only one person gives a talk between Jaya and Karan, with Jaya coming after Karan.  _(error: this statement is true in the solved arrangement)_
- **C.** The one who plays Badminton gives a talk two days before the one who plays Cricket.  _(error: this statement is true in the solved arrangement)_
- **D.** Only one person gives a talk between Deepa and Hina, with Deepa coming after Hina. ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 sport assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only one person gives a talk between Ishaan and Firoz, with Ishaan coming after Firoz.' and 'Hina gives a talk on the day immediately before Deepa.'; then place the others by elimination.
3. Solved arrangement — Monday onwards: Monday – Firoz (Chess); Tuesday – Karan (Badminton); Wednesday – Ishaan (Tennis); Thursday – Jaya (Cricket); Friday – Hina (Kabaddi); Saturday – Deepa (Hockey).
4. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-166 · L1 · easy · Month and date scheduling puzzle · foundation

Five persons – Deepa, Ekta, Firoz, Hina and Ishaan – visit a museum on five different dates of the same year: the 10th of each of January, March, April, June and August. No two persons visit on the same date.

- Ishaan visits immediately after Ekta.
- Ekta is the first to visit.
- Deepa is the last to visit.
- Only one person visits between Ekta and Firoz.

Who visits on 10 March?

- **A.** Ishaan ✅
- **B.** Firoz  _(error: off by one position)_
- **C.** Ekta  _(error: off by one position)_
- **D.** Hina  _(error: counted from the opposite end)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Deepa is the last to visit.' and 'Ekta is the first to visit.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 10 January – Ekta; 10 March – Ishaan; 10 April – Firoz; 10 June – Hina; 10 August – Deepa.
4. 10 March is occupied by Ishaan.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Check which end the count starts from.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-167 · L2 · medium · Month and date scheduling puzzle · foundation

Five persons – Arjun, Charu, Uday, Vani and Yash – visit a museum on five different dates of the same year: the 16th of each of February, April, July, October and November. No two persons visit on the same date.

- Charu visits on 16 October.
- Charu visits immediately after Vani.
- Yash visits immediately after Uday.

On which date does Charu visit?

- **A.** 16 November  _(error: off by one position)_
- **B.** 16 April  _(error: counted from the opposite end)_
- **C.** 16 October ✅
- **D.** 16 July  _(error: off by one position)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Charu visits immediately after Vani.' and 'Charu visits on 16 October.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 16 February – Uday; 16 April – Yash; 16 July – Vani; 16 October – Charu; 16 November – Arjun.
4. Charu is at 16 October.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-168 · L2 · medium · Month and date scheduling puzzle · foundation

Six persons – Aman, Bela, Chitra, Esha, Farid and Harsh – visit a museum on six different dates of the same year: the 9th and 21st of each of April, July and November. No two persons visit on the same date.

- Only one person visits between Aman and Farid, with Aman visiting later than Farid.
- Esha visits in a month that has 30 days.
- Bela visits on some date after Chitra.
- Only two persons visit between Harsh and Bela, with Harsh visiting later than Bela.

Who visits immediately after Esha?

- **A.** Bela  _(error: not at the required position)_
- **B.** Harsh ✅
- **C.** Aman  _(error: direction reversed (before instead of after))_
- **D.** Chitra  _(error: not at the required position)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only two persons visit between Harsh and Bela, with Harsh visiting later than Bela.' and 'Only one person visits between Aman and Farid, with Aman visiting later than Farid.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 9 April – Chitra; 21 April – Farid; 9 July – Bela; 21 July – Aman; 9 November – Esha; 21 November – Harsh.
4. Esha is at 9 November; the person asked for is at 21 November, i.e. Harsh.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-169 · L2 · medium · Month and date scheduling puzzle · foundation

Six persons – Aman, Chitra, Dev, Esha, Gauri and Harsh – visit a museum on six different dates of the same year: the 5th and 18th of each of March, June and September. No two persons visit on the same date.

- As many persons visit after Esha as before Harsh.
- Chitra visits immediately after Harsh.
- Esha and Gauri visit in the same month.
- Esha visits immediately before Aman.

Who visits in the same month as Aman?

- **A.** Gauri  _(error: visits in a different month)_
- **B.** Esha  _(error: visits in the adjacent slot but a different month)_
- **C.** Chitra  _(error: visits in a different month)_
- **D.** Dev ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Chitra visits immediately after Harsh.' and 'Esha visits immediately before Aman.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 5 March – Gauri; 18 March – Esha; 5 June – Aman; 18 June – Dev; 5 September – Harsh; 18 September – Chitra.
4. Aman visits on 5 June; the other date of that month belongs to Dev.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Consecutive visitors need not share a month.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-170 · L2 · medium · Month and date scheduling puzzle · foundation

Six persons – Arjun, Charu, Tara, Uday, Vani and Zoya – visit a museum on six different dates of the same year: the 12th and 25th of each of January, May and June. No two persons visit on the same date.

- As many persons visit after Uday as before Vani.
- Arjun visits immediately after Zoya.
- Arjun visits on some date after Uday.
- Charu visits in a month that has 30 days.
- Arjun visits immediately before Charu.

On which date does Arjun visit?

- **A.** 25 May ✅
- **B.** 25 June  _(error: off by two positions)_
- **C.** 12 May  _(error: counted from the opposite end)_
- **D.** 12 June  _(error: off by one position)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 5 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Arjun visits immediately after Zoya.' and 'Arjun visits immediately before Charu.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 12 January – Uday; 25 January – Tara; 12 May – Zoya; 25 May – Arjun; 12 June – Charu; 25 June – Vani.
4. Arjun is at 25 May.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-171 · L3 · hard · Month and date scheduling puzzle · officer

Eight persons – Arjun, Bhumi, Charu, Tara, Uday, Vani, Yash and Zoya – visit a museum on eight different dates of the same year: the 7th and 22nd of each of March, April, July and September. No two persons visit on the same date.

- Charu visits in a month that has 31 days.
- Vani and Yash visit in the same month.
- Tara visits on some date after Arjun.
- Charu visits immediately before Bhumi.
- Only two persons visit between Bhumi and Uday.
- Only one person visits between Arjun and Charu.
- Only three persons visit between Yash and Zoya.

Who visits in the same month as Zoya?

- **A.** Uday  _(error: visits in the adjacent slot but a different month)_
- **B.** Arjun ✅
- **C.** Bhumi  _(error: visits in a different month)_
- **D.** Charu  _(error: visits in a different month)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Charu visits immediately before Bhumi.' and 'Only three persons visit between Yash and Zoya.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 7 March – Charu; 22 March – Bhumi; 7 April – Arjun; 22 April – Zoya; 7 July – Uday; 22 July – Tara; 7 September – Vani; 22 September – Yash.
4. Zoya visits on 22 April; the other date of that month belongs to Arjun.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Consecutive visitors need not share a month.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-172 · L3 · hard · Month and date scheduling puzzle · officer

Six persons – Aman, Chitra, Dev, Farid, Gauri and Harsh – visit a museum on six different dates of the same year: the 11th and 24th of each of February, May and August. No two persons visit on the same date. Each of them is from a different city among Agra, Chennai, Delhi, Indore, Jaipur and Patna.

- Farid is not from Jaipur.
- Only two persons visit between the one from Delhi and Harsh.
- Harsh visits immediately before Chitra.
- As many persons visit after Harsh as before Aman.
- Only two persons visit between Dev and the one from Patna, with Dev visiting later than the one from Patna.
- Only one person visits between the one from Indore and Farid.
- As many persons visit after the one from Patna as before Farid.
- Only one person visits between Aman and the one from Chennai.

Who visits immediately before the one from Jaipur?

- **A.** Dev  _(error: not at the required position)_
- **B.** Chitra  _(error: direction reversed (after instead of before))_
- **C.** Gauri ✅
- **D.** Aman  _(error: not at the required position)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 city assignments leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Harsh visits immediately before Chitra.' and 'As many persons visit after Harsh as before Aman.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 11 February – Gauri (Patna); 24 February – Harsh (Jaipur); 11 May – Chitra (Chennai); 24 May – Dev (Indore); 11 August – Aman (Delhi); 24 August – Farid (Agra).
4. The one from Jaipur is at 24 February; the person asked for is at 11 February, i.e. Gauri.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-173 · L4 · hard · Month and date scheduling puzzle · officer

Eight persons – Arjun, Bhumi, Charu, Tara, Uday, Vani, Yash and Zoya – visit a museum on eight different dates of the same year: the 8th and 19th of each of January, April, June and October. No two persons visit on the same date. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- Charu visits immediately after Yash.
- Only four persons visit between the one who likes Orange and the one who likes Apple.
- Arjun visits on some date after Vani.
- Uday visits immediately before Arjun.
- The one who likes Cherry visits on the 19th of a month.
- Arjun visits immediately after the one who likes Mango.
- Bhumi visits on the 19th of a month.
- As many persons visit after Arjun as before Charu.
- Only four persons visit between the one who likes Papaya and Vani.
- The one who likes Apple visits on some date after Arjun.
- Only five persons visit between the one who likes Banana and Vani, with the one who likes Banana visiting later than Vani.
- Arjun visits in a month that has 30 days.
- The one who likes Guava visits immediately after Tara.
- Charu visits on the 19th of a month.

On which date does Arjun visit?

- **A.** 19 June  _(error: counted from the opposite end)_
- **B.** 19 April  _(error: off by one position)_
- **C.** 19 January  _(error: off by one position)_
- **D.** 8 April ✅

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 14 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Charu visits immediately after Yash.' and 'Uday visits immediately before Arjun.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 8 January – Vani (Litchi); 19 January – Uday (Mango); 8 April – Arjun (Orange); 19 April – Tara (Cherry); 8 June – Yash (Guava); 19 June – Charu (Papaya); 8 October – Zoya (Banana); 19 October – Bhumi (Apple).
4. Arjun is at 8 April.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the position from the correct end.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-174 · L4 · hard · Month and date scheduling puzzle · officer

Eight persons – Arjun, Bhumi, Charu, Tara, Uday, Vani, Yash and Zoya – visit a museum on eight different dates of the same year: the 8th and 19th of each of January, April, June and October. No two persons visit on the same date. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- Charu visits immediately after Yash.
- Only four persons visit between the one who likes Orange and the one who likes Apple.
- Arjun visits on some date after Vani.
- Uday visits immediately before Arjun.
- The one who likes Cherry visits on the 19th of a month.
- Arjun visits immediately after the one who likes Mango.
- Bhumi visits on the 19th of a month.
- As many persons visit after Arjun as before Charu.
- Only four persons visit between the one who likes Papaya and Vani.
- The one who likes Apple visits on some date after Arjun.
- Only five persons visit between the one who likes Banana and Vani, with the one who likes Banana visiting later than Vani.
- Arjun visits in a month that has 30 days.
- The one who likes Guava visits immediately after Tara.
- Charu visits on the 19th of a month.

Who visits in the same month as Yash?

- **A.** Bhumi  _(error: visits in a different month)_
- **B.** Arjun  _(error: visits in a different month)_
- **C.** Charu ✅
- **D.** Tara  _(error: visits in the adjacent slot but a different month)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 14 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Charu visits immediately after Yash.' and 'Uday visits immediately before Arjun.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 8 January – Vani (Litchi); 19 January – Uday (Mango); 8 April – Arjun (Orange); 19 April – Tara (Cherry); 8 June – Yash (Guava); 19 June – Charu (Papaya); 8 October – Zoya (Banana); 19 October – Bhumi (Apple).
4. Yash visits on 8 June; the other date of that month belongs to Charu.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Consecutive visitors need not share a month.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-175 · L4 · hard · Month and date scheduling puzzle · officer

Eight persons – Arjun, Bhumi, Charu, Tara, Uday, Vani, Yash and Zoya – visit a museum on eight different dates of the same year: the 8th and 19th of each of January, April, June and October. No two persons visit on the same date. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- Charu visits immediately after Yash.
- Only four persons visit between the one who likes Orange and the one who likes Apple.
- Arjun visits on some date after Vani.
- Uday visits immediately before Arjun.
- The one who likes Cherry visits on the 19th of a month.
- Arjun visits immediately after the one who likes Mango.
- Bhumi visits on the 19th of a month.
- As many persons visit after Arjun as before Charu.
- Only four persons visit between the one who likes Papaya and Vani.
- The one who likes Apple visits on some date after Arjun.
- Only five persons visit between the one who likes Banana and Vani, with the one who likes Banana visiting later than Vani.
- Arjun visits in a month that has 30 days.
- The one who likes Guava visits immediately after Tara.
- Charu visits on the 19th of a month.

Which fruit does Arjun like?

- **A.** Orange ✅
- **B.** Mango  _(error: attribute of Uday, a neighbour of Arjun)_
- **C.** Cherry  _(error: attribute of Tara, a neighbour of Arjun)_
- **D.** Banana  _(error: attribute of Zoya)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 14 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Charu visits immediately after Yash.' and 'Uday visits immediately before Arjun.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 8 January – Vani (Litchi); 19 January – Uday (Mango); 8 April – Arjun (Orange); 19 April – Tara (Cherry); 8 June – Yash (Guava); 19 June – Charu (Papaya); 8 October – Zoya (Banana); 19 October – Bhumi (Apple).
4. Arjun likes Orange in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-176 · L4 · hard · Month and date scheduling puzzle · officer

Eight persons – Arjun, Bhumi, Charu, Tara, Uday, Vani, Yash and Zoya – visit a museum on eight different dates of the same year: the 8th and 19th of each of January, April, June and October. No two persons visit on the same date. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- Charu visits immediately after Yash.
- Only four persons visit between the one who likes Orange and the one who likes Apple.
- Arjun visits on some date after Vani.
- Uday visits immediately before Arjun.
- The one who likes Cherry visits on the 19th of a month.
- Arjun visits immediately after the one who likes Mango.
- Bhumi visits on the 19th of a month.
- As many persons visit after Arjun as before Charu.
- Only four persons visit between the one who likes Papaya and Vani.
- The one who likes Apple visits on some date after Arjun.
- Only five persons visit between the one who likes Banana and Vani, with the one who likes Banana visiting later than Vani.
- Arjun visits in a month that has 30 days.
- The one who likes Guava visits immediately after Tara.
- Charu visits on the 19th of a month.

Which of the following statements is true?

- **A.** Only two persons visit between Zoya and Tara, with Zoya visiting later than Tara. ✅
- **B.** Only three persons visit between Tara and Zoya, with Tara visiting later than Zoya.  _(error: false in the solved arrangement)_
- **C.** Only one person visits between Charu and Zoya, with Charu visiting later than Zoya.  _(error: false in the solved arrangement)_
- **D.** Only two persons visit between Bhumi and Tara, with Bhumi visiting later than Tara.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 14 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Charu visits immediately after Yash.' and 'Uday visits immediately before Arjun.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 8 January – Vani (Litchi); 19 January – Uday (Mango); 8 April – Arjun (Orange); 19 April – Tara (Cherry); 8 June – Yash (Guava); 19 June – Charu (Papaya); 8 October – Zoya (Banana); 19 October – Bhumi (Apple).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-177 · L4 · hard · Month and date scheduling puzzle · officer

Eight persons – Arjun, Bhumi, Charu, Tara, Uday, Vani, Yash and Zoya – visit a museum on eight different dates of the same year: the 8th and 19th of each of January, April, June and October. No two persons visit on the same date. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- Charu visits immediately after Yash.
- Only four persons visit between the one who likes Orange and the one who likes Apple.
- Arjun visits on some date after Vani.
- Uday visits immediately before Arjun.
- The one who likes Cherry visits on the 19th of a month.
- Arjun visits immediately after the one who likes Mango.
- Bhumi visits on the 19th of a month.
- As many persons visit after Arjun as before Charu.
- Only four persons visit between the one who likes Papaya and Vani.
- The one who likes Apple visits on some date after Arjun.
- Only five persons visit between the one who likes Banana and Vani, with the one who likes Banana visiting later than Vani.
- Arjun visits in a month that has 30 days.
- The one who likes Guava visits immediately after Tara.
- Charu visits on the 19th of a month.

How many persons visit between Tara and Zoya?

- **A.** Four  _(error: counted both named persons)_
- **B.** Three  _(error: counted one of the two named persons)_
- **C.** Two ✅
- **D.** One  _(error: counted one short)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 14 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Charu visits immediately after Yash.' and 'Uday visits immediately before Arjun.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 8 January – Vani (Litchi); 19 January – Uday (Mango); 8 April – Arjun (Orange); 19 April – Tara (Cherry); 8 June – Yash (Guava); 19 June – Charu (Papaya); 8 October – Zoya (Banana); 19 October – Bhumi (Apple).
4. Tara is at 19 April and Zoya at 8 October; 2 position(s) lie strictly between them.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Between' excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-178 · L4 · hard · Month and date scheduling puzzle · officer

Six persons – Aman, Chitra, Dev, Esha, Farid and Harsh – visit a museum on six different dates of the same year: the 6th and 17th of each of March, June and November. No two persons visit on the same date. Each of them plays a different game among Badminton, Chess, Football, Hockey, Kabaddi and Tennis.

- Chitra visits immediately before the one who plays Football.
- Only two persons visit between Dev and Esha.
- Dev does not play Chess.
- Chitra and Farid do not visit in the same month.
- Only one person visits between the one who plays Hockey and Harsh.
- As many persons visit after the one who plays Badminton as before Esha.
- As many persons visit after Dev as before Farid.
- The one who plays Kabaddi is either the first or the last to visit.
- Aman and Esha visit in the same month.

Who visits immediately after the one who plays Hockey?

- **A.** Aman ✅
- **B.** Dev  _(error: direction reversed (before instead of after))_
- **C.** Chitra  _(error: not at the required position)_
- **D.** Esha  _(error: counted one place too far)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 sport assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Aman and Esha visit in the same month.' and 'As many persons visit after Dev as before Farid.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 6 March – Chitra (Badminton); 17 March – Harsh (Football); 6 June – Dev (Tennis); 17 June – Farid (Hockey); 6 November – Aman (Chess); 17 November – Esha (Kabaddi).
4. The one who plays Hockey is at 17 June; the person asked for is at 6 November, i.e. Aman.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Keep the direction fixed by the question; one-off counting and reversed direction are the usual slips.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-179 · L4 · hard · Month and date scheduling puzzle · officer

Six persons – Aman, Chitra, Dev, Esha, Farid and Harsh – visit a museum on six different dates of the same year: the 6th and 17th of each of March, June and November. No two persons visit on the same date. Each of them plays a different game among Badminton, Chess, Football, Hockey, Kabaddi and Tennis.

- Chitra visits immediately before the one who plays Football.
- Only two persons visit between Dev and Esha.
- Dev does not play Chess.
- Chitra and Farid do not visit in the same month.
- Only one person visits between the one who plays Hockey and Harsh.
- As many persons visit after the one who plays Badminton as before Esha.
- As many persons visit after Dev as before Farid.
- The one who plays Kabaddi is either the first or the last to visit.
- Aman and Esha visit in the same month.

How many persons visit after Aman?

- **A.** One ✅
- **B.** Two  _(error: included the person named)_
- **C.** None  _(error: missed the extreme position)_
- **D.** Four  _(error: counted before instead of after)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 sport assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Aman and Esha visit in the same month.' and 'As many persons visit after Dev as before Farid.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 6 March – Chitra (Badminton); 17 March – Harsh (Football); 6 June – Dev (Tennis); 17 June – Farid (Hockey); 6 November – Aman (Chess); 17 November – Esha (Kabaddi).
4. Aman is at 6 November; 1 position(s) lie beyond it in that direction.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Count only the persons beyond the one named, in the stated direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-180 · L4 · hard · Month and date scheduling puzzle · officer

Six persons – Aman, Chitra, Dev, Esha, Farid and Harsh – visit a museum on six different dates of the same year: the 6th and 17th of each of March, June and November. No two persons visit on the same date. Each of them plays a different game among Badminton, Chess, Football, Hockey, Kabaddi and Tennis.

- Chitra visits immediately before the one who plays Football.
- Only two persons visit between Dev and Esha.
- Dev does not play Chess.
- Chitra and Farid do not visit in the same month.
- Only one person visits between the one who plays Hockey and Harsh.
- As many persons visit after the one who plays Badminton as before Esha.
- As many persons visit after Dev as before Farid.
- The one who plays Kabaddi is either the first or the last to visit.
- Aman and Esha visit in the same month.

Which of the following statements is NOT true?

- **A.** Aman visits immediately after the one who plays Badminton. ✅
- **B.** Dev visits immediately after the one who plays Football.  _(error: this statement is true in the solved arrangement)_
- **C.** The one who plays Hockey visits in a month that has 30 days.  _(error: this statement is true in the solved arrangement)_
- **D.** The one who plays Tennis and Farid visit in the same month.  _(error: this statement is true in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 720 sport assignments leaves exactly one arrangement that satisfies all 9 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Aman and Esha visit in the same month.' and 'As many persons visit after Dev as before Farid.'; then place the others by elimination.
3. Solved arrangement — Chronological order: 6 March – Chitra (Badminton); 17 March – Harsh (Football); 6 June – Dev (Tennis); 17 June – Farid (Hockey); 6 November – Aman (Chess); 17 November – Esha (Kabaddi).
4. This statement fails in the unique arrangement; the other three hold.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-181 · L1 · easy · Odd-one-out within an arrangement · foundation

Five persons – S, T, U, V and W – sit in a straight row, all facing north.

- As many persons sit to the right of S as to the left of T.
- W sits immediately to the left of T.
- T sits third to the left of V.

Which of the following statements is true?

- **A.** Only two persons sit between S and W. ✅
- **B.** Only one person sits between S and U.  _(error: false in the solved arrangement)_
- **C.** Only three persons sit between U and V.  _(error: false in the solved arrangement)_
- **D.** Only two persons sit between V and W.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'T sits third to the left of V.' and 'As many persons sit to the right of S as to the left of T.'; then place the others by elimination.
3. Solved arrangement — Left to right: 1st from the left end – W; 2nd from the left end – T; 3rd from the left end – U; 4th from the left end – S; 5th from the left end – V.
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-182 · L2 · medium · Odd-one-out within an arrangement · foundation

Six persons – J, K, L, M, N and P – sit around a circular table, all facing the centre.

- N sits second to the left of M.
- J sits second to the left of K.
- M sits immediately to the left of J.
- L is not an immediate neighbour of N.

In each pair below, the second member bears a certain positional relation to the first. Three of the four pairs are alike in that relation and so form a group. Which pair does not belong to the group?

- **A.** L – J  _(error: belongs to the group: immediately to the left of)_
- **B.** M – P  _(error: belongs to the group: immediately to the left of)_
- **C.** J – P ✅
- **D.** N – K  _(error: belongs to the group: immediately to the left of)_

**Working**

1. Exhaustive enumeration over 120 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'J sits second to the left of K.' and 'M sits immediately to the left of J.'; then place the others by elimination.
3. Solved arrangement — Clockwise from J: J; M; P; N; K; L.
4. In three pairs the second member is immediately to the left of the first; in J – P it is second to the left of.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Measure every pair from the first member's own position (and facing); do not mix up the direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-183 · L2 · medium · Odd-one-out within an arrangement · foundation

Six persons – E, F, G, H, J and K – live on the six floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 6.

- Only two persons live between K and E, and K lives above E.
- Only one person lives between F and J, and F lives above J.
- The number of persons living above K is the same as the number of persons living below H.

Three of the following four are alike in a certain way based on their positions in the arrangement and so form a group. Which one does not belong to that group?

- **A.** F  _(error: belongs to the group (on even-numbered floors))_
- **B.** K  _(error: belongs to the group (on even-numbered floors))_
- **C.** J  _(error: belongs to the group (on even-numbered floors))_
- **D.** H ✅

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 3 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Only two persons live between K and E, and K lives above E.' and 'Only one person lives between F and J, and F lives above J.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – H; Floor 2 – J; Floor 3 – E; Floor 4 – F; Floor 5 – G; Floor 6 – K.
4. K, J, F are all on even-numbered floors; H is not.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Look for the positional property the three share, not for the letters' alphabetical pattern.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-184 · L2 · medium · Odd-one-out within an arrangement · foundation

Six persons – E, F, G, H, J and K – live on the six floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 6.

- E lives four floors above H.
- J lives on the floor immediately above F.
- The number of persons living above F is the same as the number of persons living below J.
- G lives three floors above H.

In each pair below, the second member bears a certain positional relation to the first. Three of the four pairs are alike in that relation and so form a group. Which pair does not belong to the group?

- **A.** F – E  _(error: belongs to the group: three places above)_
- **B.** K – J  _(error: belongs to the group: three places above)_
- **C.** G – J ✅
- **D.** H – G  _(error: belongs to the group: three places above)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders leaves exactly one arrangement that satisfies all 4 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'E lives four floors above H.' and 'G lives three floors above H.'; then place the others by elimination.
3. Solved arrangement — Floor 1 (lowest) upwards: Floor 1 – K; Floor 2 – H; Floor 3 – F; Floor 4 – J; Floor 5 – G; Floor 6 – E.
4. In three pairs the second member is three places above the first; in G – J it is one place below.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Measure every pair from the first member's own position (and facing); do not mix up the direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-185 · L2 · medium · Odd-one-out within an arrangement · foundation

Six persons – D, E, F, G, H and J – sit around a rectangular table: two sit on each of the longer sides and one sits at each of the shorter sides, all facing the centre.

- G is an immediate neighbour of H.
- G sits second to the right of D.
- F sits at one of the shorter sides of the table.
- G sits on one of the longer sides of the table.
- F sits second to the right of E.

Three of the following four are alike in a certain way based on their positions in the arrangement and so form a group. Which one does not belong to that group?

- **A.** H  _(error: belongs to the group (seated on the longer sides))_
- **B.** D  _(error: belongs to the group (seated on the longer sides))_
- **C.** E  _(error: belongs to the group (seated on the longer sides))_
- **D.** F ✅

**Working**

1. Exhaustive enumeration over 360 seat/position orders leaves exactly one arrangement that satisfies all 5 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'F sits second to the right of E.' and 'G sits second to the right of D.'; then place the others by elimination.
3. Solved arrangement — Clockwise from F: F [shorter side]; D [longer side]; E [longer side]; J [shorter side]; H [longer side]; G [longer side].
4. H, D, E are all seated on the longer sides; F is not.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Look for the positional property the three share, not for the letters' alphabetical pattern.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-186 · L3 · hard · Odd-one-out within an arrangement · officer

Eight persons – P, Q, R, S, T, U, V and W – sit around a square table: four sit at the four corners and four sit one at the middle of each side, all facing the centre.

- U is not an immediate neighbour of W.
- Q sits at one of the corners.
- Q sits immediately to the right of W.
- S sits second to the left of V.
- R sits third to the right of P.
- W sits third to the right of R.

Three of the following four are alike in a certain way based on their positions in the arrangement and so form a group. Which one does not belong to that group?

- **A.** V  _(error: belongs to the group (seated at the middle of sides))_
- **B.** W  _(error: belongs to the group (seated at the middle of sides))_
- **C.** P  _(error: belongs to the group (seated at the middle of sides))_
- **D.** Q ✅

**Working**

1. Exhaustive enumeration over 10,080 seat/position orders leaves exactly one arrangement that satisfies all 6 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'Q sits immediately to the right of W.' and 'R sits third to the right of P.'; then place the others by elimination.
3. Solved arrangement — Clockwise from U: U [corner]; P [middle of side]; Q [corner]; W [middle of side]; T [corner]; V [middle of side]; R [corner]; S [middle of side].
4. P, V, W are all seated at the middle of sides; Q is not.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Look for the positional property the three share, not for the letters' alphabetical pattern.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-187 · L3 · hard · Odd-one-out within an arrangement · officer

Seven persons – D, E, F, G, H, J and K – sit around a circular table. Some of them face the centre and the others face away from the centre.

- E sits immediately to the right of D.
- E sits immediately to the right of F.
- Both immediate neighbours of D face the centre.
- E sits third to the right of G.
- F sits second to the left of J.
- H sits second to the right of E.
- F sits immediately to the right of H.

In each pair below, the second member bears a certain positional relation to the first. Three of the four pairs are alike in that relation and so form a group. Which pair does not belong to the group?

- **A.** H – J ✅
- **B.** G – E  _(error: belongs to the group: third to the right of)_
- **C.** F – K  _(error: belongs to the group: third to the right of)_
- **D.** J – D  _(error: belongs to the group: third to the right of)_

**Working**

1. Exhaustive enumeration over 720 seat/position orders × 126 facing patterns leaves exactly one arrangement that satisfies all 7 conditions (uniqueness asserted by the builder's solver).
2. Solved arrangement — Clockwise from D: D [faces centre]; K [faces centre]; G [faces centre]; J [faces centre]; H [faces outside]; F [faces outside]; E [faces centre].
3. In three pairs the second member is third to the right of the first; in H – J it is immediately to the left of.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Measure every pair from the first member's own position (and facing); do not mix up the direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-188 · L4 · hard · Odd-one-out within an arrangement · officer

Eight persons – E, F, G, H, J, K, L and M – sit around a circular table, all facing the centre. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- H is an immediate neighbour of K.
- F sits second to the right of H.
- E sits third to the left of the one who likes Orange.
- G sits second to the right of the one who likes Litchi.
- E sits third to the right of L.
- Only one person sits between M and the one who likes Apple when counted from the right of M.
- H sits immediately to the left of L.
- L does not like Cherry.
- J sits immediately to the left of the one who likes Mango.
- The one who likes Banana sits second to the left of K.
- G sits third to the right of the one who likes Guava.

In each pair below, the second member bears a certain positional relation to the first. Three of the four pairs are alike in that relation and so form a group. Which pair does not belong to the group?

- **A.** L – M  _(error: belongs to the group: third to the left of)_
- **B.** K – E  _(error: belongs to the group: third to the left of)_
- **C.** H – K ✅
- **D.** J – H  _(error: belongs to the group: third to the left of)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'E sits third to the right of L.' and 'F sits second to the right of H.'; then place the others by elimination.
3. Solved arrangement — Clockwise from E: E (Mango); J (Litchi); F (Guava); L (Papaya); H (Apple); K (Orange); M (Cherry); G (Banana).
4. In three pairs the second member is third to the left of the first; in H – K it is immediately to the left of.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Measure every pair from the first member's own position (and facing); do not mix up the direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-189 · L4 · hard · Odd-one-out within an arrangement · officer

Eight persons – E, F, G, H, J, K, L and M – sit around a circular table, all facing the centre. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- H is an immediate neighbour of K.
- F sits second to the right of H.
- E sits third to the left of the one who likes Orange.
- G sits second to the right of the one who likes Litchi.
- E sits third to the right of L.
- Only one person sits between M and the one who likes Apple when counted from the right of M.
- H sits immediately to the left of L.
- L does not like Cherry.
- J sits immediately to the left of the one who likes Mango.
- The one who likes Banana sits second to the left of K.
- G sits third to the right of the one who likes Guava.

Consider the pairs below. In each, the second member bears a certain positional relation to the first. Three of the four pairs are alike in that relation and so form a group. Which pair does not belong to the group?

- **A.** G – E  _(error: belongs to the group: immediately to the left of)_
- **B.** L – K ✅
- **C.** F – L  _(error: belongs to the group: immediately to the left of)_
- **D.** K – M  _(error: belongs to the group: immediately to the left of)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'E sits third to the right of L.' and 'F sits second to the right of H.'; then place the others by elimination.
3. Solved arrangement — Clockwise from E: E (Mango); J (Litchi); F (Guava); L (Papaya); H (Apple); K (Orange); M (Cherry); G (Banana).
4. In three pairs the second member is immediately to the left of the first; in L – K it is second to the left of.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Measure every pair from the first member's own position (and facing); do not mix up the direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-190 · L4 · hard · Odd-one-out within an arrangement · officer

Eight persons – E, F, G, H, J, K, L and M – sit around a circular table, all facing the centre. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- H is an immediate neighbour of K.
- F sits second to the right of H.
- E sits third to the left of the one who likes Orange.
- G sits second to the right of the one who likes Litchi.
- E sits third to the right of L.
- Only one person sits between M and the one who likes Apple when counted from the right of M.
- H sits immediately to the left of L.
- L does not like Cherry.
- J sits immediately to the left of the one who likes Mango.
- The one who likes Banana sits second to the left of K.
- G sits third to the right of the one who likes Guava.

Who sits immediately to the right of E?

- **A.** M  _(error: counted one seat too far)_
- **B.** J  _(error: direction reversed)_
- **C.** F  _(error: not at that seat)_
- **D.** G ✅

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'E sits third to the right of L.' and 'F sits second to the right of H.'; then place the others by elimination.
3. Solved arrangement — Clockwise from E: E (Mango); J (Litchi); F (Guava); L (Papaya); H (Apple); K (Orange); M (Cherry); G (Banana).
4. E faces the centre, so E's right runs anticlockwise; 1 seat(s) that way is G.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** For a person facing the centre, right is anticlockwise; for one facing outside, right is clockwise.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-191 · L4 · hard · Odd-one-out within an arrangement · officer

Eight persons – E, F, G, H, J, K, L and M – sit around a circular table, all facing the centre. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- H is an immediate neighbour of K.
- F sits second to the right of H.
- E sits third to the left of the one who likes Orange.
- G sits second to the right of the one who likes Litchi.
- E sits third to the right of L.
- Only one person sits between M and the one who likes Apple when counted from the right of M.
- H sits immediately to the left of L.
- L does not like Cherry.
- J sits immediately to the left of the one who likes Mango.
- The one who likes Banana sits second to the left of K.
- G sits third to the right of the one who likes Guava.

Which fruit does M like?

- **A.** Cherry ✅
- **B.** Orange  _(error: attribute of K, a neighbour of M)_
- **C.** Apple  _(error: attribute of H)_
- **D.** Banana  _(error: attribute of G, a neighbour of M)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'E sits third to the right of L.' and 'F sits second to the right of H.'; then place the others by elimination.
3. Solved arrangement — Clockwise from E: E (Mango); J (Litchi); F (Guava); L (Papaya); H (Apple); K (Orange); M (Cherry); G (Banana).
4. M likes Cherry in the solved arrangement.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Read the attribute off the solved arrangement, not off the nearest clue that mentions it.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-192 · L4 · hard · Odd-one-out within an arrangement · officer

Eight persons – E, F, G, H, J, K, L and M – sit around a circular table, all facing the centre. Each of them likes a different fruit among Apple, Banana, Cherry, Guava, Litchi, Mango, Orange and Papaya.

- H is an immediate neighbour of K.
- F sits second to the right of H.
- E sits third to the left of the one who likes Orange.
- G sits second to the right of the one who likes Litchi.
- E sits third to the right of L.
- Only one person sits between M and the one who likes Apple when counted from the right of M.
- H sits immediately to the left of L.
- L does not like Cherry.
- J sits immediately to the left of the one who likes Mango.
- The one who likes Banana sits second to the left of K.
- G sits third to the right of the one who likes Guava.

Which of the following statements is true?

- **A.** Only two persons sit between the one who likes Litchi and E when counted from the left of the one who likes Litchi.  _(error: false in the solved arrangement)_
- **B.** Only two persons sit between the one who likes Banana and F when counted from the left of the one who likes Banana. ✅
- **C.** Only one person sits between the one who likes Orange and J when counted from the right of the one who likes Orange.  _(error: false in the solved arrangement)_
- **D.** Only two persons sit between the one who likes Banana and M when counted from the right of the one who likes Banana.  _(error: false in the solved arrangement)_

**Working**

1. Exhaustive enumeration over 5,040 seat/position orders × 40,320 fruit assignments leaves exactly one arrangement that satisfies all 11 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'E sits third to the right of L.' and 'F sits second to the right of H.'; then place the others by elimination.
3. Solved arrangement — Clockwise from E: E (Mango); J (Litchi); F (Guava); L (Papaya); H (Apple); K (Orange); M (Cherry); G (Banana).
4. Only this statement holds in the unique arrangement; each of the others contradicts it.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Test every option against the final arrangement; a statement that merely sounds like a clue is not automatically true.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-193 · L4 · hard · Odd-one-out within an arrangement · officer

Eight persons – J, K, L, M, N, P, Q and R – live in a four-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 4. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B.

- P lives to the east of L on the same floor.
- J and Q live on the same floor.
- N lives directly above Q.
- K lives in Flat B.
- N lives on a higher floor than M.
- Q and R live in the same type of flat.
- M and Q live on adjacent floors but in different types of flat.
- K lives on an even-numbered floor.

Three of the following four are alike in a certain way based on their positions in the arrangement and so form a group. Which one does not belong to that group?

- **A.** P  _(error: belongs to the group (in Flat B))_
- **B.** L ✅
- **C.** K  _(error: belongs to the group (in Flat B))_
- **D.** M  _(error: belongs to the group (in Flat B))_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'P lives to the east of L on the same floor.' and 'N lives directly above Q.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 4: A – N, B – K; floor 3: A – Q, B – J; floor 2: A – R, B – M; floor 1: A – L, B – P.
4. M, P, K are all in Flat B; L is not.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Look for the positional property the three share, not for the letters' alphabetical pattern.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-194 · L4 · hard · Odd-one-out within an arrangement · officer

Eight persons – J, K, L, M, N, P, Q and R – live in a four-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 4. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B.

- P lives to the east of L on the same floor.
- J and Q live on the same floor.
- N lives directly above Q.
- K lives in Flat B.
- N lives on a higher floor than M.
- Q and R live in the same type of flat.
- M and Q live on adjacent floors but in different types of flat.
- K lives on an even-numbered floor.

In each pair below, the second member bears a certain positional relation to the first. Three of the four pairs are alike in that relation and so form a group. Which pair does not belong to the group?

- **A.** J – K ✅
- **B.** N – J  _(error: belongs to the group: one floor below, to the east (Flat B) of)_
- **C.** R – P  _(error: belongs to the group: one floor below, to the east (Flat B) of)_
- **D.** Q – M  _(error: belongs to the group: one floor below, to the east (Flat B) of)_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'P lives to the east of L on the same floor.' and 'N lives directly above Q.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 4: A – N, B – K; floor 3: A – Q, B – J; floor 2: A – R, B – M; floor 1: A – L, B – P.
4. In three pairs the second member is one floor below, to the east (Flat B) of the first; in J – K it is one floor above, in the same flat type of.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** Measure every pair from the first member's own position (and facing); do not mix up the direction.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-195 · L4 · hard · Odd-one-out within an arrangement · officer

Eight persons – J, K, L, M, N, P, Q and R – live in a four-storey building, one person per flat. The lowermost floor is floor 1 and the topmost is floor 4. Each floor has two flats: Flat A on the west and Flat B on the east; Flat A of every floor is directly above Flat A of the floor below, and likewise for Flat B.

- P lives to the east of L on the same floor.
- J and Q live on the same floor.
- N lives directly above Q.
- K lives in Flat B.
- N lives on a higher floor than M.
- Q and R live in the same type of flat.
- M and Q live on adjacent floors but in different types of flat.
- K lives on an even-numbered floor.

Who lives directly above L?

- **A.** P  _(error: neighbour on the same floor)_
- **B.** R ✅
- **C.** J  _(error: not directly above)_
- **D.** M  _(error: same floor as the flat above, but the other type (diagonal))_

**Working**

1. Exhaustive enumeration over 40,320 seat/position orders leaves exactly one arrangement that satisfies all 8 conditions (uniqueness asserted by the builder's solver).
2. Start from the most restrictive position clue(s): 'P lives to the east of L on the same floor.' and 'N lives directly above Q.'; then place the others by elimination.
3. Solved arrangement — Top to bottom — floor 4: A – N, B – K; floor 3: A – Q, B – J; floor 2: A – R, B – M; floor 1: A – L, B – P.
4. L is in Flat A, floor 1; directly above is Flat A, floor 2 – R.

**Formula:** Unique arrangement by exhaustive case enumeration (itertools brute force)  
**Trap:** 'Directly above/below' keeps the same flat type (A over A, B over B).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-196 · L1 · easy · Row with unknown number of persons · foundation

In a row of students facing north, R is 14th from the left end and 19th from the right end. How many students are there in the row?

- **A.** 31  _(error: subtracted one extra)_
- **B.** 33  _(error: added the two positions without removing R's double count)_
- **C.** 32 ✅
- **D.** 6  _(error: subtracted the positions)_

**Working**

1. R is counted in both positions, so total = 14 + 19 − 1 = 32.
2. Enumeration over every row length confirms 32 is the only length consistent with both statements.

**Formula:** Total = left position + right position − 1  
**Trap:** R is included in both counts.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-197 · L1 · easy · Row with unknown number of persons · foundation

In a row of girls facing north, Meena is 9th from the left end and Sheela is 16th from the right end. If they interchange their positions, Meena becomes 21st from the left end. How many girls are there in the row?

- **A.** 29  _(error: added Meena's two left positions)_
- **B.** 37  _(error: did not subtract the common count)_
- **C.** 36 ✅
- **D.** 24  _(error: used Meena's original position with Sheela's)_

**Working**

1. After interchange Meena takes Sheela's seat, so Sheela's seat is 21st from the left and 16th from the right.
2. Total = 21 + 16 − 1 = 36.

**Formula:** Total = (new left position) + (Sheela's right position) − 1  
**Trap:** The new position belongs to the other person's original seat.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-198 · L2 · medium · Row with unknown number of persons · foundation

In a row of persons facing north, P is 7th from the left end and Q is 11th from the right end. Exactly four persons sit between P and Q, and Q is to the right of P. How many persons are there in the row?

- **A.** 23  _(error: counted one extra)_
- **B.** 21  _(error: treated P and Q as counted twice)_
- **C.** 18  _(error: ignored the persons between them)_
- **D.** 22 ✅

**Working**

1. Seats: P at 7, then 4 persons, Q at 12 from the left.
2. Q is 11th from the right, so n = 12 + 11 − 1 = 22.

**Formula:** n = P(left) + persons between + Q(right)  
**Trap:** P and Q do not overlap here, so nothing is subtracted.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-199 · L2 · medium · Row with unknown number of persons · foundation

In a row of children facing north, Anu is 10th from the left end and Binu is 8th from the right end. Exactly three children sit between them. What is the minimum possible number of children in the row?

- **A.** 21  _(error: assumed Anu must be to the left of Binu)_
- **B.** 17  _(error: treated Anu and Binu as the same child)_
- **C.** 12  _(error: subtracted one extra)_
- **D.** 13 ✅

**Working**

1. Case 1: Binu to the right of Anu → Binu at seat 14 → n = 14 + 8 − 1 = 21.
2. Case 2: Binu to the left of Anu → Binu at seat 6 → n = 6 + 8 − 1 = 13.
3. Enumeration over n = 1…60 finds only n = 13 and n = 21; the minimum is 13.

**Formula:** Check both relative orders; minimum comes from the overlapping case  
**Trap:** The two named persons can be on either side of each other.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-200 · L2 · medium · Row with unknown number of persons · foundation

Some persons sit in a single row, all facing north. K, L, M and N are among them; the total number of persons in the row is not given.

- As many persons sit to the left of L as to the right of M.
- Exactly six persons sit between L and M, and L is to the right of M.
- If K and M interchange their positions, K becomes 4th from the left end.
- L is 5th to the right of N.
- K is 4th to the right of N.

How many persons sit in the row?

- **A.** 13  _(error: left out one end seat)_
- **B.** 14 ✅
- **C.** 15  _(error: counted one seat extra at an end)_
- **D.** 16  _(error: counted both anchor persons again)_

**Working**

1. The builder enumerates every row length from 4 to 60 and every placement of the 4 named persons; exactly one combination satisfies all 5 statements: n = 14.
2. Seats from the left: M – seat 4, N – seat 6, K – seat 10, L – seat 11.
3. The unique placement needs exactly 14 seats (leftmost occupied seat is 1, rightmost is 14).

**Formula:** Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues  
**Trap:** Total = (position from left) + (position from right) − 1 for the same person.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-201 · L3 · hard · Row with unknown number of persons · officer

Some persons sit in a single row, all facing north. D, E, F, G and H are among them; the total number of persons in the row is not given.

- H is 9th from the right end.
- Exactly seven persons sit between D and F, and D is to the right of F.
- Exactly six persons sit between G and E, and G is to the right of E.
- F is 5th from the left end.
- If E and H interchange their positions, E becomes 8th from the left end.
- Only 13 persons sit to the left of G.

How many persons sit in the row?

- **A.** 15  _(error: left out one end seat)_
- **B.** 17  _(error: counted one seat extra at an end)_
- **C.** 16 ✅
- **D.** 18  _(error: counted both anchor persons again)_

**Working**

1. The builder enumerates every row length from 5 to 60 and every placement of the 5 named persons; exactly one combination satisfies all 6 statements: n = 16.
2. Seats from the left: F – seat 5, E – seat 7, H – seat 8, D – seat 13, G – seat 14.
3. The unique placement needs exactly 16 seats (leftmost occupied seat is 1, rightmost is 16).

**Formula:** Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues  
**Trap:** Total = (position from left) + (position from right) − 1 for the same person.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-202 · L3 · hard · Row with unknown number of persons · officer

Some persons sit in a single row, all facing north. P, Q, R, S and T are among them; the total number of persons in the row is not given.

- S is 5th from the right end.
- P sits immediately to the right of R.
- R is 3rd from the right end.
- Exactly 13 persons sit between P and Q.
- If S and T interchange their positions, S becomes 13th from the left end.
- If S and P interchange their positions, S becomes 21st from the left end.

What is the position of Q from the right end of the row?

- **A.** 16th ✅
- **B.** 7th  _(error: gave the position from the left end)_
- **C.** 15th  _(error: subtracted one extra)_
- **D.** 17th  _(error: added one extra)_

**Working**

1. The builder enumerates every row length from 5 to 60 and every placement of the 5 named persons; exactly one combination satisfies all 6 statements: n = 22.
2. Seats from the left: Q – seat 7, T – seat 13, S – seat 18, R – seat 20, P – seat 21.
3. Q is 7th from the left in a row of 22; from the right: 22 − 7 + 1 = 16.

**Formula:** Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues  
**Trap:** Position from right = n − (position from left) + 1.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-203 · L4 · hard · Row with unknown number of persons · officer

Some persons sit in a single row, all facing north. E, F, G, H, J and K are among them; the total number of persons in the row is not given.

- H is 7th to the right of K.
- If K and F interchange their positions, K becomes 3rd from the left end.
- G is 9th to the right of E.
- Exactly 14 persons sit between G and K, and G is to the right of K.
- If J and E interchange their positions, J becomes 12th from the left end.
- As many persons sit to the left of G as to the right of K.
- E is 10th to the right of J.

How many persons sit in the row?

- **A.** 26 ✅
- **B.** 28  _(error: counted both anchor persons again)_
- **C.** 25  _(error: left out one end seat)_
- **D.** 27  _(error: counted one seat extra at an end)_

**Working**

1. The builder enumerates every row length from 6 to 60 and every placement of the 6 named persons; exactly one combination satisfies all 7 statements: n = 26.
2. Seats from the left: J – seat 2, F – seat 3, K – seat 6, E – seat 12, H – seat 13, G – seat 21.
3. The unique placement needs exactly 26 seats (leftmost occupied seat is 1, rightmost is 26).

**Formula:** Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues  
**Trap:** Total = (position from left) + (position from right) − 1 for the same person.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-204 · L4 · hard · Row with unknown number of persons · officer

Some persons sit in a single row, all facing north. E, F, G, H, J and K are among them; the total number of persons in the row is not given.

- H is 7th to the right of K.
- If K and F interchange their positions, K becomes 3rd from the left end.
- G is 9th to the right of E.
- Exactly 14 persons sit between G and K, and G is to the right of K.
- If J and E interchange their positions, J becomes 12th from the left end.
- As many persons sit to the left of G as to the right of K.
- E is 10th to the right of J.

How many persons sit between F and H?

- **A.** 11  _(error: included both named persons)_
- **B.** 10  _(error: included one of the two named persons)_
- **C.** 9 ✅
- **D.** 8  _(error: counted one short)_

**Working**

1. The builder enumerates every row length from 6 to 60 and every placement of the 6 named persons; exactly one combination satisfies all 7 statements: n = 26.
2. Seats from the left: J – seat 2, F – seat 3, K – seat 6, E – seat 12, H – seat 13, G – seat 21.
3. F is at seat 3 and H at seat 13 (from the left); 9 seats lie between.

**Formula:** Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues  
**Trap:** Between excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-205 · L4 · hard · Row with unknown number of persons · officer

Some persons sit in a single row, all facing north. E, F, G, H, J and K are among them; the total number of persons in the row is not given.

- H is 7th to the right of K.
- If K and F interchange their positions, K becomes 3rd from the left end.
- G is 9th to the right of E.
- Exactly 14 persons sit between G and K, and G is to the right of K.
- If J and E interchange their positions, J becomes 12th from the left end.
- As many persons sit to the left of G as to the right of K.
- E is 10th to the right of J.

What is the position of E from the right end of the row?

- **A.** 14th  _(error: subtracted one extra)_
- **B.** 15th ✅
- **C.** 16th  _(error: added one extra)_
- **D.** 12th  _(error: gave the position from the left end)_

**Working**

1. The builder enumerates every row length from 6 to 60 and every placement of the 6 named persons; exactly one combination satisfies all 7 statements: n = 26.
2. Seats from the left: J – seat 2, F – seat 3, K – seat 6, E – seat 12, H – seat 13, G – seat 21.
3. E is 12th from the left in a row of 26; from the right: 26 − 12 + 1 = 15.

**Formula:** Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues  
**Trap:** Position from right = n − (position from left) + 1.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-206 · L4 · hard · Row with unknown number of persons · officer

Some persons sit in a single row, all facing north. E, F, G, H, J and K are among them; the total number of persons in the row is not given.

- H is 7th to the right of K.
- If K and F interchange their positions, K becomes 3rd from the left end.
- G is 9th to the right of E.
- Exactly 14 persons sit between G and K, and G is to the right of K.
- If J and E interchange their positions, J becomes 12th from the left end.
- As many persons sit to the left of G as to the right of K.
- E is 10th to the right of J.

How many persons sit to the right of E?

- **A.** 13  _(error: counted one short)_
- **B.** 11  _(error: counted to the left instead)_
- **C.** 14 ✅
- **D.** 15  _(error: included the person named)_

**Working**

1. The builder enumerates every row length from 6 to 60 and every placement of the 6 named persons; exactly one combination satisfies all 7 statements: n = 26.
2. Seats from the left: J – seat 2, F – seat 3, K – seat 6, E – seat 12, H – seat 13, G – seat 21.
3. E is at seat 12 of 26; 14 persons sit to the right.

**Formula:** Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues  
**Trap:** Persons to the right = n − (position from left).

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-207 · L4 · hard · Row with unknown number of persons · officer

Some persons sit in a single row, all facing north. E, F, G, H, J and K are among them; the total number of persons in the row is not given.

- H is 7th to the right of K.
- If K and F interchange their positions, K becomes 3rd from the left end.
- G is 9th to the right of E.
- Exactly 14 persons sit between G and K, and G is to the right of K.
- If J and E interchange their positions, J becomes 12th from the left end.
- As many persons sit to the left of G as to the right of K.
- E is 10th to the right of J.

What is the position of G from the left end of the row?

- **A.** 22nd  _(error: added one extra)_
- **B.** 21st ✅
- **C.** 20th  _(error: subtracted one extra)_
- **D.** 6th  _(error: gave the position from the right end)_

**Working**

1. The builder enumerates every row length from 6 to 60 and every placement of the 6 named persons; exactly one combination satisfies all 7 statements: n = 26.
2. Seats from the left: J – seat 2, F – seat 3, K – seat 6, E – seat 12, H – seat 13, G – seat 21.
3. G occupies seat 21 from the left.

**Formula:** Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues  
**Trap:** Fix the row length first, then convert end-positions.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-208 · L4 · hard · Row with unknown number of persons · officer

Some persons sit in a single row, all facing north. A, B, C, D, E and F are among them; the total number of persons in the row is not given.

- C is 3rd to the right of A.
- Exactly two persons sit between F and B, and F is to the right of B.
- Exactly nine persons sit between C and B, and C is to the right of B.
- If B and A interchange their positions, B becomes 14th from the left end.
- Exactly seven persons sit between D and E, and D is to the right of E.
- As many persons sit to the left of D as to the right of F.
- F is 9th to the right of E.

How many persons sit in the row?

- **A.** 19  _(error: counted one seat extra at an end)_
- **B.** 18 ✅
- **C.** 20  _(error: counted both anchor persons again)_
- **D.** 17  _(error: left out one end seat)_

**Working**

1. The builder enumerates every row length from 6 to 60 and every placement of the 6 named persons; exactly one combination satisfies all 7 statements: n = 18.
2. Seats from the left: E – seat 1, B – seat 7, D – seat 9, F – seat 10, A – seat 14, C – seat 17.
3. The unique placement needs exactly 18 seats (leftmost occupied seat is 1, rightmost is 18).

**Formula:** Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues  
**Trap:** Total = (position from left) + (position from right) − 1 for the same person.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-209 · L4 · hard · Row with unknown number of persons · officer

Some persons sit in a single row, all facing north. A, B, C, D, E and F are among them; the total number of persons in the row is not given.

- C is 3rd to the right of A.
- Exactly two persons sit between F and B, and F is to the right of B.
- Exactly nine persons sit between C and B, and C is to the right of B.
- If B and A interchange their positions, B becomes 14th from the left end.
- Exactly seven persons sit between D and E, and D is to the right of E.
- As many persons sit to the left of D as to the right of F.
- F is 9th to the right of E.

How many persons sit between B and C?

- **A.** 10  _(error: included one of the two named persons)_
- **B.** 11  _(error: included both named persons)_
- **C.** 8  _(error: counted one short)_
- **D.** 9 ✅

**Working**

1. The builder enumerates every row length from 6 to 60 and every placement of the 6 named persons; exactly one combination satisfies all 7 statements: n = 18.
2. Seats from the left: E – seat 1, B – seat 7, D – seat 9, F – seat 10, A – seat 14, C – seat 17.
3. B is at seat 7 and C at seat 17 (from the left); 9 seats lie between.

**Formula:** Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues  
**Trap:** Between excludes both named persons.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-210 · L4 · hard · Row with unknown number of persons · officer

Some persons sit in a single row, all facing north. A, B, C, D, E and F are among them; the total number of persons in the row is not given.

- C is 3rd to the right of A.
- Exactly two persons sit between F and B, and F is to the right of B.
- Exactly nine persons sit between C and B, and C is to the right of B.
- If B and A interchange their positions, B becomes 14th from the left end.
- Exactly seven persons sit between D and E, and D is to the right of E.
- As many persons sit to the left of D as to the right of F.
- F is 9th to the right of E.

What is the position of C from the right end of the row?

- **A.** 1st  _(error: subtracted one extra)_
- **B.** 17th  _(error: gave the position from the left end)_
- **C.** 2nd ✅
- **D.** 3rd  _(error: added one extra)_

**Working**

1. The builder enumerates every row length from 6 to 60 and every placement of the 6 named persons; exactly one combination satisfies all 7 statements: n = 18.
2. Seats from the left: E – seat 1, B – seat 7, D – seat 9, F – seat 10, A – seat 14, C – seat 17.
3. C is 17th from the left in a row of 18; from the right: 18 − 17 + 1 = 2.

**Formula:** Row length fixed by linking a left-end anchor and a right-end anchor through the relative clues  
**Trap:** Position from right = n − (position from left) + 1.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-211 · L1 · easy · Data sufficiency with numbered statements · foundation

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Five persons – E, F, G, H and J – sit in a straight row, all facing north.

Question: Who sits at the extreme right end?

I. H sits fourth to the right of G.

II. Only three persons sit between G and H.

- **A.** Either statement I alone or statement II alone is sufficient.  _(error: one of the statements alone leaves more than one answer)_
- **B.** Statement I alone is sufficient, but statement II alone is not sufficient. ✅
- **C.** Statements I and II together are necessary; neither alone is sufficient.  _(error: one statement alone is already sufficient)_
- **D.** Statement II alone is sufficient, but statement I alone is not sufficient.  _(error: statement II alone leaves more than one answer)_

**Working**

1. Common information alone allows 5 different answers.
2. With I alone: 1 possible answer(s) → a single answer.
3. With II alone: 2 possible answer(s) → more than one possible answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-212 · L2 · medium · Data sufficiency with numbered statements · foundation

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Five persons – S, T, U, V and W – are all of different heights. Exactly one person is shorter than S but taller than W.

Question: Who is the tallest?

I. U is taller than W.

II. Exactly two persons are shorter than V but taller than W. As many persons are taller than W as are shorter than U.

- **A.** Statements I and II together are not sufficient.  _(error: together (or singly) the statements do fix the answer)_
- **B.** Either statement I alone or statement II alone is sufficient.  _(error: one of the statements alone leaves more than one answer)_
- **C.** Statement I alone is sufficient, but statement II alone is not sufficient.  _(error: statement I alone leaves more than one answer)_
- **D.** Statement II alone is sufficient, but statement I alone is not sufficient. ✅

**Working**

1. Common information alone allows 4 different answers.
2. With I alone: 4 possible answer(s) → more than one possible answer.
3. With II alone: 1 possible answer(s) → a single answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-213 · L2 · medium · Data sufficiency with numbered statements · foundation

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Five persons – P, Q, R, S and T – live on the five floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 5. R lives on the floor immediately above Q.

Question: On which floor does R live?

I. Only one person lives between R and P, and R lives above P. R lives two floors below T.

II. T lives three floors above Q. P lives on the floor immediately below Q.

- **A.** Either statement I alone or statement II alone is sufficient. ✅
- **B.** Statement II alone is sufficient, but statement I alone is not sufficient.  _(error: statement I alone also answers it)_
- **C.** Statements I and II together are not sufficient.  _(error: together (or singly) the statements do fix the answer)_
- **D.** Statements I and II together are necessary; neither alone is sufficient.  _(error: one statement alone is already sufficient)_

**Working**

1. Common information alone allows 4 different answers.
2. With I alone: 1 possible answer(s) → a single answer.
3. With II alone: 1 possible answer(s) → a single answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-214 · L2 · medium · Data sufficiency with numbered statements · foundation

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Five persons – Aman, Chitra, Farid, Gauri and Harsh – each give a talk on a different day of the same week, from Monday to Friday, one talk per day. Harsh gives a talk on a day after Wednesday.

Question: Who gives a talk on Friday?

I. Harsh gives a talk on some day after Farid. Farid gives a talk two days before Aman.

II. As many persons give talks after Harsh as before Farid.

- **A.** Either statement I alone or statement II alone is sufficient.  _(error: one of the statements alone leaves more than one answer)_
- **B.** Statements I and II together are not sufficient.  _(error: together (or singly) the statements do fix the answer)_
- **C.** Statement II alone is sufficient, but statement I alone is not sufficient.  _(error: statement II alone leaves more than one answer)_
- **D.** Statements I and II together are necessary; neither alone is sufficient. ✅

**Working**

1. Common information alone allows 5 different answers.
2. With I alone: 4 possible answer(s) → more than one possible answer.
3. With II alone: 4 possible answer(s) → more than one possible answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-215 · L2 · medium · Data sufficiency with numbered statements · foundation

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Five boxes – D, E, F, G and H – are placed one above another in a single stack. Position 1 is at the bottom and position 5 is at the top. Box E is placed immediately below box F.

Question: At which position from the bottom is box G placed?

I. Box F is placed neither at the top nor at the bottom. The number of boxes above box E is the same as the number of boxes below box D.

II. Box G is placed somewhere above box F. Box E is placed at an odd-numbered position.

- **A.** Statement II alone is sufficient, but statement I alone is not sufficient.  _(error: statement II alone leaves more than one answer)_
- **B.** Statement I alone is sufficient, but statement II alone is not sufficient.  _(error: statement I alone leaves more than one answer)_
- **C.** Statements I and II together are necessary; neither alone is sufficient.  _(error: even together they leave more than one answer)_
- **D.** Statements I and II together are not sufficient. ✅

**Working**

1. Common information alone allows 5 different answers.
2. With I alone: 4 possible answer(s) → more than one possible answer.
3. With II alone: 3 possible answer(s) → more than one possible answer.
4. With I and II together: 2 possible answer(s) → more than one possible answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-216 · L3 · hard · Data sufficiency with numbered statements · officer

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Six persons – A, B, C, D, E and F – sit in a straight row, all facing north. B does not sit adjacent to F. Only one person sits between D and B, and D is to the right of B.

Question: What is the position of A from the left end of the row?

I. As many persons sit to the right of C as to the left of B. E sits second to the left of A.

II. A does not sit adjacent to F.

- **A.** Either statement I alone or statement II alone is sufficient.  _(error: one of the statements alone leaves more than one answer)_
- **B.** Statements I and II together are necessary; neither alone is sufficient. ✅
- **C.** Statement I alone is sufficient, but statement II alone is not sufficient.  _(error: statement I alone leaves more than one answer)_
- **D.** Statements I and II together are not sufficient.  _(error: together (or singly) the statements do fix the answer)_

**Working**

1. Common information alone allows 6 different answers.
2. With I alone: 2 possible answer(s) → more than one possible answer.
3. With II alone: 6 possible answer(s) → more than one possible answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-217 · L3 · hard · Data sufficiency with numbered statements · officer

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Six persons – J, K, L, M, N and P – sit around a circular table, all facing the centre. L is not an immediate neighbour of N. M sits immediately to the right of N.

Question: Who sits second to the left of J?

I. M sits second to the left of P. P sits immediately to the right of J.

II. L sits opposite M.

- **A.** Either statement I alone or statement II alone is sufficient.  _(error: one of the statements alone leaves more than one answer)_
- **B.** Statement I alone is sufficient, but statement II alone is not sufficient. ✅
- **C.** Statement II alone is sufficient, but statement I alone is not sufficient.  _(error: statement II alone leaves more than one answer)_
- **D.** Statements I and II together are not sufficient.  _(error: together (or singly) the statements do fix the answer)_

**Working**

1. Common information alone allows 5 different answers.
2. With I alone: 1 possible answer(s) → a single answer.
3. With II alone: 4 possible answer(s) → more than one possible answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-218 · L3 · hard · Data sufficiency with numbered statements · officer

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Six persons – E, F, G, H, J and K – live on the six floors of a building, one person per floor. The lowermost floor is numbered 1, the floor above it 2, and so on up to the topmost floor, numbered 6. Each of them owns a car of a different colour among black, blue, grey, red, white and yellow. The owner of the yellow car lives two floors below E. J lives three floors above K.

Question: Who lives on floor 2?

I. Only one person lives between the owner of the grey car and H. J lives two floors above E.

II. J lives on the floor immediately below H. E lives two floors above G.

- **A.** Statements I and II together are not sufficient.  _(error: together (or singly) the statements do fix the answer)_
- **B.** Either statement I alone or statement II alone is sufficient.  _(error: one of the statements alone leaves more than one answer)_
- **C.** Statements I and II together are necessary; neither alone is sufficient.  _(error: one statement alone is already sufficient)_
- **D.** Statement II alone is sufficient, but statement I alone is not sufficient. ✅

**Working**

1. Common information alone allows 4 different answers.
2. With I alone: 4 possible answer(s) → more than one possible answer.
3. With II alone: 1 possible answer(s) → a single answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-219 · L3 · hard · Data sufficiency with numbered statements · officer

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Six persons – S, T, U, V, W and X – are all of different heights. Exactly two persons are shorter than U but taller than T. Exactly one person is shorter than V but taller than X.

Question: Who is the third tallest?

I. Exactly three persons are shorter than S but taller than T. Exactly one person is shorter than S but taller than W.

II. Exactly two persons are shorter than S but taller than V.

- **A.** Either statement I alone or statement II alone is sufficient. ✅
- **B.** Statement II alone is sufficient, but statement I alone is not sufficient.  _(error: statement I alone also answers it)_
- **C.** Statements I and II together are necessary; neither alone is sufficient.  _(error: one statement alone is already sufficient)_
- **D.** Statement I alone is sufficient, but statement II alone is not sufficient.  _(error: statement II alone also answers it)_

**Working**

1. Common information alone allows 5 different answers.
2. With I alone: 1 possible answer(s) → a single answer.
3. With II alone: 1 possible answer(s) → a single answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-220 · L3 · hard · Data sufficiency with numbered statements · officer

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Seven persons – M, N, P, Q, R, S and T – sit around a circular table, all facing the centre. P sits third to the right of T.

Question: Who sits immediately to the right of R?

I. M sits third to the right of S.

II. S sits second to the right of Q. N sits second to the right of P.

- **A.** Statement I alone is sufficient, but statement II alone is not sufficient.  _(error: statement I alone leaves more than one answer)_
- **B.** Statement II alone is sufficient, but statement I alone is not sufficient.  _(error: statement II alone leaves more than one answer)_
- **C.** Statements I and II together are not sufficient. ✅
- **D.** Statements I and II together are necessary; neither alone is sufficient.  _(error: even together they leave more than one answer)_

**Working**

1. Common information alone allows 6 different answers.
2. With I alone: 6 possible answer(s) → more than one possible answer.
3. With II alone: 5 possible answer(s) → more than one possible answer.
4. With I and II together: 2 possible answer(s) → more than one possible answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-221 · L3 · hard · Data sufficiency with numbered statements · officer

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Six boxes – S, T, U, V, W and X – are placed one above another in a single stack. Position 1 is at the bottom and position 6 is at the top. Each box is of a different colour among black, blue, green, orange, pink and yellow. Only three boxes are placed between box U and box V. Box S is not yellow.

Question: Which box is placed at the bottom?

I. Box V is placed somewhere above the pink box. Box X is placed either at the top or at the bottom.

II. Box X is placed at an odd-numbered position. Box X is not orange.

- **A.** Statement II alone is sufficient, but statement I alone is not sufficient.  _(error: statement II alone leaves more than one answer)_
- **B.** Statements I and II together are necessary; neither alone is sufficient. ✅
- **C.** Statements I and II together are not sufficient.  _(error: together (or singly) the statements do fix the answer)_
- **D.** Statement I alone is sufficient, but statement II alone is not sufficient.  _(error: statement I alone leaves more than one answer)_

**Working**

1. Common information alone allows 6 different answers.
2. With I alone: 2 possible answer(s) → more than one possible answer.
3. With II alone: 6 possible answer(s) → more than one possible answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-222 · L3 · hard · Data sufficiency with numbered statements · officer

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Six persons – Deepa, Ekta, Firoz, Hina, Ishaan and Jaya – meet a counsellor one at a time on the same day. Each meeting lasts one hour and starts at one of these times: 9 a.m., 10 a.m., 11 a.m., 12 noon, 2 p.m. and 3 p.m. No two persons share a slot, and there is no meeting between 1 p.m. and 2 p.m. Ishaan meets the counsellor exactly four hours after Ekta.

Question: Who meets the counsellor at 12 noon?

I. Only four persons meet the counsellor between Firoz and Jaya, with Firoz meeting later than Jaya. Only one person meets the counsellor between Hina and Jaya, with Hina meeting later than Jaya.

II. Jaya meets the counsellor exactly two hours before Hina.

- **A.** Either statement I alone or statement II alone is sufficient.  _(error: one of the statements alone leaves more than one answer)_
- **B.** Statements I and II together are not sufficient.  _(error: together (or singly) the statements do fix the answer)_
- **C.** Statements I and II together are necessary; neither alone is sufficient.  _(error: one statement alone is already sufficient)_
- **D.** Statement I alone is sufficient, but statement II alone is not sufficient. ✅

**Working**

1. Common information alone allows 4 different answers.
2. With I alone: 1 possible answer(s) → a single answer.
3. With II alone: 4 possible answer(s) → more than one possible answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-223 · L3 · hard · Data sufficiency with numbered statements · officer

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Six persons – Ekta, Firoz, Gopal, Hina, Ishaan and Karan – each give a talk on a different day of the same week, from Monday to Saturday, one talk per day. Each of them teaches a different subject among Botany, Chemistry, Civics, Geography, Physics and Zoology. The one who teaches Physics gives a talk on the day immediately before Karan. Gopal gives a talk four days before Firoz.

Question: Who gives a talk on Friday?

I. The one who teaches Physics gives a talk four days before Ishaan. Ishaan gives a talk either on Monday or on Saturday.

II. Firoz gives a talk on the day immediately before Ishaan. Ishaan gives a talk on some day after Ekta.

- **A.** Statement II alone is sufficient, but statement I alone is not sufficient.  _(error: statement I alone also answers it)_
- **B.** Statement I alone is sufficient, but statement II alone is not sufficient.  _(error: statement II alone also answers it)_
- **C.** Statements I and II together are necessary; neither alone is sufficient.  _(error: one statement alone is already sufficient)_
- **D.** Either statement I alone or statement II alone is sufficient. ✅

**Working**

1. Common information alone allows 5 different answers.
2. With I alone: 1 possible answer(s) → a single answer.
3. With II alone: 1 possible answer(s) → a single answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-224 · L3 · hard · Data sufficiency with numbered statements · officer

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Six persons – Kavya, Lalit, Meera, Om, Preeti and Sana – visit a museum on six different dates of the same year: the 4th and 18th of each of March, July and October. No two persons visit on the same date. Only two persons visit between Preeti and Lalit, with Preeti visiting later than Lalit. Only two persons visit between Sana and Kavya, with Sana visiting later than Kavya.

Question: Who visits on 18 October?

I. Om visits immediately after Preeti. Om visits on some date after Kavya.

II. Meera is neither the first nor the last to visit. Only four persons visit between Om and Kavya, with Om visiting later than Kavya.

- **A.** Statement I alone is sufficient, but statement II alone is not sufficient.  _(error: statement I alone leaves more than one answer)_
- **B.** Statement II alone is sufficient, but statement I alone is not sufficient. ✅
- **C.** Statements I and II together are not sufficient.  _(error: together (or singly) the statements do fix the answer)_
- **D.** Statements I and II together are necessary; neither alone is sufficient.  _(error: one statement alone is already sufficient)_

**Working**

1. Common information alone allows 4 different answers.
2. With I alone: 2 possible answer(s) → more than one possible answer.
3. With II alone: 1 possible answer(s) → a single answer.
4. With I and II together: 1 possible answer(s) → a single answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-225 · L3 · hard · Data sufficiency with numbered statements · officer

The question below is followed by two statements numbered I and II. Decide whether the data given in the statements are sufficient to answer the question, read together with the common information.

Common information: Six persons – Arjun, Charu, Tara, Uday, Vani and Zoya – joined a company in six different years from 2015 to 2020, one person per year. Uday joined either in 2015 or in 2020.

Question: Who joined in 2020?

I. Vani joined in an even-numbered year.

II. Charu joined either in 2015 or in 2020. As many persons joined after Charu as before Uday.

- **A.** Statements I and II together are necessary; neither alone is sufficient.  _(error: even together they leave more than one answer)_
- **B.** Statements I and II together are not sufficient. ✅
- **C.** Statement I alone is sufficient, but statement II alone is not sufficient.  _(error: statement I alone leaves more than one answer)_
- **D.** Either statement I alone or statement II alone is sufficient.  _(error: one of the statements alone leaves more than one answer)_

**Working**

1. Common information alone allows 6 different answers.
2. With I alone: 6 possible answer(s) → more than one possible answer.
3. With II alone: 2 possible answer(s) → more than one possible answer.
4. With I and II together: 2 possible answer(s) → more than one possible answer.
5. All counts come from exhaustive enumeration of the arrangements in the builder.

**Formula:** Sufficient ⇔ every arrangement consistent with the data gives the same answer  
**Trap:** Test each statement alone first (with the common information) before combining them.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-226 · L1 · easy · Direct coded inequality · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: N ≤ L < M = K

Conclusions:
I. L ≤ K
II. L ≥ K

- **A.** Only I follows ✅
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Only II follows  _(error: conclusion II does not follow definitely)_
- **D.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_

**Working**

1. Combine the statements: N ≤ L < M = K.
2. Conclusion I (L ≤ K): derived relation is L < K → follows.
3. Conclusion II (L ≥ K): derived relation is L < K → does not follow definitely.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-227 · L1 · easy · Direct coded inequality · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: L > K < J ≤ M

Conclusions:
I. K ≤ M
II. K < M

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **C.** Both I and II follow ✅
- **D.** Only I follows  _(error: conclusion II also follows)_

**Working**

1. Combine the statements: L > K < J ≤ M.
2. Conclusion I (K ≤ M): derived relation is K < M → follows.
3. Conclusion II (K < M): derived relation is K < M → follows.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-228 · L2 · medium · Direct coded inequality · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: B ≥ D ≥ A ≤ C ≥ E

Conclusions:
I. A = E
II. A ≤ B

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Only I follows  _(error: conclusion I does not follow definitely)_
- **C.** Only II follows ✅
- **D.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_

**Working**

1. Combine the statements: B ≥ D ≥ A ≤ C ≥ E.
2. Conclusion I (A = E): no definite relation between A and E → does not follow definitely.
3. Conclusion II (A ≤ B): derived relation is A ≤ B → follows.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-229 · L2 · medium · Direct coded inequality · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: E ≥ H > F = D < G

Conclusions:
I. E = D
II. E < D

- **A.** Neither I nor II follows ✅
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Only II follows  _(error: conclusion II does not follow definitely)_
- **D.** Only I follows  _(error: conclusion I does not follow definitely)_

**Working**

1. Combine the statements: E ≥ H > F = D < G.
2. Conclusion I (E = D): derived relation is E > D → does not follow definitely.
3. Conclusion II (E < D): derived relation is E > D → does not follow definitely.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-230 · L2 · medium · Direct coded inequality · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: U ≤ T ≤ W ≤ V = S

Conclusions:
I. U < V
II. U = V

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Either I or II follows ✅
- **C.** Only II follows  _(error: conclusion II does not follow definitely)_
- **D.** Only I follows  _(error: conclusion I does not follow definitely)_

**Working**

1. Combine the statements: U ≤ T ≤ W ≤ V = S.
2. Conclusion I (U < V): derived relation is U ≤ V → does not follow definitely.
3. Conclusion II (U = V): derived relation is U ≤ V → does not follow definitely.
4. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-231 · L3 · hard · Direct coded inequality · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: N < L ≤ M = Q; M ≥ P ≥ K

Conclusions:
I. N = K
II. N > K

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Only I follows  _(error: conclusion I does not follow definitely)_
- **C.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **D.** Neither I nor II follows ✅

**Working**

1. Combine the statements: N < L ≤ M = Q; M ≥ P ≥ K.
2. Conclusion I (N = K): no definite relation between N and K → does not follow definitely.
3. Conclusion II (N > K): no definite relation between N and K → does not follow definitely.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-232 · L3 · hard · Direct coded inequality · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: R > N ≥ P = S; M > Q < R

Conclusions:
I. R > P
II. R = S

- **A.** Only II follows  _(error: conclusion II does not follow definitely)_
- **B.** Only I follows ✅
- **C.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **D.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_

**Working**

1. Combine the statements: R > N ≥ P = S; M > Q < R.
2. Conclusion I (R > P): derived relation is R > P → follows.
3. Conclusion II (R = S): derived relation is R > S → does not follow definitely.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-233 · L3 · hard · Direct coded inequality · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: E ≥ J ≥ H = F; K ≥ D ≤ F ≤ G

Conclusions:
I. D ≤ E
II. E ≥ D

- **A.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **B.** Both I and II follow ✅
- **C.** Only I follows  _(error: conclusion II also follows)_
- **D.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_

**Working**

1. Combine the statements: E ≥ J ≥ H = F; K ≥ D ≤ F ≤ G.
2. Conclusion I (D ≤ E): derived relation is D ≤ E → follows.
3. Conclusion II (E ≥ D): derived relation is E ≥ D → follows.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-234 · L3 · hard · Direct coded inequality · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: N = P ≤ J > Q; Q ≤ K > M ≤ L

Conclusions:
I. J = N
II. N ≤ J

- **A.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **D.** Only II follows ✅

**Working**

1. Combine the statements: N = P ≤ J > Q; Q ≤ K > M ≤ L.
2. Conclusion I (J = N): derived relation is J ≥ N → does not follow definitely.
3. Conclusion II (N ≤ J): derived relation is N ≤ J → follows.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-235 · L3 · hard · Direct coded inequality · officer

In which of the following expressions is the expression 'F < D' definitely true?

- **A.** C > E ≥ B = D ≤ F  _(error: here the relation is impossible)_
- **B.** D ≤ E = F ≥ B > C  _(error: here the relation is impossible)_
- **C.** F < D = E < C = B ✅
- **D.** D < F < C < B = E  _(error: here the relation is impossible)_

**Working**

1. Trace F and D along each expression; the path between them must have every sign pointing the same way.
2. In 'F < D = E < C = B', the path from F to D makes 'F < D' definitely true.
3. In each other expression the path contains an opposite sign or a weak sign, so the relation is either uncertain or the opposite of what is required.
4. Verified by enumerating every ordering consistent with each expression.

**Formula:** Relation between two letters is definite only if every sign on the path between them points the same way  
**Trap:** A single opposite sign anywhere between the two letters destroys the relation; ≥ with > still gives >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-236 · L3 · hard · Direct coded inequality · officer

In which of the following expressions is the expression 'B < E' definitely true?

- **A.** B = E < A = C > D ≥ F  _(error: here the relation is impossible)_
- **B.** C = E > F > B = A ≤ D ✅
- **C.** E ≥ A < B < D = F ≤ C  _(error: here the relation is possible but not certain)_
- **D.** F ≥ E ≤ D > A ≥ B = C  _(error: here the relation is possible but not certain)_

**Working**

1. Trace B and E along each expression; the path between them must have every sign pointing the same way.
2. In 'C = E > F > B = A ≤ D', the path from B to E makes 'B < E' definitely true.
3. In each other expression the path contains an opposite sign or a weak sign, so the relation is either uncertain or the opposite of what is required.
4. Verified by enumerating every ordering consistent with each expression.

**Formula:** Relation between two letters is definite only if every sign on the path between them points the same way  
**Trap:** A single opposite sign anywhere between the two letters destroys the relation; ≥ with > still gives >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-237 · L3 · hard · Direct coded inequality · officer

In which of the following expressions is the expression 'P > K' definitely false?

- **A.** L ≥ N = P = K = M ✅
- **B.** K < P ≥ L ≥ M > N  _(error: here the relation is possible)_
- **C.** K ≤ L > N > P ≤ M  _(error: here the relation is possible)_
- **D.** K > L = M ≤ P ≥ N  _(error: here the relation is possible)_

**Working**

1. Trace P and K along each expression; the path between them must have every sign pointing the same way.
2. In 'L ≥ N = P = K = M', the path from P to K makes 'P > K' definitely false.
3. In each other expression the path contains an opposite sign or a weak sign, so the relation is either uncertain or the opposite of what is required.
4. Verified by enumerating every ordering consistent with each expression.

**Formula:** Relation between two letters is definite only if every sign on the path between them points the same way  
**Trap:** A single opposite sign anywhere between the two letters destroys the relation; ≥ with > still gives >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-238 · L3 · hard · Direct coded inequality · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: T ≤ N ≥ Q < M; N > R ≥ P > S

Conclusions:
I. T < M
II. S < R
III. N < S

- **A.** Only III follows  _(error: misjudged conclusion(s) II, III)_
- **B.** Only II and III follow  _(error: misjudged conclusion(s) III)_
- **C.** Only II follows ✅
- **D.** Only I and either II or III follow  _(error: paired conclusions that are not a valid either-or pair)_

**Working**

1. Combine the statements: T ≤ N ≥ Q < M; N > R ≥ P > S.
2. Conclusion I (T < M): no definite relation between T and M → does not follow definitely.
3. Conclusion II (S < R): derived relation is S < R → follows.
4. Conclusion III (N < S): derived relation is N > S → does not follow definitely.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-239 · L3 · hard · Direct coded inequality · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: P ≥ R ≤ K > L; L < Q ≤ M ≥ N

Conclusions:
I. L ≤ M
II. M > L
III. M = K

- **A.** Only III and either I or II follow  _(error: paired conclusions that are not a valid either-or pair)_
- **B.** Only I and II follow ✅
- **C.** All I, II and III follow  _(error: misjudged conclusion(s) III)_
- **D.** Only I follows  _(error: misjudged conclusion(s) II)_

**Working**

1. Combine the statements: P ≥ R ≤ K > L; L < Q ≤ M ≥ N.
2. Conclusion I (L ≤ M): derived relation is L < M → follows.
3. Conclusion II (M > L): derived relation is M > L → follows.
4. Conclusion III (M = K): no definite relation between M and K → does not follow definitely.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-240 · L3 · hard · Direct coded inequality · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: S > U < V < T; Q > U = P > R

Conclusions:
I. V < R
II. S < R
III. P > V

- **A.** None follows ✅
- **B.** Only II follows  _(error: misjudged conclusion(s) II)_
- **C.** Only I and either II or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **D.** Only I follows  _(error: misjudged conclusion(s) I)_

**Working**

1. Combine the statements: S > U < V < T; Q > U = P > R.
2. Conclusion I (V < R): derived relation is V > R → does not follow definitely.
3. Conclusion II (S < R): derived relation is S > R → does not follow definitely.
4. Conclusion III (P > V): derived relation is P < V → does not follow definitely.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-241 · L2 · medium · Either-or conclusions in inequality · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: L > J ≤ M ≥ K

Conclusions:
I. L ≤ M
II. L > M

- **A.** Either I or II follows ✅
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Only I follows  _(error: conclusion I does not follow definitely)_
- **D.** Neither I nor II follows  _(error: missed the either-or pair)_

**Working**

1. Combine the statements: L > J ≤ M ≥ K.
2. Conclusion I (L ≤ M): no definite relation between L and M → does not follow definitely.
3. Conclusion II (L > M): no definite relation between L and M → does not follow definitely.
4. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-242 · L2 · medium · Either-or conclusions in inequality · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: V = U < T > W > S

Conclusions:
I. U ≥ W
II. U < W

- **A.** Only II follows  _(error: conclusion II does not follow definitely)_
- **B.** Only I follows  _(error: conclusion I does not follow definitely)_
- **C.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **D.** Either I or II follows ✅

**Working**

1. Combine the statements: V = U < T > W > S.
2. Conclusion I (U ≥ W): no definite relation between U and W → does not follow definitely.
3. Conclusion II (U < W): no definite relation between U and W → does not follow definitely.
4. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-243 · L2 · medium · Either-or conclusions in inequality · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: F ≤ E < C ≤ B ≥ D

Conclusions:
I. B > F
II. F > B

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Only I follows ✅
- **C.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **D.** Only II follows  _(error: conclusion II does not follow definitely)_

**Working**

1. Combine the statements: F ≤ E < C ≤ B ≥ D.
2. Conclusion I (B > F): derived relation is B > F → follows.
3. Conclusion II (F > B): derived relation is F < B → does not follow definitely.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-244 · L2 · medium · Either-or conclusions in inequality · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: E > C ≥ B < F < D

Conclusions:
I. F > C
II. E = F

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Only I follows  _(error: conclusion I does not follow definitely)_
- **C.** Neither I nor II follows ✅
- **D.** Only II follows  _(error: conclusion II does not follow definitely)_

**Working**

1. Combine the statements: E > C ≥ B < F < D.
2. Conclusion I (F > C): no definite relation between F and C → does not follow definitely.
3. Conclusion II (E = F): no definite relation between E and F → does not follow definitely.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-245 · L2 · medium · Either-or conclusions in inequality · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: S < U ≥ V > T < W

Conclusions:
I. S ≤ T
II. S > T

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Only II follows  _(error: conclusion II does not follow definitely)_
- **C.** Neither I nor II follows  _(error: missed the either-or pair)_
- **D.** Either I or II follows ✅

**Working**

1. Combine the statements: S < U ≥ V > T < W.
2. Conclusion I (S ≤ T): no definite relation between S and T → does not follow definitely.
3. Conclusion II (S > T): no definite relation between S and T → does not follow definitely.
4. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-246 · L3 · hard · Either-or conclusions in inequality · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: A > E < B ≥ C; D > A = F

Conclusions:
I. B ≥ A
II. B < A
III. C < D

- **A.** Either I or II follows ✅
- **B.** Only I and III follow  _(error: misjudged conclusion(s) I, II, III)_
- **C.** Only II and III follow  _(error: misjudged conclusion(s) I, II, III)_
- **D.** Only I follows  _(error: misjudged conclusion(s) I, II)_

**Working**

1. Combine the statements: A > E < B ≥ C; D > A = F.
2. Conclusion I (B ≥ A): no definite relation between B and A → does not follow definitely.
3. Conclusion II (B < A): no definite relation between B and A → does not follow definitely.
4. Conclusion III (C < D): no definite relation between C and D → does not follow definitely.
5. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
6. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-247 · L3 · hard · Either-or conclusions in inequality · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: D ≥ G ≤ B < E; G < F = C > A

Conclusions:
I. B ≤ F
II. B > F
III. F < D

- **A.** Only I and III follow  _(error: misjudged conclusion(s) I, II, III)_
- **B.** Only II follows  _(error: misjudged conclusion(s) I, II)_
- **C.** Either I or II follows ✅
- **D.** Either I or III follows  _(error: paired conclusions that are not a valid either-or pair)_

**Working**

1. Combine the statements: D ≥ G ≤ B < E; G < F = C > A.
2. Conclusion I (B ≤ F): no definite relation between B and F → does not follow definitely.
3. Conclusion II (B > F): no definite relation between B and F → does not follow definitely.
4. Conclusion III (F < D): no definite relation between F and D → does not follow definitely.
5. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
6. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-248 · L3 · hard · Either-or conclusions in inequality · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: M > Q = N = S; R ≥ S > P

Conclusions:
I. R > Q
II. R = Q
III. S < M

- **A.** Only II and either I or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **B.** Only III and either I or II follow ✅
- **C.** Either I or II follows  _(error: misjudged the third conclusion)_
- **D.** None follows  _(error: misjudged conclusion(s) I, II, III)_

**Working**

1. Combine the statements: M > Q = N = S; R ≥ S > P.
2. Conclusion I (R > Q): derived relation is R ≥ Q → does not follow definitely.
3. Conclusion II (R = Q): derived relation is R ≥ Q → does not follow definitely.
4. Conclusion III (S < M): derived relation is S < M → follows.
5. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
6. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-249 · L3 · hard · Either-or conclusions in inequality · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: K ≤ J < N > L; K < Q ≤ P > M

Conclusions:
I. M > Q
II. J ≥ L
III. J < L

- **A.** Only III and either I or II follow  _(error: paired conclusions that are not a valid either-or pair)_
- **B.** Either II or III follows ✅
- **C.** Only I and II follow  _(error: misjudged conclusion(s) I, II, III)_
- **D.** Only I and III follow  _(error: misjudged conclusion(s) I, II, III)_

**Working**

1. Combine the statements: K ≤ J < N > L; K < Q ≤ P > M.
2. Conclusion I (M > Q): no definite relation between M and Q → does not follow definitely.
3. Conclusion II (J ≥ L): no definite relation between J and L → does not follow definitely.
4. Conclusion III (J < L): no definite relation between J and L → does not follow definitely.
5. Conclusions II and III involve the same pair, are mutually exclusive and together cover every possibility → either II or III follows.
6. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-250 · L3 · hard · Either-or conclusions in inequality · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: B ≤ D = A < F; F ≥ C ≥ E

Conclusions:
I. F > D
II. B < A
III. B = A

- **A.** None follows  _(error: misjudged conclusion(s) I, II, III)_
- **B.** Only I and either II or III follow ✅
- **C.** Only I and II follow  _(error: misjudged conclusion(s) II, III)_
- **D.** Only III and either I or II follow  _(error: paired conclusions that are not a valid either-or pair)_

**Working**

1. Combine the statements: B ≤ D = A < F; F ≥ C ≥ E.
2. Conclusion I (F > D): derived relation is F > D → follows.
3. Conclusion II (B < A): derived relation is B ≤ A → does not follow definitely.
4. Conclusion III (B = A): derived relation is B ≤ A → does not follow definitely.
5. Conclusions II and III involve the same pair, are mutually exclusive and together cover every possibility → either II or III follows.
6. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-251 · L3 · hard · Either-or conclusions in inequality · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: B ≥ E ≤ A = C; G < A < D < F

Conclusions:
I. B ≤ A
II. B > A
III. G > D

- **A.** All I, II and III follow  _(error: misjudged conclusion(s) I, II, III)_
- **B.** Either I or II follows ✅
- **C.** Only III follows  _(error: misjudged conclusion(s) I, II, III)_
- **D.** Only II follows  _(error: misjudged conclusion(s) I, II)_

**Working**

1. Combine the statements: B ≥ E ≤ A = C; G < A < D < F.
2. Conclusion I (B ≤ A): no definite relation between B and A → does not follow definitely.
3. Conclusion II (B > A): no definite relation between B and A → does not follow definitely.
4. Conclusion III (G > D): derived relation is G < D → does not follow definitely.
5. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
6. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-252 · L3 · hard · Either-or conclusions in inequality · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: K ≥ L ≤ M ≤ J; M > Q ≥ P < N

Conclusions:
I. Q = K
II. Q > K

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Neither I nor II follows ✅
- **C.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **D.** Only I follows  _(error: conclusion I does not follow definitely)_

**Working**

1. Combine the statements: K ≥ L ≤ M ≤ J; M > Q ≥ P < N.
2. Conclusion I (Q = K): no definite relation between Q and K → does not follow definitely.
3. Conclusion II (Q > K): no definite relation between Q and K → does not follow definitely.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-253 · L3 · hard · Either-or conclusions in inequality · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: S > X ≥ Y > U; T ≤ Y ≤ V = W

Conclusions:
I. U ≥ T
II. U < T

- **A.** Only II follows  _(error: conclusion II does not follow definitely)_
- **B.** Neither I nor II follows  _(error: missed the either-or pair)_
- **C.** Only I follows  _(error: conclusion I does not follow definitely)_
- **D.** Either I or II follows ✅

**Working**

1. Combine the statements: S > X ≥ Y > U; T ≤ Y ≤ V = W.
2. Conclusion I (U ≥ T): no definite relation between U and T → does not follow definitely.
3. Conclusion II (U < T): no definite relation between U and T → does not follow definitely.
4. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-254 · L3 · hard · Either-or conclusions in inequality · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: C < B > F = D; F ≥ A ≥ E < G

Conclusions:
I. B ≥ A
II. B > A

- **A.** Only II follows  _(error: conclusion I also follows)_
- **B.** Both I and II follow ✅
- **C.** Only I follows  _(error: conclusion II also follows)_
- **D.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_

**Working**

1. Combine the statements: C < B > F = D; F ≥ A ≥ E < G.
2. Conclusion I (B ≥ A): derived relation is B > A → follows.
3. Conclusion II (B > A): derived relation is B > A → follows.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-255 · L3 · hard · Either-or conclusions in inequality · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: F ≤ H > E = D; G < K < J < H

Conclusions:
I. F < J
II. G < J

- **A.** Only I follows  _(error: conclusion I does not follow definitely)_
- **B.** Only II follows ✅
- **C.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **D.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_

**Working**

1. Combine the statements: F ≤ H > E = D; G < K < J < H.
2. Conclusion I (F < J): no definite relation between F and J → does not follow definitely.
3. Conclusion II (G < J): derived relation is G < J → follows.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-256 · L2 · medium · Multi-chain inequality with linked variables · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: U < X ≤ S ≤ W; V = U > T

Conclusions:
I. T < S
II. V ≤ T

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **D.** Only I follows ✅

**Working**

1. Combine the statements: U < X ≤ S ≤ W; V = U > T.
2. Conclusion I (T < S): derived relation is T < S → follows.
3. Conclusion II (V ≤ T): derived relation is V > T → does not follow definitely.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-257 · L2 · medium · Multi-chain inequality with linked variables · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: E ≤ A < D ≥ B; F > C ≥ A

Conclusions:
I. E ≤ B
II. E > D

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Only I follows  _(error: conclusion I does not follow definitely)_
- **D.** Neither I nor II follows ✅

**Working**

1. Combine the statements: E ≤ A < D ≥ B; F > C ≥ A.
2. Conclusion I (E ≤ B): no definite relation between E and B → does not follow definitely.
3. Conclusion II (E > D): derived relation is E < D → does not follow definitely.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-258 · L2 · medium · Multi-chain inequality with linked variables · foundation

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: G ≤ B ≥ C < F; E < G ≤ D

Conclusions:
I. E < D
II. B ≥ E

- **A.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **B.** Only II follows  _(error: conclusion I also follows)_
- **C.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **D.** Both I and II follow ✅

**Working**

1. Combine the statements: G ≤ B ≥ C < F; E < G ≤ D.
2. Conclusion I (E < D): derived relation is E < D → follows.
3. Conclusion II (B ≥ E): derived relation is B > E → follows.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-259 · L2 · medium · Multi-chain inequality with linked variables · foundation

Which of the following symbols should replace the question mark (?) in the expression 'L ? K = P ≤ M < N' so that both 'L ≥ K' and 'L = P' are definitely true?

- **A.** >  _(error: makes at least one of the two relations uncertain or false)_
- **B.** <  _(error: makes at least one of the two relations uncertain or false)_
- **C.** ≥  _(error: makes at least one of the two relations uncertain or false)_
- **D.** = ✅

**Working**

1. Try each symbol in place of ? and trace L–K and L–P.
2. Only '=' makes both relations definite: L = K = P ≤ M < N.
3. Every other symbol either reverses a sign on one of the paths or weakens a required strict sign.
4. Each of the five symbols was tested by exhaustive enumeration of orderings in the builder.

**Formula:** Both target paths pass through '?'; the symbol must point the same way as the rest of each path and supply strictness if required  
**Trap:** Check both targets; a symbol that satisfies one can break the other.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-260 · L2 · medium · Multi-chain inequality with linked variables · foundation

Which of the following symbols should replace the question mark (?) in the expression 'S < U = T ? V = W' so that both 'U ≤ W' and 'T = W' are definitely true?

- **A.** ≥  _(error: makes at least one of the two relations uncertain or false)_
- **B.** = ✅
- **C.** >  _(error: makes at least one of the two relations uncertain or false)_
- **D.** <  _(error: makes at least one of the two relations uncertain or false)_

**Working**

1. Try each symbol in place of ? and trace U–W and T–W.
2. Only '=' makes both relations definite: S < U = T = V = W.
3. Every other symbol either reverses a sign on one of the paths or weakens a required strict sign.
4. Each of the five symbols was tested by exhaustive enumeration of orderings in the builder.

**Formula:** Both target paths pass through '?'; the symbol must point the same way as the rest of each path and supply strictness if required  
**Trap:** Check both targets; a symbol that satisfies one can break the other.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-261 · L3 · hard · Multi-chain inequality with linked variables · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: T > Q = R; N ≥ U = T; Q ≥ M > S > P

Conclusions:
I. T ≥ N
II. T < N

- **A.** Either I or II follows ✅
- **B.** Only I follows  _(error: conclusion I does not follow definitely)_
- **C.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **D.** Only II follows  _(error: conclusion II does not follow definitely)_

**Working**

1. Combine the statements: T > Q = R; N ≥ U = T; Q ≥ M > S > P.
2. Conclusion I (T ≥ N): derived relation is T ≤ N → does not follow definitely.
3. Conclusion II (T < N): derived relation is T ≤ N → does not follow definitely.
4. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-262 · L3 · hard · Multi-chain inequality with linked variables · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: R ≥ M > Q; J ≤ K ≥ R; J ≤ L < N = P

Conclusions:
I. N < J
II. J < P

- **A.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Only I follows  _(error: conclusion I does not follow definitely)_
- **D.** Only II follows ✅

**Working**

1. Combine the statements: R ≥ M > Q; J ≤ K ≥ R; J ≤ L < N = P.
2. Conclusion I (N < J): derived relation is N > J → does not follow definitely.
3. Conclusion II (J < P): derived relation is J < P → follows.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-263 · L3 · hard · Multi-chain inequality with linked variables · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: F ≥ A = E; D > A < C; F ≤ H ≥ G ≤ B

Conclusions:
I. B > D
II. B < E

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Neither I nor II follows ✅
- **D.** Only II follows  _(error: conclusion II does not follow definitely)_

**Working**

1. Combine the statements: F ≥ A = E; D > A < C; F ≤ H ≥ G ≤ B.
2. Conclusion I (B > D): no definite relation between B and D → does not follow definitely.
3. Conclusion II (B < E): no definite relation between B and E → does not follow definitely.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-264 · L3 · hard · Multi-chain inequality with linked variables · officer

In the question below, some statements are followed by two conclusions I and II. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: M < Q ≤ P; T < R < Q; P ≥ U = S ≤ N

Conclusions:
I. R ≤ P
II. U > T

- **A.** Only II follows  _(error: conclusion II does not follow definitely)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Only I follows ✅
- **D.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_

**Working**

1. Combine the statements: M < Q ≤ P; T < R < Q; P ≥ U = S ≤ N.
2. Conclusion I (R ≤ P): derived relation is R < P → follows.
3. Conclusion II (U > T): no definite relation between U and T → does not follow definitely.
4. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** A relation follows only if it holds in every ordering consistent with the statements; opposite signs (> then <) break the chain  
**Trap:** Do not read across opposite-direction signs; ≥ combined with > gives >, but ≥ with ≥ gives only ≥.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-265 · L3 · hard · Multi-chain inequality with linked variables · officer

Which of the following sets of symbols, placed in the blanks from left to right, will make the expressions 'S < R' and 'Q < R' definitely true?

S _ P _ T _ Q _ R

- **A.** <, ≤, <, < ✅
- **B.** <, ≤, <, ≥  _(error: one sign on a required path points the wrong way or is not strict)_
- **C.** <, ≤, <, >  _(error: one sign on a required path points the wrong way or is not strict)_
- **D.** ≥, ≤, <, <  _(error: one sign on a required path points the wrong way or is not strict)_

**Working**

1. With '<, ≤, <, <' the expression reads S < P ≤ T < Q < R.
2. Both paths (S to R, Q to R) have all signs in one direction with the needed strictness.
3. Each of the other sets leaves at least one target uncertain or false.
4. All four options checked by exhaustive enumeration in the builder.

**Formula:** Target '>' needs all signs on the path in the same direction with at least one strict sign  
**Trap:** A set can satisfy the end-to-end relation yet fail the middle-letter relation.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-266 · L3 · hard · Multi-chain inequality with linked variables · officer

Which of the following sets of symbols, placed in the blanks from left to right, will make the expressions 'R > M' and 'Q ≥ M' definitely true?

R _ Q _ N _ P _ M

- **A.** >, ≥, >, ≤  _(error: one sign on a required path points the wrong way or is not strict)_
- **B.** <, ≥, >, ≥  _(error: one sign on a required path points the wrong way or is not strict)_
- **C.** >, ≤, >, ≥  _(error: one sign on a required path points the wrong way or is not strict)_
- **D.** >, ≥, >, ≥ ✅

**Working**

1. With '>, ≥, >, ≥' the expression reads R > Q ≥ N > P ≥ M.
2. Both paths (R to M, Q to M) have all signs in one direction with the needed strictness.
3. Each of the other sets leaves at least one target uncertain or false.
4. All four options checked by exhaustive enumeration in the builder.

**Formula:** Target '>' needs all signs on the path in the same direction with at least one strict sign  
**Trap:** A set can satisfy the end-to-end relation yet fail the middle-letter relation.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-267 · L3 · hard · Multi-chain inequality with linked variables · officer

Which of the following sets of symbols, placed in the blanks from left to right, will make the expressions 'N < K' and 'P < K' definitely true?

N _ L _ M _ P _ K

- **A.** ≤, =, ≥, <  _(error: one sign on a required path points the wrong way or is not strict)_
- **B.** ≤, =, <, ≤  _(error: one sign on a required path points the wrong way or is not strict)_
- **C.** ≤, ≥, <, <  _(error: one sign on a required path points the wrong way or is not strict)_
- **D.** ≤, =, <, < ✅

**Working**

1. With '≤, =, <, <' the expression reads N ≤ L = M < P < K.
2. Both paths (N to K, P to K) have all signs in one direction with the needed strictness.
3. Each of the other sets leaves at least one target uncertain or false.
4. All four options checked by exhaustive enumeration in the builder.

**Formula:** Target '>' needs all signs on the path in the same direction with at least one strict sign  
**Trap:** A set can satisfy the end-to-end relation yet fail the middle-letter relation.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-268 · L3 · hard · Multi-chain inequality with linked variables · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: B ≤ C ≥ G; A > G < F; E < H < F ≤ D

Conclusions:
I. D > C
II. B < D
III. H < A

- **A.** None follows ✅
- **B.** Only I and III follow  _(error: misjudged conclusion(s) I, III)_
- **C.** Only II and III follow  _(error: misjudged conclusion(s) II, III)_
- **D.** Only I and either II or III follow  _(error: paired conclusions that are not a valid either-or pair)_

**Working**

1. Combine the statements: B ≤ C ≥ G; A > G < F; E < H < F ≤ D.
2. Conclusion I (D > C): no definite relation between D and C → does not follow definitely.
3. Conclusion II (B < D): no definite relation between B and D → does not follow definitely.
4. Conclusion III (H < A): no definite relation between H and A → does not follow definitely.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-269 · L3 · hard · Multi-chain inequality with linked variables · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: C < D < H; C ≤ G ≤ A; F > B ≥ E < D

Conclusions:
I. A < H
II. C = A
III. C < A

- **A.** None follows  _(error: misjudged conclusion(s) II, III)_
- **B.** Either I or III follows  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** Either II or III follows ✅
- **D.** Only I follows  _(error: misjudged conclusion(s) I, II, III)_

**Working**

1. Combine the statements: C < D < H; C ≤ G ≤ A; F > B ≥ E < D.
2. Conclusion I (A < H): no definite relation between A and H → does not follow definitely.
3. Conclusion II (C = A): derived relation is C ≤ A → does not follow definitely.
4. Conclusion III (C < A): derived relation is C ≤ A → does not follow definitely.
5. Conclusions II and III involve the same pair, are mutually exclusive and together cover every possibility → either II or III follows.
6. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-270 · L3 · hard · Multi-chain inequality with linked variables · officer

In the question below, some statements are followed by three conclusions. Assuming the statements to be true, decide which conclusion(s) definitely follow.

Statements: G > H > C; F ≥ J < G; F > E > D > B

Conclusions:
I. E = G
II. J ≥ C
III. H = E

- **A.** Only III follows  _(error: misjudged conclusion(s) III)_
- **B.** Only I and either II or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** None follows ✅
- **D.** All I, II and III follow  _(error: misjudged conclusion(s) I, II, III)_

**Working**

1. Combine the statements: G > H > C; F ≥ J < G; F > E > D > B.
2. Conclusion I (E = G): no definite relation between E and G → does not follow definitely.
3. Conclusion II (J ≥ C): no definite relation between J and C → does not follow definitely.
4. Conclusion III (H = E): no definite relation between H and E → does not follow definitely.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Definite relation ⇔ holds in every consistent ordering; either-or ⇔ same pair, exclusive and exhaustive, neither definite  
**Trap:** An either-or pair is valid only when neither conclusion follows on its own and together they cover all cases.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-271 · L2 · medium · Symbol-substitution inequality · foundation

In the following question, the symbols are used with the meanings given below.

'P $ Q' means 'P is either smaller than or equal to Q'. 'P ★ Q' means 'P is smaller than Q'. 'P * Q' means 'P is greater than Q'. 'P # Q' means 'P is either greater than or equal to Q'. 'P @ Q' means 'P is equal to Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: R # P * Q # S

Conclusions:
I. R # Q
II. P ★ S

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Only II follows  _(error: conclusion II does not follow definitely)_
- **D.** Only I follows ✅

**Working**

1. Decode the symbols: * → >, # → ≥, @ → =, $ → ≤, ★ → <.
2. Combine the statements: R ≥ P > Q ≥ S.
3. Conclusion I (R ≥ Q): derived relation is R > Q → follows.
4. Conclusion II (P < S): derived relation is P > S → does not follow definitely.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-272 · L2 · medium · Symbol-substitution inequality · foundation

In the following question, the symbols are used with the meanings given below.

'P @ Q' means 'P is not greater than Q'. 'P $ Q' means 'P is not smaller than Q'. 'P ★ Q' means 'P is neither smaller than nor greater than Q'. 'P % Q' means 'P is neither greater than nor equal to Q'. 'P © Q' means 'P is neither smaller than nor equal to Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: N ★ M @ K ★ L

Conclusions:
I. N © K
II. L ★ M

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Only I follows  _(error: conclusion I does not follow definitely)_
- **C.** Neither I nor II follows ✅
- **D.** Only II follows  _(error: conclusion II does not follow definitely)_

**Working**

1. Decode the symbols: © → >, $ → ≥, ★ → =, @ → ≤, % → <.
2. Combine the statements: N = M ≤ K = L.
3. Conclusion I (N > K): derived relation is N ≤ K → does not follow definitely.
4. Conclusion II (L = M): derived relation is L ≥ M → does not follow definitely.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-273 · L2 · medium · Symbol-substitution inequality · foundation

In the following question, the symbols are used with the meanings given below.

'P & Q' means 'P is either smaller than or equal to Q'. 'P % Q' means 'P is either greater than or equal to Q'. 'P ★ Q' means 'P is greater than Q'. 'P # Q' means 'P is equal to Q'. 'P @ Q' means 'P is smaller than Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: D & A ★ B @ E & C

Conclusions:
I. B & C
II. C ★ B

- **A.** Only I follows  _(error: conclusion II also follows)_
- **B.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **C.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **D.** Both I and II follow ✅

**Working**

1. Decode the symbols: ★ → >, % → ≥, # → =, & → ≤, @ → <.
2. Combine the statements: D ≤ A > B < E ≤ C.
3. Conclusion I (B ≤ C): derived relation is B < C → follows.
4. Conclusion II (C > B): derived relation is C > B → follows.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-274 · L2 · medium · Symbol-substitution inequality · foundation

In the following question, the symbols are used with the meanings given below.

'P ★ Q' means 'P is equal to Q'. 'P * Q' means 'P is smaller than Q'. 'P # Q' means 'P is either greater than or equal to Q'. 'P & Q' means 'P is either smaller than or equal to Q'. 'P $ Q' means 'P is greater than Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: F & G ★ D # H # E

Conclusions:
I. G $ H
II. G ★ H

- **A.** Only I follows  _(error: conclusion I does not follow definitely)_
- **B.** Neither I nor II follows  _(error: missed the either-or pair)_
- **C.** Either I or II follows ✅
- **D.** Only II follows  _(error: conclusion II does not follow definitely)_

**Working**

1. Decode the symbols: $ → >, # → ≥, ★ → =, & → ≤, * → <.
2. Combine the statements: F ≤ G = D ≥ H ≥ E.
3. Conclusion I (G > H): derived relation is G ≥ H → does not follow definitely.
4. Conclusion II (G = H): derived relation is G ≥ H → does not follow definitely.
5. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
6. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-275 · L2 · medium · Symbol-substitution inequality · foundation

In the following question, the symbols are used with the meanings given below.

'P # Q' means 'P is either greater than or equal to Q'. 'P @ Q' means 'P is smaller than Q'. 'P © Q' means 'P is either smaller than or equal to Q'. 'P $ Q' means 'P is equal to Q'. 'P * Q' means 'P is greater than Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: H © F # G © E @ D

Conclusions:
I. H * D
II. D * G

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **C.** Only I follows  _(error: conclusion I does not follow definitely)_
- **D.** Only II follows ✅

**Working**

1. Decode the symbols: * → >, # → ≥, $ → =, © → ≤, @ → <.
2. Combine the statements: H ≤ F ≥ G ≤ E < D.
3. Conclusion I (H > D): no definite relation between H and D → does not follow definitely.
4. Conclusion II (D > G): derived relation is D > G → follows.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-276 · L3 · hard · Symbol-substitution inequality · officer

In the following question, the symbols are used with the meanings given below.

'P * Q' means 'P is neither smaller than nor greater than Q'. 'P ★ Q' means 'P is neither smaller than nor equal to Q'. 'P @ Q' means 'P is not greater than Q'. 'P # Q' means 'P is not smaller than Q'. 'P © Q' means 'P is neither greater than nor equal to Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: A ★ F ★ D * B; C @ A * G © E

Conclusions:
I. F © C
II. D @ G
III. F # C

- **A.** Only III follows  _(error: misjudged conclusion(s) I, II, III)_
- **B.** Only III and either I or II follow  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** Only II and either I or III follow ✅
- **D.** Only I follows  _(error: misjudged conclusion(s) I, II, III)_

**Working**

1. Decode the symbols: ★ → >, # → ≥, * → =, @ → ≤, © → <.
2. Combine the statements: A > F > D = B; C ≤ A = G < E.
3. Conclusion I (F < C): no definite relation between F and C → does not follow definitely.
4. Conclusion II (D ≤ G): derived relation is D < G → follows.
5. Conclusion III (F ≥ C): no definite relation between F and C → does not follow definitely.
6. Conclusions I and III involve the same pair, are mutually exclusive and together cover every possibility → either I or III follows.
7. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-277 · L3 · hard · Symbol-substitution inequality · officer

In the following question, the symbols are used with the meanings given below.

'P © Q' means 'P is either smaller than or equal to Q'. 'P % Q' means 'P is greater than Q'. 'P $ Q' means 'P is either greater than or equal to Q'. 'P ★ Q' means 'P is smaller than Q'. 'P @ Q' means 'P is equal to Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: P $ M @ R © Q; S ★ P ★ T @ N

Conclusions:
I. P @ Q
II. P ★ R
III. N ★ Q

- **A.** Either I or III follows  _(error: paired conclusions that are not a valid either-or pair)_
- **B.** Only II and either I or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** None follows ✅
- **D.** Only I and III follow  _(error: misjudged conclusion(s) I, III)_

**Working**

1. Decode the symbols: % → >, $ → ≥, @ → =, © → ≤, ★ → <.
2. Combine the statements: P ≥ M = R ≤ Q; S < P < T = N.
3. Conclusion I (P = Q): no definite relation between P and Q → does not follow definitely.
4. Conclusion II (P < R): derived relation is P ≥ R → does not follow definitely.
5. Conclusion III (N < Q): no definite relation between N and Q → does not follow definitely.
6. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-278 · L4 · hard · Symbol-substitution inequality · officer

In the following question, the symbols are used with the meanings given below.

'P $ Q' means 'P is not greater than Q'. 'P @ Q' means 'P is neither smaller than nor greater than Q'. 'P * Q' means 'P is neither greater than nor equal to Q'. 'P # Q' means 'P is neither smaller than nor equal to Q'. 'P © Q' means 'P is not smaller than Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: L * Q © K @ N; K @ M © P

Conclusions:
I. Q # P
II. Q $ P

- **A.** Either I or II follows ✅
- **B.** Only II follows  _(error: conclusion II does not follow definitely)_
- **C.** Neither I nor II follows  _(error: missed the either-or pair)_
- **D.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_

**Working**

1. Decode the symbols: # → >, © → ≥, @ → =, $ → ≤, * → <.
2. Combine the statements: L < Q ≥ K = N; K = M ≥ P.
3. Conclusion I (Q > P): derived relation is Q ≥ P → does not follow definitely.
4. Conclusion II (Q ≤ P): derived relation is Q ≥ P → does not follow definitely.
5. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
6. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-279 · L4 · hard · Symbol-substitution inequality · officer

In the following question, the symbols are used with the meanings given below.

'P $ Q' means 'P is not greater than Q'. 'P @ Q' means 'P is neither smaller than nor greater than Q'. 'P * Q' means 'P is neither greater than nor equal to Q'. 'P # Q' means 'P is neither smaller than nor equal to Q'. 'P © Q' means 'P is not smaller than Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: R $ Q $ P $ T; S * V # T $ U

Conclusions:
I. R $ U
II. T # R

- **A.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Only I follows ✅
- **D.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_

**Working**

1. Decode the symbols: # → >, © → ≥, @ → =, $ → ≤, * → <.
2. Combine the statements: R ≤ Q ≤ P ≤ T; S < V > T ≤ U.
3. Conclusion I (R ≤ U): derived relation is R ≤ U → follows.
4. Conclusion II (T > R): derived relation is T ≥ R → does not follow definitely.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-280 · L4 · hard · Symbol-substitution inequality · officer

In the following question, the symbols are used with the meanings given below.

'P $ Q' means 'P is not greater than Q'. 'P @ Q' means 'P is neither smaller than nor greater than Q'. 'P * Q' means 'P is neither greater than nor equal to Q'. 'P # Q' means 'P is neither smaller than nor equal to Q'. 'P © Q' means 'P is not smaller than Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: R # N # S @ P; N @ Q @ M

Conclusions:
I. M * P
II. M @ P

- **A.** Neither I nor II follows ✅
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Only I follows  _(error: conclusion I does not follow definitely)_
- **D.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_

**Working**

1. Decode the symbols: # → >, © → ≥, @ → =, $ → ≤, * → <.
2. Combine the statements: R > N > S = P; N = Q = M.
3. Conclusion I (M < P): derived relation is M > P → does not follow definitely.
4. Conclusion II (M = P): derived relation is M > P → does not follow definitely.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-281 · L4 · hard · Symbol-substitution inequality · officer

In the following question, the symbols are used with the meanings given below.

'P $ Q' means 'P is not greater than Q'. 'P @ Q' means 'P is neither smaller than nor greater than Q'. 'P * Q' means 'P is neither greater than nor equal to Q'. 'P # Q' means 'P is neither smaller than nor equal to Q'. 'P © Q' means 'P is not smaller than Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: F * B @ C # G; D # A © F * E

Conclusions:
I. F * D
II. B © G

- **A.** Both I and II follow ✅
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Only II follows  _(error: conclusion I also follows)_
- **D.** Only I follows  _(error: conclusion II also follows)_

**Working**

1. Decode the symbols: # → >, © → ≥, @ → =, $ → ≤, * → <.
2. Combine the statements: F < B = C > G; D > A ≥ F < E.
3. Conclusion I (F < D): derived relation is F < D → follows.
4. Conclusion II (B ≥ G): derived relation is B > G → follows.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-282 · L4 · hard · Symbol-substitution inequality · officer

In the following question, the symbols are used with the meanings given below.

'P $ Q' means 'P is not greater than Q'. 'P @ Q' means 'P is neither smaller than nor greater than Q'. 'P * Q' means 'P is neither greater than nor equal to Q'. 'P # Q' means 'P is neither smaller than nor equal to Q'. 'P © Q' means 'P is not smaller than Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: N * J # P * L; K © M © L

Conclusions:
I. L # N
II. P $ M

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Only I follows  _(error: conclusion I does not follow definitely)_
- **C.** Only II follows ✅
- **D.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_

**Working**

1. Decode the symbols: # → >, © → ≥, @ → =, $ → ≤, * → <.
2. Combine the statements: N < J > P < L; K ≥ M ≥ L.
3. Conclusion I (L > N): no definite relation between L and N → does not follow definitely.
4. Conclusion II (P ≤ M): derived relation is P < M → follows.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-283 · L4 · hard · Symbol-substitution inequality · officer

In the following question, the symbols are used with the meanings given below.

'P & Q' means 'P is neither smaller than nor equal to Q'. 'P ★ Q' means 'P is not smaller than Q'. 'P © Q' means 'P is not greater than Q'. 'P $ Q' means 'P is neither smaller than nor greater than Q'. 'P @ Q' means 'P is neither greater than nor equal to Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: R $ T © P © Q; U $ Q @ S

Conclusions:
I. T ★ Q
II. R © U

- **A.** Only II follows ✅
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Only I follows  _(error: conclusion I does not follow definitely)_
- **D.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_

**Working**

1. Decode the symbols: & → >, ★ → ≥, $ → =, © → ≤, @ → <.
2. Combine the statements: R = T ≤ P ≤ Q; U = Q < S.
3. Conclusion I (T ≥ Q): derived relation is T ≤ Q → does not follow definitely.
4. Conclusion II (R ≤ U): derived relation is R ≤ U → follows.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-284 · L4 · hard · Symbol-substitution inequality · officer

In the following question, the symbols are used with the meanings given below.

'P & Q' means 'P is neither smaller than nor equal to Q'. 'P ★ Q' means 'P is not smaller than Q'. 'P © Q' means 'P is not greater than Q'. 'P $ Q' means 'P is neither smaller than nor greater than Q'. 'P @ Q' means 'P is neither greater than nor equal to Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: Q @ R $ T © M; N © P ★ T @ S

Conclusions:
I. S @ M
II. S ★ M

- **A.** Either I or II follows ✅
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Only II follows  _(error: conclusion II does not follow definitely)_
- **D.** Neither I nor II follows  _(error: missed the either-or pair)_

**Working**

1. Decode the symbols: & → >, ★ → ≥, $ → =, © → ≤, @ → <.
2. Combine the statements: Q < R = T ≤ M; N ≤ P ≥ T < S.
3. Conclusion I (S < M): no definite relation between S and M → does not follow definitely.
4. Conclusion II (S ≥ M): no definite relation between S and M → does not follow definitely.
5. Conclusions I and II involve the same pair, are mutually exclusive and together cover every possibility → either I or II follows.
6. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-285 · L4 · hard · Symbol-substitution inequality · officer

In the following question, the symbols are used with the meanings given below.

'P & Q' means 'P is neither smaller than nor equal to Q'. 'P ★ Q' means 'P is not smaller than Q'. 'P © Q' means 'P is not greater than Q'. 'P $ Q' means 'P is neither smaller than nor greater than Q'. 'P @ Q' means 'P is neither greater than nor equal to Q'.

Assuming the statements to be true, decide which of the conclusions definitely follow.

Statements: B & F & C & D; A $ B ★ E

Conclusions:
I. B @ C
II. C $ B

- **A.** Neither I nor II follows ✅
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **D.** Only I follows  _(error: conclusion I does not follow definitely)_

**Working**

1. Decode the symbols: & → >, ★ → ≥, $ → =, © → ≤, @ → <.
2. Combine the statements: B > F > C > D; A = B ≥ E.
3. Conclusion I (B < C): derived relation is B > C → does not follow definitely.
4. Conclusion II (C = B): derived relation is C < B → does not follow definitely.
5. Checked by enumerating every ordering of the letters consistent with the statements.

**Formula:** Decode each symbol to >, <, =, ≥ or ≤, then apply the chain rule  
**Trap:** 'Not smaller than' is ≥ (not >); 'neither smaller than nor equal to' is >.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-286 · L1 · easy · Two-statement syllogism · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
All bottles are chairs.
Some teachers are chairs.

Conclusions:
I. Some bottles are chairs.
II. No teacher is a chair.

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **C.** Only II follows  _(error: conclusion II does not follow definitely)_
- **D.** Only I follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: All bottles are chairs. Some teachers are chairs.
2. Conclusion I: Some bottles are chairs. → true in every valid diagram → follows.
3. Conclusion II: No teacher is a chair. → false in every valid diagram → does not follow.
4. Verified by enumerating all 20 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-287 · L1 · easy · Two-statement syllogism · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
All doctors are birds.
Some doctors are stars.

Conclusions:
I. Some birds are stars.
II. Some doctors are birds.

- **A.** Only I follows  _(error: conclusion II also follows)_
- **B.** Only II follows  _(error: conclusion I also follows)_
- **C.** Both I and II follow ✅
- **D.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: All doctors are birds. Some doctors are stars.
2. Conclusion I: Some birds are stars. → true in every valid diagram → follows.
3. Conclusion II: Some doctors are birds. → true in every valid diagram → follows.
4. Verified by enumerating all 16 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-288 · L2 · medium · Two-statement syllogism · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No bus is a rose.
Some chairs are roses.

Conclusions:
I. All chairs are roses.
II. Some buses are chairs.

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Neither I nor II follows ✅
- **C.** Only I follows  _(error: conclusion I does not follow definitely)_
- **D.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: No bus is a rose. Some chairs are roses.
2. Conclusion I: All chairs are roses. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: Some buses are chairs. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Verified by enumerating all 12 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-289 · L2 · medium · Two-statement syllogism · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some teachers are buses.
All pilots are buses.

Conclusions:
I. Some buses are not pilots.
II. All buses are pilots.

- **A.** Either I or II follows ✅
- **B.** Neither I nor II follows  _(error: missed the either-or pair)_
- **C.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **D.** Only I follows  _(error: conclusion I does not follow definitely)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some teachers are buses. All pilots are buses.
2. Conclusion I: Some buses are not pilots. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All buses are pilots. → possible but not certain (a diagram exists where it fails) → does not follow.
4. I and II form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or II follows.
5. Verified by enumerating all 20 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-290 · L2 · medium · Two-statement syllogism · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No jar is a phone.
All bricks are phones.

Conclusions:
I. No brick is a phone.
II. Some phones are not jars.

- **A.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **D.** Only II follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: No jar is a phone. All bricks are phones.
2. Conclusion I: No brick is a phone. → false in every valid diagram → does not follow.
3. Conclusion II: Some phones are not jars. → true in every valid diagram → follows.
4. Verified by enumerating all 2 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-291 · L3 · hard · Two-statement syllogism · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some kites are not chairs.
No kite is a door.

Conclusions:
I. No door is a kite.
II. Some chairs are kites.
III. Some chairs are not doors.

- **A.** Only II follows  _(error: misjudged conclusion(s) I, II)_
- **B.** Only I follows ✅
- **C.** Only III follows  _(error: misjudged conclusion(s) I, III)_
- **D.** Only I and either II or III follow  _(error: paired conclusions that are not a valid either-or pair)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some kites are not chairs. No kite is a door.
2. Conclusion I: No door is a kite. → true in every valid diagram → follows.
3. Conclusion II: Some chairs are kites. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some chairs are not doors. → possible but not certain (a diagram exists where it fails) → does not follow.
5. Verified by enumerating all 11 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-292 · L3 · hard · Two-statement syllogism · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No coin is a river.
All doctors are rivers.

Conclusions:
I. All coins are rivers.
II. Some coins are not doctors.
III. No doctor is a coin.

- **A.** Only II and either I or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **B.** Only II and III follow ✅
- **C.** All I, II and III follow  _(error: misjudged conclusion(s) I)_
- **D.** Only III follows  _(error: misjudged conclusion(s) II)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: No coin is a river. All doctors are rivers.
2. Conclusion I: All coins are rivers. → false in every valid diagram → does not follow.
3. Conclusion II: Some coins are not doctors. → true in every valid diagram → follows.
4. Conclusion III: No doctor is a coin. → true in every valid diagram → follows.
5. Verified by enumerating all 2 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-293 · L3 · hard · Two-statement syllogism · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some roses are not lions.
Some roses are not laptops.

Conclusions:
I. All laptops are lions.
II. No laptop is a lion.
III. Some laptops are roses.

- **A.** Only II and III follow  _(error: misjudged conclusion(s) II, III)_
- **B.** Only I and II follow  _(error: misjudged conclusion(s) I, II)_
- **C.** Only III follows  _(error: misjudged conclusion(s) III)_
- **D.** None follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some roses are not lions. Some roses are not laptops.
2. Conclusion I: All laptops are lions. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: No laptop is a lion. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some laptops are roses. → possible but not certain (a diagram exists where it fails) → does not follow.
5. Verified by enumerating all 73 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-294 · L3 · hard · Two-statement syllogism · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some apples are not buses.
Some doors are not buses.

Conclusions:
I. All doors are apples.
II. Some doors are not apples.
III. Some buses are not doors.

- **A.** Only II follows  _(error: misjudged conclusion(s) I, II)_
- **B.** Either II or III follows  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** Either I or II follows ✅
- **D.** Only III and either I or II follow  _(error: misjudged the third conclusion)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some apples are not buses. Some doors are not buses.
2. Conclusion I: All doors are apples. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: Some doors are not apples. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some buses are not doors. → possible but not certain (a diagram exists where it fails) → does not follow.
5. I and II form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or II follows.
6. Verified by enumerating all 75 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-295 · L3 · hard · Two-statement syllogism · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No engineer is a coin.
Some clouds are not engineers.

Conclusions:
I. No cloud is an engineer.
II. All engineers are coins.
III. Some coins are not engineers.

- **A.** Only III follows ✅
- **B.** Either I or III follows  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** Only I and II follow  _(error: misjudged conclusion(s) I, II, III)_
- **D.** Only I and III follow  _(error: misjudged conclusion(s) I)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: No engineer is a coin. Some clouds are not engineers.
2. Conclusion I: No cloud is an engineer. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All engineers are coins. → false in every valid diagram → does not follow.
4. Conclusion III: Some coins are not engineers. → true in every valid diagram → follows.
5. Verified by enumerating all 15 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-296 · L3 · hard · Two-statement syllogism · officer

Statement I: No stone is a wall.
Conclusion: Some walls are not stars.

Which of the following, taken as Statement II along with Statement I, makes the conclusion follow definitely?

- **A.** Some stars are stones.  _(error: with this statement the conclusion is at best possible, not definite)_
- **B.** All stars are stones. ✅
- **C.** Some stones are not stars.  _(error: with this statement the conclusion is at best possible, not definite)_
- **D.** All stones are stars.  _(error: with this statement the conclusion is at best possible, not definite)_

**Working**

1. Only with 'All stars are stones.' does 'Some walls are not stars.' hold in every admissible diagram (2 models enumerated).
2. For each other candidate, enumeration finds a valid diagram in which the conclusion fails.
3. All candidate second statements were tested exhaustively in the builder (each one listed pair of the middle term).

**Formula:** The middle term must be distributed at least once; a particular premise yields only a particular conclusion  
**Trap:** 'Some' premises chained through the middle term never give a definite conclusion.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-297 · L3 · hard · Two-statement syllogism · officer

Statement I: Some lilies are clouds.
Conclusion: Some rivers are lilies.

Which of the following, taken as Statement II along with Statement I, makes the conclusion follow definitely?

- **A.** All clouds are rivers. ✅
- **B.** Some rivers are clouds.  _(error: with this statement the conclusion is at best possible, not definite)_
- **C.** No cloud is a river.  _(error: with this statement the conclusion is at best possible, not definite)_
- **D.** Some clouds are not rivers.  _(error: with this statement the conclusion is at best possible, not definite)_

**Working**

1. Only with 'All clouds are rivers.' does 'Some rivers are lilies.' hold in every admissible diagram (16 models enumerated).
2. For each other candidate, enumeration finds a valid diagram in which the conclusion fails.
3. All candidate second statements were tested exhaustively in the builder (each one listed pair of the middle term).

**Formula:** The middle term must be distributed at least once; a particular premise yields only a particular conclusion  
**Trap:** 'Some' premises chained through the middle term never give a definite conclusion.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-298 · L3 · hard · Two-statement syllogism · officer

Statement I: All dancers are buses.
Conclusion: All dancers are coins.

Which of the following, taken as Statement II along with Statement I, makes the conclusion follow definitely?

- **A.** No coin is a bus.  _(error: with this statement the conclusion is at best possible, not definite)_
- **B.** All buses are coins. ✅
- **C.** Some coins are not buses.  _(error: with this statement the conclusion is at best possible, not definite)_
- **D.** No bus is a coin.  _(error: with this statement the conclusion is at best possible, not definite)_

**Working**

1. Only with 'All buses are coins.' does 'All dancers are coins.' hold in every admissible diagram (4 models enumerated).
2. For each other candidate, enumeration finds a valid diagram in which the conclusion fails.
3. All candidate second statements were tested exhaustively in the builder (each one listed pair of the middle term).

**Formula:** The middle term must be distributed at least once; a particular premise yields only a particular conclusion  
**Trap:** 'Some' premises chained through the middle term never give a definite conclusion.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-299 · L2 · medium · Two-statement syllogism · officer

Statements:
Some trains are dancers.
Some dancers are stars.

Taking the statements to be true, which of the following conclusions logically follows?

- **A.** No dancer is a star.  _(error: ruled out by the statements)_
- **B.** Some stars are not trains.  _(error: possible but not certain)_
- **C.** Some stars are dancers. ✅
- **D.** No train is a dancer.  _(error: ruled out by the statements)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some trains are dancers. Some dancers are stars.
2. 'Some stars are dancers.' holds in every valid diagram.
3. Each other option fails in at least one valid diagram (or is ruled out altogether).
4. Verified by enumerating all 80 admissible Venn-region models in the builder.

**Formula:** A definite conclusion must hold in every admissible diagram  
**Trap:** Converting 'All A are B' gives only 'Some B are A', never 'All B are A'.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-300 · L2 · medium · Two-statement syllogism · officer

Statements:
Some walls are files.
Some files are not jackets.

Taking the statements to be true, which of the following conclusions logically follows?

- **A.** Some jackets are not walls.  _(error: possible but not certain)_
- **B.** Some jackets are walls.  _(error: possible but not certain)_
- **C.** No file is a wall.  _(error: ruled out by the statements)_
- **D.** Some files are walls. ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some walls are files. Some files are not jackets.
2. 'Some files are walls.' holds in every valid diagram.
3. Each other option fails in at least one valid diagram (or is ruled out altogether).
4. Verified by enumerating all 76 admissible Venn-region models in the builder.

**Formula:** A definite conclusion must hold in every admissible diagram  
**Trap:** Converting 'All A are B' gives only 'Some B are A', never 'All B are A'.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-301 · L2 · medium · Three or more statement syllogism · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No jacket is a train.
All tigers are apples.
Some jackets are apples.

Conclusions:
I. Some apples are jackets.
II. Some apples are not jackets.

- **A.** Only I follows ✅
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **D.** Only II follows  _(error: conclusion II does not follow definitely)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: No jacket is a train. All tigers are apples. Some jackets are apples.
2. Conclusion I: Some apples are jackets. → true in every valid diagram → follows.
3. Conclusion II: Some apples are not jackets. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Verified by enumerating all 156 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-302 · L2 · medium · Three or more statement syllogism · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No bottle is a river.
Some rivers are lions.
No mango is a lion.

Conclusions:
I. No lion is a bottle.
II. All mangoes are bottles.

- **A.** Only I follows  _(error: conclusion I does not follow definitely)_
- **B.** Only II follows  _(error: conclusion II does not follow definitely)_
- **C.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **D.** Neither I nor II follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: No bottle is a river. Some rivers are lions. No mango is a lion.
2. Conclusion I: No lion is a bottle. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All mangoes are bottles. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Verified by enumerating all 100 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-303 · L2 · medium · Three or more statement syllogism · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some coins are tables.
All coins are birds.
All tables are teachers.

Conclusions:
I. Some tables are birds.
II. Some teachers are tables.

- **A.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **B.** Only II follows  _(error: conclusion I also follows)_
- **C.** Only I follows  _(error: conclusion II also follows)_
- **D.** Both I and II follow ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some coins are tables. All coins are birds. All tables are teachers.
2. Conclusion I: Some tables are birds. → true in every valid diagram → follows.
3. Conclusion II: Some teachers are tables. → true in every valid diagram → follows.
4. Verified by enumerating all 128 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-304 · L2 · medium · Three or more statement syllogism · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
All walls are tigers.
Some jars are tigers.
All jars are birds.

Conclusions:
I. Some jars are not walls.
II. Some tigers are walls.

- **A.** Only I follows  _(error: conclusion I does not follow definitely)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **D.** Only II follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: All walls are tigers. Some jars are tigers. All jars are birds.
2. Conclusion I: Some jars are not walls. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: Some tigers are walls. → true in every valid diagram → follows.
4. Verified by enumerating all 176 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-305 · L2 · medium · Three or more statement syllogism · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some tigers are pilots.
All tigers are dancers.
All dancers are plates.

Conclusions:
I. All pilots are plates.
II. Some pilots are not plates.

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Neither I nor II follows  _(error: missed the either-or pair)_
- **C.** Either I or II follows ✅
- **D.** Only II follows  _(error: conclusion II does not follow definitely)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some tigers are pilots. All tigers are dancers. All dancers are plates.
2. Conclusion I: All pilots are plates. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: Some pilots are not plates. → possible but not certain (a diagram exists where it fails) → does not follow.
4. I and II form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or II follows.
5. Verified by enumerating all 64 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-306 · L3 · hard · Three or more statement syllogism · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No phone is a stone.
All mangoes are lions.
Some phones are lions.
All pens are stones.

Conclusions:
I. No stone is a phone.
II. Some phones are not pens.

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **C.** Only II follows  _(error: conclusion I also follows)_
- **D.** Both I and II follow ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: No phone is a stone. All mangoes are lions. Some phones are lions. All pens are stones.
2. Conclusion I: No stone is a phone. → true in every valid diagram → follows.
3. Conclusion II: Some phones are not pens. → true in every valid diagram → follows.
4. Verified by enumerating all 1296 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-307 · L3 · hard · Three or more statement syllogism · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some singers are not roses.
Some bricks are not bottles.
No bottle is a mango.
All bricks are singers.

Conclusions:
I. No mango is a rose.
II. No bottle is a brick.

- **A.** Only II follows  _(error: conclusion II does not follow definitely)_
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Neither I nor II follows ✅
- **D.** Only I follows  _(error: conclusion I does not follow definitely)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some singers are not roses. Some bricks are not bottles. No bottle is a mango. All bricks are singers.
2. Conclusion I: No mango is a rose. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: No bottle is a brick. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Verified by enumerating all 117914 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-308 · L3 · hard · Three or more statement syllogism · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some pilots are stones.
No apple is a stone.
All pilots are birds.
No apple is a phone.

Conclusions:
I. Some birds are stones.
II. Some phones are apples.

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Only II follows  _(error: conclusion II does not follow definitely)_
- **C.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **D.** Only I follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some pilots are stones. No apple is a stone. All pilots are birds. No apple is a phone.
2. Conclusion I: Some birds are stones. → true in every valid diagram → follows.
3. Conclusion II: Some phones are apples. → false in every valid diagram → does not follow.
4. Verified by enumerating all 10640 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-309 · L3 · hard · Three or more statement syllogism · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some tigers are kites.
No wall is a kite.
All stones are walls.
All stones are doctors.

Conclusions:
I. Some tigers are stones.
II. No stone is a kite.
III. Some kites are not walls.

- **A.** Only II follows  _(error: misjudged conclusion(s) III)_
- **B.** Either II or III follows  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** Only II and III follow ✅
- **D.** Only III follows  _(error: misjudged conclusion(s) II)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some tigers are kites. No wall is a kite. All stones are walls. All stones are doctors.
2. Conclusion I: Some tigers are stones. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: No stone is a kite. → true in every valid diagram → follows.
4. Conclusion III: Some kites are not walls. → true in every valid diagram → follows.
5. Verified by enumerating all 4608 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-310 · L3 · hard · Three or more statement syllogism · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
All files are bricks.
Some dancers are mangoes.
No brick is a cup.
No cup is a dancer.

Conclusions:
I. Some dancers are not bricks.
II. All dancers are bricks.
III. Some files are mangoes.

- **A.** Only III and either I or II follow  _(error: misjudged the third conclusion)_
- **B.** Either I or II follows ✅
- **C.** Only I follows  _(error: misjudged conclusion(s) I, II)_
- **D.** Only I and either II or III follow  _(error: paired conclusions that are not a valid either-or pair)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: All files are bricks. Some dancers are mangoes. No brick is a cup. No cup is a dancer.
2. Conclusion I: Some dancers are not bricks. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All dancers are bricks. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some files are mangoes. → possible but not certain (a diagram exists where it fails) → does not follow.
5. I and II form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or II follows.
6. Verified by enumerating all 5088 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-311 · L3 · hard · Three or more statement syllogism · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some stars are not rings.
No star is a mango.
Some mangoes are not pilots.

Conclusions:
I. Some pilots are not rings.
II. Some stars are rings.
III. All pilots are rings.

- **A.** Only I follows  _(error: misjudged conclusion(s) I, III)_
- **B.** Only I and either II or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** Either I or II follows  _(error: paired conclusions that are not a valid either-or pair)_
- **D.** Either I or III follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some stars are not rings. No star is a mango. Some mangoes are not pilots.
2. Conclusion I: Some pilots are not rings. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: Some stars are rings. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: All pilots are rings. → possible but not certain (a diagram exists where it fails) → does not follow.
5. I and III form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or III follows.
6. Verified by enumerating all 1129 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-312 · L3 · hard · Three or more statement syllogism · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
All lakes are teachers.
Some cups are not teachers.
Some lakes are singers.

Conclusions:
I. Some teachers are lakes.
II. Some cups are teachers.
III. Some singers are lakes.

- **A.** Only I and III follow ✅
- **B.** Only III and either I or II follow  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** Only III follows  _(error: misjudged conclusion(s) I)_
- **D.** None follows  _(error: misjudged conclusion(s) I, III)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: All lakes are teachers. Some cups are not teachers. Some lakes are singers.
2. Conclusion I: Some teachers are lakes. → true in every valid diagram → follows.
3. Conclusion II: Some cups are teachers. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some singers are lakes. → true in every valid diagram → follows.
5. Verified by enumerating all 1152 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-313 · L3 · hard · Three or more statement syllogism · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
All shirts are stars.
Some tigers are not folders.
All stars are tigers.

Conclusions:
I. All tigers are folders.
II. Some folders are stars.
III. Some shirts are folders.

- **A.** Either I or III follows  _(error: paired conclusions that are not a valid either-or pair)_
- **B.** Only III follows  _(error: misjudged conclusion(s) III)_
- **C.** Only I and II follow  _(error: misjudged conclusion(s) I, II)_
- **D.** None follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: All shirts are stars. Some tigers are not folders. All stars are tigers.
2. Conclusion I: All tigers are folders. → false in every valid diagram → does not follow.
3. Conclusion II: Some folders are stars. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some shirts are folders. → possible but not certain (a diagram exists where it fails) → does not follow.
5. Verified by enumerating all 84 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-314 · L3 · hard · Three or more statement syllogism · officer

Statements:
Some kites are not teachers.
Some kites are jackets.
Some teachers are clouds.

Taking the statements to be true, which of the following conclusions logically follows?

- **A.** Some clouds are jackets.  _(error: possible but not certain)_
- **B.** No kite is a cloud.  _(error: possible but not certain)_
- **C.** Some jackets are kites. ✅
- **D.** Some kites are clouds.  _(error: possible but not certain)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some kites are not teachers. Some kites are jackets. Some teachers are clouds.
2. 'Some jackets are kites.' holds in every valid diagram.
3. Each other option fails in at least one valid diagram (or is ruled out altogether).
4. Verified by enumerating all 27456 admissible Venn-region models in the builder.

**Formula:** A definite conclusion must hold in every admissible diagram  
**Trap:** Converting 'All A are B' gives only 'Some B are A', never 'All B are A'.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-315 · L3 · hard · Three or more statement syllogism · officer

Statements:
No river is a wall.
Some doors are not rivers.
All singers are doors.
Some teachers are not singers.

Taking the statements to be true, which of the following conclusions logically follows?

- **A.** Some teachers are not rivers.  _(error: possible but not certain)_
- **B.** Some walls are not rivers. ✅
- **C.** All rivers are singers.  _(error: possible but not certain)_
- **D.** Some rivers are not singers.  _(error: possible but not certain)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: No river is a wall. Some doors are not rivers. All singers are doors. Some teachers are not singers.
2. 'Some walls are not rivers.' holds in every valid diagram.
3. Each other option fails in at least one valid diagram (or is ruled out altogether).
4. Verified by enumerating all 123150 admissible Venn-region models in the builder.

**Formula:** A definite conclusion must hold in every admissible diagram  
**Trap:** Converting 'All A are B' gives only 'Some B are A', never 'All B are A'.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-316 · L2 · medium · Only and only-a-few statements · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some cups are roses.
Only a few roses are phones.

Conclusions:
I. Some roses are not phones.
II. All phones are roses.

- **A.** Only II follows  _(error: conclusion II does not follow definitely)_
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **D.** Only I follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some cups are roses. Only a few roses are phones.
2. Conclusion I: Some roses are not phones. → true in every valid diagram → follows.
3. Conclusion II: All phones are roses. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Verified by enumerating all 64 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-317 · L2 · medium · Only and only-a-few statements · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some doors are apples.
Only a few files are apples.

Conclusions:
I. Some apples are not doors.
II. All doors are files.

- **A.** Neither I nor II follows ✅
- **B.** Only I follows  _(error: conclusion I does not follow definitely)_
- **C.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **D.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some doors are apples. Only a few files are apples.
2. Conclusion I: Some apples are not doors. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All doors are files. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Verified by enumerating all 60 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-318 · L2 · medium · Only and only-a-few statements · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Only a few tables are shirts.
No jar is a table.

Conclusions:
I. Some shirts are not jars.
II. Some tables are not shirts.

- **A.** Only I follows  _(error: conclusion II also follows)_
- **B.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **C.** Both I and II follow ✅
- **D.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Only a few tables are shirts. No jar is a table.
2. Conclusion I: Some shirts are not jars. → true in every valid diagram → follows.
3. Conclusion II: Some tables are not shirts. → true in every valid diagram → follows.
4. Verified by enumerating all 6 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-319 · L2 · medium · Only and only-a-few statements · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Only a few roses are clouds.
No cloud is a lily.

Conclusions:
I. Some lilies are not roses.
II. Some clouds are not lilies.

- **A.** Only II follows ✅
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **D.** Only I follows  _(error: conclusion I does not follow definitely)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Only a few roses are clouds. No cloud is a lily.
2. Conclusion I: Some lilies are not roses. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: Some clouds are not lilies. → true in every valid diagram → follows.
4. Verified by enumerating all 10 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-320 · L2 · medium · Only and only-a-few statements · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some plates are jackets.
Only a few rings are jackets.

Conclusions:
I. All rings are plates.
II. Some rings are not plates.

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Only II follows  _(error: conclusion II does not follow definitely)_
- **C.** Either I or II follows ✅
- **D.** Neither I nor II follows  _(error: missed the either-or pair)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some plates are jackets. Only a few rings are jackets.
2. Conclusion I: All rings are plates. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: Some rings are not plates. → possible but not certain (a diagram exists where it fails) → does not follow.
4. I and II form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or II follows.
5. Verified by enumerating all 60 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-321 · L3 · hard · Only and only-a-few statements · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Only shirts are chairs.
No folder is a shirt.

Conclusions:
I. Some chairs are folders.
II. No shirt is a folder.

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Only II follows ✅
- **C.** Only I follows  _(error: conclusion I does not follow definitely)_
- **D.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Only shirts are chairs. No folder is a shirt.
2. Conclusion I: Some chairs are folders. → false in every valid diagram → does not follow.
3. Conclusion II: No shirt is a folder. → true in every valid diagram → follows.
4. Verified by enumerating all 2 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-322 · L3 · hard · Only and only-a-few statements · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Only a few pens are shirts.
All shirts are birds.
Some pens are dancers.

Conclusions:
I. Some shirts are birds.
II. Some birds are pens.

- **A.** Only I follows  _(error: conclusion II also follows)_
- **B.** Both I and II follow ✅
- **C.** Only II follows  _(error: conclusion I also follows)_
- **D.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Only a few pens are shirts. All shirts are birds. Some pens are dancers.
2. Conclusion I: Some shirts are birds. → true in every valid diagram → follows.
3. Conclusion II: Some birds are pens. → true in every valid diagram → follows.
4. Verified by enumerating all 1344 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-323 · L3 · hard · Only and only-a-few statements · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
All lakes are pilots.
Only pilots are tables.

Conclusions:
I. No pilot is a lake.
II. Some tables are not pilots.

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Only II follows  _(error: conclusion II does not follow definitely)_
- **C.** Neither I nor II follows ✅
- **D.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: All lakes are pilots. Only pilots are tables.
2. Conclusion I: No pilot is a lake. → false in every valid diagram → does not follow.
3. Conclusion II: Some tables are not pilots. → false in every valid diagram → does not follow.
4. Verified by enumerating all 10 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-324 · L3 · hard · Only and only-a-few statements · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Only a few mangoes are rings.
Only a few lions are pens.
All rings are pens.

Conclusions:
I. Some lions are pens.
II. Only a few lions are mangoes.

- **A.** Only II follows  _(error: conclusion II does not follow definitely)_
- **B.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **C.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **D.** Only I follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Only a few mangoes are rings. Only a few lions are pens. All rings are pens.
2. Conclusion I: Some lions are pens. → true in every valid diagram → follows.
3. Conclusion II: Only a few lions are mangoes. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Verified by enumerating all 1060 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-325 · L3 · hard · Only and only-a-few statements · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Only a few phones are folders.
Only phones are trains.
No train is a bus.

Conclusions:
I. Some folders are not buses.
II. No train is a folder.
III. Some buses are not trains.

- **A.** Only III follows ✅
- **B.** Only I and III follow  _(error: misjudged conclusion(s) I)_
- **C.** Only II and either I or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **D.** None follows  _(error: misjudged conclusion(s) III)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Only a few phones are folders. Only phones are trains. No train is a bus.
2. Conclusion I: Some folders are not buses. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: No train is a folder. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some buses are not trains. → true in every valid diagram → follows.
5. Verified by enumerating all 304 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-326 · L3 · hard · Only and only-a-few statements · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Only a few pilots are buses.
Only tigers are cups.
No pilot is a tiger.

Conclusions:
I. Only buses are cups.
II. All cups are tigers.
III. Some pilots are not cups.

- **A.** Only I and either II or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **B.** Only II and III follow ✅
- **C.** Only III and either I or II follow  _(error: paired conclusions that are not a valid either-or pair)_
- **D.** Either II or III follows  _(error: paired conclusions that are not a valid either-or pair)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Only a few pilots are buses. Only tigers are cups. No pilot is a tiger.
2. Conclusion I: Only buses are cups. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All cups are tigers. → true in every valid diagram → follows.
4. Conclusion III: Some pilots are not cups. → true in every valid diagram → follows.
5. Verified by enumerating all 24 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-327 · L3 · hard · Only and only-a-few statements · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some rivers are trains.
No star is a train.
Only stars are teachers.

Conclusions:
I. No teacher is a train.
II. All rivers are trains.
III. Some rivers are not trains.

- **A.** Either I or II follows  _(error: paired conclusions that are not a valid either-or pair)_
- **B.** Only I and either II or III follow ✅
- **C.** Only II and either I or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **D.** Only III and either I or II follow  _(error: paired conclusions that are not a valid either-or pair)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some rivers are trains. No star is a train. Only stars are teachers.
2. Conclusion I: No teacher is a train. → true in every valid diagram → follows.
3. Conclusion II: All rivers are trains. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some rivers are not trains. → possible but not certain (a diagram exists where it fails) → does not follow.
5. II and III form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either II or III follows.
6. Verified by enumerating all 48 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-328 · L3 · hard · Only and only-a-few statements · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
All mangoes are stars.
Only stars are files.
All doctors are files.

Conclusions:
I. No mango is a star.
II. Only files are mangoes.
III. Only mangoes are files.

- **A.** Either I or II follows  _(error: paired conclusions that are not a valid either-or pair)_
- **B.** Only I and either II or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** Only II follows  _(error: misjudged conclusion(s) II)_
- **D.** None follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: All mangoes are stars. Only stars are files. All doctors are files.
2. Conclusion I: No mango is a star. → false in every valid diagram → does not follow.
3. Conclusion II: Only files are mangoes. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Only mangoes are files. → possible but not certain (a diagram exists where it fails) → does not follow.
5. Verified by enumerating all 44 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-329 · L3 · hard · Only and only-a-few statements · officer

Statements:
Only tigers are engineers.
Only a few tigers are doctors.
Only engineers are tables.

Taking the statements to be true, which of the following conclusions logically follows?

- **A.** Some doctors are tables.  _(error: possible but not certain)_
- **B.** No doctor is an engineer.  _(error: possible but not certain)_
- **C.** Some tables are engineers. ✅
- **D.** All tigers are doctors.  _(error: ruled out by the statements)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Only tigers are engineers. Only a few tigers are doctors. Only engineers are tables.
2. 'Some tables are engineers.' holds in every valid diagram.
3. Each other option fails in at least one valid diagram (or is ruled out altogether).
4. Verified by enumerating all 80 admissible Venn-region models in the builder.

**Formula:** A definite conclusion must hold in every admissible diagram  
**Trap:** Converting 'All A are B' gives only 'Some B are A', never 'All B are A'.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-330 · L3 · hard · Only and only-a-few statements · officer

Statements:
All clouds are jackets.
Only a few dancers are clouds.
Only plates are dancers.

Taking the statements to be true, which of the following conclusions logically follows?

- **A.** No cloud is a jacket.  _(error: ruled out by the statements)_
- **B.** Only a few plates are dancers.  _(error: possible but not certain)_
- **C.** No plate is a dancer.  _(error: ruled out by the statements)_
- **D.** Some plates are jackets. ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: All clouds are jackets. Only a few dancers are clouds. Only plates are dancers.
2. 'Some plates are jackets.' holds in every valid diagram.
3. Each other option fails in at least one valid diagram (or is ruled out altogether).
4. Verified by enumerating all 96 admissible Venn-region models in the builder.

**Formula:** A definite conclusion must hold in every admissible diagram  
**Trap:** Converting 'All A are B' gives only 'Some B are A', never 'All B are A'.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-331 · L2 · medium · Possibility conclusions · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some chairs are lakes.
All cups are lakes.

Conclusions:
I. Some cups not being chairs is a possibility.
II. Some cups are chairs.

- **A.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Only II follows  _(error: conclusion II does not follow definitely)_
- **D.** Only I follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some chairs are lakes. All cups are lakes.
2. Conclusion I: Some cups not being chairs is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
3. Conclusion II: Some cups are chairs. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Verified by enumerating all 20 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-332 · L2 · medium · Possibility conclusions · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some roses are clouds.
All phones are roses.

Conclusions:
I. All roses being clouds is a possibility.
II. Some phones are roses.

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Only II follows  _(error: conclusion I also follows)_
- **C.** Both I and II follow ✅
- **D.** Only I follows  _(error: conclusion II also follows)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some roses are clouds. All phones are roses.
2. Conclusion I: All roses being clouds is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
3. Conclusion II: Some phones are roses. → true in every valid diagram → follows.
4. Verified by enumerating all 20 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-333 · L2 · medium · Possibility conclusions · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some lakes are not books.
Some books are pens.

Conclusions:
I. No book is a pen.
II. Some books are not pens.

- **A.** Only I follows  _(error: conclusion I does not follow definitely)_
- **B.** Only II follows  _(error: conclusion II does not follow definitely)_
- **C.** Neither I nor II follows ✅
- **D.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some lakes are not books. Some books are pens.
2. Conclusion I: No book is a pen. → false in every valid diagram → does not follow.
3. Conclusion II: Some books are not pens. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Verified by enumerating all 72 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-334 · L2 · medium · Possibility conclusions · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some doctors are dancers.
All birds are dancers.

Conclusions:
I. No dancer being a doctor is a possibility.
II. All dancers being birds is a possibility.

- **A.** Only I follows  _(error: conclusion I does not follow definitely)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **D.** Only II follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some doctors are dancers. All birds are dancers.
2. Conclusion I: No dancer being a doctor is a possibility. → contradicted by the statements in every valid diagram → does not follow.
3. Conclusion II: All dancers being birds is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
4. Verified by enumerating all 20 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-335 · L2 · medium · Possibility conclusions · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some rivers are birds.
Some rivers are not bottles.

Conclusions:
I. All bottles being birds is a possibility.
II. Some bottles not being rivers is a possibility.

- **A.** Both I and II follow ✅
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **D.** Only II follows  _(error: conclusion I also follows)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some rivers are birds. Some rivers are not bottles.
2. Conclusion I: All bottles being birds is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
3. Conclusion II: Some bottles not being rivers is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
4. Verified by enumerating all 76 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-336 · L3 · hard · Possibility conclusions · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some jars are not teachers.
Some clouds are lions.
Only a few lions are teachers.

Conclusions:
I. No jar is a lion.
II. All clouds being lions is a possibility.

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Only II follows ✅
- **D.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some jars are not teachers. Some clouds are lions. Only a few lions are teachers.
2. Conclusion I: No jar is a lion. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All clouds being lions is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
4. Verified by enumerating all 26304 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-337 · L3 · hard · Possibility conclusions · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Only a few roses are coins.
Only a few rings are coins.
All folders are roses.

Conclusions:
I. All rings are roses.
II. No folder is a rose.

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Neither I nor II follows ✅
- **D.** Only II follows  _(error: conclusion II does not follow definitely)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Only a few roses are coins. Only a few rings are coins. All folders are roses.
2. Conclusion I: All rings are roses. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: No folder is a rose. → false in every valid diagram → does not follow.
4. Verified by enumerating all 1408 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-338 · L3 · hard · Possibility conclusions · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
All bricks are stars.
Some bottles are not bricks.
Some stars are tables.

Conclusions:
I. Some tables not being stars is a possibility.
II. All bottles being stars is a possibility.

- **A.** Both I and II follow ✅
- **B.** Only II follows  _(error: conclusion I also follows)_
- **C.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **D.** Only I follows  _(error: conclusion II also follows)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: All bricks are stars. Some bottles are not bricks. Some stars are tables.
2. Conclusion I: Some tables not being stars is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
3. Conclusion II: All bottles being stars is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
4. Verified by enumerating all 1716 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-339 · L3 · hard · Possibility conclusions · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No shirt is a dancer.
Some plates are not shirts.
Some laptops are not dancers.

Conclusions:
I. Some plates not being dancers is a possibility.
II. Some dancers are plates.

- **A.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Only II follows  _(error: conclusion II does not follow definitely)_
- **D.** Only I follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: No shirt is a dancer. Some plates are not shirts. Some laptops are not dancers.
2. Conclusion I: Some plates not being dancers is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
3. Conclusion II: Some dancers are plates. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Verified by enumerating all 1629 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-340 · L3 · hard · Possibility conclusions · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Only stars are birds.
No cloud is a bird.
Only stars are rivers.

Conclusions:
I. Some birds are not stars.
II. No cloud being a star is a possibility.
III. No star being a cloud is a possibility.

- **A.** Only II and either I or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **B.** None follows  _(error: misjudged conclusion(s) II, III)_
- **C.** Only II follows  _(error: misjudged conclusion(s) III)_
- **D.** Only II and III follow ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Only stars are birds. No cloud is a bird. Only stars are rivers.
2. Conclusion I: Some birds are not stars. → false in every valid diagram → does not follow.
3. Conclusion II: No cloud being a star is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
4. Conclusion III: No star being a cloud is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
5. Verified by enumerating all 78 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-341 · L3 · hard · Possibility conclusions · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some bricks are not jackets.
Some doors are not lakes.
No lake is a brick.

Conclusions:
I. Some lakes being bricks is a possibility.
II. All bricks are lakes.
III. Some doors being lakes is a possibility.

- **A.** Only III follows ✅
- **B.** Only II and III follow  _(error: misjudged conclusion(s) II)_
- **C.** Only II and either I or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **D.** Only III and either I or II follow  _(error: paired conclusions that are not a valid either-or pair)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some bricks are not jackets. Some doors are not lakes. No lake is a brick.
2. Conclusion I: Some lakes being bricks is a possibility. → contradicted by the statements in every valid diagram → does not follow.
3. Conclusion II: All bricks are lakes. → false in every valid diagram → does not follow.
4. Conclusion III: Some doors being lakes is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
5. Verified by enumerating all 1365 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-342 · L3 · hard · Possibility conclusions · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No chair is a laptop.
Only folders are chairs.
All dancers are folders.

Conclusions:
I. Some dancers being laptops is a possibility.
II. Some folders are not laptops.
III. All laptops being folders is a possibility.

- **A.** All I, II and III follow ✅
- **B.** Only III and either I or II follow  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** Only II follows  _(error: misjudged conclusion(s) I, III)_
- **D.** Only I and either II or III follow  _(error: paired conclusions that are not a valid either-or pair)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: No chair is a laptop. Only folders are chairs. All dancers are folders.
2. Conclusion I: Some dancers being laptops is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
3. Conclusion II: Some folders are not laptops. → true in every valid diagram → follows.
4. Conclusion III: All laptops being folders is a possibility. → possible in at least one valid diagram and not contradicted by any statement → follows.
5. Verified by enumerating all 78 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-343 · L3 · hard · Possibility conclusions · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No jacket is a ring.
All clouds are tables.
No ring is a cloud.

Conclusions:
I. Some jackets are clouds.
II. Some rings being clouds is a possibility.
III. No table being a cloud is a possibility.

- **A.** Only II and III follow  _(error: misjudged conclusion(s) II, III)_
- **B.** Either II or III follows  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** None follows ✅
- **D.** Only I follows  _(error: misjudged conclusion(s) I)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: No jacket is a ring. All clouds are tables. No ring is a cloud.
2. Conclusion I: Some jackets are clouds. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: Some rings being clouds is a possibility. → contradicted by the statements in every valid diagram → does not follow.
4. Conclusion III: No table being a cloud is a possibility. → contradicted by the statements in every valid diagram → does not follow.
5. Verified by enumerating all 66 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-344 · L3 · hard · Possibility conclusions · officer

Statements:
No doctor is a cloud.
All doctors are apples.
No apple is a book.

Taking the statements to be true, which of the following conclusions logically follows?

- **A.** No cloud being a book is a possibility. ✅
- **B.** Some clouds being doctors is a possibility.  _(error: ruled out by the statements)_
- **C.** No apple is a cloud.  _(error: possible but not certain)_
- **D.** No cloud is an apple.  _(error: possible but not certain)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: No doctor is a cloud. All doctors are apples. No apple is a book.
2. 'No cloud being a book is a possibility.' holds in at least one valid diagram and is not ruled out.
3. Each other option fails in at least one valid diagram (or is ruled out altogether).
4. Verified by enumerating all 22 admissible Venn-region models in the builder.

**Formula:** A definite conclusion must hold in every admissible diagram  
**Trap:** Converting 'All A are B' gives only 'Some B are A', never 'All B are A'.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-345 · L3 · hard · Possibility conclusions · officer

Statements:
Some tigers are not phones.
No phone is a pilot.
No tiger is a dancer.

Taking the statements to be true, which of the following conclusions logically follows?

- **A.** All phones being pilots is a possibility.  _(error: ruled out by the statements)_
- **B.** No pilot being a tiger is a possibility. ✅
- **C.** Some tigers are not pilots.  _(error: possible but not certain)_
- **D.** All phones are dancers.  _(error: possible but not certain)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some tigers are not phones. No phone is a pilot. No tiger is a dancer.
2. 'No pilot being a tiger is a possibility.' holds in at least one valid diagram and is not ruled out.
3. Each other option fails in at least one valid diagram (or is ruled out altogether).
4. Verified by enumerating all 139 admissible Venn-region models in the builder.

**Formula:** A definite conclusion must hold in every admissible diagram  
**Trap:** Converting 'All A are B' gives only 'Some B are A', never 'All B are A'.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-346 · L2 · medium · Either-or and complementary pairs · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
All lilies are pilots.
Some buses are lilies.

Conclusions:
I. Some pilots are not lilies.
II. All pilots are lilies.

- **A.** Either I or II follows ✅
- **B.** Only II follows  _(error: conclusion II does not follow definitely)_
- **C.** Only I follows  _(error: conclusion I does not follow definitely)_
- **D.** Neither I nor II follows  _(error: missed the either-or pair)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: All lilies are pilots. Some buses are lilies.
2. Conclusion I: Some pilots are not lilies. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All pilots are lilies. → possible but not certain (a diagram exists where it fails) → does not follow.
4. I and II form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or II follows.
5. Verified by enumerating all 16 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-347 · L2 · medium · Either-or and complementary pairs · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No dancer is a ring.
Some rings are not teachers.

Conclusions:
I. Some teachers are not dancers.
II. All teachers are dancers.

- **A.** Only I follows  _(error: conclusion I does not follow definitely)_
- **B.** Neither I nor II follows  _(error: missed the either-or pair)_
- **C.** Either I or II follows ✅
- **D.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: No dancer is a ring. Some rings are not teachers.
2. Conclusion I: Some teachers are not dancers. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All teachers are dancers. → possible but not certain (a diagram exists where it fails) → does not follow.
4. I and II form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or II follows.
5. Verified by enumerating all 11 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-348 · L2 · medium · Either-or and complementary pairs · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No coin is a star.
All coins are jackets.

Conclusions:
I. No star is a coin.
II. Some stars are coins.

- **A.** Only II follows  _(error: conclusion II does not follow definitely)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **D.** Only I follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: No coin is a star. All coins are jackets.
2. Conclusion I: No star is a coin. → true in every valid diagram → follows.
3. Conclusion II: Some stars are coins. → false in every valid diagram → does not follow.
4. Verified by enumerating all 6 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-349 · L2 · medium · Either-or and complementary pairs · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No file is a rose.
No mango is a file.

Conclusions:
I. Some mangoes are roses.
II. No mango is a rose.

- **A.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **B.** Either I or II follows ✅
- **C.** Neither I nor II follows  _(error: missed the either-or pair)_
- **D.** Only II follows  _(error: conclusion II does not follow definitely)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: No file is a rose. No mango is a file.
2. Conclusion I: Some mangoes are roses. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: No mango is a rose. → possible but not certain (a diagram exists where it fails) → does not follow.
4. I and II form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or II follows.
5. Verified by enumerating all 5 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-350 · L2 · medium · Either-or and complementary pairs · foundation

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No bus is a table.
All buses are pilots.

Conclusions:
I. All buses are tables.
II. Some buses are pilots.

- **A.** Only I follows  _(error: conclusion I does not follow definitely)_
- **B.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **C.** Only II follows ✅
- **D.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: No bus is a table. All buses are pilots.
2. Conclusion I: All buses are tables. → false in every valid diagram → does not follow.
3. Conclusion II: Some buses are pilots. → true in every valid diagram → follows.
4. Verified by enumerating all 6 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-351 · L3 · hard · Either-or and complementary pairs · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some lilies are books.
Some bricks are not books.

Conclusions:
I. Some books are bricks.
II. No book is a brick.
III. All lilies are bricks.

- **A.** Only III and either I or II follow  _(error: misjudged the third conclusion)_
- **B.** Only I and III follow  _(error: misjudged conclusion(s) I, II, III)_
- **C.** Only II follows  _(error: misjudged conclusion(s) I, II)_
- **D.** Either I or II follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some lilies are books. Some bricks are not books.
2. Conclusion I: Some books are bricks. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: No book is a brick. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: All lilies are bricks. → possible but not certain (a diagram exists where it fails) → does not follow.
5. I and II form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or II follows.
6. Verified by enumerating all 72 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-352 · L3 · hard · Either-or and complementary pairs · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some chairs are pens.
Some chairs are shirts.
Some pens are phones.

Conclusions:
I. All shirts are pens.
II. All phones are shirts.
III. Some phones are not shirts.

- **A.** Only II follows  _(error: misjudged conclusion(s) II, III)_
- **B.** Only I and III follow  _(error: misjudged conclusion(s) I, II, III)_
- **C.** Either II or III follows ✅
- **D.** Only I and II follow  _(error: misjudged conclusion(s) I, II, III)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some chairs are pens. Some chairs are shirts. Some pens are phones.
2. Conclusion I: All shirts are pens. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All phones are shirts. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some phones are not shirts. → possible but not certain (a diagram exists where it fails) → does not follow.
5. II and III form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either II or III follows.
6. Verified by enumerating all 27776 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-353 · L3 · hard · Either-or and complementary pairs · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No jacket is a kite.
Some tigers are kites.

Conclusions:
I. Some tigers are not kites.
II. All tigers are kites.
III. Some kites are not tigers.

- **A.** Only I and III follow  _(error: misjudged conclusion(s) I, II, III)_
- **B.** None follows  _(error: misjudged conclusion(s) I, II)_
- **C.** Only II and III follow  _(error: misjudged conclusion(s) I, II, III)_
- **D.** Either I or II follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: No jacket is a kite. Some tigers are kites.
2. Conclusion I: Some tigers are not kites. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All tigers are kites. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some kites are not tigers. → possible but not certain (a diagram exists where it fails) → does not follow.
5. I and II form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or II follows.
6. Verified by enumerating all 12 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-354 · L3 · hard · Either-or and complementary pairs · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some bricks are roses.
Only a few tables are bricks.
All files are tables.

Conclusions:
I. Some bricks are tables.
II. Some files are roses.
III. No file is a rose.

- **A.** Either I or II follows  _(error: paired conclusions that are not a valid either-or pair)_
- **B.** Only III and either I or II follow  _(error: paired conclusions that are not a valid either-or pair)_
- **C.** Only I and III follow  _(error: misjudged conclusion(s) II, III)_
- **D.** Only I and either II or III follow ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some bricks are roses. Only a few tables are bricks. All files are tables.
2. Conclusion I: Some bricks are tables. → true in every valid diagram → follows.
3. Conclusion II: Some files are roses. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: No file is a rose. → possible but not certain (a diagram exists where it fails) → does not follow.
5. II and III form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either II or III follows.
6. Verified by enumerating all 1560 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-355 · L3 · hard · Either-or and complementary pairs · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some plates are not rings.
All rings are folders.

Conclusions:
I. All folders are rings.
II. All folders are plates.
III. Some folders are not rings.

- **A.** All I, II and III follow  _(error: misjudged conclusion(s) I, II, III)_
- **B.** Either I or III follows ✅
- **C.** Only I and either II or III follow  _(error: paired conclusions that are not a valid either-or pair)_
- **D.** Either II or III follows  _(error: paired conclusions that are not a valid either-or pair)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some plates are not rings. All rings are folders.
2. Conclusion I: All folders are rings. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: All folders are plates. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some folders are not rings. → possible but not certain (a diagram exists where it fails) → does not follow.
5. I and III form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or III follows.
6. Verified by enumerating all 18 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-356 · L3 · hard · Either-or and complementary pairs · officer

In the question below, some statements are followed by three conclusions. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some lakes are not trains.
Some bricks are trains.
Only a few lakes are chairs.

Conclusions:
I. All bricks are trains.
II. No train is a chair.
III. Some bricks are not trains.

- **A.** Only I and II follow  _(error: misjudged conclusion(s) I, II, III)_
- **B.** Only II and III follow  _(error: misjudged conclusion(s) I, II, III)_
- **C.** Either I or III follows ✅
- **D.** Only II and either I or III follow  _(error: misjudged the third conclusion)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some lakes are not trains. Some bricks are trains. Only a few lakes are chairs.
2. Conclusion I: All bricks are trains. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: No train is a chair. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Conclusion III: Some bricks are not trains. → possible but not certain (a diagram exists where it fails) → does not follow.
5. I and III form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or III follows.
6. Verified by enumerating all 26112 admissible Venn-region models in the builder.

**Formula:** Definite: true in every valid diagram; possibility: true in at least one; either-or: complementary pair on same terms, neither definite  
**Trap:** Check each conclusion separately before looking for a complementary pair.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-357 · L3 · hard · Either-or and complementary pairs · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some jars are not jackets.
All jackets are trains.
No jar is a shirt.

Conclusions:
I. No jacket is a jar.
II. No jacket is a train.

- **A.** Neither I nor II follows ✅
- **B.** Only II follows  _(error: conclusion II does not follow definitely)_
- **C.** Only I follows  _(error: conclusion I does not follow definitely)_
- **D.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some jars are not jackets. All jackets are trains. No jar is a shirt.
2. Conclusion I: No jacket is a jar. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: No jacket is a train. → false in every valid diagram → does not follow.
4. Verified by enumerating all 150 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-358 · L3 · hard · Either-or and complementary pairs · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some mangoes are singers.
Some bricks are folders.
Some bricks are singers.

Conclusions:
I. All bricks are folders.
II. Some bricks are not folders.

- **A.** Neither I nor II follows  _(error: missed the either-or pair)_
- **B.** Either I or II follows ✅
- **C.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **D.** Only II follows  _(error: conclusion II does not follow definitely)_

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some mangoes are singers. Some bricks are folders. Some bricks are singers.
2. Conclusion I: All bricks are folders. → possible but not certain (a diagram exists where it fails) → does not follow.
3. Conclusion II: Some bricks are not folders. → possible but not certain (a diagram exists where it fails) → does not follow.
4. I and II form a complementary pair on the same two terms; neither is definite, and exactly one must be true → either I or II follows.
5. Verified by enumerating all 27776 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-359 · L3 · hard · Either-or and complementary pairs · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
Some apples are folders.
Some kites are pilots.
No kite is an apple.

Conclusions:
I. Some kites are not apples.
II. Some pilots are not apples.

- **A.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **B.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **C.** Only I follows  _(error: conclusion II also follows)_
- **D.** Both I and II follow ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: Some apples are folders. Some kites are pilots. No kite is an apple.
2. Conclusion I: Some kites are not apples. → true in every valid diagram → follows.
3. Conclusion II: Some pilots are not apples. → true in every valid diagram → follows.
4. Verified by enumerating all 1152 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:


---

## GRA-360 · L3 · hard · Either-or and complementary pairs · officer

In the question below, some statements are followed by two conclusions I and II. Take the statements to be true even if they seem to be at variance with commonly known facts, and decide which of the conclusions logically follow.

Statements:
No stone is a lily.
Some stones are not stars.
No doctor is a star.

Conclusions:
I. Some stones are not lilies.
II. Some lilies are doctors.

- **A.** Neither I nor II follows  _(error: overlooked a conclusion that does follow)_
- **B.** Either I or II follows  _(error: missed that the pair is not complementary / one of them is definite)_
- **C.** Both I and II follow  _(error: treated an uncertain conclusion as definite)_
- **D.** Only I follows ✅

**Working**

1. Draw the least-overlap (Venn) case for the statements: No stone is a lily. Some stones are not stars. No doctor is a star.
2. Conclusion I: Some stones are not lilies. → true in every valid diagram → follows.
3. Conclusion II: Some lilies are doctors. → possible but not certain (a diagram exists where it fails) → does not follow.
4. Verified by enumerating all 139 admissible Venn-region models in the builder.

**Formula:** Definite conclusion: true in every valid Venn diagram; possibility: true in at least one; either-or: complementary pair, neither definite  
**Trap:** Test the definite conclusions on the least-overlap diagram; a possibility follows unless a statement rules it out.

**Reviewer:** ☐ key ☐ stem ☐ distractors ☐ level ☐ fact — notes:
