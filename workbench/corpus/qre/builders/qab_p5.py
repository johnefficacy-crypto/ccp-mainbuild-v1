"""QRE-QA-B part 5: Geometry and Mensuration. Keys and distractors computed below; π = 22/7 where stated."""
from qab_common import *

PI = F(22, 7)
dg = lambda v: n(v) + "°"


def G(B, M, items, formula, trap, kind="numerical"):
    """items: (tier, level, stem, key, cands, steps, unit[, formula, trap])."""
    for it in items:
        tier, lv, stem, key, cands, steps, unit = it[:7]
        fm, tp = (it[7], it[8]) if len(it) == 9 else (formula, trap)
        fmt = dg if unit == "°" else n
        q(B, M, lv, tier, stem, key, cands, steps, fm, tp, fmt=fmt, unit="" if unit == "°" else unit, kind=kind)


def sq(c, r=3, unit=""):
    """c√r with unit."""
    return f"{n(c)}√{r}{unit}"


# =====================================================================
def area_perimeter(B):
    M = "qa-area-and-perimeter-rectangle-square-triangle-e23db61d"
    # O-level computations
    b = F(88, 2) / F(22, 10)
    assert (b, b * F(6, 5)) == (20, 24)
    s = F(13 + 14 + 15, 2)
    heron = math.isqrt(int(s * (s - 13) * (s - 14) * (s - 15)))
    assert heron == 84
    lb = F(23 ** 2 - 17 ** 2, 2)
    assert lb == 120
    path_out = (40 + 5) * (30 + 5) - 40 * 30
    path_in = 40 * 30 - (40 - 5) * (30 - 5)
    path_once = F(85, 2) * F(65, 2) - 1200
    path_nocorner = 2 * F(5, 2) * (40 + 30)
    h = math.isqrt(10 ** 2 - 6 ** 2)
    hcf = math.gcd(750, 480)
    items = [
        ("foundation", "L1", "The perimeter of a rectangle measuring 18 m by 12 m is:", 2 * (18 + 12),
         [(18 * 12, "computed the area"), (18 + 12, "did not double (semi-perimeter)"), (2 * 18 + 12, "doubled only the length")],
         ["P = 2(l + b) = 2(18 + 12) = 60 m"], " m"),
        ("foundation", "L1", "The diagonal of a square is 12√2 cm. Its area is:", 144,
         [(288, "used d² instead of d²/2"), (72, "used d²/4"), (48, "computed the perimeter")],
         ["Side = d/√2 = 12 cm", "Area = 12² = 144 cm² (or d²/2 = 288/2)"], " cm²"),
        ("foundation", "L1", "A triangle has base 16 cm and height 9 cm. Its area is:", 72,
         [(144, "forgot the factor ½"), (25, "added base and height"), (36, "used ¼ instead of ½")],
         ["Area = ½ × 16 × 9 = 72 cm²"], " cm²"),
        ("foundation", "L2", "The area of an equilateral triangle of side 8√3 cm is:", sq(48, 3, " cm²"),
         [(sq(192, 3, " cm²"), "omitted the ÷ 4"), (sq(96, 3, " cm²"), "used √3/2 instead of √3/4"), ("48 cm²", "dropped the √3")],
         ["Area = (√3/4) a² = (√3/4) × 192 = 48√3 cm²"], ""),
        ("foundation", "L2", "The length of a rectangle is 20% more than its breadth and its perimeter is 88 cm. Its area is:", 480,
         [(1920, "took 88 as the semi-perimeter"), (484, "assumed a square of the same perimeter"), (400, "took the breadth as both sides")],
         ["2(1.2b + b) = 88 ⇒ 4.4b = 88 ⇒ b = 20, l = 24", "Area = 24 × 20 = 480 cm²"], " cm²"),
        ("officer", "L2", "The legs of a right triangle are in the ratio 3 : 4 and its hypotenuse is 25 cm. Its area is:", 150,
         [(300, "forgot the factor ½"), (F(25 * 15, 2), "used the hypotenuse as a leg"), (96, "took the hypotenuse as 20 (legs 12 and 16)")],
         ["Legs 3k, 4k; 5k = 25 ⇒ k = 5 ⇒ legs 15, 20", "Area = ½ × 15 × 20 = 150 cm²"], " cm²"),
        ("officer", "L3", "The length of a rectangle is increased by 30% and its breadth is decreased by 20%. The area:",
         "increases by 4%",
         [("increases by 10%", "added the percentages (30 − 20)"), ("decreases by 4%", "took the sign of the product term wrongly"),
          ("increases by 16%", "added the product term instead of subtracting it")],
         ["New area factor = 1.3 × 0.8 = 1.04", "Net change = 30 − 20 − (30 × 20)/100 = +4%"], "",
         "Net % = a + b + ab/100 (with signs)", "Successive percentage changes multiply."),
        ("officer", "L3", "A path 2.5 m wide runs around the outside of a 40 m × 30 m garden. At ₹12 per m², the cost of paving the path is:",
         R(path_out * 12),
         [(R(path_in * 12), "treated the path as inside the garden"), (R(path_once * 12), "added the width only once to each dimension"),
          (R(path_nocorner * 12), "omitted the four corner squares")],
         ["Outer rectangle = 45 × 35 = 1,575 m²", "Path = 1,575 − 1,200 = 375 m²", "Cost = 375 × 12 = ₹4,500"], "",
         "Path area = outer area − inner area", "A path on both sides adds twice the width to each dimension."),
        ("officer", "L3", "A triangle has sides 13 cm, 14 cm and 15 cm. The altitude on the 14 cm side is:", F(2 * heron, 14),
         [(heron, "stopped at the area"), (F(heron, 14), "forgot the factor 2"), (F(2 * heron, 15), "used the 15 cm side")],
         ["s = 21; Area = √(21 × 8 × 7 × 6) = 84 cm²", "Altitude = 2 × 84/14 = 12 cm"], " cm",
         "Heron: √(s(s−a)(s−b)(s−c)); h = 2A/base", "Use the side on which the altitude falls."),
        ("officer", "L3", "A square has the same area as a 32 cm × 18 cm rectangle. By how much does the rectangle's perimeter exceed the square's?", 100 - 96,
         [(50 - 48, "compared semi-perimeters"), (50 - 24, "subtracted the square's side from the rectangle's semi-perimeter"), (8, "doubled the difference twice")],
         ["Area = 576 ⇒ square side 24 ⇒ perimeter 96", "Rectangle perimeter = 100", "Difference = 4 cm"], " cm"),
        ("officer", "L3", "An isosceles triangle has equal sides of 10 cm and a base of 12 cm. Its area is:", 12 * h // 2,
         [(60, "used the equal side as the height"), (12 * h, "forgot the factor ½"), (36, "took half the base as the height")],
         ["Height = √(10² − 6²) = 8", "Area = ½ × 12 × 8 = 48 cm²"], " cm²"),
        ("officer", "L3", "An equilateral triangle has the same perimeter as a square of area 81 cm². The area of the triangle is:", sq(36, 3, " cm²"),
         [(sq(F(81, 4), 3, " cm²"), "used the square's side as the triangle's side"), (sq(144, 3, " cm²"), "omitted the ÷ 4"),
          (sq(72, 3, " cm²"), "used √3/2 instead of √3/4")],
         ["Square side 9 ⇒ perimeter 36 ⇒ triangle side 12", "Area = (√3/4) × 144 = 36√3 cm²"], ""),
        ("officer", "L3", "A floor 7.5 m × 4.8 m is to be covered with the largest possible identical square tiles without cutting. The number of tiles needed is:",
         (750 // hcf) * (480 // hcf),
         [((750 // 15) * (480 // 15), "used 15 cm, a common factor that is not the highest"), ((750 // 10) * (480 // 10), "used 10 cm tiles"),
          (2 * (750 + 480) // hcf, "divided the perimeter by the tile side")],
         ["HCF(750, 480) = 30 cm", "Tiles = (750/30) × (480/30) = 25 × 16 = 400"], "",
         "Largest tile side = HCF of dimensions", "Convert to cm before taking the HCF."),
        ("officer", "L3", "A rectangle has a diagonal of 17 cm and a perimeter of 46 cm. Its area is:", lb,
         [(2 * lb, "did not halve (l + b)² − (l² + b²)"), (F(289, 2), "used d²/2 as for a square"), (F(23, 2) ** 2, "assumed a square")],
         ["l + b = 23, l² + b² = 289", "2lb = 529 − 289 = 240 ⇒ lb = 120 cm²"], " cm²",
         "2lb = (l + b)² − (l² + b²)", "The identity gives 2lb, not lb."),
        ("officer", "L3", "The area of an equilateral triangle is 64√3 cm². Its perimeter is:", "48 cm",
         [("16 cm", "gave the side"), ("24 cm", "took a² = 64"), ("24√2 cm", "used √3/2 in the area formula")],
         ["(√3/4)a² = 64√3 ⇒ a² = 256 ⇒ a = 16", "Perimeter = 48 cm"], ""),
    ]
    G(B, M, items, "Area/perimeter formulas for rectangle, square and triangle", "Match the formula to the figure and keep units consistent.")


# =====================================================================
def circles(B):
    M = "qa-circle-area-circumference-and-sectors-e98b662b"
    r_ring_o, r_ring_i = 176 / (2 * PI), 132 / (2 * PI)
    assert (r_ring_o, r_ring_i) == (28, 21)
    ring = PI * (28 ** 2 - 21 ** 2)
    assert ring == 1078
    track = PI * (77 ** 2 - 70 ** 2)
    assert 440 / (2 * PI) == 70 and track == 3234
    items = [
        ("foundation", "L1", "The circumference of a circle of radius 7 cm is (π = 22/7):", 2 * PI * 7,
         [(PI * 49, "computed the area"), (PI * 7, "used πr"), (2 * PI * 14, "used the diameter as radius")],
         ["C = 2πr = 2 × 22/7 × 7 = 44 cm"], " cm"),
        ("foundation", "L1", "The area of a circle of diameter 28 cm is (π = 22/7):", PI * 14 ** 2,
         [(PI * 28 ** 2, "used the diameter as radius"), (PI * 28, "computed the circumference"), (PI * 14 ** 2 * 2, "doubled the area")],
         ["r = 14", "A = 22/7 × 196 = 616 cm²"], " cm²"),
        ("foundation", "L2", "The circumference of a circle is 132 cm. Its area is (π = 22/7):", PI * 21 ** 2,
         [(PI * 42 ** 2, "took 132 as πr (r = 42)"), (PI * 21 ** 2 / 2, "gave a semicircle"), (21 ** 2, "forgot π")],
         ["2πr = 132 ⇒ r = 21", "A = 22/7 × 441 = 1,386 cm²"], " cm²"),
        ("foundation", "L2", "The area of a sector of radius 14 cm and angle 90° is (π = 22/7):", PI * 196 / 4,
         [(PI * 196, "gave the full circle"), (2 * PI * 14 / 4, "gave the arc length"), (PI * 196 / 2, "gave a semicircle")],
         ["Area = (90/360) × 22/7 × 196 = 154 cm²"], " cm²"),
        ("foundation", "L2", "A wheel of diameter 70 cm makes how many revolutions to cover 1.1 km? (π = 22/7)", 110000 / (PI * 70),
         [(110000 / (PI * 35), "used the radius in C = πd"), (110000 / (PI * 140), "treated 70 cm as the radius"), (1100000 / (PI * 70), "converted 1.1 km as 11,000 m")],
         ["Circumference = πd = 220 cm", "1.1 km = 1,10,000 cm", "Revolutions = 1,10,000/220 = 500"], ""),
        ("officer", "L3", "A sector of a circle of radius 21 cm has an arc length of 22 cm. Its area is:", F(22 * 21, 2),
         [(22 * 21, "used r × l instead of ½ r × l"), (F(22 * 21, 4), "halved twice"), (PI * 441 / 2, "gave a semicircle")],
         ["Sector area = ½ × arc × radius", "= ½ × 22 × 21 = 231 cm²"], " cm²", "Sector area = ½ l r", "No need to find the angle."),
        ("officer", "L3", "If the area of a circle increases by 44%, by what percentage does its radius increase?", "20%",
         [("44%", "assumed the same percentage change"), ("22%", "halved the area change"), ("12%", "took √144 as the percentage")],
         ["Area factor 1.44 ⇒ radius factor √1.44 = 1.2", "Increase = 20%"], "", "Area ∝ r²", "Take the square root of the factor, not of the percentage."),
        ("officer", "L3", "The outer and inner circumferences of a circular ring are 176 cm and 132 cm. The area of the ring is (π = 22/7):", ring,
         [(PI * 7 ** 2, "squared the difference of radii"), (4 * ring, "used the diameters as radii"), (2 * ring, "used 2π(R² − r²)")],
         ["R = 176/(2π) = 28, r = 132/(2π) = 21", "Area = π(28² − 21²) = 22/7 × 343 = 1,078 cm²"], " cm²",
         "Ring area = π(R² − r²)", "(R² − r²) ≠ (R − r)²."),
        ("officer", "L3", "The minute hand of a clock is 14 cm long. The area it sweeps in 20 minutes is (π = 22/7):", PI * 196 / 3,
         [(PI * 196 / 2, "used 30 minutes"), (PI * 196 / 4, "used 15 minutes"), (2 * PI * 14 / 3, "computed the arc length")],
         ["20 minutes = 120° = 1/3 of the circle", "Area = 616/3 = 205.33 cm²"], " cm²", "Sector = (θ/360) πr²", "The minute hand turns 6° per minute."),
        ("officer", "L3", "A circle is inscribed in a square of side 14 cm. The area inside the square but outside the circle is (π = 22/7):", 196 - PI * 49,
         [(PI * 49, "gave the circle's area"), (PI * 98 - 196, "used the circumscribed circle"), (196 - PI * 49 / 2, "subtracted a semicircle only")],
         ["Inscribed circle radius = 7 ⇒ area 154", "Region = 196 − 154 = 42 cm²"], " cm²", "Region = square − circle", "Inscribed circle radius = side/2."),
        ("officer", "L3", "A wire bent into a square encloses 484 cm². If it is rebent into a circle, the area enclosed is (π = 22/7):", PI * 14 ** 2,
         [(PI * 28 ** 2, "took the perimeter as πr"), (PI * 7 ** 2, "halved the radius"), (484, "assumed the area is unchanged")],
         ["Square side 22 ⇒ wire 88 cm", "2πr = 88 ⇒ r = 14", "Area = 616 cm²"], " cm²", "Perimeter is conserved when a wire is rebent", "Area is not conserved."),
        ("officer", "L2", "The perimeter of a semicircle of radius 14 cm is (π = 22/7):", PI * 14 + 28,
         [(PI * 14, "forgot the diameter"), (2 * PI * 14, "gave the full circumference"), (PI * 14 + 14, "added the radius instead of the diameter")],
         ["Perimeter = πr + 2r = 44 + 28 = 72 cm"], " cm", "Semicircle perimeter = πr + 2r", "Include the straight edge."),
        ("officer", "L3", "A sector of radius 21 cm and angle 120° is folded into a cone. The height of the cone is:", "14√2 cm",
         [("7√10 cm", "added the squares instead of subtracting"), ("7 cm", "gave the base radius"), ("21 cm", "gave the slant height")],
         ["Arc = (120/360) × 2π × 21 = 44 = 2πr ⇒ r = 7", "Slant = 21 ⇒ h = √(441 − 49) = √392 = 14√2 cm"], "",
         "Arc of sector = circumference of cone base; h² = l² − r²", "The sector radius becomes the slant height."),
        ("officer", "L3", "A horse is tied at a corner of a square field of side 28 m with a 14 m rope. The area of the field it cannot graze is (π = 22/7):", 784 - PI * 196 / 4,
         [(PI * 196 / 4, "gave the grazed area"), (784 - PI * 196, "used a full circle"), (784 - PI * 196 / 2, "used a semicircle")],
         ["Grazed = quarter circle = 154 m²", "Ungrazed = 784 − 154 = 630 m²"], " m²", "Corner of a square ⇒ quarter circle", "The corner angle is 90°."),
        ("officer", "L3", "The inner circumference of a circular track is 440 m and the track is 7 m wide. The area of the track is (π = 22/7):", track,
         [(440 * 7, "multiplied inner circumference by width"), (484 * 7, "multiplied outer circumference by width"), (PI * 49, "used π × width²")],
         ["r = 70 m, R = 77 m", "Area = π(77² − 70²) = 22/7 × 1,029 = 3,234 m²"], " m²", "Ring area = π(R² − r²)", "Strip area ≈ mean circumference × width, not either edge."),
    ]
    G(B, M, items, "Circle: C = 2πr, A = πr², sector = (θ/360)πr²", "Distinguish radius from diameter and area from length.")


# =====================================================================
def circle_theorems(B):
    M = "qa-circle-theorems-chords-tangents-and-cyclic-quadrilaterals-3a6cb205"
    assert F(6 * 8, 4) == 12
    pt = math.isqrt(4 * 9)
    items = [
        ("foundation", "L1", "An arc subtends 110° at the centre of a circle. The angle it subtends at any point on the remaining part of the circle is:", 55,
         [(110, "took the same angle"), (220, "doubled instead of halving"), (125, "subtracted the half-angle from 180°")],
         ["Angle at circumference = ½ × angle at centre = 55°"], "°"),
        ("foundation", "L1", "In a cyclic quadrilateral ABCD, ∠A = 75°. Then ∠C is:", 105,
         [(75, "took opposite angles as equal"), (285, "subtracted from 360°"), (15, "subtracted from 90°")],
         ["Opposite angles of a cyclic quadrilateral are supplementary", "∠C = 180° − 75° = 105°"], "°"),
        ("foundation", "L2", "A chord of length 16 cm is drawn in a circle of radius 10 cm. Its distance from the centre is:", 6,
         [(8, "gave half the chord"), (math.sqrt(164), "added the squares"), (2, "subtracted 8 from 10")],
         ["Perpendicular from centre bisects the chord ⇒ half-chord 8", "d = √(10² − 8²) = 6 cm"], " cm"),
        ("foundation", "L2", "A point is 13 cm from the centre of a circle of radius 5 cm. The length of the tangent from the point is:", 12,
         [(math.sqrt(194), "added the squares"), (8, "subtracted radius from distance"), (18, "added radius and distance")],
         ["Tangent ⟂ radius ⇒ t = √(13² − 5²) = 12 cm"], " cm"),
        ("foundation", "L1", "AB is a diameter of a circle and C is a point on the circle. If ∠CAB = 35°, then ∠ABC is:", 55,
         [(35, "took the angles as equal"), (90, "gave the angle at C"), (145, "subtracted 35° from 180°")],
         ["Angle in a semicircle ∠ACB = 90°", "∠ABC = 180° − 90° − 35° = 55°"], "°"),
        ("officer", "L3", "Chords AB and CD of a circle intersect at P inside it. If AP = 6 cm, PB = 8 cm and CP = 4 cm, then PD is:", 12,
         [(3, "set AP·CP = PB·PD"), (F(16, 3), "set PB·CP = AP·PD"), (10, "used AP + PB − CP")],
         ["Intersecting chords: AP·PB = CP·PD", "6 × 8 = 4 × PD ⇒ PD = 12 cm"], " cm", "AP·PB = CP·PD", "Pair the segments of the same chord."),
        ("officer", "L3", "From an external point P, a secant meets a circle at A and B with PA = 4 cm and PB = 9 cm. The length of the tangent from P is:", pt,
         [(math.sqrt(4 * 5), "used the chord AB instead of PB"), (F(13, 2), "averaged PA and PB"), (13, "added PA and PB")],
         ["PT² = PA × PB = 4 × 9 = 36", "PT = 6 cm"], " cm", "Tangent–secant: PT² = PA·PB", "PB is the whole secant from P."),
        ("officer", "L3", "PA and PB are tangents from P to a circle with centre O, and ∠APB = 50°. If C is a point on the major arc AB, ∠ACB is:", 65,
         [(130, "gave ∠AOB"), (25, "halved ∠APB"), (115, "took C on the minor arc")],
         ["∠AOB = 180° − 50° = 130°", "∠ACB = ½ × 130° = 65°"], "°", "OAPB has two right angles; inscribed = ½ central", "Check which arc C lies on."),
        ("officer", "L3", "Two circles of radii 8 cm and 3 cm have centres 13 cm apart. The length of their direct common tangent is:", "12 cm",
         [("4√3 cm", "used the transverse tangent formula"), ("√194 cm", "added (R − r)² instead of subtracting"), ("5 cm", "gave R − r")],
         ["Direct tangent = √(d² − (R − r)²) = √(169 − 25) = 12 cm"], "", "Direct: √(d² − (R − r)²); transverse: √(d² − (R + r)²)",
         "Direct uses the difference of radii."),
        ("officer", "L3", "In a cyclic quadrilateral ABCD, ∠BAD = (2x + 10)° and ∠BCD = (3x − 5)°. Then ∠BCD is:", 3 * 35 - 5,
         [(2 * 35 + 10, "gave ∠BAD"), (3 * 15 - 5, "equated the opposite angles"), (35, "gave x")],
         ["2x + 10 + 3x − 5 = 180 ⇒ x = 35", "∠BCD = 100°"], "°", "Opposite angles of a cyclic quadrilateral sum to 180°", "Opposite angles are supplementary, not equal."),
        ("officer", "L3", "Two parallel chords of lengths 24 cm and 10 cm lie on the same side of the centre of a circle of radius 13 cm. The distance between them is:",
         12 - 5, [(12 + 5, "placed them on opposite sides"), (24 - 10, "subtracted the chord lengths"), (12, "gave the distance of one chord")],
         ["Distances from centre: √(169 − 144) = 5 and √(169 − 25) = 12", "Same side ⇒ 12 − 5 = 7 cm"], " cm",
         "d = √(r² − (chord/2)²)", "Same side subtracts, opposite sides add."),
        ("officer", "L3", "The tangent at A to a circle with centre O makes an angle of 58° with chord AB. The angle ∠AOB is:", 116,
         [(58, "gave the angle in the alternate segment"), (122, "subtracted 58° from 180°"), (64, "doubled the complement of 58°")],
         ["Angle in alternate segment = 58°", "∠AOB = 2 × 58° = 116°"], "°", "Tangent–chord angle = inscribed angle on the other side", "Central angle is twice the inscribed angle."),
        ("officer", "L2", "ABCD is a cyclic quadrilateral. Side AB is produced to E and ∠CBE = 70°. Then ∠ADC is:", 70,
         [(110, "gave ∠ABC"), (140, "doubled the exterior angle"), (35, "halved the exterior angle")],
         ["Exterior angle of a cyclic quadrilateral = interior opposite angle", "∠ADC = 70°"], "°"),
        ("officer", "L3", "A circle is inscribed in a right triangle with legs 6 cm and 8 cm. Its radius is:", F(6 + 8 - 10, 2),
         [(6 + 8 - 10, "did not halve (a + b − c)"), (F(24, 10), "divided the area by the hypotenuse"), (5, "gave the circumradius")],
         ["Hypotenuse = 10", "r = (a + b − c)/2 = 2 cm (also area/s = 24/12)"], " cm", "Inradius of right triangle = (a + b − c)/2", "Circumradius is half the hypotenuse; inradius is not."),
        ("officer", "L3", "A quadrilateral ABCD circumscribes a circle. If AB = 6 cm, BC = 7 cm and CD = 8 cm, then DA is:", 6 + 8 - 7,
         [(6 + 7 - 8, "paired AB with BC"), (7 + 8 - 6, "paired BC with CD"), (6 + 7 + 8, "added the three sides")],
         ["Tangent lengths ⇒ AB + CD = BC + DA", "DA = 6 + 8 − 7 = 7 cm"], " cm", "Pitot: AB + CD = BC + DA", "Opposite sides pair up."),
    ]
    G(B, M, items, "Circle theorems", "Identify the theorem before computing.")


# =====================================================================
def similarity(B):
    M = "qa-congruence-and-similarity-19870cbb"
    alt = 12 * F(11, 8)
    area_iso = F(1, 2) * 10 * 12
    items = [
        ("foundation", "L1", "Two similar triangles have corresponding sides in the ratio 2 : 3. The ratio of their areas is:", "4 : 9",
         [("2 : 3", "used the side ratio"), ("8 : 27", "cubed the ratio"), ("9 : 4", "reversed the ratio")],
         ["Area ratio = (side ratio)² = 4 : 9"], ""),
        ("foundation", "L2", "ΔABC ~ ΔDEF with AB = 6 cm, DE = 9 cm and BC = 8 cm. Then EF is:", 12,
         [(F(16, 3), "inverted the ratio"), (11, "added the difference 3"), (F(27, 4), "paired AB with EF")],
         ["EF/BC = DE/AB = 3/2", "EF = 8 × 3/2 = 12 cm"], " cm"),
        ("foundation", "L2", "In ΔABC, DE ∥ BC with D on AB and E on AC. If AD = 4 cm, DB = 6 cm and AE = 6 cm, then EC is:", 9,
         [(4, "inverted the ratio"), (15, "gave AC"), (10, "added AD and AE")],
         ["AD/DB = AE/EC ⇒ 4/6 = 6/EC", "EC = 9 cm"], " cm"),
        ("foundation", "L1", "Which of the following is NOT a criterion for congruence of triangles?", "AAA",
         [("SAS", "SAS is a valid congruence rule"), ("ASA", "ASA is a valid congruence rule"), ("RHS", "RHS is a valid congruence rule")],
         ["AAA guarantees only similarity, not equal size"], ""),
        ("foundation", "L2", "A 6 m pole casts a 4 m shadow. At the same time a tower casts a 28 m shadow. The height of the tower is:", 42,
         [(F(28 * 4, 6), "inverted the ratio"), (30, "added the difference of 2 m"), (168, "multiplied 6 by 28")],
         ["Height/shadow is constant: 6/4 = h/28", "h = 42 m"], " m"),
        ("officer", "L3", "The areas of two similar triangles are 64 cm² and 121 cm². If an altitude of the smaller is 12 cm, the corresponding altitude of the larger is:", alt,
         [(12 * F(121, 64), "used the area ratio directly"), (12 * F(8, 11), "inverted the side ratio"), (12 + 11 - 8, "added the side-ratio difference")],
         ["Side ratio = √(64/121) = 8/11", "Altitude = 12 × 11/8 = 16.5 cm"], " cm", "Linear ratio = √(area ratio)", "Altitudes scale linearly."),
        ("officer", "L3", "In ΔABC right-angled at B, BD ⟂ AC. If AD = 4 cm and DC = 9 cm, then BD is:", 6,
         [(F(13, 2), "took the arithmetic mean"), (13, "gave AC"), (5, "subtracted AD from DC")],
         ["ΔABD ~ ΔBCD ⇒ BD² = AD × DC = 36", "BD = 6 cm"], " cm", "BD² = AD·DC", "It is the geometric mean, not the average."),
        ("officer", "L3", "In ΔABC, D on AB divides it in the ratio AD : DB = 2 : 3, and DE ∥ BC meets AC at E. The ratio of the area of ΔADE to that of trapezium DBCE is:", "4 : 21",
         [("4 : 25", "compared with the whole triangle"), ("4 : 9", "squared AD : DB"), ("2 : 5", "used the linear ratio AD : AB")],
         ["AD : AB = 2 : 5 ⇒ areas ADE : ABC = 4 : 25", "Trapezium = 25 − 4 = 21 ⇒ 4 : 21"], "", "Area ratio = (AD/AB)²", "Use AD : AB, not AD : DB."),
        ("officer", "L3", "The midpoints of the sides of a triangle of area 96 cm² are joined. The area of the triangle so formed is:", 24,
         [(48, "halved the area"), (32, "took one-third"), (12, "took one-eighth")],
         ["Midpoint triangle is similar with ratio 1 : 2", "Area = 96/4 = 24 cm²"], " cm²", "Area ratio = (1/2)²", "Sides halve, area quarters."),
        ("officer", "L3", "In ΔABC, AB = 12 cm, AC = 18 cm and BC = 20 cm. The bisector of ∠A meets BC at D. Then BD is:", F(20 * 12, 30),
         [(F(20 * 18, 30), "gave DC"), (10, "took D as the midpoint"), (F(20, 3), "divided BC into three equal parts")],
         ["BD/DC = AB/AC = 2/3", "BD = 20 × 2/5 = 8 cm"], " cm", "Angle-bisector theorem", "The bisector divides the opposite side in the ratio of the adjacent sides."),
        ("officer", "L3", "The perimeters of two similar triangles are 36 cm and 48 cm. If the area of the larger is 128 cm², the area of the smaller is:", 128 * F(9, 16),
         [(128 * F(3, 4), "used the linear ratio"), (128 * F(16, 9), "inverted the squared ratio"), (64, "halved the area")],
         ["Linear ratio = 36 : 48 = 3 : 4", "Area = 128 × 9/16 = 72 cm²"], " cm²", "Area ratio = (perimeter ratio)²", "Perimeters scale like sides."),
        ("officer", "L3", "A man 1.8 m tall walks away from a 5.4 m lamp post at 1.2 m/s. The length of his shadow after 5 seconds is:", 3,
         [(F(6 * 18, 54), "ignored the shadow in the larger triangle"), (6, "took the shadow equal to the distance walked"), (9, "gave distance plus shadow")],
         ["Distance = 6 m; let shadow = s", "1.8/s = 5.4/(6 + s) ⇒ 3.6s = 10.8 ⇒ s = 3 m"], " m",
         "Similar triangles: h/s = H/(d + s)", "The big triangle's base includes the shadow."),
        ("officer", "L3", "In trapezium ABCD, AB ∥ CD and AB = 2CD. Its diagonals meet at O. The ratio of the areas of ΔAOB and ΔCOD is:", "4 : 1",
         [("2 : 1", "used the side ratio"), ("1 : 4", "reversed the ratio"), ("3 : 1", "subtracted the ratio terms")],
         ["ΔAOB ~ ΔCOD with ratio AB : CD = 2 : 1", "Area ratio = 4 : 1"], "", "Area ratio = (side ratio)²", "Square the ratio of parallel sides."),
        ("officer", "L3", "ΔABC ~ ΔPQR and their medians are in the ratio 5 : 7. If the area of ΔPQR is 196 cm², the area of ΔABC is:", 196 * F(25, 49),
         [(196 * F(5, 7), "used the linear ratio"), (196 * F(7, 5), "inverted the linear ratio"), (196 * F(49, 25), "inverted the squared ratio")],
         ["Medians scale like sides ⇒ area ratio 25 : 49", "Area = 196 × 25/49 = 100 cm²"], " cm²", "Area ratio = (median ratio)²", "Any corresponding lengths give the linear ratio."),
        ("officer", "L3", "In ΔABC, AB = AC = 13 cm and BC = 10 cm. BD ⟂ AC and CE ⟂ AB (so ΔBCD ≅ ΔCBE). The length of BD is:", 2 * area_iso / 13,
         [(12, "gave the altitude from A"), (area_iso / 13, "forgot the factor 2"), (math.sqrt(75), "took √(10² − 5²)")],
         ["Altitude from A = √(169 − 25) = 12 ⇒ area = 60", "BD = 2 × 60/13 = 9.23 cm (= CE by congruence)"], " cm",
         "Area = ½ × base × height, used twice", "Equal altitudes to the equal sides of an isosceles triangle."),
    ]
    G(B, M, items, "Similarity: corresponding sides proportional; area ratio = square of side ratio", "Keep correspondence of vertices in order.")


# =====================================================================
def coordinate(B):
    M = "qa-coordinate-and-line-geometry-eb041f58"
    tri = abs(1 * (6 - 2) + 4 * (2 - 2) + 7 * (2 - 6)) / F(2)
    assert tri == 12
    # collinearity k
    kk = [k for k in range(-20, 21) if (4 - k) * (7 - 3) == (10 - 4) * (3 - 1)]
    assert kk == [1]
    # parallel lines 2x + ky = 5 and 4x + 6y = 7 ⇒ 2/4 = k/6
    assert F(2, 4) == F(3, 6)
    # equidistant point on x-axis
    xs = [x for x in range(-50, 51) if (x - 1) ** 2 + 4 == (x - 3) ** 2 + 64]
    assert xs == [17]
    for eq, pt in [((3, -2, 0), (2, 3)), ((2, 3, -13), (2, 3)), ((3, 2, -12), (2, 3)), ((2, -3, 5), (2, 3))]:
        assert eq[0] * pt[0] + eq[1] * pt[1] + eq[2] == 0
    items = [
        ("foundation", "L1", "The distance between the points (2, 3) and (8, 11) is:", 10,
         [(14, "added the differences"), (math.sqrt(28), "did not square the differences"), (100, "did not take the square root")],
         ["d = √(6² + 8²) = √100 = 10"], " units"),
        ("foundation", "L1", "The midpoint of the segment joining (−4, 6) and (10, −2) is:", "(3, 2)",
         [("(7, −4)", "subtracted and halved"), ("(6, 4)", "did not halve"), ("(3, −2)", "sign slip on the y-coordinate")],
         ["x = (−4 + 10)/2 = 3, y = (6 − 2)/2 = 2"], ""),
        ("foundation", "L2", "The slope of the line through (1, −2) and (5, 10) is:", 3,
         [(F(1, 3), "inverted rise and run"), (-3, "sign slip"), (2, "used (10 − 2)/4")],
         ["m = (10 − (−2))/(5 − 1) = 12/4 = 3"], ""),
        ("foundation", "L2", "The x-intercept of the line 3x − 4y + 12 = 0 is:", -4,
         [(4, "sign slip"), (3, "gave the y-intercept"), (-3, "gave the y-intercept with a sign slip")],
         ["Put y = 0: 3x + 12 = 0 ⇒ x = −4"], ""),
        ("foundation", "L2", "The point dividing the segment from (2, 1) to (8, 7) internally in the ratio 1 : 2 is:", "(4, 3)",
         [("(6, 5)", "used the ratio 2 : 1"), ("(5, 4)", "gave the midpoint"), ("(−4, −5)", "used external division")],
         ["x = (1·8 + 2·2)/3 = 4, y = (1·7 + 2·1)/3 = 3"], ""),
        ("officer", "L3", "The area of the triangle with vertices (1, 2), (4, 6) and (7, 2) is:", tri,
         [(2 * tri, "forgot the factor ½"), (tri / 2, "halved twice"), (18, "used 6 as the height")],
         ["Base (1, 2)–(7, 2) = 6, height = 4", "Area = ½ × 6 × 4 = 12 sq units"], " sq units", "Area = ½|x₁(y₂ − y₃) + x₂(y₃ − y₁) + x₃(y₁ − y₂)|", "Take the modulus and halve."),
        ("officer", "L3", "The perpendicular distance of the point (3, 4) from the line 4x + 3y − 4 = 0 is:", F(abs(12 + 12 - 4), 5),
         [(abs(12 + 12 - 4), "did not divide by √(a² + b²)"), (F(12 + 12 + 4, 5), "sign slip on the constant"), (F(20, 7), "divided by a + b")],
         ["d = |4·3 + 3·4 − 4|/√(16 + 9) = 20/5 = 4"], " units", "d = |ax₁ + by₁ + c|/√(a² + b²)", "Divide by √(a² + b²)."),
        ("officer", "L3", "The equation of the line through (2, 3) perpendicular to 2x + 3y = 6 is:", "3x − 2y = 0",
         [("2x + 3y = 13", "wrote the parallel line"), ("3x + 2y = 12", "slope sign wrong (−3/2)"), ("2x − 3y + 5 = 0", "used slope 2/3")],
         ["Given slope = −2/3 ⇒ perpendicular slope = 3/2", "y − 3 = (3/2)(x − 2) ⇒ 3x − 2y = 0"], "", "m₁m₂ = −1", "Negate AND invert the slope."),
        ("officer", "L3", "The points (1, k), (3, 4) and (7, 10) are collinear. The value of k is:", 1,
         [(7, "sign slip in (4 − k)"), (F(8, 3), "inverted the slope"), (3, "used slope 1/2")],
         ["Slope of (3, 4)–(7, 10) = 6/4 = 3/2", "(4 − k)/2 = 3/2 ⇒ k = 1"], "", "Equal slopes ⇒ collinear", "Keep the order of subtraction consistent."),
        ("officer", "L3", "The centroid of the triangle with vertices (2, 5), (−4, 3) and (8, −2) is:", "(2, 2)",
         [("(3, 3)", "divided by 2"), ("(6, 6)", "did not divide by 3"), ("(2, 10/3)", "sign slip on −2")],
         ["x = (2 − 4 + 8)/3 = 2, y = (5 + 3 − 2)/3 = 2"], "", "G = ((x₁ + x₂ + x₃)/3, (y₁ + y₂ + y₃)/3)", "Divide by 3."),
        ("officer", "L3", "The angle made by the line √3x − y + 5 = 0 with the positive x-axis is:", 60,
         [(30, "took slope 1/√3"), (120, "took slope −√3"), (45, "took slope 1")],
         ["y = √3x + 5 ⇒ m = √3 = tan 60°"], "°", "m = tan θ", "Rewrite in slope form first."),
        ("officer", "L3", "The area of the triangle formed by the line 2x + 3y = 12 and the coordinate axes is:", F(6 * 4, 2),
         [(6 * 4, "forgot the factor ½"), (6 + 4, "added the intercepts"), (F(6 * 4, 4), "halved twice")],
         ["Intercepts: x = 6, y = 4", "Area = ½ × 6 × 4 = 12 sq units"], " sq units", "Area = ½ |a b| for intercepts a, b", "Find both intercepts."),
        ("officer", "L3", "The x-axis divides the segment joining (2, −3) and (5, 6) in the ratio:", "1 : 2",
         [("2 : 1", "reversed the ratio"), ("2 : 5", "used the x-coordinates"), ("1 : 3", "used 3 : 9 from the y-values")],
         ["Let ratio k : 1: y = (6k − 3)/(k + 1) = 0 ⇒ k = 1/2", "Ratio = 1 : 2"], "", "Section formula with y = 0", "The ratio is |y₁| : |y₂| = 3 : 6."),
        ("officer", "L3", "The point on the x-axis equidistant from (1, 2) and (3, 8) is:", "(17, 0)",
         [("(−17, 0)", "sign slip"), ("(2, 0)", "took the midpoint's x-coordinate"), ("(0, 17/3)", "searched on the y-axis")],
         ["(x − 1)² + 4 = (x − 3)² + 64", "4x = 68 ⇒ x = 17"], "", "Equate squared distances", "Put y = 0 for a point on the x-axis."),
        ("officer", "L3", "The lines 2x + ky = 5 and 4x + 6y = 7 are parallel. The value of k is:", 3,
         [(12, "inverted the coefficient ratio"), (F(-4, 3), "used the perpendicular condition"), (F(30, 7), "compared the constants")],
         ["Parallel ⇒ 2/4 = k/6", "k = 3"], "", "a₁/a₂ = b₁/b₂ ≠ c₁/c₂", "Compare x- and y-coefficients, not constants."),
    ]
    G(B, M, items, "Coordinate geometry formulas", "Keep signs and order of subtraction consistent.")


# =====================================================================
def lines_angles(B):
    M = "qa-lines-and-angles-f48e31c3"
    assert F(180, 6) == 30
    items = [
        ("foundation", "L1", "The complement of 38° is:", 52,
         [(142, "gave the supplement"), (322, "subtracted from 360°"), (38, "gave the angle itself")], ["90° − 38° = 52°"], "°"),
        ("foundation", "L1", "An angle is one-fifth of its supplement. The angle is:", 30,
         [(36, "took one-fifth of 180°"), (15, "used 90° in place of 180°"), (18, "took one-fifth of 90°")],
         ["x = (180 − x)/5 ⇒ 6x = 180 ⇒ x = 30°"], "°"),
        ("foundation", "L2", "Two parallel lines are cut by a transversal. The interior angles on the same side are (3x + 10)° and (2x + 20)°. The larger angle is:", 100,
         [(80, "gave the smaller angle"), (40, "equated the angles"), (30, "gave x")],
         ["Co-interior angles sum to 180°: 5x + 30 = 180 ⇒ x = 30", "Angles 100° and 80°"], "°"),
        ("foundation", "L1", "Two lines intersect and one of the angles formed is 65°. The angle adjacent to it is:", 115,
         [(65, "gave the vertically opposite angle"), (25, "gave the complement"), (295, "subtracted from 360°")],
         ["Adjacent angles on a line sum to 180°", "180° − 65° = 115°"], "°"),
        ("foundation", "L2", "Four angles at a point are x, 2x, 3x and 4x. The largest angle is:", 144,
         [(72, "used 180° as the total"), (36, "gave x"), (90, "divided 360° equally")],
         ["10x = 360 ⇒ x = 36", "Largest = 4x = 144°"], "°"),
        ("officer", "L3", "AB ∥ CD, and E is a point between the lines such that ∠ABE = 40° and ∠CDE = 35°. E lies on the same side of line BD as A and C. The angle ∠BED is:", 75,
         [(105, "subtracted the sum from 180°"), (285, "gave the reflex angle"), (5, "took the difference")],
         ["Draw EF ∥ AB through E", "∠BEF = 40° and ∠FED = 35° (alternate angles) ⇒ ∠BED = 75°"], "°",
         "Angle at the bend = sum of alternate angles", "Draw the auxiliary parallel."),
        ("officer", "L3", "Two adjacent angles form a linear pair and measure 70° and 110°. The angle between their bisectors is:", 90,
         [(180, "added the angles"), (20, "halved the difference"), (45, "halved 90°")],
         ["Angle = 35° + 55° = 90°"], "°", "Bisectors of a linear pair are perpendicular", "Half of 180° is 90°."),
        ("officer", "L3", "AB ∥ CD and a transversal makes alternate interior angles (5x − 20)° and (3x + 16)°. The first angle is:", 5 * 18 - 20,
         [(18, "gave x"), (180 - 70, "gave the co-interior angle"), (5 * 23 - 20, "treated them as co-interior (sum 180°)")],
         ["Alternate angles are equal: 5x − 20 = 3x + 16 ⇒ x = 18", "Angle = 70°"], "°", "Alternate interior angles are equal", "Identify the angle pair correctly."),
        ("officer", "L3", "The complement and the supplement of an angle are in the ratio 2 : 7. The angle is:", 54,
         [(36, "gave the complement"), (70, "used complement : angle = 2 : 7"), (126, "gave the supplement")],
         ["(90 − x)/(180 − x) = 2/7 ⇒ 630 − 7x = 360 − 2x ⇒ x = 54°"], "°", "Form the ratio equation", "Solve for the angle, not its complement."),
        ("officer", "L3", "The reflex angle of an angle is five times the angle. The angle is:", 60,
         [(30, "used 180° instead of 360°"), (72, "took one-fifth of 360°"), (45, "took one-eighth of 360°")],
         ["360 − x = 5x ⇒ x = 60°"], "°", "Reflex = 360° − angle", "Reflex is measured from 360°."),
        ("officer", "L3", "Two interior angles on the same side of a transversal cutting two parallel lines are in the ratio 4 : 5. The smaller angle is:", 80,
         [(100, "gave the larger angle"), (40, "used 90° as the sum"), (160, "used 360° as the sum")],
         ["4k + 5k = 180 ⇒ k = 20", "Smaller = 80°"], "°", "Co-interior angles sum to 180°", "They are supplementary."),
        ("officer", "L3", "Lines l ∥ m are cut by transversal t at P and Q. The bisectors of the two interior angles on the same side of t at P and Q meet at R. ∠PRQ is:", 90,
         [(180, "added the full angles"), (45, "halved 90°"), (60, "assumed an equilateral triangle")],
         ["Half-angles sum to 180°/2 = 90°", "∠PRQ = 180° − 90° = 90°"], "°", "Co-interior half-angles sum to 90°", "Use the triangle PQR."),
        ("officer", "L3", "An angle exceeds its complement by 24°. Its supplement is:", 180 - 57,
         [(57, "gave the angle"), (33, "gave the complement"), (180 - 33, "gave the supplement of the complement")],
         ["x − (90 − x) = 24 ⇒ x = 57", "Supplement = 123°"], "°", "Complement 90 − x; supplement 180 − x", "Answer what is asked."),
        ("officer", "L3", "Three lines meet at a point forming six angles. Three consecutive angles are x, 2x and 3x. The largest of these is:", 90,
         [(180, "used 360° for three consecutive angles"), (60, "gave 2x"), (45, "divided 180° by 4")],
         ["Three consecutive angles lie on a straight line: 6x = 180 ⇒ x = 30", "Largest = 90°"], "°",
         "Consecutive angles across three concurrent lines sum to 180°", "Six angles = three vertically opposite pairs."),
        ("officer", "L3", "Two angles forming a linear pair differ by 36°. The larger angle is:", 108,
         [(72, "gave the smaller angle"), (63, "used 90° as the sum"), (144, "subtracted the difference from 180°")],
         ["x + y = 180, x − y = 36 ⇒ x = 108°"], "°", "Sum and difference", "Linear pair sums to 180°."),
    ]
    G(B, M, items, "Angle relations: complementary 90°, supplementary 180°, parallel-line angle pairs", "Identify the angle pair before equating.")


# =====================================================================
def polygons(B):
    M = "qa-quadrilaterals-and-polygons-4a164691"
    # ratio of sides 1:2, interior angle ratio 3:4
    sol = [k for k in range(3, 60) if F(180 * (k - 2), k) * 4 == F(180 * (2 * k - 2), 2 * k) * 3]
    assert sol == [5]
    items = [
        ("foundation", "L1", "Each interior angle of a regular hexagon is:", 120,
         [(60, "gave the exterior angle"), (108, "used a pentagon"), (135, "used an octagon")], ["(6 − 2) × 180/6 = 120°"], "°"),
        ("foundation", "L1", "The sum of the interior angles of an octagon is:", 1080,
         [(1440, "used n × 180°"), (900, "used n = 7"), (1260, "used n = 9")], ["(8 − 2) × 180° = 1,080°"], "°"),
        ("foundation", "L2", "The diagonals of a rhombus are 16 cm and 12 cm. Its side is:", 10,
         [(14, "averaged the diagonals"), (20, "used the full diagonals in Pythagoras"), (96, "computed the area")],
         ["Half-diagonals 8 and 6, at right angles", "Side = √(64 + 36) = 10 cm"], " cm"),
        ("foundation", "L2", "Each exterior angle of a regular polygon is 24°. The number of sides is:", 15,
         [(F(180, 24), "divided 180° by 24°"), (16, "added one side"), (24, "took the angle as the count")], ["n = 360/24 = 15"], ""),
        ("foundation", "L2", "Two adjacent angles of a parallelogram are in the ratio 2 : 3. The larger angle is:", 108,
         [(72, "gave the smaller angle"), (216, "used 360° as the sum"), (144, "used 240° as the sum")], ["2k + 3k = 180 ⇒ k = 36 ⇒ 108°"], "°"),
        ("officer", "L3", "The number of diagonals of a 12-sided polygon is:", 12 * 9 // 2,
         [(12 * 11 // 2, "counted all pairs of vertices (includes sides)"), (12 * 9, "did not halve"), (12 * 10 // 2, "used n(n − 2)/2")],
         ["Diagonals = n(n − 3)/2 = 12 × 9/2 = 54"], "", "n(n − 3)/2", "Each vertex joins n − 3 others by diagonals."),
        ("officer", "L3", "Each interior angle of a regular polygon is four times its exterior angle. The number of sides is:", 10,
         [(8, "used interior = 3 × exterior"), (20, "divided 720° by 36°"), (12, "used exterior = 30°")],
         ["Interior + exterior = 180 ⇒ 5e = 180 ⇒ e = 36°", "n = 360/36 = 10"], "", "Interior + exterior = 180°", "Find the exterior angle first."),
        ("officer", "L3", "An isosceles trapezium has parallel sides 18 cm and 12 cm and each non-parallel side 5 cm. Its area is:", F(18 + 12, 2) * 4,
         [(F(18 + 12, 2) * 5, "used the slant side as height"), ((18 + 12) * 4, "forgot the factor ½"), (12 * 4, "used only the shorter side")],
         ["Overhang each side = (18 − 12)/2 = 3 ⇒ height = √(25 − 9) = 4", "Area = ½ × 30 × 4 = 60 cm²"], " cm²",
         "Area = ½(a + b)h", "Height is not the slant side."),
        ("officer", "L3", "A rhombus has area 120 cm² and one diagonal 10 cm. Its perimeter is:", 52,
         [(68, "added the diagonals and doubled"), (13, "gave the side"), (48, "doubled the other diagonal")],
         ["Other diagonal = 2 × 120/10 = 24", "Side = √(5² + 12²) = 13 ⇒ perimeter 52 cm"], " cm", "Area = ½ d₁d₂; side² = (d₁/2)² + (d₂/2)²", "Use half-diagonals."),
        ("officer", "L3", "The sum of the interior angles of a polygon is 1,620°. The number of its diagonals is:", 11 * 8 // 2,
         [(11 * 10 // 2, "counted all vertex pairs"), (11, "gave the number of sides"), (11 * 8, "did not halve")],
         ["(n − 2) × 180 = 1,620 ⇒ n = 11", "Diagonals = 11 × 8/2 = 44"], "", "(n − 2)180 then n(n − 3)/2", "Find n first."),
        ("officer", "L3", "Adjacent sides of a parallelogram are 12 cm and 8 cm and the angle between them is 30°. Its area is:", 12 * 8 * F(1, 2),
         [(12 * 8, "omitted sin 30°"), (12 * 8 * math.sqrt(3) / 2, "used sin 60°"), (2 * (12 + 8), "computed the perimeter")],
         ["Area = ab sin θ = 12 × 8 × ½ = 48 cm²"], " cm²", "Area = ab sin θ", "Height = 8 sin 30° = 4."),
        ("officer", "L3", "In rectangle ABCD, AB = 24 cm and BC = 10 cm. The perpendicular distance from A to diagonal BD is:", F(240, 26),
         [(13, "gave half the diagonal"), (F(120, 26), "forgot the factor 2"), (12, "gave half of AB")],
         ["BD = 26; area ΔABD = 120", "Distance = 2 × 120/26 = 9.23 cm"], " cm", "h = 2 × area / base", "Use twice the triangle's area."),
        ("officer", "L3", "The area of a regular hexagon of side 6 cm is:", sq(54, 3, " cm²"),
         [(sq(36, 3, " cm²"), "used 4 triangles"), (sq(108, 3, " cm²"), "forgot the factor ½"), (sq(9, 3, " cm²"), "gave one triangle")],
         ["Hexagon = 6 equilateral triangles of side 6", "Area = 6 × 9√3 = 54√3 cm²"], "", "Area = (3√3/2) a²", "Six triangles, each (√3/4)a²."),
        ("officer", "L3", "A square and a rhombus both have perimeter 40 cm. One diagonal of the rhombus is 12 cm. By how much does the square's area exceed the rhombus's?", 100 - 96,
         [(0, "assumed equal perimeters give equal areas"), (96, "gave the rhombus's area"), (28, "added the diagonals")],
         ["Side 10 ⇒ square area 100", "Rhombus: half-diagonals 6 and 8 ⇒ diagonals 12, 16 ⇒ area 96", "Difference = 4 cm²"], " cm²",
         "Rhombus area = ½ d₁d₂", "Same perimeter does not mean same area."),
        ("officer", "L3", "The numbers of sides of two regular polygons are in the ratio 1 : 2 and their interior angles are in the ratio 3 : 4. The number of sides of the smaller polygon is:", 5,
         [(10, "gave the larger polygon"), (4, "tested only a square"), (6, "tested only a hexagon")],
         ["Angles: 180(n − 2)/n and 180(2n − 2)/(2n)", "4(180 − 360/n) = 3(180 − 180/n) ⇒ 180 = 900/n ⇒ n = 5"], "",
         "Interior angle = 180(n − 2)/n", "Set up the ratio with n and 2n."),
    ]
    G(B, M, items, "Polygon and quadrilateral properties", "Use (n − 2)180° for the angle sum and 360° for exterior angles.")


# =====================================================================
def reshaping(B):
    M = "qa-reshaping-and-equal-perimeter-problems-ef477223"
    Vs = F(4, 3) * 216
    assert Vs / 16 == 18
    cone_n = F(1, 3) * 144 * 24 / (F(4, 3) * 8)
    assert cone_n == 108
    V_rod, a_wire = 1 * 12, F(1, 25)
    assert V_rod / a_wire == 300
    V_roll = PI * 49 * 18
    items = [
        ("foundation", "L1", "A wire in the shape of a square of side 11 cm is rebent into a circle. The radius of the circle is (π = 22/7):", 7,
         [(14, "took the perimeter as πr"), (F(7, 2), "halved the radius"), (11, "kept the square's side")],
         ["Wire = 44 cm = 2πr ⇒ r = 7 cm"], " cm"),
        ("foundation", "L2", "A wire bent as an 18 cm × 10 cm rectangle is rebent into a square. The area of the square is:", 196,
         [(180, "assumed the area is unchanged"), (784, "did not halve the perimeter twice (side 28)"), (49, "divided the perimeter by 8")],
         ["Perimeter = 56 ⇒ side 14", "Area = 196 cm²"], " cm²"),
        ("foundation", "L2", "A metal sphere of radius 6 cm is melted and recast into a cylinder of radius 4 cm. The height of the cylinder is:", 18,
         [(F(216, 16), "dropped the 4/3"), (F(288, 64), "used the cylinder's diameter as radius"), (F(144, 16), "equated surface areas")],
         ["(4/3)π × 216 = π × 16 × h", "h = 288/16 = 18 cm"], " cm"),
        ("foundation", "L2", "A cube of side 12 cm is melted into small cubes of side 3 cm. The number of small cubes is:", 64,
         [(16, "divided the face areas"), (4, "divided the sides"), (48, "divided 1,728 by 36")], ["(12/3)³ = 64"], ""),
        ("foundation", "L2", "A wire forming an equilateral triangle of perimeter 36 cm is rebent into a square. The area of the square is:", 81,
         [(144, "used the triangle's side as the square's side"), (324, "used P²/4"), (sq(36, 3, " cm²"), "gave the triangle's area")],
         ["Side = 36/4 = 9", "Area = 81 cm²"], " cm²"),
        ("officer", "L3", "A wire in the shape of a circle of radius 42 cm is rebent into a square. The area of the square is (π = 22/7):", (2 * PI * 42 / 4) ** 2,
         [(PI * 42 ** 2, "gave the circle's area"), ((2 * PI * 42 / 2) ** 2, "halved the perimeter for the side"), ((2 * PI * 42 / 8) ** 2, "divided the perimeter by 8")],
         ["Wire = 2π × 42 = 264 cm", "Side = 66 ⇒ area = 4,356 cm²"], " cm²", "Perimeter conserved", "Side = perimeter/4."),
        ("officer", "L3", "A circle and a square have the same perimeter. The ratio of the area of the circle to that of the square is (π = 22/7):", "14 : 11",
         [("11 : 14", "reversed the ratio"), ("22 : 7", "gave π"), ("1 : 1", "assumed equal areas")],
         ["Circle area = P²/(4π); square area = P²/16", "Ratio = 16/(4π) = 4/π = 28/22 = 14 : 11"], "", "Equal perimeter ⇒ circle encloses more", "Express both areas in terms of P."),
        ("officer", "L3", "A cylinder is melted and recast into a cone of the same base radius. The cone's height is how many times the cylinder's?", 3,
         [(F(1, 3), "inverted the relation"), (1, "assumed equal heights"), (2, "used ½ instead of ⅓")],
         ["πr²h = ⅓ πr²H ⇒ H = 3h"], "", "Volume conserved", "Cone = ⅓ of cylinder of same base and height."),
        ("officer", "L3", "Eight identical spheres of radius 3 cm are melted into one sphere. The ratio of the total surface area before to that after is:", "2 : 1",
         [("1 : 2", "reversed the ratio"), ("8 : 1", "compared volumes"), ("1 : 1", "assumed surface area is conserved")],
         ["8 × 27 = R³ ⇒ R = 6", "Before 8 × 4π × 9 = 288π; after 4π × 36 = 144π ⇒ 2 : 1"], "", "Volume conserved, surface area not", "Find R from volumes."),
        ("officer", "L3", "A rope encloses a square of side 22 m. If the same rope is laid as a circle, how much more area does it enclose? (π = 22/7)", PI * 196 - 484,
         [(PI * 196, "gave the circle's area, not the gain"), (abs(PI * 49 - 484), "used r = 7 and took the difference"), (0, "assumed the area is unchanged")],
         ["Rope = 88 m ⇒ r = 14 ⇒ circle area 616 m²", "Gain = 616 − 484 = 132 m²"], " m²", "Perimeter conserved", "Circle maximises area for a given perimeter."),
        ("officer", "L3", "A solid cone of base radius 12 cm and height 24 cm is melted into spheres of radius 2 cm. The number of spheres is:", cone_n,
         [(3 * cone_n, "forgot the ⅓ for the cone"), (F(1152, 32), "took the sphere volume as 32π (dropped the ÷ 3)"), (F(1152, 16), "used the sphere's surface area")],
         ["Cone = ⅓π × 144 × 24 = 1,152π", "Sphere = (4/3)π × 8 = 32π/3", "Number = 1,152 × 3/32 = 108"], "", "n = V(cone)/V(sphere)", "Keep both fractions."),
        ("officer", "L3", "A wire in the shape of a semicircle of radius 14 cm (arc plus diameter) is rebent into a square. The area of the square is (π = 22/7):", ((PI * 14 + 28) / 4) ** 2,
         [((PI * 14 / 4) ** 2, "omitted the diameter"), (((PI * 14 + 14) / 4) ** 2, "added the radius, not the diameter"), (PI * 196 / 2, "gave the semicircle's area")],
         ["Wire = 44 + 28 = 72 cm", "Side = 18 ⇒ area = 324 cm²"], " cm²", "Semicircle perimeter = πr + 2r", "Include the straight edge."),
        ("officer", "L3", "A 44 cm × 18 cm sheet is rolled along its length (the 44 cm side forms the circumference) into a cylinder. Its volume is (π = 22/7):", V_roll,
         [(PI * (18 / (2 * PI)) ** 2 * 44, "rolled it along the breadth"), (PI * 196 * 18, "took 44 as πr"), (44 * 18, "computed the curved surface")],
         ["2πr = 44 ⇒ r = 7; h = 18", "V = 22/7 × 49 × 18 = 2,772 cm³"], " cm³", "Rolled edge = circumference", "Identify which side becomes the circumference."),
        ("officer", "L3", "A solid hemisphere of radius 21 cm is melted into a cone of the same radius. The height of the cone is:", 42,
         [(84, "used the full-sphere volume"), (14, "forgot the ⅓ for the cone"), (21, "took equal radius and height")],
         ["⅔πr³ = ⅓πr²h ⇒ h = 2r = 42 cm"], " cm", "Volume conserved", "Hemisphere = ⅔πr³."),
        ("officer", "L3", "A copper rod of diameter 2 cm and length 12 cm is drawn into a wire of diameter 4 mm. The length of the wire is:", "3 m",
         [("0.75 m", "used the wire's diameter as radius"), ("0.6 m", "used the ratio of diameters, not their squares"), ("30 m", "slipped a unit (mm/cm)")],
         ["π × 1² × 12 = π × 0.2² × L", "L = 12/0.04 = 300 cm = 3 m"], "", "Volume conserved: r₁²L₁ = r₂²L₂", "Length scales with the square of the radius ratio."),
    ]
    G(B, M, items, "Conservation of volume (melting) or perimeter (rebending)", "Only the conserved quantity is equated.")


# =====================================================================
def triangles(B):
    M = "qa-triangle-properties-and-centres-b1451b8f"
    for s3 in [(5, 6, 10), (7, 8, 12), (6, 6, 11)]:
        a, b, c = sorted(s3)
        assert a + b > c
    assert 3 + 4 < 8
    third = [x for x in range(1, 30) if 11 - 7 < x < 11 + 7]
    assert len(third) == 13
    items = [
        ("foundation", "L1", "The angles of a triangle are in the ratio 2 : 3 : 4. The largest angle is:", 80,
         [(60, "gave the middle angle"), (40, "gave the smallest angle"), (160, "used 360° as the sum")], ["9k = 180 ⇒ k = 20 ⇒ 80°"], "°"),
        ("foundation", "L1", "An exterior angle of a triangle is 110° and one interior opposite angle is 45°. The other interior opposite angle is:", 65,
         [(70, "gave the adjacent interior angle"), (25, "subtracted from 70°"), (135, "subtracted 45° from 180°")],
         ["Exterior angle = sum of interior opposite angles", "110 − 45 = 65°"], "°"),
        ("foundation", "L2", "Which set of lengths CANNOT form a triangle?", "3, 4, 8",
         [("5, 6, 10", "5 + 6 > 10, so it is a triangle"), ("7, 8, 12", "7 + 8 > 12, so it is a triangle"), ("6, 6, 11", "6 + 6 > 11, so it is a triangle")],
         ["Triangle inequality: sum of the two smaller sides must exceed the largest", "3 + 4 = 7 < 8"], ""),
        ("foundation", "L2", "G is the centroid of ΔABC and AD is a median of length 18 cm. Then AG is:", 12,
         [(9, "took G as the midpoint"), (6, "gave GD"), (F(27, 2), "used the ratio 3 : 1")], ["AG : GD = 2 : 1 ⇒ AG = 12 cm"], " cm"),
        ("foundation", "L2", "The circumradius of a right triangle with legs 9 cm and 12 cm is:", F(15, 2),
         [(15, "gave the hypotenuse"), (3, "gave the inradius"), (F(21, 2), "averaged the legs")], ["Hypotenuse = 15; R = 15/2 = 7.5 cm"], " cm"),
        ("officer", "L3", "In ΔABC, AB = 10 cm, AC = 14 cm and BC = 12 cm. The length of the median from A is:", "4√7 cm",
         [("8√7 cm", "forgot the ÷ 4"), ("√38 cm", "used (b² + c² − a²)/4"), ("2√19 cm", "subtracted a²/2 instead of a²/4")],
         ["m² = (2b² + 2c² − a²)/4 = (392 + 200 − 144)/4 = 112", "m = 4√7 cm"], "", "Apollonius: 4m² = 2b² + 2c² − a²", "Divide by 4."),
        ("officer", "L3", "I is the incentre of ΔABC and ∠A = 70°. Then ∠BIC is:", 90 + 35,
         [(140, "used the circumcentre rule 2A"), (110, "used the orthocentre rule 180° − A"), (145, "added 90° to 55°")],
         ["∠BIC = 90° + A/2 = 125°"], "°", "Incentre: 90° + A/2", "Match the rule to the centre."),
        ("officer", "L3", "H is the orthocentre of acute ΔABC and ∠A = 64°. Then ∠BHC is:", 180 - 64,
         [(90 + 32, "used the incentre rule"), (128, "used the circumcentre rule"), (64, "took ∠BHC = ∠A")],
         ["∠BHC = 180° − A = 116°"], "°", "Orthocentre: 180° − A", "Match the rule to the centre."),
        ("officer", "L3", "O is the circumcentre of acute ΔABC and ∠A = 56°. Then ∠BOC is:", 112,
         [(118, "used the incentre rule"), (124, "used the orthocentre rule"), (28, "halved instead of doubling")],
         ["∠BOC = 2A = 112°"], "°", "Circumcentre: 2A", "Central angle doubles the inscribed angle."),
        ("officer", "L3", "The circumradius of an equilateral triangle of side 12√3 cm is:", 12,
         [(6, "gave the inradius"), (18, "gave the height"), (24, "doubled the circumradius")],
         ["R = a/√3 = 12 cm (height 18, R = ⅔ × 18)"], " cm", "R = a/√3, r = a/(2√3)", "Centroid = circumcentre divides the height 2 : 1."),
        ("officer", "L3", "The inradius of a triangle with sides 7 cm, 24 cm and 25 cm is:", 3,
         [(F(25, 2), "gave the circumradius"), (6, "did not halve (a + b − c)"), (F(84, 56), "divided the area by the perimeter")],
         ["Right triangle (7² + 24² = 25²); area 84, s = 28", "r = 84/28 = 3 cm"], " cm", "r = Area/s", "Use the semi-perimeter."),
        ("officer", "L3", "Two sides of a triangle are 7 cm and 11 cm. How many integer values are possible for the third side?", 13,
         [(15, "included the degenerate cases 4 and 18"), (14, "included one endpoint"), (17, "counted from 1 to 17")],
         ["4 < x < 18 ⇒ x = 5, 6, …, 17", "13 values"], "", "|a − b| < c < a + b", "Strict inequalities."),
        ("officer", "L3", "In ΔABC, ∠B = 60° and ∠C = 40°. AD bisects ∠A and AE ⟂ BC. The angle ∠DAE is:", 10,
         [(20, "did not halve (B − C)"), (40, "gave ∠BAD"), (30, "gave ∠BAE")],
         ["∠A = 80°, ∠BAD = 40°", "∠BAE = 90° − 60° = 30° ⇒ ∠DAE = 10°"], "°", "∠DAE = (B − C)/2", "Work from vertex A."),
        ("officer", "L3", "The sides of a triangle are in the ratio 5 : 12 : 13 and its perimeter is 60 cm. Its area is:", F(10 * 24, 2),
         [(10 * 24, "forgot the factor ½"), (F(10 * 26, 2), "used the hypotenuse as a leg"), (F(24 * 26, 2), "used 24 and 26 as legs")],
         ["30k = 60 ⇒ k = 2 ⇒ sides 10, 24, 26 (right-angled)", "Area = ½ × 10 × 24 = 120 cm²"], " cm²", "Right triangle: ½ × legs", "The hypotenuse is not a leg."),
        ("officer", "L3", "G is the centroid of ΔABC of area 72 cm² and D is the midpoint of BC. The area of ΔBGD is:", 12,
         [(24, "gave the area of ΔAGB"), (18, "took one-quarter"), (36, "gave the area of ΔABD")],
         ["The three medians divide the triangle into six equal parts", "72/6 = 12 cm²"], " cm²", "Medians create six equal-area triangles", "ΔBGD is one of six."),
    ]
    G(B, M, items, "Triangle properties and centres", "Know which centre each rule belongs to.")


# =====================================================================
def solids(B):
    M = "qa-volume-and-surface-area-of-solids-42588cef"
    fr_v = PI * 12 / 3 * (196 + 49 + 98)
    assert fr_v == 4312
    tank = F(50 * 44 * 7, 100)
    flow = PI * F(7, 100) ** 2 * 5000
    assert tank / flow == 2
    rain = F(22 * 20 * 3, 100)
    assert rain / PI == F(21, 5)
    bricks = F(1000 * 300 * 25) * F(9, 10) / (F(25) * F(25, 2) * F(15, 2))
    assert bricks == 2880
    items = [
        ("foundation", "L1", "The total surface area of a cube of side 5 cm is:", 150,
         [(125, "computed the volume"), (100, "gave the lateral surface area"), (25, "gave one face")], ["TSA = 6a² = 150 cm²"], " cm²"),
        ("foundation", "L1", "The volume of a cuboid 10 cm × 8 cm × 5 cm is:", 400,
         [(340, "computed the total surface area"), (180, "computed the lateral surface area"), (23, "added the dimensions")], ["V = 10 × 8 × 5 = 400 cm³"], " cm³"),
        ("foundation", "L2", "The curved surface area of a cylinder of radius 7 cm and height 10 cm is (π = 22/7):", 2 * PI * 7 * 10,
         [(PI * 49 * 10, "computed the volume"), (2 * PI * 7 * 10 + 2 * PI * 49, "gave the total surface area"), (PI * 7 * 10, "used πrh")],
         ["CSA = 2πrh = 440 cm²"], " cm²"),
        ("foundation", "L2", "A cone has base radius 7 cm and height 24 cm. Its curved surface area is (π = 22/7):", PI * 7 * 25,
         [(PI * 7 * 24, "used the height instead of the slant height"), (PI * 7 * 25 + PI * 49, "gave the total surface area"), (PI * 49 * 24 / 3, "computed the volume")],
         ["l = √(49 + 576) = 25", "CSA = πrl = 550 cm²"], " cm²"),
        ("foundation", "L2", "The volume of a sphere of radius 21 cm is (π = 22/7):", F(4, 3) * PI * 21 ** 3,
         [(4 * PI * 441, "computed the surface area"), (4 * PI * 21 ** 3, "forgot the ⅓"), (F(2, 3) * PI * 21 ** 3, "gave a hemisphere")],
         ["V = (4/3) × 22/7 × 9,261 = 38,808 cm³"], " cm³"),
        ("officer", "L3", "The diagonal of a cube is 6√3 cm. Its volume is:", "216 cm³",
         [("648√3 cm³", "used the diagonal as the side"), ("81√3 cm³", "divided the diagonal by 2 instead of √3"), ("36 cm³", "computed one face")],
         ["Diagonal = a√3 ⇒ a = 6", "V = 216 cm³"], "", "Cube diagonal = a√3", "Recover the side first."),
        ("officer", "L3", "The dimensions of a cuboid are in the ratio 3 : 2 : 1 and its total surface area is 88 cm². Its volume is:", 48,
         [(6 * (2 * math.sqrt(2)) ** 3, "dropped the factor 2 in the TSA formula"), (8, "gave k³"), (96, "doubled the volume")],
         ["TSA = 2(6k² + 2k² + 3k²) = 22k² = 88 ⇒ k = 2", "Dimensions 6, 4, 2 ⇒ V = 48 cm³"], " cm³", "TSA = 2(lb + bh + hl)", "Keep the factor 2."),
        ("officer", "L3", "A solid consists of a cylinder of radius 7 cm and height 20 cm with a hemisphere attached at each end. Its total surface area is (π = 22/7):",
         2 * PI * 7 * 20 + 4 * PI * 49,
         [(2 * PI * 7 * 20 + 4 * PI * 49 + 2 * PI * 49, "also added the two flat circular ends"), (2 * PI * 7 * 20 + 2 * PI * 49, "included only one hemisphere"),
          (PI * 49 * 20 + F(4, 3) * PI * 343, "computed the volume")],
         ["Cylinder CSA = 880", "Two hemispheres = 4πr² = 616", "Total = 1,496 cm²"], " cm²", "Exposed surfaces only", "The joined circular faces are hidden."),
        ("officer", "L3", "Water flows at 5 km/h through a pipe of internal diameter 14 cm into a tank 50 m × 44 m. How long will it take for the water level to rise by 7 cm? (π = 22/7)", "2 hours",
         [("30 minutes", "used the diameter as the radius"), ("20 hours", "read the rise as 70 cm"), ("8 hours", "halved the pipe radius")],
         ["Tank volume = 50 × 44 × 0.07 = 154 m³", "Flow = 22/7 × 0.07² × 5,000 = 77 m³/h", "Time = 2 hours"], "",
         "Time = volume / (area × speed)", "Convert all lengths to metres."),
        ("officer", "L2", "A cone, a hemisphere and a cylinder stand on equal bases and have the same height (equal to the radius). The ratio of their volumes is:", "1 : 2 : 3",
         [("3 : 2 : 1", "reversed the order"), ("1 : 3 : 2", "swapped hemisphere and cylinder"), ("2 : 1 : 3", "swapped cone and hemisphere")],
         ["⅓πr³ : ⅔πr³ : πr³ = 1 : 2 : 3"], "", "h = r in each formula", "Keep the order cone : hemisphere : cylinder."),
        ("officer", "L3", "The radius of a sphere is increased by 50%. By what percentage does its volume increase?", 237.5,
         [(125, "gave the surface area increase"), (150, "cubed incorrectly (3 × 50%)"), (337.5, "gave new volume as % of old")],
         ["Factor = 1.5³ = 3.375", "Increase = 237.5%"], "%", "Volume ∝ r³", "Subtract 100% from the new/old ratio."),
        ("officer", "L3", "A closed wooden box has external dimensions 20 cm × 16 cm × 12 cm and walls 1 cm thick. The volume of wood used is:", 20 * 16 * 12 - 18 * 14 * 10,
         [(20 * 16 * 12 - 18 * 14 * 11, "treated the box as open"), (20 * 16 * 12 - 19 * 15 * 11, "subtracted the thickness only once per dimension"),
          (18 * 14 * 10, "gave the internal volume")],
         ["Internal = 18 × 14 × 10 = 2,520", "External = 3,840", "Wood = 1,320 cm³"], " cm³", "Wood = external − internal volume", "Closed box: subtract 2 cm from each dimension."),
        ("officer", "L3", "A bucket is a frustum with end radii 14 cm and 7 cm and height 12 cm. Its capacity is (π = 22/7):", fr_v,
         [(PI * F(21, 2) ** 2 * 12, "used a cylinder of mean radius"), (PI * 12 / 3 * (196 + 49), "omitted the Rr term"), (PI * 12 * (196 + 49 + 98), "omitted the ⅓")],
         ["V = (πh/3)(R² + r² + Rr) = (22/7)(4)(343) = 4,312 cm³"], " cm³", "Frustum: (πh/3)(R² + r² + Rr)", "The Rr term is essential."),
        ("officer", "L3", "3 cm of rain falls on a flat roof 22 m × 20 m and is collected in a cylindrical tank of diameter 2 m. The height of water in the tank is (π = 22/7):", "4.2 m",
         [("1.05 m", "used the diameter as the radius"), ("0.42 m", "took the rainfall as 3 mm"), ("2.1 m", "divided by the circumference instead of the area")],
         ["Rain volume = 22 × 20 × 0.03 = 13.2 m³", "h = 13.2/(22/7 × 1²) = 4.2 m"], "", "Volume conserved", "Radius = 1 m."),
        ("officer", "L3", "A wall 10 m × 3 m × 25 cm is built with bricks 25 cm × 12.5 cm × 7.5 cm; mortar fills one-tenth of the wall. The number of bricks is:", bricks,
         [(bricks * F(10, 9), "ignored the mortar"), (bricks * F(10, 9) * F(11, 10), "added 10% instead of removing it"), (bricks / 10, "slipped a unit")],
         ["Wall = 75,00,000 cm³; bricks occupy 9/10 = 67,50,000 cm³", "Brick = 2,343.75 cm³ ⇒ 2,880 bricks"], "",
         "n = usable volume / brick volume", "Remove the mortar share first."),
    ]
    G(B, M, items, "Mensuration of solids", "Separate volume from surface area and use consistent units.")


def add_all(B):
    area_perimeter(B)
    circles(B)
    circle_theorems(B)
    similarity(B)
    coordinate(B)
    lines_angles(B)
    polygons(B)
    reshaping(B)
    triangles(B)
    solids(B)
