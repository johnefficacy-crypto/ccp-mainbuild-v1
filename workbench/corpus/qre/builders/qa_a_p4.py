"""QRE-QA-A part 4: Speed, Time and Distance (case-set items in qa_a_cases)."""
from fractions import Fraction as Fr
from math import lcm
from qa_a_common import N, D, P, ratio, hm_time, hmin, make_q


def hm(a, b):
    return Fr(2 * a * b, a + b)


def add_all(B):
    q = make_q(B)
    kmh = lambda v: f"{N(v)} km/h"

    # ===================== Average speed and journey segments =====================
    q("avgspd", "L1", "f", "A car goes from P to Q at 60 km/h and returns at 40 km/h. Its average speed for the round trip is:",
      kmh(hm(60, 40)), [(kmh(50), "arithmetic mean of speeds"), (kmh(24), "half the harmonic mean"), (kmh(100), "speeds added")],
      ["Average = 2 × 60 × 40/(60 + 40) = 48"], "Equal distances ⇒ harmonic mean", "Time is longer on the slow leg.")

    q("avgspd", "L1", "f", "A bus covers 120 km in 2 hours and then 180 km in 4 hours. Its average speed for the whole journey is:",
      kmh(Fr(300, 6)), [(kmh(Fr(60 + 45, 2)), "average of the two speeds"), (kmh(45), "second-leg speed"), (kmh(60), "first-leg speed")],
      ["Total 300 km in 6 h", "Average = 50 km/h"], "Average speed = total distance ÷ total time", "Do not average the speeds.")

    v = Fr(3) / (Fr(1, 30) + Fr(1, 40) + Fr(1, 60))
    q("avgspd", "L2", "f", "A cyclist covers equal thirds of a route at 30, 40 and 60 km/h. The average speed is:",
      kmh(v), [(kmh(Fr(130, 3)), "arithmetic mean"), (kmh(45), "middle and top speed averaged"), (kmh(D(hm(30, 40))), "harmonic mean of the two slower speeds only")],
      ["Time per unit third: 1/30 + 1/40 + 1/60 = 9/120", "Average = 3 ÷ 9/120 = 40"], "Equal distances: n ÷ Σ(1/vᵢ)", "Use the harmonic mean.")

    q("avgspd", "L2", "f", "A car travels half the time at 50 km/h and half the time at 70 km/h. Its average speed is:",
      kmh(60), [(kmh(hm(50, 70)), "harmonic mean (equal distances) used"), (kmh(120), "speeds added"), (kmh(55), "weighted towards the slower speed")],
      ["Equal times ⇒ distances 50t and 70t", "Average = 120t/2t = 60"], "Equal times ⇒ arithmetic mean", "Equal time, not equal distance.")

    v = Fr(24, Fr(6, 4) + 1)
    q("avgspd", "L2", "f", "A man walks 6 km at 4 km/h and then cycles 18 km at 18 km/h. His average speed for the whole trip is:",
      kmh(v), [(kmh(11), "arithmetic mean of 4 and 18"), (kmh(Fr(6 * 4 + 18 * 18, 24)), "distance-weighted speeds"), (kmh(Fr(24, 2)), "total time taken as 2 h")],
      ["Times: 1.5 h and 1 h", "Average = 24/2.5 = 9.6"], "Total distance ÷ total time", "Speeds must be weighted by time.")

    v = Fr(320) / (Fr(160, 64) + Fr(160, 80))
    q("avgspd", "L3", "o", "A train covers the first 160 km at 64 km/h and the next 160 km at 80 km/h. Its average speed over the 320 km is:",
      kmh(v), [(kmh(72), "arithmetic mean"), (kmh(144), "speeds added"), (kmh(Fr(320, 5)), "total time taken as 5 h")],
      ["Times 2.5 h and 2 h", "Average = 320/4.5 = 71 1/9"], "Harmonic mean for equal distances", "Weighted by time, the slower leg counts more.")

    d = Fr(5) / (Fr(1, 12) + Fr(1, 18))
    q("avgspd", "L3", "o", "A trekker climbs a hill at 12 km/h and comes down the same path at 18 km/h, taking 5 hours in all. The one-way distance is:",
      f"{N(d)} km", [(f"{N(2 * d)} km", "round-trip distance"), (f"{N(Fr(15 * 5, 2))} km", "average of speeds used"), ("30 km", "slower speed × 2.5 h")],
      ["d/12 + d/18 = 5 ⇒ 5d/36 = 5", "d = 36 km"], "Σ(d/vᵢ) = total time", "Arithmetic mean overstates the pace.")

    need = Fr(60 * 2 - 45 * Fr(1, 2), Fr(3, 2))
    q("avgspd", "L3", "o", "A car travels at 45 km/h for the first 30 minutes. At what speed must it travel for the next 1.5 hours to average 60 km/h over the 2 hours?",
      kmh(need), [(kmh(75), "speeds averaged: (45 + x)/2 = 60"), (kmh(Fr(195, 2)), "remaining distance read as speed"), (kmh(80), "first 22.5 km not subtracted")],
      ["Required total = 120 km", "Covered = 22.5 km", "Speed = 97.5/1.5 = 65"], "Remaining distance ÷ remaining time", "Weights are the times.")

    v = Fr(30, Fr(3, 2) + Fr(1, 2) + Fr(3, 2))
    q("avgspd", "L3", "o", "A cyclist rides 12 km at 8 km/h, rests for 30 minutes, then rides 18 km at 12 km/h. His average speed for the whole journey, including the rest, is:",
      kmh(D(v)), [(kmh(10), "rest excluded"), (kmh(D(Fr(20, 3))), "mean of 8, 0 and 12"), (kmh(D(Fr(30, Fr(33, 10)))), "30 min taken as 0.3 h")],
      ["Riding times 1.5 h + 1.5 h; rest 0.5 h", "Average = 30/3.5 = 8.57"], "Include stoppage time", "Rest adds time, not distance.")

    t = Fr(20) * 3
    q("avgspd", "L3", "o", "Running at 3/4 of its usual speed, a train reaches 20 minutes late. Its usual journey time is:",
      "1 h", [("1 h 20 min", "late-running time reported"), ("45 min", "usual time × 3/4"), ("15 min", "20 × 3/4")],
      ["Time becomes 4/3 of usual", "Extra = 1/3 of usual = 20 min ⇒ usual = 60 min"], "Time ∝ 1/speed", "Extra time is 1/3 of usual time.")
    assert t == 60

    d = Fr(12, 60) * 30
    q("avgspd", "L3", "o", "Walking at 5 km/h a man misses his train by 7 minutes; walking at 6 km/h he reaches 5 minutes early. The distance to the station is:",
      f"{N(d)} km", [("1 km", "time gap taken as 2 min (7 − 5)"), (f"{N(Fr(12, 100) * 30)} km", "12 min taken as 0.12 h"), ("12 km", "minutes read as km")],
      ["d/5 − d/6 = 12/60", "d/30 = 1/5 ⇒ d = 6 km"], "Time gap = late + early", "Minutes late and early add up.")

    v = Fr(4) / (Fr(1, 20) + Fr(1, 30) + Fr(1, 60) + Fr(1, 60))
    q("avgspd", "L3", "o", "A courier covers four equal legs of a route at 20, 30, 60 and 60 km/h. The average speed for the route is:",
      kmh(D(v)), [(kmh(Fr(85, 2)), "arithmetic mean"), (kmh(30), "repeated 60 km/h leg counted once"), (kmh(40), "rough midpoint")],
      ["Time per unit leg: 1/20 + 1/30 + 1/60 + 1/60 = 7/60", "Average = 4 ÷ 7/60 = 34.29"], "Equal distances: n ÷ Σ(1/v)", "Every leg counts.")

    k = Fr(48 * 7, 24)
    q("avgspd", "L3", "o", "An athlete's speeds over the two halves of a run are in the ratio 3 : 4, and his average speed for the whole run is 48 km/h. His speed in the first half is:",
      kmh(3 * k), [(kmh(D(Fr(48 * 3 * 2, 7))), "arithmetic-mean relation used"), (kmh(4 * k), "second-half speed"), (kmh(36), "48 × 3/4")],
      ["Speeds 3k, 4k; harmonic mean = 24k/7 = 48", "k = 14 ⇒ first half 42 km/h"], "Equal halves by distance ⇒ harmonic mean", "Harmonic mean, not arithmetic.")

    # ===================== Relative speed and meeting =====================
    q("rel", "L1", "f", "Two walkers 60 km apart start towards each other at 7 km/h and 5 km/h. They meet after:",
      "5 h", [("30 h", "speeds subtracted"), ("8.57 h", "only the faster speed used"), ("12 h", "only the slower speed used")],
      ["Closing speed = 12 km/h", "Time = 60/12 = 5 h"], "Opposite directions: add speeds", "Towards each other ⇒ sum.")

    q("rel", "L1", "f", "A thief running at 8 km/h is 300 m ahead of a policeman running at 10 km/h in the same direction. The policeman catches him in:",
      "9 min", [("1 min", "speeds added"), ("1.8 min", "policeman's speed alone used"), ("2.25 min", "thief's speed alone used")],
      ["Relative speed = 2 km/h = 2,000/60 m/min", "Time = 300 ÷ (100/3) = 9 min"], "Same direction: subtract speeds", "Chasing ⇒ difference.")

    q("rel", "L2", "f", "Two cars start from the same point in opposite directions at 45 km/h and 55 km/h. Their distance apart after 2.5 hours is:",
      "250 km", [("25 km", "speeds subtracted"), ("137.5 km", "faster car's distance"), ("100 km", "one hour's separation")],
      ["Separation speed = 100 km/h", "Distance = 250 km"], "Opposite ⇒ add", "Use 2.5 h.")

    q("rel", "L2", "f", "A and B start at the same time from P and Q, 300 km apart, towards each other at 40 km/h and 60 km/h. They meet at a distance from P of:",
      "120 km", [("180 km", "distance from Q"), ("150 km", "midpoint assumed"), ("3 km", "time read as distance")],
      ["Time = 300/100 = 3 h", "A covers 40 × 3 = 120 km"], "Distances ∝ speeds", "Split 300 in 40 : 60.")

    q("rel", "L2", "f", "Two cyclists ride from the same point in the same direction at 15 km/h and 12 km/h. After how long will they be 9 km apart?",
      "3 h", [("20 min", "speeds added then inverted"), ("9 h", "relative speed taken as 1"), ("36 min", "9/15 h")],
      ["Relative speed = 3 km/h", "Time = 9/3 = 3 h"], "Same direction: subtract", "Gap grows at the difference.")

    q("rel", "L3", "o", "Two trains start at the same time from A and B towards each other. After meeting, they take 9 h and 16 h to reach B and A respectively. The ratio of their speeds (train from A : train from B) is:",
      "4:3", [("9:16", "times used directly"), ("16:9", "times inverted without roots"), ("3:4", "square roots inverted")],
      ["S₁ : S₂ = √t₂ : √t₁", "= √16 : √9 = 4 : 3"], "Speed ratio = √(t₂/t₁)", "Take square roots.")

    t = Fr(80, 20)
    q("rel", "L3", "o", "A leaves X at 8:00 am at 40 km/h. B leaves X at 10:00 am on the same road at 60 km/h. B overtakes A at:",
      hm_time(10 + t), [(hm_time(8 + t), "4 h counted from 8 am"), (hm_time(10 + Fr(80, 100)), "speeds added"), (hm_time(12 + Fr(80, 60)), "80 km ÷ 60 counted from noon")],
      ["Head start = 2 × 40 = 80 km", "Gain rate = 20 km/h ⇒ 4 h", "10 am + 4 h = 2 pm"], "Head start ÷ relative speed", "Count from B's start.")

    dist = Fr(45, 100) / 9 * 12
    q("rel", "L3", "o", "Two people 450 m apart walk towards each other at 4 km/h and 5 km/h. A dog runs to and fro between them at 12 km/h until they meet. The total distance the dog runs is:",
      f"{N(dist * 1000)} m", [(f"{N(Fr(45, 100) / 5 * 12 * 1000)} m", "time taken from one walker alone"), ("450 m", "initial gap reported"),
                              (f"{N(Fr(45, 100) / Fr(9, 2) * 12 * 1000)} m", "average walking speed used")],
      ["Meeting time = 0.45/9 h = 0.05 h", "Dog: 12 × 0.05 = 0.6 km = 600 m"], "Distance = speed × meeting time", "Only the time matters.")

    t = Fr(240 + 45 * Fr(1, 3), 75)
    q("rel", "L3", "o", "Two buses start at 9:00 am from towns 240 km apart and drive towards each other at 45 km/h and 30 km/h. The faster bus halts for 20 minutes on the way. They meet at:",
      hm_time(9 + t), [(hm_time(9 + Fr(240, 75)), "halt ignored"), (hm_time(9 + Fr(240, 75) + Fr(1, 3)), "full halt added to meeting time"),
                        (hm_time(9 + Fr(240 + 30 * Fr(1, 3), 75)), "halt charged to the slower bus")],
      ["45(t − 1/3) + 30t = 240", "75t = 255 ⇒ t = 3.4 h", "9:00 + 3 h 24 min = 12:24 pm"], "Moving time differs by the halt", "During the halt only one bus closes the gap.")

    t = 2 + Fr(40, 100)
    q("rel", "L3", "o", "A car and a motorbike leave the same point in the same direction at 60 km/h and 40 km/h. After 2 hours the car turns back. It meets the bike after a total time from the start of:",
      hmin(t), [("4 h", "relative speed 20 used after turning"), (hmin(2 + Fr(120, 100)), "car's distance used as gap"), (hmin(2 + Fr(40, 60)), "gap ÷ car speed")],
      ["Gap after 2 h = 40 km", "Closing speed = 100 km/h ⇒ 0.4 h", "Total = 2 h 24 min"], "After turning: add speeds", "They now approach each other.")

    d = 50 + Fr(150, 120) * 50
    q("rel", "L3", "o", "A leaves Delhi at 6:00 am for Agra, 200 km away, at 50 km/h. B leaves Agra at 7:00 am for Delhi at 70 km/h. They meet at a distance from Delhi of:",
      f"{N(d)} km", [(f"{N(Fr(200 * 50, 120))} km", "simultaneous start assumed"), (f"{N(200 - d)} km", "distance from Agra"), (f"{N(Fr(150, 120) * 50)} km", "A's first-hour lead left out")],
      ["By 7 am A has done 50 km; gap 150 km", "Meet after 150/120 = 1.25 h", "A: 50 + 62.5 = 112.5 km"], "Handle head start first", "Add A's first hour.")

    q("rel", "L3", "o", "Two people start from P and Q towards each other. They first meet 60 km from P. After reaching the far ends they turn back and meet again 40 km from Q. The distance PQ is:",
      "140 km", [("100 km", "60 + 40"), ("220 km", "3 × 60 + 40"), ("180 km", "3 × 60")],
      ["By the second meeting they cover 3 × PQ together", "The P-starter covers 3 × 60 = 180 = PQ + 40", "PQ = 140 km"], "Second meeting ⇒ 3× combined distance", "Each covers three times his first stretch.")

    q("rel", "L2", "o", "A is twice as fast as B, and B is thrice as fast as C. If C covers a distance in 54 minutes, A covers it in:",
      "9 min", [("27 min", "only B's factor used"), ("18 min", "only the ×3 factor used"), ("6 min", "factors squared")],
      ["A = 2 × 3 = 6 times C", "Time = 54/6 = 9 min"], "Time ∝ 1/speed", "Combine the factors.")

    # ===================== Races and circular tracks =====================
    q("race", "L1", "f", "In a 1 km race, A beats B by 100 m. The ratio of their speeds A : B is:",
      "10:9", [("9:10", "ratio inverted"), ("11:10", "margin added to A"), ("10:1", "margin as B's distance")],
      ["When A runs 1,000 m, B runs 900 m", "A : B = 10 : 9"], "Speed ratio = distance ratio in equal time", "B covers 900 m.")

    q("race", "L1", "f", "Two runners start together on a 400 m circular track at 5 m/s and 3 m/s in the same direction. They first meet after:",
      "200 s", [("50 s", "opposite directions assumed"), ("80 s", "400/5"), ("133.33 s", "400/3")],
      ["Relative speed = 2 m/s", "Time = 400/2 = 200 s"], "Same direction: track ÷ difference", "The faster must gain a full lap.")

    q("race", "L2", "f", "In a 200 m race A beats B by 20 m. B takes 40 s to finish. A's time is:",
      "36 s", [("40 s", "B's time"), ("44 s", "margin added"), ("32 s", "margin counted twice")],
      ["B's speed = 5 m/s", "When A finishes, B has run 180 m ⇒ 36 s"], "A's time = time for B to run 180 m", "Use B's speed.")

    q("race", "L2", "f", "Two runners start from the same point on a 600 m circular track in opposite directions at 4 m/s and 6 m/s. They first meet after:",
      "60 s", [("300 s", "same direction assumed"), ("150 s", "600/4"), ("100 s", "600/6")],
      ["Closing speed = 10 m/s", "Time = 60 s"], "Opposite: track ÷ sum", "Together they cover one lap.")

    q("race", "L2", "f", "A runs 100 m in 20 s and beats B by 5 s. By how many metres does A beat B?",
      "20 m", [("25 m", "5 s at A's speed"), ("5 m", "seconds read as metres"), ("16 m", "5 s at a mix of speeds")],
      ["B takes 25 s ⇒ 4 m/s", "In 20 s B covers 80 m", "Margin = 20 m"], "Margin in metres = loser's speed × time margin", "Use B's speed, not A's.")

    c = 900 * Fr(95, 100)
    q("race", "L3", "o", "In a 1,000 m race, A beats B by 50 m and B beats C by 100 m. By how much does A beat C?",
      f"{N(1000 - c)} m", [("150 m", "margins added"), ("140 m", "B's margin scaled by 0.9"), ("100 m", "only the B–C margin reported")],
      ["When B runs 1,000, C runs 900", "When B runs 950, C runs 900 × 0.95 = 855", "A beats C by 145 m"], "Chain the ratios", "B runs only 950 m when A finishes.")

    laps = [Fr(12, 10) / v * 60 for v in (3, Fr(9, 2), 6)]
    L = lcm(*[int(x) for x in laps])
    q("race", "L3", "o", "Three walkers start together from the same point on a 1.2 km circular track at 3, 4.5 and 6 km/h in the same direction. They will next be together at the starting point after:",
      f"{L} min", [(f"{int(laps[0])} min", "slowest lap time"), (f"{int(laps[2])} min", "fastest lap time"), (f"{int(laps[0]) * 3} min", "slowest lap × number of walkers")],
      ["Lap times: 24, 16 and 12 min", "LCM = 48 min"], "Together at start ⇒ LCM of lap times", "Not the relative-speed meeting time.")

    q("race", "L3", "o", "A and B run on a circular track in the same direction with speeds in the ratio 3 : 2. At how many distinct points on the track do they meet?",
      "1", [("5", "opposite-direction count (3 + 2)"), ("2", "slower speed term"), ("3", "faster speed term")],
      ["Same direction: distinct points = a − b (ratio in lowest terms)", "3 − 2 = 1"], "Same: a − b; opposite: a + b", "Direction changes the count.", kind="conceptual")

    q("race", "L3", "o", "A and B run in opposite directions on a 1.5 km circular track at 18 km/h and 12 km/h, starting together. Not counting the start but counting the meeting at the starting point, how many times will they have met by the time they are first together again at the starting point?",
      "5", [("4", "final meeting at start excluded"), ("1", "difference of ratio terms"), ("3", "faster ratio term")],
      ["Meet every 1.5/30 h = 3 min", "At start together: LCM(5, 7.5) = 15 min", "15/3 = 5 meetings"], "Meetings = LCM ÷ meeting interval", "Speed ratio 3 : 2 ⇒ 5 points.")

    q("race", "L3", "o", "In a 400 m race, A beats B by 40 m or 8 s. A's time for the race is:",
      "72 s", [("80 s", "B's time"), ("88 s", "8 s added to B"), ("50 s", "400/8")],
      ["B's speed = 40/8 = 5 m/s ⇒ B's time 80 s", "A's time = 80 − 8 = 72 s"], "Margin distance ÷ margin time = loser's speed", "Subtract the 8 s from B's time.")

    cB = Fr(336, 360) * 400
    q("race", "L3", "o", "In a 400 m race, A can give B a start of 40 m and C a start of 64 m. How many metres' start can B give C in a 400 m race?",
      f"{N(400 - cB)} m", [("24 m", "starts subtracted"), (f"{N(24 * Fr(360, 400))} m", "difference scaled down"), ("30 m", "difference scaled by 400/320")],
      ["B runs 360 while C runs 336", "In 400 m: C runs 400 × 336/360 = 373 1/3", "Start = 26 2/3 m"], "Scale to B's 400 m", "Starts are not additive.")

    q("race", "L3", "o", "A dog chasing a hare takes 5 leaps for every 6 leaps of the hare, but 4 of the dog's leaps equal 5 of the hare's. The ratio of the dog's speed to the hare's is:",
      ratio(5 * Fr(5, 4), 6), [("5:6", "leap counts only"), ("24:25", "ratio inverted"), ("4:5", "leap lengths only")],
      ["Dog leap = 5/4 hare leap", "Dog speed = 5 × 5/4 = 25/4; hare = 6", "25 : 24"], "Speed = leaps × leap length", "Combine rate and length.")

    Lc = Fr(80 * 5, 2)
    q("race", "L3", "o", "A runs 1 2/3 times as fast as B. If A gives B a start of 80 m, how long should the race be so that they finish together?",
      f"{N(Lc)} m", [(f"{N(Fr(400, 3))} m", "80 × 5/3"), ("120 m", "80 × 3/2"), ("240 m", "80 × 3")],
      ["A : B = 5 : 3", "L/(L − 80) = 5/3 ⇒ 2L = 400 ⇒ L = 200"], "Equal times ⇒ distances ∝ speeds", "The start equals 2/5 of the course.")

    laps = [Fr(24, 10) / v * 60 for v in (20, 32)]
    Lm = 36
    assert Lm % laps[0] == 0 and Lm % laps[1] == 0 and all(Lm > 0 for _ in laps)
    q("race", "L3", "o", "Two cyclists start together on a 2.4 km circular track in the same direction at 20 km/h and 32 km/h. When will they first be together again at the starting point?",
      f"{Lm} min", [("12 min", "first meeting anywhere"), (f"{N(laps[0] * laps[1])} min", "product of lap times"), ("72 min", "LCM doubled")],
      ["Lap times: 7.2 min and 4.5 min", "LCM = 36 min"], "At start ⇒ LCM of lap times", "Meeting anywhere happens every 12 min.")

    q("race", "L3", "o", "In a game of 100 points, A can give B 20 points and C 28 points. How many points can B give C in a game of 100?",
      "10", [("8", "points subtracted"), ("7.2", "difference scaled down by 0.9"), ("12", "difference scaled by 1.5")],
      ["B scores 80 while C scores 72", "In 100: C scores 90 ⇒ B gives 10"], "Scale to B's 100", "Not simple subtraction.")

    # ===================== Trains =====================
    q("trn", "L1", "f", "A 240 m train running at 72 km/h passes a pole in:",
      "12 s", [("3.33 s", "km/h not converted"), ("20 s", "72 km/h taken as 12 m/s"), ("43.2 s", "multiplied instead of divided")],
      ["72 km/h = 20 m/s", "Time = 240/20 = 12 s"], "Time = length ÷ speed", "Convert with 5/18.")

    q("trn", "L1", "f", "A 180 m train at 54 km/h crosses a 270 m platform in:",
      "30 s", [("12 s", "platform ignored"), ("18 s", "train length ignored"), ("8.33 s", "km/h not converted")],
      ["54 km/h = 15 m/s", "(180 + 270)/15 = 30 s"], "Distance = train + platform", "Add both lengths.")

    v = Fr(200, 12) * Fr(18, 5) + 6
    q("trn", "L2", "f", "A 200 m train passes a man walking at 6 km/h in the same direction in 12 seconds. The train's speed is:",
      kmh(v), [(kmh(v - 6), "relative speed reported"), (kmh(v - 12), "man's speed subtracted"), (kmh(v + 6), "man's speed added twice")],
      ["Relative speed = 200/12 m/s = 60 km/h", "Train = 60 + 6 = 66 km/h"], "Same direction: relative = train − man", "Add back the man's speed.")

    q("trn", "L2", "f", "Trains of 150 m and 200 m run on parallel tracks in opposite directions at 50 km/h and 76 km/h. They cross each other in:",
      "10 s", [(f"{D(Fr(350, Fr(26 * 5, 18)))} s", "same direction assumed"), (f"{D(Fr(200, 35))} s", "only the longer train's length"),
               (f"{D(Fr(150, 35))} s", "only the shorter train's length")],
      ["Relative speed = 126 km/h = 35 m/s", "Time = 350/35 = 10 s"], "Opposite: add speeds; add lengths", "Both lengths must pass.")

    L = 20 * 15
    q("trn", "L2", "f", "A train passes a pole in 15 s and a 100 m platform in 20 s. Its length is:",
      f"{L} m", [("100 m", "platform length"), ("400 m", "train + platform"), ("75 m", "100 × 15/20")],
      ["Extra 5 s covers 100 m ⇒ speed 20 m/s", "Length = 20 × 15 = 300 m"], "Speed from the difference", "The extra time is for the platform.")

    v = next(v for v in range(5, 100) if 9 * (v - 2) == 10 * (v - 4))
    L = Fr((v - 2) * 5, 18) * 9
    q("trn", "L3", "o", "A train overtakes two walkers going in its direction at 2 km/h and 4 km/h in 9 s and 10 s respectively. The train's length is:",
      f"{N(L)} m", [(f"{N(Fr(v * 5, 18) * 9)} m", "walker's speed not subtracted"), (f"{D(Fr(v * 5, 18) * 10)} m", "train speed × 10 s"), ("20 m", "relative speed read as length")],
      ["(v − 2) × 9 = (v − 4) × 10 ⇒ v = 22 km/h", "L = 20 × 5/18 × 9 = 50 m"], "Same length both times", "Use relative speeds.")

    L2 = Fr(10 * 5, 18) * 36
    q("trn", "L3", "o", "Two trains of equal length run on parallel tracks in the same direction at 46 km/h and 36 km/h. The faster passes the slower in 36 s. The length of each train is:",
      f"{N(L2 / 2)} m", [(f"{N(L2)} m", "combined length"), (f"{N(Fr(82 * 5, 18) * 36 / 2)} m", "opposite directions assumed"), (f"{N(L2 / 4)} m", "halved twice")],
      ["Relative = 10 km/h = 25/9 m/s", "Distance = 25/9 × 36 = 100 m = 2L", "L = 50 m"], "Same direction: subtract", "Distance is both lengths.")

    rel = Fr(300, 30)
    v = rel + Fr(9 * 5, 18)
    q("trn", "L3", "o", "A 300 m train overtakes a man running at 9 km/h in the same direction in 30 s. How long will it take to cross a 450 m platform?",
      f"{N(Fr(750) / v)} s", [(f"{N(Fr(750) / rel)} s", "man's speed not added back"), (f"{N(Fr(450) / v)} s", "train length omitted"), (f"{N(Fr(750) / Fr(15, 2))} s", "man's speed subtracted instead")],
      ["Relative = 10 m/s; man = 2.5 m/s ⇒ train 12.5 m/s", "Time = 750/12.5 = 60 s"], "Recover true speed", "Relative speed was reduced by the man.")

    v = Fr(100, 5)
    q("trn", "L3", "o", "A train crosses a 150 m platform in 15 s and a 250 m platform in 20 s. Its speed is:",
      kmh(v * Fr(18, 5)), [(kmh(v), "m/s written as km/h"), (kmh(Fr(100, 20) * Fr(18, 5)), "100 m divided by 20 s"), (kmh(D(Fr(400, 35) * Fr(18, 5))), "platforms and times added")],
      ["Extra 100 m in 5 s ⇒ 20 m/s", "= 72 km/h"], "Speed = Δplatform ÷ Δtime", "Convert m/s to km/h.")

    q("trn", "L3", "o", "A 250 m train running at 45 km/h crosses a bridge in 44 s. The bridge is:",
      f"{N(Fr(45 * 5, 18) * 44 - 250)} m long", [(f"{N(Fr(45 * 5, 18) * 44)} m long", "train length not subtracted"), ("1,980 m long", "km/h not converted"),
                                                 (f"{N(Fr(45 * 5, 18) * 44 + 250)} m long", "train length added")],
      ["45 km/h = 12.5 m/s", "Distance = 550 m = 250 + bridge ⇒ bridge 300 m"], "Distance = train + bridge", "Subtract the train.")

    q("trn", "L3", "o", "A 180 m train at 72 km/h crosses a train coming from the opposite direction at 54 km/h in 12 s. The other train's length is:",
      f"{N(35 * 12 - 180)} m", [(f"{35 * 12} m", "combined length reported"), (f"{20 * 12 - 180} m", "only first train's speed used"), (f"{126 * 12 - 180} m", "km/h not converted")],
      ["Relative = 126 km/h = 35 m/s", "Combined = 420 m ⇒ other = 240 m"], "Opposite: add speeds", "Subtract the known length.")

    rel = Fr(500, 50) * Fr(18, 5)
    q("trn", "L3", "o", "Train A (200 m, 90 km/h) overtakes train B (300 m) running in the same direction in 50 s. The speed of B is:",
      kmh(90 - rel), [(kmh(rel), "relative speed reported"), (kmh(90 + rel), "opposite directions assumed"), (kmh(90 - Fr(200, 50) * Fr(18, 5)), "only A's length used")],
      ["Relative = 500/50 = 10 m/s = 36 km/h", "B = 90 − 36 = 54 km/h"], "Same direction: subtract", "Both lengths pass.")

    L = 15 * 20
    q("trn", "L3", "o", "A train running at 54 km/h passes a platform in 36 s and a man standing on it in 20 s. The platform's length is:",
      f"{15 * 36 - L} m", [(f"{L} m", "train length reported"), (f"{15 * 36} m", "train + platform reported"), (f"{15 * 36 + L} m", "train length added")],
      ["54 km/h = 15 m/s", "Train = 300 m; train + platform = 540 m", "Platform = 240 m"], "Subtract the two distances", "Man-crossing gives train length.")

    # ===================== Boats and streams =====================
    q("boat", "L1", "f", "A boat's downstream speed is 18 km/h and upstream speed is 12 km/h. The speed of the stream is:",
      kmh(3), [(kmh(6), "difference not halved"), (kmh(15), "boat's speed"), (kmh(Fr(3, 2)), "halved twice")],
      ["Stream = (18 − 12)/2 = 3"], "Stream = (D − U)/2", "Halve the difference.")

    q("boat", "L1", "f", "A boat moves at 10 km/h in still water; the stream flows at 2 km/h. The time to go 36 km downstream is:",
      "3 h", [("4.5 h", "upstream speed used"), ("3.6 h", "still-water speed used"), ("18 h", "stream speed used")],
      ["Downstream = 12 km/h", "36/12 = 3 h"], "Downstream = b + s", "Add the stream.")

    u, dn = Fr(24, 6), Fr(20, 2)
    q("boat", "L2", "f", "A boat goes 24 km upstream in 6 hours and 20 km downstream in 2 hours. Its speed in still water is:",
      kmh((u + dn) / 2), [(kmh((dn - u) / 2), "stream speed"), (kmh(u + dn), "not halved"), (kmh(Fr(44, 8)), "total distance ÷ total time")],
      ["Up = 4, down = 10", "Boat = (4 + 10)/2 = 7"], "Boat = (D + U)/2", "Averaging distance/time mixes legs.")

    q("boat", "L2", "f", "A boat moves at 9 km/h in still water; the stream flows at 3 km/h. The time to go 24 km downstream and return is:",
      "6 h", [(f"{N(Fr(48, 9))} h", "still-water speed for both legs"), ("4 h", "upstream leg only"), ("2 h", "downstream leg only")],
      ["Down: 24/12 = 2 h; up: 24/6 = 4 h", "Total 6 h"], "Time = d/(b + s) + d/(b − s)", "Legs take unequal times.")

    s = next(s for s in range(1, 6) if 6 + s == 2 * (6 - s))
    q("boat", "L2", "f", "A man rows at 6 km/h in still water. Rowing upstream takes him twice as long as rowing the same distance downstream. The stream's speed is:",
      kmh(s), [(kmh(3), "half the still-water speed"), (kmh(4), "downstream-upstream gap"), (kmh(Fr(3, 2)), "quarter of rowing speed")],
      ["6 + s = 2(6 − s)", "s = 2"], "Time ratio ⇒ speed ratio (inverse)", "Downstream speed is twice upstream speed.")

    d, u = Fr(48, 8), Fr(32, 8)
    t = 30 / d + 30 / u
    q("boat", "L3", "o", "A man rows 48 km downstream in 8 hours and 32 km upstream in 8 hours. How long will he take to row 30 km downstream and back?",
      f"{N(t)} h", [(f"{N(Fr(60, 5))} h", "still-water speed for both ways"), (f"{N(Fr(60, 4))} h", "upstream speed both ways"), (f"{N(Fr(60, 6))} h", "downstream speed both ways")],
      ["Down 6, up 4 km/h", "30/6 + 30/4 = 5 + 7.5 = 12.5 h"], "Separate legs", "Never use the still-water speed for a trip in a stream.")

    s = next(s for s in range(1, 15) if Fr(30, 15 + s) + Fr(30, 15 - s) == Fr(9, 2))
    q("boat", "L3", "o", "A boat with still-water speed 15 km/h goes 30 km downstream and returns in 4.5 hours in all. The speed of the stream is:",
      kmh(s), [(kmh(D(15 - Fr(60, Fr(9, 2)))), "average speed subtracted from 15"), (kmh(Fr(5, 2)), "half the answer"), (kmh(10), "upstream speed")],
      ["30/(15 + s) + 30/(15 − s) = 4.5", "900/(225 − s²) = 4.5 ⇒ s² = 25 ⇒ s = 5"], "Round-trip equation", "Average speed is not boat − stream.")

    q("boat", "L3", "o", "A swimmer takes three times as long to swim a stretch upstream as downstream. The ratio of his still-water speed to the stream's speed is:",
      "2:1", [("3:1", "time ratio reported"), ("1:2", "ratio inverted"), ("4:1", "speed sum used")],
      ["(b + s)/(b − s) = 3", "b = 2s ⇒ 2 : 1"], "Speed ratio = inverse time ratio", "Solve with componendo.")

    uu, dd = 5, 11
    assert 20 / uu + 44 / dd == 8 and 30 / uu + 55 / dd == 11
    q("boat", "L3", "o", "A boat covers 20 km upstream and 44 km downstream in 8 hours; it covers 30 km upstream and 55 km downstream in 11 hours. Its speed in still water is:",
      kmh(Fr(uu + dd, 2)), [(kmh(Fr(dd - uu, 2)), "stream speed"), (kmh(uu + dd), "not halved"), (kmh(uu), "upstream speed")],
      ["Let 1/U = a, 1/D = b: 20a + 44b = 8, 30a + 55b = 11", "a = 1/5, b = 1/11 ⇒ U = 5, D = 11", "Boat = 8"], "Solve for 1/U and 1/D", "Treat reciprocals as unknowns.")

    b = next(b for b in range(3, 30) if Fr(b + 2, b - 2) == Fr(3, 2))
    q("boat", "L3", "o", "A river flows at 2 km/h. A boat takes 50% more time upstream than downstream over the same distance. The boat's still-water speed is:",
      kmh(b), [(kmh(8), "arithmetic slip in (b + 2)/(b − 2)"), (kmh(6), "time ratio applied to stream"), (kmh(12), "downstream speed")],
      ["(b + 2)/(b − 2) = 1.5", "b + 2 = 1.5b − 3 ⇒ b = 10"], "Speed ratio = inverse time ratio", "50% more time ⇒ ratio 3 : 2.")

    k = next(k for k in range(1, 10) if Fr(30, 5 * k) + Fr(30, 3 * k) == 16)
    q("boat", "L3", "o", "A man rows 5 km downstream in the time he rows 3 km upstream. He rows 30 km downstream and back in 16 hours. The speed of the stream is:",
      kmh((5 * k - 3 * k) / 2), [(kmh(2), "difference not halved"), (kmh(4), "still-water speed"), (kmh(3), "upstream ratio term read as speed")],
      ["D : U = 5 : 3 ⇒ D = 5k, U = 3k", "30/5k + 30/3k = 16 ⇒ 16/k = 16 ⇒ k = 1", "Stream = (5 − 3)/2 = 1"], "Use the ratio then the total time", "Halve the difference.")

    dd = Fr(19) / (Fr(1, 18) + Fr(1, 20))
    q("boat", "L3", "o", "A boat's still-water speed is 14 km/h and the stream flows at 4 km/h. It takes 19 hours to go downstream from A to B and come back to C, midway between A and B. The distance AB is:",
      f"{N(dd)} km", [(f"{N(dd / 2)} km", "AC reported"), (f"{D(Fr(19) / (Fr(1, 18) + Fr(1, 10)))} km", "full distance used for the return"), (f"{N(2 * dd)} km", "doubled")],
      ["Down 18, up 10 km/h", "d/18 + (d/2)/10 = 19 ⇒ d(1/18 + 1/20) = 19", "d = 180 km"], "Return is only half-way", "Upstream leg is d/2.")

    dist = Fr(5, 6) / (Fr(1, 9) + Fr(1, 6))
    q("boat", "L3", "o", "A man rows at 7.5 km/h in still water. In a stream of 1.5 km/h he takes 50 minutes to row to a place and back. The distance to the place is:",
      f"{N(dist)} km", [(f"{N(2 * dist)} km", "round-trip distance"), (f"{N(Fr(15, 2) * Fr(5, 12))} km", "still-water speed for half the time"), ("2.5 km", "rough split")],
      ["Down 9, up 6 km/h", "d/9 + d/6 = 5/6 ⇒ 5d/18 = 5/6 ⇒ d = 3"], "Round-trip time equation", "Convert 50 min to 5/6 h.")
