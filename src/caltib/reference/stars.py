from __future__ import annotations

import math
from dataclasses import dataclass

from . import astro_args as aa

@dataclass(frozen=True)
class Star:
    hip_id: int
    mag: float
    ra_j2000_deg: float
    dec_j2000_deg: float
    pm_ra_mas_yr: float
    pm_dec_mas_yr: float

@dataclass(frozen=True)
class EquatorialCoords:
    ra_deg: float
    dec_deg: float

@dataclass(frozen=True)
class EclipticCoords:
    L_deg: float
    B_deg: float

# ============================================================
# Hipparcos Catalog (Generated)
# ============================================================

STAR_CATALOG = {
    677: Star(hip_id=677, mag=2.07, ra_j2000_deg=2.09653333, dec_j2000_deg=29.09082805, pm_ra_mas_yr=135.68, pm_dec_mas_yr=-162.95),
    746: Star(hip_id=746, mag=2.28, ra_j2000_deg=2.29204036, dec_j2000_deg=59.15021814, pm_ra_mas_yr=523.39, pm_dec_mas_yr=-180.42),
    1067: Star(hip_id=1067, mag=2.83, ra_j2000_deg=3.30895828, dec_j2000_deg=15.18361593, pm_ra_mas_yr=4.7, pm_dec_mas_yr=-8.24),
    2021: Star(hip_id=2021, mag=2.82, ra_j2000_deg=6.41334183, dec_j2000_deg=-77.25503511, pm_ra_mas_yr=2220.12, pm_dec_mas_yr=324.37),
    2081: Star(hip_id=2081, mag=2.4, ra_j2000_deg=6.57028075, dec_j2000_deg=-42.30512197, pm_ra_mas_yr=232.76, pm_dec_mas_yr=-353.64),
    3179: Star(hip_id=3179, mag=2.24, ra_j2000_deg=10.12661349, dec_j2000_deg=56.53740928, pm_ra_mas_yr=50.36, pm_dec_mas_yr=-32.17),
    3419: Star(hip_id=3419, mag=2.04, ra_j2000_deg=10.89678452, dec_j2000_deg=-17.9866841, pm_ra_mas_yr=232.79, pm_dec_mas_yr=32.71),
    4427: Star(hip_id=4427, mag=2.15, ra_j2000_deg=14.17708808, dec_j2000_deg=60.71674966, pm_ra_mas_yr=25.65, pm_dec_mas_yr=-3.82),
    5447: Star(hip_id=5447, mag=2.07, ra_j2000_deg=17.43248991, dec_j2000_deg=35.62083048, pm_ra_mas_yr=175.59, pm_dec_mas_yr=-112.23),
    6686: Star(hip_id=6686, mag=2.66, ra_j2000_deg=21.45251267, dec_j2000_deg=60.23540347, pm_ra_mas_yr=297.24, pm_dec_mas_yr=-49.49),
    7588: Star(hip_id=7588, mag=0.45, ra_j2000_deg=24.42813204, dec_j2000_deg=-57.23666007, pm_ra_mas_yr=88.02, pm_dec_mas_yr=-40.08),
    8903: Star(hip_id=8903, mag=2.64, ra_j2000_deg=28.65978771, dec_j2000_deg=20.80829949, pm_ra_mas_yr=96.32, pm_dec_mas_yr=-108.8),
    9236: Star(hip_id=9236, mag=2.86, ra_j2000_deg=29.69113269, dec_j2000_deg=-61.56992444, pm_ra_mas_yr=262.54, pm_dec_mas_yr=26.88),
    9640: Star(hip_id=9640, mag=2.1, ra_j2000_deg=30.97466283, dec_j2000_deg=42.32984832, pm_ra_mas_yr=43.08, pm_dec_mas_yr=-50.85),
    9884: Star(hip_id=9884, mag=2.01, ra_j2000_deg=31.79285757, dec_j2000_deg=23.46277743, pm_ra_mas_yr=190.73, pm_dec_mas_yr=-145.77),
    11767: Star(hip_id=11767, mag=1.97, ra_j2000_deg=37.94614689, dec_j2000_deg=89.26413805, pm_ra_mas_yr=44.22, pm_dec_mas_yr=-11.74),
    13847: Star(hip_id=13847, mag=2.88, ra_j2000_deg=44.5654818, dec_j2000_deg=-40.30473491, pm_ra_mas_yr=-53.53, pm_dec_mas_yr=25.71),
    14135: Star(hip_id=14135, mag=2.54, ra_j2000_deg=45.56991279, dec_j2000_deg=4.08992539, pm_ra_mas_yr=-11.81, pm_dec_mas_yr=-78.76),
    14328: Star(hip_id=14328, mag=2.91, ra_j2000_deg=46.19912598, dec_j2000_deg=53.50645031, pm_ra_mas_yr=0.5, pm_dec_mas_yr=-4.19),
    14576: Star(hip_id=14576, mag=2.09, ra_j2000_deg=47.04220716, dec_j2000_deg=40.9556512, pm_ra_mas_yr=2.39, pm_dec_mas_yr=-1.44),
    15863: Star(hip_id=15863, mag=1.79, ra_j2000_deg=51.08061889, dec_j2000_deg=49.86124281, pm_ra_mas_yr=24.11, pm_dec_mas_yr=-26.01),
    17702: Star(hip_id=17702, mag=2.85, ra_j2000_deg=56.87110065, dec_j2000_deg=24.10524193, pm_ra_mas_yr=19.35, pm_dec_mas_yr=-43.11),
    18246: Star(hip_id=18246, mag=2.84, ra_j2000_deg=58.53299363, dec_j2000_deg=31.88365776, pm_ra_mas_yr=4.41, pm_dec_mas_yr=-9.15),
    18532: Star(hip_id=18532, mag=2.9, ra_j2000_deg=59.46342138, dec_j2000_deg=40.01027315, pm_ra_mas_yr=12.61, pm_dec_mas_yr=-24.06),
    18543: Star(hip_id=18543, mag=2.97, ra_j2000_deg=59.50720862, dec_j2000_deg=-13.50824471, pm_ra_mas_yr=60.51, pm_dec_mas_yr=-111.34),
    21421: Star(hip_id=21421, mag=0.87, ra_j2000_deg=68.98000195, dec_j2000_deg=16.50976164, pm_ra_mas_yr=62.78, pm_dec_mas_yr=-189.36),
    23015: Star(hip_id=23015, mag=2.69, ra_j2000_deg=74.24840098, dec_j2000_deg=33.16613537, pm_ra_mas_yr=3.63, pm_dec_mas_yr=-18.54),
    23875: Star(hip_id=23875, mag=2.78, ra_j2000_deg=76.96264146, dec_j2000_deg=-5.08626282, pm_ra_mas_yr=-83.39, pm_dec_mas_yr=-75.44),
    24436: Star(hip_id=24436, mag=0.18, ra_j2000_deg=78.63446353, dec_j2000_deg=-8.20163919, pm_ra_mas_yr=1.87, pm_dec_mas_yr=-0.56),
    24608: Star(hip_id=24608, mag=0.08, ra_j2000_deg=79.17206517, dec_j2000_deg=45.99902927, pm_ra_mas_yr=75.52, pm_dec_mas_yr=-427.13),
    25336: Star(hip_id=25336, mag=1.64, ra_j2000_deg=81.28278416, dec_j2000_deg=6.34973451, pm_ra_mas_yr=-8.75, pm_dec_mas_yr=-13.28),
    25428: Star(hip_id=25428, mag=1.65, ra_j2000_deg=81.57290804, dec_j2000_deg=28.60787346, pm_ra_mas_yr=23.28, pm_dec_mas_yr=-174.22),
    25606: Star(hip_id=25606, mag=2.81, ra_j2000_deg=82.06135971, dec_j2000_deg=-20.75923214, pm_ra_mas_yr=-5.03, pm_dec_mas_yr=-85.92),
    25930: Star(hip_id=25930, mag=2.25, ra_j2000_deg=83.00166562, dec_j2000_deg=-0.2990934, pm_ra_mas_yr=1.67, pm_dec_mas_yr=0.56),
    25985: Star(hip_id=25985, mag=2.58, ra_j2000_deg=83.18255798, dec_j2000_deg=-17.82229227, pm_ra_mas_yr=3.27, pm_dec_mas_yr=1.54),
    26241: Star(hip_id=26241, mag=2.75, ra_j2000_deg=83.85825475, dec_j2000_deg=-5.90989984, pm_ra_mas_yr=2.27, pm_dec_mas_yr=-0.62),
    26311: Star(hip_id=26311, mag=1.69, ra_j2000_deg=84.05338572, dec_j2000_deg=-1.20191725, pm_ra_mas_yr=1.49, pm_dec_mas_yr=-1.06),
    26451: Star(hip_id=26451, mag=2.97, ra_j2000_deg=84.41118447, dec_j2000_deg=21.14259299, pm_ra_mas_yr=2.39, pm_dec_mas_yr=-18.04),
    26634: Star(hip_id=26634, mag=2.65, ra_j2000_deg=84.91224975, dec_j2000_deg=-34.07404941, pm_ra_mas_yr=-0.1, pm_dec_mas_yr=-24.05),
    26727: Star(hip_id=26727, mag=1.74, ra_j2000_deg=85.18968672, dec_j2000_deg=-1.94257841, pm_ra_mas_yr=3.99, pm_dec_mas_yr=2.54),
    27366: Star(hip_id=27366, mag=2.07, ra_j2000_deg=86.93911641, dec_j2000_deg=-9.66960186, pm_ra_mas_yr=1.55, pm_dec_mas_yr=-1.2),
    27989: Star(hip_id=27989, mag=0.45, ra_j2000_deg=88.79287161, dec_j2000_deg=7.40703634, pm_ra_mas_yr=27.33, pm_dec_mas_yr=10.86),
    28360: Star(hip_id=28360, mag=1.9, ra_j2000_deg=89.88237261, dec_j2000_deg=44.94743492, pm_ra_mas_yr=-56.41, pm_dec_mas_yr=-0.88),
    28380: Star(hip_id=28380, mag=2.65, ra_j2000_deg=89.93015897, dec_j2000_deg=37.21276409, pm_ra_mas_yr=42.09, pm_dec_mas_yr=-73.61),
    30324: Star(hip_id=30324, mag=1.98, ra_j2000_deg=95.6749475, dec_j2000_deg=-17.95591658, pm_ra_mas_yr=-3.45, pm_dec_mas_yr=-0.47),
    30343: Star(hip_id=30343, mag=2.87, ra_j2000_deg=95.73996302, dec_j2000_deg=22.51385027, pm_ra_mas_yr=56.84, pm_dec_mas_yr=-108.79),
    30438: Star(hip_id=30438, mag=-0.62, ra_j2000_deg=95.98787763, dec_j2000_deg=-52.69571799, pm_ra_mas_yr=19.99, pm_dec_mas_yr=23.67),
    31681: Star(hip_id=31681, mag=1.93, ra_j2000_deg=99.42792641, dec_j2000_deg=16.39941482, pm_ra_mas_yr=-2.04, pm_dec_mas_yr=-66.92),
    32349: Star(hip_id=32349, mag=-1.44, ra_j2000_deg=101.28854105, dec_j2000_deg=-16.71314306, pm_ra_mas_yr=-546.01, pm_dec_mas_yr=-1223.08),
    32768: Star(hip_id=32768, mag=2.94, ra_j2000_deg=102.48390349, dec_j2000_deg=-50.61439973, pm_ra_mas_yr=34.23, pm_dec_mas_yr=-65.85),
    33579: Star(hip_id=33579, mag=1.5, ra_j2000_deg=104.65644451, dec_j2000_deg=-28.97208931, pm_ra_mas_yr=2.63, pm_dec_mas_yr=2.29),
    34444: Star(hip_id=34444, mag=1.83, ra_j2000_deg=107.09785853, dec_j2000_deg=-26.39320776, pm_ra_mas_yr=-2.75, pm_dec_mas_yr=3.33),
    35264: Star(hip_id=35264, mag=2.71, ra_j2000_deg=109.28568399, dec_j2000_deg=-37.09748689, pm_ra_mas_yr=-10.57, pm_dec_mas_yr=7.0),
    35904: Star(hip_id=35904, mag=2.45, ra_j2000_deg=111.02377104, dec_j2000_deg=-29.30311979, pm_ra_mas_yr=-3.76, pm_dec_mas_yr=6.66),
    36188: Star(hip_id=36188, mag=2.89, ra_j2000_deg=111.78780121, dec_j2000_deg=8.28940893, pm_ra_mas_yr=-50.28, pm_dec_mas_yr=-38.45),
    36850: Star(hip_id=36850, mag=1.58, ra_j2000_deg=113.65001898, dec_j2000_deg=31.88863645, pm_ra_mas_yr=-206.33, pm_dec_mas_yr=-148.18),
    37279: Star(hip_id=37279, mag=0.4, ra_j2000_deg=114.82724194, dec_j2000_deg=5.22750767, pm_ra_mas_yr=-716.57, pm_dec_mas_yr=-1034.58),
    37826: Star(hip_id=37826, mag=1.16, ra_j2000_deg=116.33068263, dec_j2000_deg=28.02631031, pm_ra_mas_yr=-625.69, pm_dec_mas_yr=-45.95),
    39429: Star(hip_id=39429, mag=2.21, ra_j2000_deg=120.89612561, dec_j2000_deg=-40.00318846, pm_ra_mas_yr=-30.82, pm_dec_mas_yr=16.77),
    39757: Star(hip_id=39757, mag=2.83, ra_j2000_deg=121.88625899, dec_j2000_deg=-24.30443677, pm_ra_mas_yr=-83.29, pm_dec_mas_yr=46.38),
    39953: Star(hip_id=39953, mag=1.75, ra_j2000_deg=122.38314727, dec_j2000_deg=-47.33661177, pm_ra_mas_yr=-5.93, pm_dec_mas_yr=9.9),
    41037: Star(hip_id=41037, mag=1.86, ra_j2000_deg=125.62860299, dec_j2000_deg=-59.50953829, pm_ra_mas_yr=-25.34, pm_dec_mas_yr=22.72),
    42913: Star(hip_id=42913, mag=1.93, ra_j2000_deg=131.17582214, dec_j2000_deg=-54.70856797, pm_ra_mas_yr=28.78, pm_dec_mas_yr=-104.14),
    44816: Star(hip_id=44816, mag=2.23, ra_j2000_deg=136.99907126, dec_j2000_deg=-43.43262406, pm_ra_mas_yr=-23.21, pm_dec_mas_yr=14.28),
    45238: Star(hip_id=45238, mag=1.67, ra_j2000_deg=138.30100329, dec_j2000_deg=-69.71747245, pm_ra_mas_yr=-157.66, pm_dec_mas_yr=108.91),
    45556: Star(hip_id=45556, mag=2.21, ra_j2000_deg=139.27261834, dec_j2000_deg=-59.27526115, pm_ra_mas_yr=-19.03, pm_dec_mas_yr=13.11),
    45941: Star(hip_id=45941, mag=2.47, ra_j2000_deg=140.52845511, dec_j2000_deg=-55.01069531, pm_ra_mas_yr=-10.72, pm_dec_mas_yr=11.24),
    46390: Star(hip_id=46390, mag=1.99, ra_j2000_deg=141.8968826, dec_j2000_deg=-8.65868335, pm_ra_mas_yr=-14.49, pm_dec_mas_yr=33.25),
    47908: Star(hip_id=47908, mag=2.97, ra_j2000_deg=146.4629267, dec_j2000_deg=23.77427792, pm_ra_mas_yr=-46.09, pm_dec_mas_yr=-9.57),
    48002: Star(hip_id=48002, mag=2.92, ra_j2000_deg=146.7755734, dec_j2000_deg=-65.07201888, pm_ra_mas_yr=-11.55, pm_dec_mas_yr=4.97),
    49669: Star(hip_id=49669, mag=1.36, ra_j2000_deg=152.09358075, dec_j2000_deg=11.96719513, pm_ra_mas_yr=-249.4, pm_dec_mas_yr=4.91),
    50583: Star(hip_id=50583, mag=2.01, ra_j2000_deg=154.99234054, dec_j2000_deg=19.84186032, pm_ra_mas_yr=310.77, pm_dec_mas_yr=-152.88),
    52419: Star(hip_id=52419, mag=2.74, ra_j2000_deg=160.73927802, dec_j2000_deg=-64.39447937, pm_ra_mas_yr=-18.87, pm_dec_mas_yr=12.06),
    52727: Star(hip_id=52727, mag=2.69, ra_j2000_deg=161.69217542, dec_j2000_deg=-49.42012517, pm_ra_mas_yr=62.55, pm_dec_mas_yr=-53.57),
    53910: Star(hip_id=53910, mag=2.34, ra_j2000_deg=165.4599615, dec_j2000_deg=56.38234478, pm_ra_mas_yr=81.66, pm_dec_mas_yr=33.74),
    54061: Star(hip_id=54061, mag=1.81, ra_j2000_deg=165.93265365, dec_j2000_deg=61.75111888, pm_ra_mas_yr=-136.46, pm_dec_mas_yr=-35.25),
    54872: Star(hip_id=54872, mag=2.56, ra_j2000_deg=168.52671705, dec_j2000_deg=20.52403384, pm_ra_mas_yr=143.31, pm_dec_mas_yr=-130.43),
    57632: Star(hip_id=57632, mag=2.14, ra_j2000_deg=177.26615977, dec_j2000_deg=14.57233687, pm_ra_mas_yr=-499.02, pm_dec_mas_yr=-113.78),
    58001: Star(hip_id=58001, mag=2.41, ra_j2000_deg=178.45725536, dec_j2000_deg=53.69473296, pm_ra_mas_yr=107.76, pm_dec_mas_yr=11.16),
    59196: Star(hip_id=59196, mag=2.58, ra_j2000_deg=182.08976505, dec_j2000_deg=-50.72240999, pm_ra_mas_yr=-47.53, pm_dec_mas_yr=-6.42),
    59747: Star(hip_id=59747, mag=2.79, ra_j2000_deg=183.78648733, dec_j2000_deg=-58.74890179, pm_ra_mas_yr=-36.68, pm_dec_mas_yr=-10.72),
    59803: Star(hip_id=59803, mag=2.58, ra_j2000_deg=183.95194937, dec_j2000_deg=-17.5419837, pm_ra_mas_yr=-159.58, pm_dec_mas_yr=22.31),
    60718: Star(hip_id=60718, mag=0.77, ra_j2000_deg=186.64975585, dec_j2000_deg=-63.09905586, pm_ra_mas_yr=-35.37, pm_dec_mas_yr=-14.73),
    60965: Star(hip_id=60965, mag=2.94, ra_j2000_deg=187.4665965, dec_j2000_deg=-16.51509397, pm_ra_mas_yr=-209.97, pm_dec_mas_yr=-139.3),
    61084: Star(hip_id=61084, mag=1.59, ra_j2000_deg=187.79137202, dec_j2000_deg=-57.11256922, pm_ra_mas_yr=27.94, pm_dec_mas_yr=-264.33),
    61359: Star(hip_id=61359, mag=2.65, ra_j2000_deg=188.59680864, dec_j2000_deg=-23.39662306, pm_ra_mas_yr=0.86, pm_dec_mas_yr=-56.0),
    61585: Star(hip_id=61585, mag=2.69, ra_j2000_deg=189.29618208, dec_j2000_deg=-69.13553358, pm_ra_mas_yr=-39.87, pm_dec_mas_yr=-12.44),
    61932: Star(hip_id=61932, mag=2.2, ra_j2000_deg=190.38002079, dec_j2000_deg=-48.95988553, pm_ra_mas_yr=-187.28, pm_dec_mas_yr=-1.2),
    61941: Star(hip_id=61941, mag=2.74, ra_j2000_deg=190.41667557, dec_j2000_deg=-1.44952231, pm_ra_mas_yr=-616.66, pm_dec_mas_yr=60.66),
    62434: Star(hip_id=62434, mag=1.25, ra_j2000_deg=191.93049537, dec_j2000_deg=-59.68873246, pm_ra_mas_yr=-48.24, pm_dec_mas_yr=-12.82),
    62956: Star(hip_id=62956, mag=1.76, ra_j2000_deg=193.5068041, dec_j2000_deg=55.95984301, pm_ra_mas_yr=111.74, pm_dec_mas_yr=-8.99),
    63125: Star(hip_id=63125, mag=2.89, ra_j2000_deg=194.00767051, dec_j2000_deg=38.31824617, pm_ra_mas_yr=-233.43, pm_dec_mas_yr=54.98),
    63608: Star(hip_id=63608, mag=2.85, ra_j2000_deg=195.54483557, dec_j2000_deg=10.95910186, pm_ra_mas_yr=-275.05, pm_dec_mas_yr=19.96),
    64962: Star(hip_id=64962, mag=2.99, ra_j2000_deg=199.7302224, dec_j2000_deg=-23.17141246, pm_ra_mas_yr=68.41, pm_dec_mas_yr=-41.09),
    65109: Star(hip_id=65109, mag=2.75, ra_j2000_deg=200.15027321, dec_j2000_deg=-36.71208109, pm_ra_mas_yr=-340.76, pm_dec_mas_yr=-87.98),
    65378: Star(hip_id=65378, mag=2.23, ra_j2000_deg=200.98091604, dec_j2000_deg=54.92541525, pm_ra_mas_yr=121.23, pm_dec_mas_yr=-22.01),
    65474: Star(hip_id=65474, mag=0.98, ra_j2000_deg=201.2983523, dec_j2000_deg=-11.16124491, pm_ra_mas_yr=-42.5, pm_dec_mas_yr=-31.73),
    66657: Star(hip_id=66657, mag=2.29, ra_j2000_deg=204.97196962, dec_j2000_deg=-53.46636269, pm_ra_mas_yr=-14.6, pm_dec_mas_yr=-12.79),
    67301: Star(hip_id=67301, mag=1.85, ra_j2000_deg=206.8856088, dec_j2000_deg=49.31330288, pm_ra_mas_yr=-121.23, pm_dec_mas_yr=-15.56),
    67927: Star(hip_id=67927, mag=2.68, ra_j2000_deg=208.6713175, dec_j2000_deg=18.39858742, pm_ra_mas_yr=-60.95, pm_dec_mas_yr=-358.1),
    68002: Star(hip_id=68002, mag=2.55, ra_j2000_deg=208.88514539, dec_j2000_deg=-47.28826634, pm_ra_mas_yr=-57.14, pm_dec_mas_yr=-44.75),
    68702: Star(hip_id=68702, mag=0.61, ra_j2000_deg=210.95601898, dec_j2000_deg=-60.3729784, pm_ra_mas_yr=-33.96, pm_dec_mas_yr=-25.06),
    68933: Star(hip_id=68933, mag=2.06, ra_j2000_deg=211.67218608, dec_j2000_deg=-36.36869575, pm_ra_mas_yr=-519.29, pm_dec_mas_yr=-517.87),
    69673: Star(hip_id=69673, mag=-0.05, ra_j2000_deg=213.91811403, dec_j2000_deg=19.18726997, pm_ra_mas_yr=-1093.45, pm_dec_mas_yr=-1999.4),
    71352: Star(hip_id=71352, mag=2.33, ra_j2000_deg=218.87688163, dec_j2000_deg=-42.15774562, pm_ra_mas_yr=-35.31, pm_dec_mas_yr=-32.44),
    71681: Star(hip_id=71681, mag=1.35, ra_j2000_deg=219.91412833, dec_j2000_deg=-60.83947139, pm_ra_mas_yr=-3600.35, pm_dec_mas_yr=952.11),
    71683: Star(hip_id=71683, mag=-0.01, ra_j2000_deg=219.92041034, dec_j2000_deg=-60.83514707, pm_ra_mas_yr=-3678.19, pm_dec_mas_yr=481.84),
    71860: Star(hip_id=71860, mag=2.3, ra_j2000_deg=220.48239101, dec_j2000_deg=-47.38814127, pm_ra_mas_yr=-21.15, pm_dec_mas_yr=-24.22),
    72105: Star(hip_id=72105, mag=2.35, ra_j2000_deg=221.24687869, dec_j2000_deg=27.07417383, pm_ra_mas_yr=-50.65, pm_dec_mas_yr=20.0),
    72607: Star(hip_id=72607, mag=2.07, ra_j2000_deg=222.67664751, dec_j2000_deg=74.15547596, pm_ra_mas_yr=-32.29, pm_dec_mas_yr=11.91),
    72622: Star(hip_id=72622, mag=2.75, ra_j2000_deg=222.71990536, dec_j2000_deg=-16.04161047, pm_ra_mas_yr=-105.69, pm_dec_mas_yr=-69.0),
    73273: Star(hip_id=73273, mag=2.68, ra_j2000_deg=224.63314193, dec_j2000_deg=-43.13386699, pm_ra_mas_yr=-34.06, pm_dec_mas_yr=-38.3),
    74785: Star(hip_id=74785, mag=2.61, ra_j2000_deg=229.25196591, dec_j2000_deg=-9.38286694, pm_ra_mas_yr=-96.39, pm_dec_mas_yr=-20.76),
    74946: Star(hip_id=74946, mag=2.87, ra_j2000_deg=229.72787007, dec_j2000_deg=-68.67946723, pm_ra_mas_yr=-66.48, pm_dec_mas_yr=-32.0),
    76267: Star(hip_id=76267, mag=2.22, ra_j2000_deg=233.67162293, dec_j2000_deg=26.71491041, pm_ra_mas_yr=120.38, pm_dec_mas_yr=-89.44),
    76297: Star(hip_id=76297, mag=2.8, ra_j2000_deg=233.78525156, dec_j2000_deg=-41.16669497, pm_ra_mas_yr=-16.05, pm_dec_mas_yr=-25.52),
    77070: Star(hip_id=77070, mag=2.63, ra_j2000_deg=236.06664914, dec_j2000_deg=6.42551971, pm_ra_mas_yr=134.66, pm_dec_mas_yr=44.14),
    77952: Star(hip_id=77952, mag=2.83, ra_j2000_deg=238.78670013, dec_j2000_deg=-63.42974973, pm_ra_mas_yr=-188.45, pm_dec_mas_yr=-401.92),
    78265: Star(hip_id=78265, mag=2.89, ra_j2000_deg=239.71300283, dec_j2000_deg=-26.1140428, pm_ra_mas_yr=-12.0, pm_dec_mas_yr=-25.71),
    78401: Star(hip_id=78401, mag=2.29, ra_j2000_deg=240.08338225, dec_j2000_deg=-22.62162024, pm_ra_mas_yr=-8.67, pm_dec_mas_yr=-36.9),
    78820: Star(hip_id=78820, mag=2.56, ra_j2000_deg=241.35931206, dec_j2000_deg=-19.80539286, pm_ra_mas_yr=-6.75, pm_dec_mas_yr=-24.89),
    79593: Star(hip_id=79593, mag=2.73, ra_j2000_deg=243.58652601, dec_j2000_deg=-3.69397562, pm_ra_mas_yr=-45.83, pm_dec_mas_yr=-142.91),
    80112: Star(hip_id=80112, mag=2.9, ra_j2000_deg=245.29717718, dec_j2000_deg=-25.59275259, pm_ra_mas_yr=-10.03, pm_dec_mas_yr=-18.03),
    80331: Star(hip_id=80331, mag=2.73, ra_j2000_deg=245.99794523, dec_j2000_deg=61.51407536, pm_ra_mas_yr=-16.98, pm_dec_mas_yr=56.68),
    80763: Star(hip_id=80763, mag=1.06, ra_j2000_deg=247.35194804, dec_j2000_deg=-26.43194608, pm_ra_mas_yr=-10.16, pm_dec_mas_yr=-23.21),
    80816: Star(hip_id=80816, mag=2.78, ra_j2000_deg=247.55525697, dec_j2000_deg=21.4896485, pm_ra_mas_yr=-98.43, pm_dec_mas_yr=-14.49),
    81266: Star(hip_id=81266, mag=2.82, ra_j2000_deg=248.97066423, dec_j2000_deg=-28.21596156, pm_ra_mas_yr=-8.59, pm_dec_mas_yr=-22.5),
    81377: Star(hip_id=81377, mag=2.54, ra_j2000_deg=249.28970847, dec_j2000_deg=-10.5671518, pm_ra_mas_yr=13.07, pm_dec_mas_yr=25.44),
    81693: Star(hip_id=81693, mag=2.81, ra_j2000_deg=250.32282132, dec_j2000_deg=31.60188695, pm_ra_mas_yr=-462.58, pm_dec_mas_yr=345.05),
    82273: Star(hip_id=82273, mag=1.91, ra_j2000_deg=252.16610742, dec_j2000_deg=-69.02763503, pm_ra_mas_yr=17.85, pm_dec_mas_yr=-32.92),
    82396: Star(hip_id=82396, mag=2.29, ra_j2000_deg=252.54268738, dec_j2000_deg=-34.29260982, pm_ra_mas_yr=-611.83, pm_dec_mas_yr=-255.87),
    84012: Star(hip_id=84012, mag=2.43, ra_j2000_deg=257.59442659, dec_j2000_deg=-15.72514757, pm_ra_mas_yr=41.16, pm_dec_mas_yr=97.65),
    84345: Star(hip_id=84345, mag=2.78, ra_j2000_deg=258.66192687, dec_j2000_deg=14.39025314, pm_ra_mas_yr=-6.71, pm_dec_mas_yr=32.78),
    85258: Star(hip_id=85258, mag=2.84, ra_j2000_deg=261.32498828, dec_j2000_deg=-55.52982397, pm_ra_mas_yr=-8.23, pm_dec_mas_yr=-24.71),
    85670: Star(hip_id=85670, mag=2.79, ra_j2000_deg=262.60823708, dec_j2000_deg=52.30135901, pm_ra_mas_yr=-15.59, pm_dec_mas_yr=11.57),
    85696: Star(hip_id=85696, mag=2.7, ra_j2000_deg=262.69099501, dec_j2000_deg=-37.29574016, pm_ra_mas_yr=-4.19, pm_dec_mas_yr=-29.14),
    85792: Star(hip_id=85792, mag=2.84, ra_j2000_deg=262.96050661, dec_j2000_deg=-49.87598159, pm_ra_mas_yr=-31.27, pm_dec_mas_yr=-67.15),
    85927: Star(hip_id=85927, mag=1.62, ra_j2000_deg=263.40219373, dec_j2000_deg=-37.10374835, pm_ra_mas_yr=-8.9, pm_dec_mas_yr=-29.95),
    86032: Star(hip_id=86032, mag=2.08, ra_j2000_deg=263.73335321, dec_j2000_deg=12.56057584, pm_ra_mas_yr=110.08, pm_dec_mas_yr=-222.61),
    86228: Star(hip_id=86228, mag=1.86, ra_j2000_deg=264.32969072, dec_j2000_deg=-42.99782155, pm_ra_mas_yr=6.06, pm_dec_mas_yr=-0.95),
    86670: Star(hip_id=86670, mag=2.39, ra_j2000_deg=265.62199908, dec_j2000_deg=-39.02992092, pm_ra_mas_yr=-6.49, pm_dec_mas_yr=-25.55),
    86742: Star(hip_id=86742, mag=2.76, ra_j2000_deg=265.86823714, dec_j2000_deg=4.56691684, pm_ra_mas_yr=-40.67, pm_dec_mas_yr=158.8),
    87073: Star(hip_id=87073, mag=2.99, ra_j2000_deg=266.89617137, dec_j2000_deg=-40.12698197, pm_ra_mas_yr=0.44, pm_dec_mas_yr=-6.4),
    87833: Star(hip_id=87833, mag=2.24, ra_j2000_deg=269.15157439, dec_j2000_deg=51.48895101, pm_ra_mas_yr=-8.52, pm_dec_mas_yr=-23.05),
    88635: Star(hip_id=88635, mag=2.98, ra_j2000_deg=271.45218586, dec_j2000_deg=-30.42365007, pm_ra_mas_yr=-55.75, pm_dec_mas_yr=-181.53),
    89931: Star(hip_id=89931, mag=2.72, ra_j2000_deg=275.24842337, dec_j2000_deg=-29.82803914, pm_ra_mas_yr=29.96, pm_dec_mas_yr=-26.38),
    90185: Star(hip_id=90185, mag=1.79, ra_j2000_deg=276.04310967, dec_j2000_deg=-34.3843146, pm_ra_mas_yr=-39.61, pm_dec_mas_yr=-124.05),
    90496: Star(hip_id=90496, mag=2.82, ra_j2000_deg=276.99278955, dec_j2000_deg=-25.42124732, pm_ra_mas_yr=-44.81, pm_dec_mas_yr=-186.29),
    91262: Star(hip_id=91262, mag=0.03, ra_j2000_deg=279.23410832, dec_j2000_deg=38.78299311, pm_ra_mas_yr=201.02, pm_dec_mas_yr=287.46),
    92855: Star(hip_id=92855, mag=2.05, ra_j2000_deg=283.81631956, dec_j2000_deg=-26.29659428, pm_ra_mas_yr=13.87, pm_dec_mas_yr=-52.65),
    93506: Star(hip_id=93506, mag=2.6, ra_j2000_deg=285.65301428, dec_j2000_deg=-29.88011429, pm_ra_mas_yr=-14.1, pm_dec_mas_yr=3.66),
    93747: Star(hip_id=93747, mag=2.99, ra_j2000_deg=286.3525518, dec_j2000_deg=13.86370983, pm_ra_mas_yr=-7.04, pm_dec_mas_yr=-95.31),
    94141: Star(hip_id=94141, mag=2.88, ra_j2000_deg=287.44097404, dec_j2000_deg=-21.02352534, pm_ra_mas_yr=-1.17, pm_dec_mas_yr=-36.83),
    97165: Star(hip_id=97165, mag=2.86, ra_j2000_deg=296.24350878, dec_j2000_deg=45.13069195, pm_ra_mas_yr=43.22, pm_dec_mas_yr=48.44),
    97278: Star(hip_id=97278, mag=2.72, ra_j2000_deg=296.56487567, dec_j2000_deg=10.61326869, pm_ra_mas_yr=15.72, pm_dec_mas_yr=-3.08),
    97649: Star(hip_id=97649, mag=0.76, ra_j2000_deg=297.6945086, dec_j2000_deg=8.86738491, pm_ra_mas_yr=536.82, pm_dec_mas_yr=385.54),
    100453: Star(hip_id=100453, mag=2.23, ra_j2000_deg=305.55708346, dec_j2000_deg=40.2566815, pm_ra_mas_yr=2.43, pm_dec_mas_yr=-0.93),
    100751: Star(hip_id=100751, mag=1.94, ra_j2000_deg=306.41187347, dec_j2000_deg=-56.73488071, pm_ra_mas_yr=7.71, pm_dec_mas_yr=-86.15),
    102098: Star(hip_id=102098, mag=1.25, ra_j2000_deg=310.3579727, dec_j2000_deg=45.28033423, pm_ra_mas_yr=1.56, pm_dec_mas_yr=1.55),
    102488: Star(hip_id=102488, mag=2.48, ra_j2000_deg=311.55180091, dec_j2000_deg=33.96945334, pm_ra_mas_yr=356.16, pm_dec_mas_yr=330.28),
    105199: Star(hip_id=105199, mag=2.45, ra_j2000_deg=319.64408982, dec_j2000_deg=62.58545529, pm_ra_mas_yr=149.91, pm_dec_mas_yr=48.27),
    106278: Star(hip_id=106278, mag=2.9, ra_j2000_deg=322.88966951, dec_j2000_deg=-5.57115593, pm_ra_mas_yr=22.79, pm_dec_mas_yr=-6.7),
    107315: Star(hip_id=107315, mag=2.38, ra_j2000_deg=326.04641808, dec_j2000_deg=9.87500791, pm_ra_mas_yr=30.02, pm_dec_mas_yr=1.38),
    107556: Star(hip_id=107556, mag=2.85, ra_j2000_deg=326.75952199, dec_j2000_deg=-16.12656595, pm_ra_mas_yr=263.26, pm_dec_mas_yr=-296.23),
    109074: Star(hip_id=109074, mag=2.95, ra_j2000_deg=331.44593869, dec_j2000_deg=-0.31982656, pm_ra_mas_yr=17.9, pm_dec_mas_yr=-9.93),
    109268: Star(hip_id=109268, mag=1.73, ra_j2000_deg=332.05781838, dec_j2000_deg=-46.96061593, pm_ra_mas_yr=127.6, pm_dec_mas_yr=-147.91),
    110130: Star(hip_id=110130, mag=2.87, ra_j2000_deg=334.62574257, dec_j2000_deg=-60.25949486, pm_ra_mas_yr=-71.48, pm_dec_mas_yr=-38.15),
    112122: Star(hip_id=112122, mag=2.07, ra_j2000_deg=340.66639531, dec_j2000_deg=-46.88456594, pm_ra_mas_yr=135.68, pm_dec_mas_yr=-4.51),
    112158: Star(hip_id=112158, mag=2.93, ra_j2000_deg=340.75053573, dec_j2000_deg=30.22130866, pm_ra_mas_yr=13.11, pm_dec_mas_yr=-26.11),
    113368: Star(hip_id=113368, mag=1.17, ra_j2000_deg=344.41177323, dec_j2000_deg=-29.62183701, pm_ra_mas_yr=329.22, pm_dec_mas_yr=-164.22),
    113881: Star(hip_id=113881, mag=2.44, ra_j2000_deg=345.94305575, dec_j2000_deg=28.08245462, pm_ra_mas_yr=187.76, pm_dec_mas_yr=137.61),
    113963: Star(hip_id=113963, mag=2.49, ra_j2000_deg=346.1900702, dec_j2000_deg=15.20536786, pm_ra_mas_yr=61.1, pm_dec_mas_yr=-42.56),
}

