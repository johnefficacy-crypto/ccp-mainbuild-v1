"""QRE-QA-A part 3: Ratio and Proportion (ages, averages, median/mode, mixtures, partnership,
proportional division, simple/compound ratio). Case-set items live in qa_a_cases."""
from fractions import Fraction as Fr
from itertools import product
from qa_a_common import N, D, P, Rs, ratio, make_q


def add_all(B):
    q = make_q(B)

    # ===================== Ages =====================
    x = next(x for x in range(1, 50) if Fr(4 * x + 5, 5 * x + 5) == Fr(5, 6))
    q("ages", "L1", "f", "The present ages of two cousins are in the ratio 4 : 5. After 5 years the ratio will be 5 : 6. The elder cousin's present age is:",
      f"{5 * x} years",
      [(f"{4 * x} years", "younger cousin's age"), (f"{5 * x + 5} years", "age after 5 years"), (f"{6 * x + 5} years", "future ratio term used as present multiple")],
      ["(4x + 5)/(5x + 5) = 5/6", "24x + 30 = 25x + 25 ⇒ x = 5", "Elder = 25 years"],
      "Add the same years to both ages", "Years are added to ages, not to ratio terms.")

    s = next(s for s in range(1, 60) if 3 * s + 10 == 2 * (s + 10))
    q("ages", "L1", "f", "A father is three times as old as his son. After 10 years he will be twice as old as the son. The son's present age is:",
      f"{s} years", [(f"{3 * s} years", "father's age reported"), (f"{2 * s} years", "son's age after 10 years"), ("15 years", "10 added to one side only")],
      ["3s + 10 = 2(s + 10)", "s = 10"],
      "Future: (F + t) = k(S + t)", "Both ages grow by 10.")

    a, b = 18 + 5, 30 + 5
    q("ages", "L2", "f", "The sum of the present ages of A and B is 58 years. Five years ago their ages were in the ratio 3 : 5. B's present age is:",
      f"{b} years", [(f"{b - 5} years", "age five years ago"), (f"{N(Fr(58 * 5, 8))} years", "ratio applied to present sum"), (f"{a} years", "A's age reported")],
      ["Sum five years ago = 58 − 10 = 48", "B then = 48 × 5/8 = 30", "B now = 35"],
      "Reduce the sum by 5 for each person", "Ratio holds five years ago, not now.")

    Bg = next(b for b in range(1, 60) if (b + 6 - 4) == 2 * (b - 4))
    q("ages", "L2", "f", "A is 6 years older than B. Four years ago A was twice as old as B. B's present age is:",
      f"{Bg} years", [(f"{Bg + 6} years", "A's age reported"), (f"{Bg - 4} years", "B's age four years ago"), ("8 years", "4 subtracted from one side only")],
      ["A − 4 = 2(B − 4), A = B + 6", "B + 2 = 2B − 8 ⇒ B = 10"],
      "Age difference is constant", "Subtract 4 from both ages.")

    x = next(x for x in range(1, 50) if 2 * (3 * x - 10) == 4 * x - 10)
    q("ages", "L2", "f", "Ten years ago, P was half as old as Q. Their present ages are in the ratio 3 : 4. The sum of their present ages is:",
      f"{7 * x} years", [(f"{7 * x - 20} years", "sum ten years ago"), (f"{7 * x + 10} years", "10 added only once"), (f"{7 * 10} years", "multiplier taken as 10")],
      ["2(3x − 10) = 4x − 10 ⇒ x = 5", "Ages 15 and 20; sum 35"],
      "Past ages = present − 10", "Both ages lose 10.")

    x = next(x for x in range(1, 50) if Fr(7 * x - 8, 9 * x - 8) == Fr(5, 7))
    Pn, Qn = 7 * x + 12, 9 * x + 12
    q("ages", "L3", "o", "The present ages of P and Q are in the ratio 7 : 9. Eight years ago the ratio was 5 : 7. What will be the ratio of their ages 12 years from now?",
      ratio(Pn, Qn), [("7:9", "present ratio assumed unchanged"), ("19:21", "12 added to ratio terms"), (ratio(Pn, 9 * x), "12 added to P's age only")],
      ["(7x − 8)/(9x − 8) = 5/7 ⇒ 4x = 16 ⇒ x = 4", "Ages 28 and 36", "In 12 years: 40 : 48 = 5 : 6"],
      "Find actual ages first", "Adding years to ratio terms is wrong.")

    child = 22 * 3 - (50 + 2 * 6)
    q("ages", "L3", "o", "At their wedding, the average age of a husband and wife was 25 years. Six years later, with one child, the family's average age is 22 years. The child's age is:",
      f"{child} years", [("6 years", "years since marriage"), (f"{66 - 50} years", "couple's ageing ignored"), (f"{66 - 56} years", "only one spouse aged 6 years")],
      ["Couple's sum at wedding = 50; after 6 years = 62", "Family sum = 3 × 22 = 66", "Child = 66 − 62 = 4"],
      "Sum = average × count; each person ages", "Both spouses age by 6.")

    D_, M = 13, 37
    t = next(t for t in range(0, 20) if M - t == 4 * (D_ - t))
    assert M + D_ == 50 and 3 * (M + 5) == 7 * (D_ + 5)
    q("ages", "L3", "o", "A mother and daughter have a combined age of 50 years. In 5 years the mother's age will be 7/3 of the daughter's. When was the mother four times as old as the daughter?",
      f"{t} years ago", [(f"{t} years hence", "direction of time reversed"), (f"{N(Fr(4 * D_ - M, 4))} years ago", "t not subtracted from mother's age"),
                         (f"{D_ - t} years ago", "daughter's age then read as time")],
      ["M + D = 50; 3(M + 5) = 7(D + 5) ⇒ D = 13, M = 37", "37 − t = 4(13 − t) ⇒ 3t = 15 ⇒ t = 5"],
      "Subtract t from both ages", "Solve present ages first.")

    k = Fr(105, 35)
    q("ages", "L3", "o", "The ages of A and B are in the ratio 3 : 4, and those of B and C in the ratio 6 : 7. If the three ages total 105 years, C's age is:",
      f"{N(14 * k)} years", [(f"{N(12 * k)} years", "B's age reported"), (f"{N(Fr(105 * 7, 14))} years", "chain not equalised (3 : 4 : 7)"),
                             (f"{N(Fr(105 * 7, 16))} years", "chain written as 3 : 6 : 7")],
      ["A : B : C = 9 : 12 : 14", "C = 105 × 14/35 = 42"],
      "Equalise the common term B", "Make B's terms equal (12) before combining.")

    q("ages", "L3", "o", "The ratio of A's age five years ago to B's age five years hence is 1 : 2, and A's age five years hence equals B's age five years ago. A's present age is:",
      "25 years", [("35 years", "B's age reported"), ("20 years", "A's age five years ago"), ("30 years", "A's age five years hence")],
      ["(A − 5)/(B + 5) = 1/2 and A + 5 = B − 5", "B = A + 10 ⇒ 2A − 10 = A + 15 ⇒ A = 25"],
      "Translate each clause to an equation", "Keep 'ago' and 'hence' on the right person.")
    assert (25 - 5) * 2 == 35 + 5 and 25 + 5 == 35 - 5

    S = next(s for s in range(1, 60) if 3 * s + 4 + 8 == 2 * (s + 8) + 10)
    q("ages", "L3", "o", "A father's age is 4 years more than three times his son's. After 8 years, the father's age will be 10 years more than twice the son's. The father's present age is:",
      f"{3 * S + 4} years", [(f"{S} years", "son's age reported"), (f"{3 * S + 12} years", "father's age after 8 years"), ("16 years", "the extra 10 years left out")],
      ["F = 3S + 4", "3S + 12 = 2S + 26 ⇒ S = 14", "F = 46"],
      "Substitute F in the future equation", "Add 8 to both before comparing.")

    child = Fr(143) - (120 + 4 * 5)
    assert child == 3
    q("ages", "L3", "o", "Five years ago, the average age of a family of four was 30 years. A baby has since been born, and the average age of the five members is now 28.6 years. The baby's age is:",
      f"{N(child)} years", [(f"{143 - 120} years", "ageing of the four ignored"), (f"{143 - 125} years", "ageing counted as 5 years in total"),
                            (f"{143 - 135} years", "ageing counted for three members")],
      ["Sum five years ago = 120; now for the four = 140", "Family sum now = 5 × 28.6 = 143", "Baby = 3 years"],
      "Each of the four adds 5 years", "Four members × 5 years = 20.")

    x = 7
    q("ages", "L3", "o", "The ages of A and B are in the ratio 5 : 3. When A was as old as B is now, the sum of their ages was 28 years. A's present age is:",
      f"{5 * x} years", [(f"{3 * x} years", "B's age reported"), (f"{N(Fr(28 * 5, 8))} years", "28 taken as present sum"), ("28 years", "the sum itself")],
      ["A = 5x, B = 3x; 2x years ago A was 3x, B was x", "3x + x = 28 ⇒ x = 7", "A = 35"],
      "Go back by the age gap", "The gap 2x is the time elapsed.")

    s_, p_ = 32, 240
    roots = sorted(t for t in range(1, 40) if t * (s_ - t) == p_)
    assert (roots[0] - 4) * (roots[1] - 4) == 128
    q("ages", "L3", "o", "The product of the present ages of two brothers is 240. Four years ago the product was 128. The elder brother's present age is:",
      f"{roots[1]} years", [(f"{roots[0]} years", "younger brother's age"), (f"{s_ // 2} years", "half the sum taken"), (f"{roots[1] + 4} years", "elder's age four years hence")],
      ["(a − 4)(b − 4) = ab − 4(a + b) + 16", "128 = 240 − 4S + 16 ⇒ S = 32", "Ages 12 and 20"],
      "Expand the product", "Sum from the product condition, then factor.")

    S2 = next(s for s in range(8, 80) if 4 * (s - 5 - 7) == 3 * (s - 7))
    R2 = S2 - 5
    q("ages", "L3", "o", "Rita is 5 years younger than Sunil. Seven years ago Rita's age was 3/4 of Sunil's. The ratio of their ages 3 years from now will be:",
      ratio(R2 + 3, S2 + 3), [(ratio(R2, S2), "present ratio"), ("3:4", "past ratio assumed"), (ratio(R2 + 3, S2), "3 years added to Rita only")],
      ["R = S − 5; 4(S − 12) = 3(S − 7) ⇒ S = 27", "R = 22", "In 3 years: 25 : 30 = 5 : 6"],
      "Solve for present ages", "Future ratio changes with time.")

    # ===================== Averages =====================
    vals = [12, 18, 25, 31, 44]
    q("avg", "L1", "f", "The average of 12, 18, 25, 31 and 44 is:",
      N(Fr(sum(vals), 5)), [("25", "median reported"), (N(Fr(sum(vals), 4)), "divided by 4"), (N(sum(vals)), "sum reported")],
      ["Sum = 130", "Average = 130/5 = 26"], "Mean = Σx/n", "Count all five values.")

    new = Fr(40 * 62 + 85, 41)
    q("avg", "L1", "f", "The average mark of 40 students is 62. When the teacher's mark of 85 is included, the new average is:",
      D(new), [(D(Fr(62 + 85, 2)), "average of the two averages"), (D(Fr(40 * 62 + 85, 40)), "still divided by 40"), ("63", "teacher adds exactly one mark")],
      ["Sum = 2,480 + 85 = 2,565", "2,565/41 = 62.56"], "New mean = (n·x̄ + y)/(n + 1)", "Weight 40 vs 1.")

    s6 = 180 - 4 * 26
    sixth = Fr(s6 - 8, 2)
    q("avg", "L2", "f", "The average of six numbers is 30. The average of the first four is 26, and the fifth number is 8 more than the sixth. The fifth number is:",
      N(sixth + 8), [(N(sixth), "sixth number reported"), (N(Fr(s6, 2)), "equal split of the last two"), (N(sixth + 12), "difference added twice")],
      ["Sum of last two = 180 − 104 = 76", "x + (x + 8) = 76 ⇒ x = 34", "Fifth = 42"], "Split a sum with a known difference", "Solve with the 8 difference.")

    new = Fr(11 * 42 + 90, 12)
    q("avg", "L2", "f", "A batsman averaged 42 in 11 innings. He scores 90 in the 12th. His new average is:",
      N(new), [(N(Fr(42 + 90, 2)), "average of 42 and 90"), (D(Fr(11 * 42 + 90, 11)), "divided by 11"), (D(42 + Fr(48, 11)), "increase spread over 11")],
      ["Sum = 462 + 90 = 552", "552/12 = 46"], "New average = total ÷ innings", "Divide by 12.")

    q("avg", "L2", "f", "Section A has 30 students averaging 60 marks; section B has 20 averaging 75. The combined average is:",
      N(Fr(30 * 60 + 20 * 75, 50)), [(N(Fr(135, 2)), "simple average of 60 and 75"), (N(Fr(20 * 60 + 30 * 75, 50)), "weights swapped"), ("63", "rough guess towards A")],
      ["(1,800 + 1,500)/50 = 66"], "Weighted mean", "Weights are class sizes.")

    q("avg", "L3", "o", "The average weight of 8 people increases by 2.5 kg when one of them, weighing 65 kg, is replaced by a new person. The new person weighs:",
      f"{N(65 + 8 * Fr(5, 2))} kg", [(f"{N(65 + Fr(5, 2))} kg", "increase added only once"), (f"{N(65 + 9 * Fr(5, 2))} kg", "9 members used"), ("75 kg", "increase × 4")],
      ["Total rises by 8 × 2.5 = 20 kg", "New person = 65 + 20 = 85 kg"], "Replacement: new = old + n × Δavg", "Multiply the rise by 8.")

    n = 7 + Fr(7 * (12000 - 8000), 8000 - 6000)
    assert n == 21
    q("avg", "L3", "o", "The average salary of all workers in a unit is ₹8,000. The 7 technicians average ₹12,000 and the rest average ₹6,000. The total number of workers is:",
      N(n), [(N(n - 7), "non-technicians only"), (N(2 * (n - 7)), "doubled"), (N(Fr(7 * 3, 2)), "ratio 3 : 2 misapplied")],
      ["7 × (12,000 − 8,000) = x × (8,000 − 6,000)", "28,000 = 2,000x ⇒ x = 14", "Total = 21"], "Deviations above = deviations below", "Balance about the mean.")

    lo = 61 - 4
    q("avg", "L3", "o", "The average of five consecutive odd numbers is 61. The product of the smallest and largest is:",
      N(lo * (lo + 8)), [(N(61 * 61), "square of the average"), (N(59 * 63), "consecutive integers used"), (N(55 * 67), "seven numbers assumed")],
      ["Numbers 57, 59, 61, 63, 65", "57 × 65 = 3,705"], "Middle term = mean", "Odd numbers step by 2.")

    new = 64 + Fr((84 - 48) - (63 - 36), 45)
    q("avg", "L3", "o", "The average mark of 45 students is 64. Later it is found that 84 was entered as 48 and 36 was entered as 63. The correct average is:",
      N(new), [(N(64 + Fr(36, 45)), "only the first error corrected"), (N(64 - Fr(27, 45)), "only the second error corrected"), (N(64 + Fr(63, 45)), "both corrections added")],
      ["Net correction = +36 − 27 = +9", "Average rises by 9/45 = 0.2 ⇒ 64.2"], "Adjust the total, then divide", "One error inflated, one deflated the total.")

    a = Fr(15, Fr(1, 2))
    q("avg", "L3", "o", "The average of a, b and c is 40; the average of b, c and d is 45. If d = 1.5a, then d equals:",
      N(Fr(3, 2) * a), [(N(a), "a reported"), (N(Fr(45, 2)), "d taken as 1.5 × 15"), ("15", "difference d − a reported")],
      ["a + b + c = 120, b + c + d = 135", "d − a = 15; 0.5a = 15 ⇒ a = 30", "d = 45"], "Subtract the sums", "b and c cancel.")

    runs = 21 * 39 - 20 * 36
    q("avg", "L3", "o", "A cricketer averages 36 runs over 20 innings. How many runs must he score in the next innings to raise his average by 3?",
      N(runs), [("96", "old average used for the new innings"), ("39", "new average reported"), ("63", "20 × 3 + 3")],
      ["Needed total = 21 × 39 = 819", "Current total = 720", "Runs = 99"], "x = new avg + n × Δ", "The new innings must also score the new average.")

    q("avg", "L3", "o", "A shop sells three grades of rice at ₹40, ₹55 and ₹70 per kg in the quantity ratio 3 : 2 : 1. The average price per kg is:",
      Rs(Fr(3 * 40 + 2 * 55 + 70, 6)), [(Rs(55), "simple average"), (Rs(Fr(40 + 110 + 210, 6)), "weights reversed"), (Rs(Fr(120 + 110, 5)), "third grade dropped")],
      ["(120 + 110 + 70)/6 = 50"], "Weighted mean", "Weights 3 : 2 : 1.")

    q("avg", "L3", "o", "The average of 7 consecutive integers is n. If the next three integers are included, the new average is:",
      "n + 1.5", [("n + 3", "average of the three new numbers minus n"), ("n + 1", "one step added"), ("n + 5", "middle of the new three")],
      ["Numbers n − 3 … n + 3; new ones n + 4, n + 5, n + 6", "Sum = 7n + 3n + 15 = 10n + 15", "Average = n + 1.5"],
      "Mean of consecutive integers = middle", "New list runs n − 3 to n + 6; middle is n + 1.5.")

    tot = Fr(30 * 29, 2) - 5 * 16 + 8 * 13
    q("avg", "L3", "o", "The average age of 30 students is 14.5 years. Five students averaging 16 years leave and eight averaging 13 years join. The new average age is:",
      D(tot / 33), [(D(tot / 30), "divided by 30"), (D((Fr(435) - 80) / 25), "joiners ignored"), ("14.5", "assumes average unchanged")],
      ["Total = 435 − 80 + 104 = 459", "459/33 = 13.91"], "Adjust total and count", "Count becomes 33.")

    # ===================== Median and mode =====================
    d = [7, 3, 9, 12, 5, 8, 10]
    q("med", "L1", "f", "The median of 7, 3, 9, 12, 5, 8, 10 is:",
      "8", [("12", "middle of unsorted list"), (D(Fr(sum(d), 7)), "mean reported"), ("9", "off-by-one position")],
      ["Sorted: 3, 5, 7, 8, 9, 10, 12", "4th value = 8"], "Median = middle of sorted data", "Sort first.")

    d = [4, 6, 4, 7, 6, 4, 9, 6, 4]
    q("med", "L1", "f", "The mode of 4, 6, 4, 7, 6, 4, 9, 6, 4 is:",
      "4", [("6", "second most frequent"), (D(Fr(sum(d), 9)), "mean reported"), ("9", "largest value")],
      ["4 occurs 4 times; 6 occurs 3 times", "Mode = 4"], "Mode = most frequent value", "Count frequencies carefully.")

    d = sorted([15, 22, 9, 31, 18, 27, 12, 20, 25, 14, 29, 17])
    q("med", "L2", "f", "The median of 15, 22, 9, 31, 18, 27, 12, 20, 25, 14, 29, 17 is:",
      N(Fr(d[5] + d[6], 2)), [(str(d[5]), "6th value only"), (str(d[6]), "7th value only"), (D(Fr(sum(d), 12)), "mean reported")],
      ["Sorted: 9, 12, 14, 15, 17, 18, 20, 22, 25, 27, 29, 31", "Median = (18 + 20)/2 = 19"], "Even n: average the two middle values", "Twelve values: 6th and 7th.")

    q("med", "L2", "f", "In a moderately skewed distribution the median is 24 and the mean is 26. Using the empirical relation, the mode is approximately:",
      "20", [("22", "mode = 2 × median − mean"), ("28", "mean + (mean − median)"), ("30", "3 × mean − 2 × median")],
      ["Mode = 3 Median − 2 Mean", "= 72 − 52 = 20"], "Mode ≈ 3 Median − 2 Mean", "Coefficients 3 and 2 go on median and mean.")

    x = next(x for x in range(0, 30) if Fr(x + x + 2, 2) == 11)
    q("med", "L2", "f", "The data 5, 8, x, x + 2, 15, 18 are in ascending order and their median is 11. The value of x is:",
      str(x), [("11", "median taken as x"), ("9", "median taken as x + 2"), ("12", "x + 1 taken as 13")],
      ["Median = (x + x + 2)/2 = x + 1", "x + 1 = 11 ⇒ x = 10"], "Even n: average of 3rd and 4th", "Median is x + 1, not x.")

    q("med", "L3", "o", "The median of 25 observations is 40. If each of the largest 5 is increased by 10 and each of the smallest 3 is decreased by 5, the new median is:",
      "40", [("41.4", "net shift in total spread over 25 (mean logic)"), ("45", "largest-value change applied"), ("35", "smallest-value change applied")],
      ["Median is the 13th value", "Changes affect only positions 1–3 and 21–25", "13th value unchanged ⇒ 40"],
      "Median depends on position", "Extreme-value changes do not move the median here.")

    data = [6, 9, 14, 9, 14, 21, 14, 9]
    full = sorted(data + [14])
    from collections import Counter
    c = Counter(full)
    assert c.most_common(1)[0] == (14, 4) and c[9] == 3
    q("med", "L3", "o", "For the data 6, 9, 14, 9, x, 21, 14, 9, 14 the mode is 14 and it is the only mode. The median of the data is:",
      str(full[4]), [("9", "mode taken as 9"), (D(Fr(sum(full), 9)), "mean reported"), (N(Fr(9 + 14, 2)), "average of the two frequent values")],
      ["Without x, 9 and 14 each occur 3 times", "A unique mode 14 needs x = 14", "Sorted: 6, 9, 9, 9, 14, 14, 14, 14, 21 ⇒ median 14"],
      "Median = 5th of 9 sorted values", "Find x from the mode condition first.")

    vals, fr_ = [10, 20, 30, 40, 50], [4, 7, 12, 9, 8]
    mean = Fr(sum(v * f for v, f in zip(vals, fr_)), sum(fr_))
    mode = 30
    q("med", "L3", "o", "Marks (frequency): 10 (4), 20 (7), 30 (12), 40 (9), 50 (8). The mean exceeds the mode by:",
      N(mean - mode), [(N(mode - mean), "subtraction reversed"), ("0", "mean assumed equal to mode"), (N(mean - 40), "mode taken as 40")],
      ["Mean = 1,300/40 = 32.5", "Mode = 30 (highest frequency 12)", "Difference = 2.5"],
      "Mean = Σfx/Σf", "Mode is the value, not the frequency.")

    q("med", "L3", "o", "Nine numbers have mean 20 and median 18. Each number is multiplied by 3 and then 5 is subtracted. The new mean and median are:",
      "55 and 49", [("60 and 54", "subtraction of 5 missed"), ("55 and 54", "median not reduced by 5"), ("15 and 13", "only the subtraction applied")],
      ["Mean: 3 × 20 − 5 = 55", "Median: 3 × 18 − 5 = 49"], "Linear transforms act on mean and median alike", "Apply both steps to both measures.")

    data = [0, 6, 6, 7, 8]
    mode_, med_, mean_ = 6, 6, Fr(sum(data), 5)
    assert not (min(mode_, med_) <= mean_ <= max(mode_, med_))
    q("med", "L3", "o",
      "Consider:\n\nI. The median is not affected by changing the extreme values.\nII. A data set can have more than one mode.\nIII. The mean always lies between the median and the mode.\n\nWhich are correct?",
      "I and II only", [("I only", "II wrongly rejected"), ("II and III only", "III accepted as a rule"), ("I, II and III", "empirical relation treated as a law")],
      ["I: true as long as the order of middle values is unchanged", "II: true (bimodal data)", "III: false — data 0, 6, 6, 7, 8 has mode 6, median 6, mean 5.4"],
      "Mode ≈ 3 Median − 2 Mean is only approximate", "III fails for many data sets.", kind="statement")

    best = None
    for a_, b_, d_, e_ in product(range(1, 40), repeat=4):
        arr = sorted([a_, b_, 11, d_, e_])
        if arr[2] != 11 or sum(arr) != 60:
            continue
        cc = Counter(arr)
        top = cc.most_common()
        if top[0][0] != 8 or (len(top) > 1 and top[1][1] == top[0][1]):
            continue
        best = max(best or 0, arr[-1])
    assert best == 21
    q("med", "L3", "o", "Five positive integers have mean 12, median 11 and a unique mode of 8. The largest possible value of the greatest integer is:",
      str(best), [("22", "fourth number allowed to be 11, creating a tie"), ("17", "minimised instead of maximised"), ("33", "fourth number ignored")],
      ["Order: 8, 8, 11, d, e with sum 60", "d + e = 33; d ≥ 12 (d = 11 would tie with 8 as mode)", "Max e = 33 − 12 = 21"],
      "Fix the known values; push the rest to the extreme", "A repeated 11 would break the unique mode.")

    ev = list(range(2, 41, 2))
    q("med", "L2", "o", "The median of the first 20 even natural numbers is:",
      N(Fr(ev[9] + ev[10], 2)), [(str(ev[9]), "10th value only"), (str(ev[10]), "11th value only"), ("20.5", "average of 1…40 range misread")],
      ["Numbers 2, 4, …, 40", "Median = (20 + 22)/2 = 21"], "Even n: average two middle", "20 values: 10th and 11th.")

    # ===================== Mixtures and alligation =====================
    q("mix", "L1", "f", "A 40-litre mixture contains milk and water in the ratio 3 : 1. The quantity of water is:",
      "10 L", [("30 L", "milk reported"), ("13.33 L", "ratio 3 : 1 read as 1/3"), ("12 L", "water taken as 30%")],
      ["Water = 40 × 1/4 = 10 L"], "Part = total × term/sum", "Sum of ratio terms is 4.")

    q("mix", "L2", "f", "In what ratio must rice at ₹32/kg be mixed with rice at ₹44/kg to get a mixture worth ₹36/kg?",
      ratio(44 - 36, 36 - 32), [(ratio(36 - 32, 44 - 36), "alligation sides swapped"), ("3:1", "difference 12 split as 9 : 3"), ("4:3", "ratio of prices 44 : 32 reduced")],
      ["Cheap : Dear = (44 − 36) : (36 − 32) = 8 : 4 = 2 : 1"], "Alligation", "Cheaper grade pairs with (dear − mean).")

    q("mix", "L2", "f", "A 60-litre mixture has milk and water in the ratio 2 : 1. How much water must be added to make the ratio 1 : 1?",
      "20 L", [("10 L", "half the needed water"), ("40 L", "milk quantity reported"), ("30 L", "half the mixture")],
      ["Milk 40, water 20", "Water must equal milk: add 20 L"], "Keep milk fixed", "Only water changes.")

    q("mix", "L2", "f", "In what ratio should a 30% acid solution be mixed with a 50% acid solution to get a 36% solution?",
      ratio(50 - 36, 36 - 30), [(ratio(36 - 30, 50 - 36), "alligation sides swapped"), ("3:2", "rough split"), ("1:1", "simple average assumed")],
      ["30% : 50% = (50 − 36) : (36 − 30) = 14 : 6 = 7 : 3"], "Alligation", "36 is nearer 30, so more of the 30% solution.")

    q("mix", "L1", "f", "25 litres of a 20% salt solution is diluted with water to make a 10% solution. The water added is:",
      "25 L", [("50 L", "final volume reported"), ("12.5 L", "half the original volume"), ("20 L", "rate read as litres")],
      ["Salt = 5 L", "Final volume = 5/0.10 = 50 L", "Water added = 25 L"], "Solute fixed: C₁V₁ = C₂V₂", "Subtract the original volume.")

    left = 80 * Fr(9, 10) ** 3
    q("mix", "L3", "o", "From 80 L of pure milk, 8 L is removed and replaced with water. This is done three times in all. The milk left is:",
      f"{N(left)} L", [("56 L", "8 L of milk removed each time"), (f"{N(80 * Fr(81, 100))} L", "only two operations"), ("57.6 L", "rough 28% loss")],
      ["Fraction left each time = 72/80 = 0.9", "Milk = 80 × 0.9³ = 58.32 L"], "Final = Initial × (1 − x/V)^n", "Later removals take out less milk.")

    fa, fb, tgt = Fr(5, 8), Fr(3, 4), Fr(7, 10)
    rA = (fb - tgt) / (tgt - fa)
    q("mix", "L3", "o", "Vessel A has milk and water in the ratio 5 : 3; vessel B in the ratio 3 : 1. In what ratio should A and B be mixed to get milk and water in the ratio 7 : 3?",
      ratio(fb - tgt, tgt - fa), [(ratio(tgt - fa, fb - tgt), "alligation sides swapped"), ("1:1", "equal mixing assumed"), ("5:3", "A's own ratio reported")],
      ["Milk fractions: A = 5/8, B = 3/4, target = 7/10", "A : B = (3/4 − 7/10) : (7/10 − 5/8) = 1/20 : 3/40 = 2 : 3"],
      "Alligate on milk fractions", "Convert ratios to fractions of the whole.")
    assert rA == Fr(2, 3)

    milk, water = 35, 25
    add = Fr(9 * water, 5) - milk
    q("mix", "L3", "o", "A 60-litre can holds milk and water in the ratio 7 : 5. How much milk must be added to make the ratio 9 : 5?",
      f"{N(add)} L", [(f"{D(Fr(60 * 9, 14) - milk)} L", "target share applied to old total"), ("12 L", "20% of the can"), ("5 L", "one part of the original 12")],
      ["Milk 35, water 25", "Water fixed: milk must be 9/5 × 25 = 45", "Add 10 L"], "Keep water fixed", "Use the unchanged component.")

    alc = 32
    q("mix", "L3", "o", "40 L of a mixture has alcohol and water in the ratio 4 : 1. How much water must be added so that alcohol forms 64% of the mixture?",
      f"{N(Fr(alc * 100, 64) - 40)} L", [("6.4 L", "16-point drop taken as 16% of 40"), ("50 L", "final volume reported"), ("8 L", "original water reported")],
      ["Alcohol = 32 L", "Final volume = 32/0.64 = 50 L", "Water added = 10 L"], "Solute fixed", "Subtract the original 40 L.")

    x = Fr(153 * 4 - 126 - 135, 2)
    q("mix", "L3", "o", "Teas at ₹126/kg and ₹135/kg are mixed with a third variety in the ratio 1 : 1 : 2. The mixture is worth ₹153/kg. The price of the third variety is:",
      Rs(x), [(Rs(153 * 3 - 261), "three equal parts assumed"), (Rs(153 * 4 - 261), "third variety given weight 1 in a total of 4"), (Rs(153), "mixture price reported")],
      ["126 + 135 + 2x = 4 × 153 = 612", "2x = 351 ⇒ x = 175.5"], "Weighted mean", "Third variety has weight 2.")

    wine = 50 * Fr(4, 5) ** 2
    q("mix", "L3", "o", "A cask holds 50 L of wine. 10 L is drawn off and replaced with water; then 10 L of the mixture is drawn off and replaced with water. The ratio of wine to water now is:",
      ratio(wine, 50 - wine), [("3:2", "10 L of pure wine removed each time"), ("4:1", "only one replacement"), (ratio(50 - wine, wine), "ratio inverted")],
      ["Wine = 50 × (4/5)² = 32 L", "Water = 18 L ⇒ 16 : 9"], "Final = V(1 − x/V)^n", "Second draw removes mixture, not pure wine.")

    cpm = Fr(50) / Fr(125, 100)
    q("mix", "L3", "o", "A milkman mixes water with milk costing ₹50/L and sells the mixture at ₹50/L, gaining 25%. The ratio of milk to water in the mixture is:",
      ratio(cpm, 50 - cpm), [("3:1", "25% gain taken on SP"), ("5:1", "20% gain scenario"), ("1:4", "ratio inverted")],
      ["Cost of 1 L mixture = 50/1.25 = ₹40", "Milk fraction = 40/50 = 4/5", "Milk : water = 4 : 1"], "Gain comes from free water", "Profit is on cost.")

    # ===================== Partnership =====================
    q("part", "L1", "f", "A and B invest ₹40,000 and ₹60,000. The annual profit is ₹25,000. A's share is:",
      Rs(10000), [(Rs(15000), "B's share"), (Rs(12500), "equal split"), (Rs(D(Fr(25000 * 2, 3))), "ratio 2 : 3 read as 2/3")],
      ["Ratio 2 : 3", "A = 25,000 × 2/5 = 10,000"], "Share ∝ capital", "Denominator is 5.")

    q("part", "L2", "f", "A invests ₹30,000 for 12 months and B ₹45,000 for 8 months. Out of a profit of ₹36,000, B's share is:",
      Rs(18000), [(Rs(Fr(36000 * 3, 5)), "time ignored"), (Rs(Fr(36000 * 2, 5)), "capital ratio inverted"), (Rs(24000), "time ratio 12 : 8 misapplied")],
      ["A: 3,60,000; B: 3,60,000 capital-months", "Equal ⇒ B = 18,000"], "Share ∝ capital × time", "Time can equalise unequal capitals.")

    q("part", "L2", "f", "A, B and C share capital in the ratio 2 : 3 : 5. Out of a profit of ₹1,20,000, C gets:",
      Rs(60000), [(Rs(36000), "B's share"), (Rs(24000), "A's share"), (Rs(40000), "equal split")],
      ["C = 1,20,000 × 5/10 = 60,000"], "Share = profit × term/sum", "Sum of terms is 10.")

    b = Fr(42000 * 480, 1080)
    q("part", "L2", "f", "A starts a business with ₹50,000; B joins after 4 months with ₹60,000. Out of the year's profit of ₹42,000, B's share is:",
      Rs(b), [(Rs(Fr(42000 * 6, 11)), "joining time ignored"), (Rs(42000 - b), "A's share"), (Rs(16000), "B's months taken as 6")],
      ["A: 50,000 × 12 = 6,00,000; B: 60,000 × 8 = 4,80,000", "B = 42,000 × 480/1,080 = 18,666.67"], "Capital × months", "B works 8 months.")

    q("part", "L2", "f", "A (working partner) and B share profit in their capital ratio 3 : 2 after A takes 10% of the profit as salary. Out of ₹50,000, A receives in all:",
      Rs(5000 + 27000), [(Rs(30000), "salary not taken"), (Rs(27000), "salary omitted from A's total"), (Rs(35000), "salary added to 3/5 of full profit")],
      ["Salary = 5,000", "Rest 45,000 × 3/5 = 27,000", "A total = 32,000"], "Deduct salary before sharing", "Salary is a first charge.")

    A_, B_ = 60000 * 3 + 40000 * 9, 50000 * 6 + 60000 * 6
    q("part", "L3", "o", "A starts with ₹60,000 and withdraws ₹20,000 after 3 months. B starts with ₹50,000 and adds ₹10,000 after 6 months. Out of the year's profit of ₹1,02,000, A's share is:",
      Rs(Fr(102000 * A_, A_ + B_)), [(Rs(Fr(102000 * B_, A_ + B_)), "B's share"), (Rs(D(Fr(102000 * 6, 11))), "initial capitals only"), (Rs(51000), "equal split")],
      ["A: 60k × 3 + 40k × 9 = 5,40,000", "B: 50k × 6 + 60k × 6 = 6,60,000", "A = 1,02,000 × 540/1,200 = 45,900"], "Sum capital × months per stretch", "Track each change.")

    c = Fr(158000 * 40, 79)
    q("part", "L3", "o", "A, B and C invest capitals in the ratio 5 : 6 : 8 for periods in the ratio 3 : 4 : 5. Out of a profit of ₹1,58,000, C's share is:",
      Rs(c), [(Rs(D(Fr(158000 * 8, 19))), "periods ignored"), (Rs(D(Fr(158000 * 5, 12))), "capitals ignored"), (Rs(Fr(158000 * 24, 79)), "B's share")],
      ["Profit ratio = 15 : 24 : 40", "C = 1,58,000 × 40/79 = 80,000"], "Multiply capital and time ratios", "Sum of products is 79.")

    q("part", "L3", "o", "The profits of A and B are in the ratio 5 : 4 and their capitals in the ratio 3 : 4. The ratio of the periods of their investments is:",
      ratio(Fr(5, 3), Fr(4, 4)), [("3:5", "ratio inverted"), ("15:16", "capital and profit ratios multiplied"), ("4:3", "capital ratio inverted")],
      ["Time ∝ profit/capital", "A : B = 5/3 : 4/4 = 5 : 3"], "t = P/C", "Divide profit by capital.")

    x = 12 - Fr(24 * 12, 36)
    q("part", "L3", "o", "A invests ₹24,000 at the start; B joins some months later with ₹36,000. At year end profit is shared equally. B joined after:",
      f"{N(x)} months", [("8 months", "B's months reported"), ("6 months", "half-year assumed"), ("3 months", "capital gap ÷ 4,000")],
      ["24,000 × 12 = 36,000 × (12 − x)", "12 − x = 8 ⇒ x = 4"], "Equal shares ⇒ equal capital-months", "Solve for B's months, then subtract.")

    P_ = Fr(57000) / (Fr(125, 1000) + Fr(875, 1000) * Fr(2, 5))
    assert P_ == 120000
    q("part", "L3", "o", "A sleeping partner invests ₹1,20,000 and a working partner ₹80,000. The working partner first gets 12.5% of profit as salary; the rest is shared in capital ratio. If the working partner receives ₹57,000 in all, the total profit is:",
      Rs(P_), [(Rs(Fr(57000 * 5, 2)), "salary ignored"), (Rs(D(Fr(57000) / (Fr(125, 1000) + Fr(875, 1000) * Fr(3, 5)))), "capital shares swapped"),
               (Rs(D(Fr(57000) / (Fr(125, 1000) + Fr(2, 5)))), "salary added to 2/5 of full profit")],
      ["Working share = 0.125P + 0.875P × 2/5 = 0.475P", "0.475P = 57,000 ⇒ P = 1,20,000"], "Salary first, then capital ratio", "Capital ratio 3 : 2 gives him 2/5.")

    P_ = Fr(10000) / (Fr(5, 12) - Fr(1, 4))
    q("part", "L3", "o", "In a firm A gets 1/3 of the profit, B gets 1/4 and C the rest. C's share is ₹10,000 more than B's. The total profit is:",
      Rs(P_), [(Rs(Fr(10000, Fr(1, 12))), "gap taken as C − A"), (Rs(Fr(10000, Fr(1, 4))), "gap taken as 1/4"), (Rs(D(Fr(10000) / Fr(5, 12))), "C's share taken as ₹10,000")],
      ["C = 1 − 1/3 − 1/4 = 5/12", "C − B = 5/12 − 3/12 = 1/6", "P = 10,000 × 6 = 60,000"], "Fractions of the whole", "Compare C with B.")

    A_, B_ = 3 * 4 + Fr(3, 2) * 8, 5 * 8 + 4 * 4
    q("part", "L3", "o", "A and B invest in the ratio 3 : 5. After 4 months A withdraws half his capital; after 8 months B withdraws one-fifth of his. The ratio of their annual profits is:",
      ratio(A_, B_), [("3:5", "withdrawals ignored"), (ratio(A_, 60), "B's withdrawal ignored"), (ratio(36, B_), "A's withdrawal ignored")],
      ["A: 3 × 4 + 1.5 × 8 = 24", "B: 5 × 8 + 4 × 4 = 56", "24 : 56 = 3 : 7"], "Σ capital × months", "Each partner changes at a different time.")

    # ===================== Proportional division =====================
    q("prop", "L1", "f", "₹7,200 is divided between two people in the ratio 5 : 7. The larger share is:",
      Rs(4200), [(Rs(3000), "smaller share"), (Rs(Fr(7200 * 7, 10)), "7 taken out of 10"), (Rs(3600), "equal split")],
      ["Larger = 7,200 × 7/12 = 4,200"], "Share = total × term/sum", "Sum of terms is 12.")

    q("prop", "L2", "f", "₹1,750 is divided among A, B and C such that A : B = 2 : 3 and B : C = 4 : 5. C's share is:",
      Rs(750), [(Rs(875), "chain written as 2 : 3 : 5"), (Rs(600), "B's share"), (Rs(700), "5 taken out of 12.5")],
      ["A : B : C = 8 : 12 : 15", "C = 1,750 × 15/35 = 750"], "Equalise B's term", "LCM of 3 and 4 for B.")

    q("prop", "L2", "f", "₹1,560 is divided among A, B and C in the ratio 1/2 : 1/3 : 1/4. A's share is:",
      Rs(720), [(Rs(D(Fr(1560 * 2, 9))), "ratio taken as 2 : 3 : 4"), (Rs(520), "equal split"), (Rs(480), "B's share")],
      ["1/2 : 1/3 : 1/4 = 6 : 4 : 3", "A = 1,560 × 6/13 = 720"], "Clear fractions with the LCM", "Denominators are not the ratio.")

    q("prop", "L1", "f", "₹840 is divided in the ratio 3 : 4. The difference between the shares is:",
      Rs(120), [(Rs(360), "smaller share"), (Rs(480), "larger share"), (Rs(210), "quarter of the total")],
      ["One part = 840/7 = 120", "Difference = 1 part = 120"], "Difference = total × (b − a)/(a + b)", "One ratio part here.")

    q("prop", "L2", "f", "An amount is divided among P, Q and R so that 2P = 3Q = 4R. The ratio P : Q : R is:",
      "6:4:3", [("2:3:4", "coefficients used directly"), ("4:3:2", "coefficients reversed"), ("3:4:6", "ratio inverted")],
      ["P : Q : R = 1/2 : 1/3 : 1/4 = 6 : 4 : 3"], "kx = const ⇒ x ∝ 1/k", "Invert the coefficients.")

    c = Fr(6000 * 5, 12) + 80
    q("prop", "L3", "o", "₹6,200 is divided among A, B and C so that if ₹50, ₹70 and ₹80 are taken from their shares respectively, the remainders are in the ratio 3 : 4 : 5. C's share is:",
      Rs(c), [(Rs(c - 80), "C's remainder reported"), (Rs(D(Fr(6200 * 5, 12))), "deductions ignored"), (Rs(Fr(6000 * 4, 12) + 70), "B's share")],
      ["Remainders total 6,200 − 200 = 6,000", "C's remainder = 6,000 × 5/12 = 2,500", "C = 2,580"], "Remove the deductions first", "Add back C's own deduction.")

    x = Fr(95, Fr(475, 100))
    q("prop", "L3", "o", "A bag holds ₹1, 50-paise and 25-paise coins in the ratio 2 : 3 : 5 by number, worth ₹95 in all. The number of 25-paise coins is:",
      N(5 * x), [(D(Fr(95 * 5, 10)), "value split in 2 : 3 : 5"), (N(Fr(5 * x, 4)), "value of 25-paise coins in ₹ read as count"), (N(3 * x), "50-paise coins")],
      ["Value per set: 2 + 1.5 + 1.25 = ₹4.75", "x = 95/4.75 = 20", "25-paise coins = 5 × 20 = 100"], "Value = count × denomination", "Ratio is by number, not value.")

    q("prop", "L3", "o", "Salaries of A, B and C are in the ratio 2 : 3 : 5. They get increments of 15%, 10% and 20% respectively. The new ratio is:",
      ratio(Fr(23, 10), Fr(33, 10), 6), [("2:3:5", "increments ignored"), ("3:2:4", "increment ratio reported"), (ratio(Fr(23, 10), 3, 6), "B's increment missed")],
      ["2 × 1.15 = 2.3; 3 × 1.1 = 3.3; 5 × 1.2 = 6", "2.3 : 3.3 : 6 = 23 : 33 : 60"], "Scale each term", "Clear decimals.")

    w = [(300, 20), (350, 24), (400, 15)]
    e = [a * b for a, b in w]
    tot = 18700
    q("prop", "L3", "o", "A contractor pays ₹18,700 to three workers in proportion to their earnings: daily wages ₹300, ₹350 and ₹400 for 20, 24 and 15 days. The second worker gets:",
      Rs(Fr(tot * e[1], sum(e))), [(Rs(D(Fr(tot * 350, 1050))), "days ignored"), (Rs(D(Fr(tot * 24, 59))), "wages ignored"), (Rs(Fr(tot * e[0], sum(e))), "first worker's share")],
      ["Earnings ratio 6,000 : 8,400 : 6,000 = 5 : 7 : 5", "Second = 18,700 × 7/17 = 7,700"], "Share ∝ wage × days", "Both factors matter.")

    T = Fr(4200) / (1 - Fr(1, 4) - Fr(2, 5))
    assert T == 12000
    q("prop", "L3", "o", "An amount is divided among A, B and C. A gets 1/3 of what B and C together get, and B gets 2/3 of what A and C together get. If C gets ₹4,200, the total is:",
      Rs(T), [(Rs(Fr(4200) / (1 - Fr(1, 3) - Fr(2, 5))), "A taken as 1/3 of total"), (Rs(Fr(4200) / (1 - Fr(1, 4) - Fr(2, 3))), "B taken as 2/3 of total"),
              (Rs(4200 * 2), "fractions added to 1 and doubled")],
      ["A = (T − A)/3 ⇒ A = T/4", "B = 2(T − B)/3 ⇒ B = 2T/5", "C = T − T/4 − 2T/5 = 7T/20 = 4,200 ⇒ T = 12,000"],
      "Convert 'of the others' into 'of the total'", "A = k(T − A) ⇒ A = kT/(1 + k).")

    x = next(x for x in range(1, 50) if 6 * 7 * x == 7 * (5 * x + 12))
    q("prop", "L3", "o", "Boys and girls in a class are in the ratio 7 : 5. After 12 more girls join, the ratio becomes 7 : 6. The total strength now is:",
      N(12 * x + 12), [(N(12 * x), "strength before"), (N(12 * x - 12), "girls subtracted"), (N(12 * x + 24), "new girls counted twice")],
      ["7x/(5x + 12) = 7/6 ⇒ 42x = 35x + 84 ⇒ x = 12", "Now 84 + 72 = 156"], "Boys fixed", "Add the 12 new girls.")

    x = Fr(4200, 50 + 60 + 100)
    q("prop", "L3", "o", "A cash box has ₹10, ₹20 and ₹50 notes in the ratio 5 : 3 : 2 by number, worth ₹4,200 in all. The number of ₹20 notes is:",
      N(3 * x), [(N(Fr(4200 * 3, 10 * 20)), "value split in 5 : 3 : 2, then ÷ 20"), (N(2 * x), "₹50 notes"), (N(5 * x), "₹10 notes")],
      ["Value per set = 50 + 60 + 100 = ₹210", "x = 20", "₹20 notes = 60"], "Value = count × face value", "Ratio is by count.")

    tot = 1040
    parts = [Fr(1, 4), Fr(1, 3), Fr(1, 2)]
    s_ = sum(parts)
    q("prop", "L3", "o", "1,040 is split into three parts such that 4 times the first = 3 times the second = 2 times the third. The third part is:",
      N(tot * parts[2] / s_), [(D(Fr(tot * 2, 9)), "ratio taken as 4 : 3 : 2"), (D(Fr(tot * 4, 9)), "ratio taken as 2 : 3 : 4"), (D(Fr(tot, 3)), "equal parts")],
      ["Parts ∝ 1/4 : 1/3 : 1/2 = 3 : 4 : 6", "Third = 1,040 × 6/13 = 480"], "kx = const ⇒ invert k", "Largest coefficient gives smallest part.")

    C = Fr(39000 - 7500 - 4500, 3)
    q("prop", "L3", "o", "₹39,000 is divided among A, B and C so that A gets ₹3,000 more than B and B gets ₹4,500 more than C. A's share is:",
      Rs(C + 7500), [(Rs(13000), "equal split"), (Rs(Fr(39000 - 7500, 3) + 3000), "A read as ₹3,000 more than C (this also equals B's share)"), (Rs(C), "C's share reported")],
      ["A = C + 7,500, B = C + 4,500", "3C + 12,000 = 39,000 ⇒ C = 9,000", "A = 16,500"], "Express all in terms of C", "Remove offsets before dividing by 3.")

    # ===================== Simple and compound ratio =====================
    q("sratio", "L1", "f", "The compound ratio of 2 : 3, 4 : 5 and 5 : 8 is:",
      ratio(2 * 4 * 5, 3 * 5 * 8), [("11:16", "terms added"), ("1:2", "rough cancellation"), ("2:5", "middle ratio skipped")],
      ["(2 × 4 × 5) : (3 × 5 × 8) = 40 : 120 = 1 : 3"], "Compound ratio = product of antecedents : product of consequents", "Multiply, don't add.")

    q("sratio", "L1", "f", "The duplicate ratio of 3 : 4 is:",
      "9:16", [("6:8", "terms doubled"), ("27:64", "triplicate ratio"), ("√3:2", "sub-duplicate ratio")],
      ["Duplicate = a² : b² = 9 : 16"], "Duplicate ratio = square of terms", "Not doubling.")

    q("sratio", "L2", "f", "If A : B = 2 : 3 and B : C = 4 : 5, then A : C is:",
      "8:15", [("2:5", "first and last terms joined directly"), ("10:12", "cross-multiplied wrongly"), ("6:5", "B's terms not equalised")],
      ["A/C = (2/3)(4/5) = 8/15"], "Chain ratios by multiplying", "Equalise B.")

    q("sratio", "L2", "f", "The fourth proportional to 4, 9 and 12 is:",
      "27", [(N(Fr(16, 3)), "4 × 12 ÷ 9"), ("6", "mean proportional of 4 and 9"), ("17", "12 + (9 − 4)")],
      ["4 : 9 = 12 : x", "x = 9 × 12/4 = 27"], "a : b = c : d ⇒ d = bc/a", "Proportion is multiplicative.")

    x = next(x for x in range(0, 20) if (3 + x) * (13 + x) == (5 + x) * (9 + x))
    q("sratio", "L2", "f", "What number must be added to each of 3, 5, 9 and 13 so that the results are in proportion?",
      str(x), [("1", "trial slip"), ("2", "difference of first two numbers"), ("4", "difference of 9 and 5")],
      ["(3 + x)(13 + x) = (5 + x)(9 + x)", "39 + 16x = 45 + 14x ⇒ x = 3"], "Extremes product = means product", "Check: 6 : 8 = 12 : 16.")

    x = next(x for x in range(1, 50) if Fr(3 * x - 9, 5 * x - 9) == Fr(12, 23))
    q("sratio", "L3", "o", "Two numbers are in the ratio 3 : 5. If 9 is subtracted from each, the ratio becomes 12 : 23. The sum of the numbers is:",
      str(8 * x), [(str(5 * x), "larger number only"), (str(8 * 9), "multiplier taken as 9"), (str(9 * x), "9x reported")],
      ["(3x − 9)/(5x − 9) = 12/23", "69x − 207 = 60x − 108 ⇒ x = 11", "Numbers 33 and 55; sum 88"], "Cross-multiply", "Subtract from actual numbers, not ratio terms.")

    a, b, c = 9, 12, 14
    q("sratio", "L3", "o", "If a : b = 3 : 4 and b : c = 6 : 7, then (2a + 3b) : (4c − b) equals:",
      ratio(2 * a + 3 * b, 4 * c - b), [(ratio(2 * 3 + 3 * 4, 4 * 7 - 4), "chain not equalised (3 : 4 : 7)"), (ratio(2 * 3 + 3 * 6, 4 * 7 - 6), "chain read as 3 : 6 : 7"),
                                       (ratio(2 * a + 3 * b, 4 * c), "b not subtracted")],
      ["a : b : c = 9 : 12 : 14", "(18 + 36) : (56 − 12) = 54 : 44 = 27 : 22"], "Equalise b", "Use consistent values.")

    q("sratio", "L3", "o", "If x : y = 5 : 7, then (7x − 2y) : (3x + y) equals:",
      ratio(7 * 5 - 2 * 7, 3 * 5 + 7), [(ratio(3 * 5 + 7, 7 * 5 - 2 * 7), "ratio inverted"), (ratio(7 * 7 - 2 * 5, 3 * 7 + 5), "x and y swapped"), (ratio(35, 22), "y term in the first bracket dropped")],
      ["x = 5, y = 7", "(35 − 14) : (15 + 7) = 21 : 22"], "Substitute proportional values", "Keep x and y in order.")

    x = Fr(310, 31)
    q("sratio", "L3", "o", "A purse has ₹5 and ₹2 coins in the ratio 3 : 8 by number, worth ₹310 in all. The total number of coins is:",
      N(11 * x), [(N(8 * x), "₹2 coins only"), (N(3 * x), "₹5 coins only"), (N(Fr(310, 5)), "₹310 ÷ 5")],
      ["Value per set = 15 + 16 = ₹31", "x = 10; coins = 30 + 80 = 110"], "Value = count × face value", "Ratio is by number.")

    q("sratio", "L3", "o", "A : B = 3 : 5. If A is increased by 20% and B by 50%, the new ratio is:",
      ratio(Fr(36, 10), Fr(75, 10)), [("3:5", "increments ignored"), ("23:55", "percentages added to terms"), ("3:4", "increments swapped")],
      ["3 × 1.2 = 3.6; 5 × 1.5 = 7.5", "3.6 : 7.5 = 12 : 25"], "Scale each term", "Clear decimals.")

    x = next(x for x in range(1, 50) if Fr(5 * x + 12, 8 * x + 12) == Fr(2, 3))
    q("sratio", "L3", "o", "Two numbers are in the ratio 5 : 8. If 12 is added to each, the ratio becomes 2 : 3. The smaller number is:",
      str(5 * x), [(str(8 * x), "larger number"), (str(x), "multiplier reported"), (str(5 * x + 12), "number after adding 12")],
      ["(5x + 12)/(8x + 12) = 2/3 ⇒ 15x + 36 = 16x + 24 ⇒ x = 12", "Smaller = 60"], "Cross-multiply", "Add to actual numbers.")

    q("sratio", "L2", "o", "The mean proportional between 0.08 and 0.18 is:",
      "0.12", [("0.13", "arithmetic mean"), ("0.0144", "product, not its root"), ("1.2", "decimal misplaced")],
      ["√(0.08 × 0.18) = √0.0144 = 0.12"], "Mean proportional = √(ab)", "Take the square root.")

    q("sratio", "L3", "o", "If a : b = 2 : 3, b : c = 5 : 7 and c : d = 3 : 4, then a : d is:",
      ratio(Fr(2, 3) * Fr(5, 7) * Fr(3, 4), 1), [("1:2", "first and last terms 2 : 4 joined"), ("10:21", "c : d ignored"), ("5:7", "terms added")],
      ["a/d = (2/3)(5/7)(3/4) = 30/84 = 5/14"], "Multiply the chain", "All three links matter.")

    q("sratio", "L3", "o", "The third proportional to (x² − y²) and (x − y) is:",
      "(x − y)/(x + y)", [("(x + y)/(x − y)", "inverted"), ("x + y", "cancelled wrongly"), ("(x − y)²", "denominator dropped")],
      ["a : b = b : c ⇒ c = b²/a", "c = (x − y)²/[(x − y)(x + y)] = (x − y)/(x + y)"], "Third proportional = b²/a", "Factor x² − y².")