# Star names to hip_id
COMMON_STARS = {
    "sirius": 32349,
    "canopus": 30438,
    "arcturus": 69673,
    "vega": 91262,
    "capella": 24608,
    "rigel": 24436,
    "betelgeuse": 27989,
    "polaris": 11767,
    # Primary Lunar Mansion Reference Stars (Yogataras)
    "aldebaran": 21421,  # Rohini / snar ma
    "pleiades": 17702,   # Alcyone (Krittika / smin drug)
    "regulus": 49669,    # Magha / mchu
    "spica": 65474,      # Chitra / nag pa
    "antares": 80763,    # Jyeshtha / snrubs
}

def get_star_id(name: str) -> int:
    """Safely retrieves the HIP ID for a common star name."""
    clean_name = name.lower().strip()
    if clean_name not in COMMON_STARS:
        raise ValueError(f"Star '{name}' not found in COMMON_STARS mapping.")
    return COMMON_STARS[clean_name]

def get_star_ecliptic(hip_id: int, jd_tt: float) -> EclipticCoords:
    """Computes Apparent Geocentric Ecliptic coordinates of Date."""
    star = STAR_CATALOG[hip_id]
    
    # 1. Apply Proper Motion (Linear drift from J2000.0)
    # pm_ra_mas_yr in Hipparcos is pm_RA * cos(Dec), so we divide out the cos(Dec).
    years_since_2000 = (jd_tt - 2451545.0) / 365.25
    
    pm_ra_deg_yr = (star.pm_ra_mas_yr / 1000.0 / 3600.0) / math.cos(math.radians(star.dec_j2000_deg))
    pm_dec_deg_yr = (star.pm_dec_mas_yr / 1000.0 / 3600.0)
    
    ra_j2000_now = star.ra_j2000_deg + pm_ra_deg_yr * years_since_2000
    dec_j2000_now = star.dec_j2000_deg + pm_dec_deg_yr * years_since_2000
    
    ra_rad = math.radians(ra_j2000_now)
    dec_rad = math.radians(dec_j2000_now)
    
    # 2. Convert to 3D Rectangular Coordinates (Equatorial J2000)
    x = math.cos(dec_rad) * math.cos(ra_rad)
    y = math.cos(dec_rad) * math.sin(ra_rad)
    z = math.sin(dec_rad)
    
    # 3. Rotate from Equatorial J2000 directly to Ecliptic of Date
    T = aa.T_centuries(jd_tt)
    rot_matrix = aa.matrix_eq_j2000_to_ecl_date(T)
    x_ecl, y_ecl, z_ecl = aa.apply_matrix(rot_matrix, (x, y, z))
    
    # 4. Extract Spherical Ecliptic Coordinates
    L_deg = aa.wrap_deg(math.degrees(math.atan2(y_ecl, x_ecl)))
    B_deg = math.degrees(math.asin(z_ecl))
    
    return EclipticCoords(L_deg=L_deg, B_deg=B_deg)

def get_star_equatorial(hip_id: int, jd_tt: float) -> EquatorialCoords:
    """Computes Apparent Geocentric Equatorial coordinates of Date (for Rise/Set)."""
    # Get the ecliptic of date, then tilt by Obliquity of Date
    ecl = get_star_ecliptic(hip_id, jd_tt)
    
    T = aa.T_centuries(jd_tt)
    eps_rad = math.radians(aa.mean_obliquity_deg(T))
    
    L_rad = math.radians(ecl.L_deg)
    B_rad = math.radians(ecl.B_deg)
    
    sin_dec = math.sin(B_rad) * math.cos(eps_rad) + math.cos(B_rad) * math.sin(eps_rad) * math.sin(L_rad)
    dec_deg = math.degrees(math.asin(sin_dec))
    
    y = math.sin(L_rad) * math.cos(eps_rad) - math.tan(B_rad) * math.sin(eps_rad)
    x = math.cos(L_rad)
    ra_deg = aa.wrap_deg(math.degrees(math.atan2(y, x)))
    
    return EquatorialCoords(ra_deg=ra_deg, dec_deg=dec_deg)