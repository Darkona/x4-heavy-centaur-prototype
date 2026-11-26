# Ship Stats

All values of the Heavy Centaur Prototype (`ship_arg_l_hcp_01_a_macro`), with every module mark it can fit. Hull and physics come from the ship macro; module values come from the X4 9.00 game files. Values marked ≈ are estimates (see [How the estimates work](#how-the-estimates-work)); the shipyard's ship comparison screen shows the exact numbers.

## Hull and physics

| Stat | Base game | With VRO |
|---|---|---|
| Hull | 42000 | 78000 |
| Mass | 48 | 58 |
| Inertia pitch / yaw / roll | 17 / 17 / 9 | 18.2 / 18.2 / 9.7 |
| Drag forward / reverse | 28.62 / 92.6 | 23.46 / 87.7 |
| Drag horizontal / vertical | 28.62 / 28.62 | 43.7 / 43.7 |
| Drag pitch / yaw / roll | 55 / 55 / 45 | 77.7 / 100.9 / 60.7 |
| Acceleration factors | reverse 0.85, horizontal 1.2, vertical 1.2 | same |
| Jerk | forward 0.25 accel / 0.8 decel, boost 0.3, travel 0.5 / 0.9, strafe 0.5, angular 0.4 | same |
| Explosion damage (hull / shield) | 500 / 3000 | 1350 / 3000 |
| Missile storage | 120 | 164 |
| Drones (units) | 12 | 18 |
| Countermeasures / deployables | 30 / 10 | same |
| Crew capacity | 18 | same |
| Weapon heat modifier | 0.8 | same |
| Docking | 1 S pad on the top deck, 1 XS dock | same |

## Slots

| Slot | Count |
|---|---|
| Engines (M, any race) | 7 |
| Shields | 1 L (HCP internal), 6 M standard, 1 S standard |
| Thrusters | L |

## Engines

Seven M engines. Speeds are for the base game ship (drag forward 28.62). VRO changes engine stats too, so these speeds do not apply with VRO.

| Engine | Thrust (x7) | Top speed | Boost | Travel | Reverse | Acceleration (thrust / mass) |
|---|---|---|---|---|---|---|
| Argon M allround mk1 | 6720 | ≈ 312 m/s | ≈ 2300 m/s | ≈ 3280 m/s | ≈ 97 m/s | 140 |
| Argon M allround mk2 | 8064 | ≈ 375 m/s | ≈ 2770 m/s | ≈ 3940 m/s | ≈ 116 m/s | 168 |
| Argon M allround mk3 | 9072 | ≈ 422 m/s | ≈ 3110 m/s | ≈ 4430 m/s | ≈ 130 m/s | 189 |
| Argon M combat mk1 | 7594 | ≈ 353 m/s | ≈ 2790 m/s | ≈ 2840 m/s | ≈ 109 m/s | 158 |
| Argon M combat mk2 | 9112 | ≈ 423 m/s | ≈ 3350 m/s | ≈ 3410 m/s | ≈ 131 m/s | 190 |
| Argon M combat mk3 | 10251 | ≈ 476 m/s | ≈ 3760 m/s | ≈ 3830 m/s | ≈ 147 m/s | 214 |
| Argon M travel mk1 | 6048 | ≈ 281 m/s | ≈ 1730 m/s | ≈ 4040 m/s | ≈ 87 m/s | 126 |
| Argon M travel mk2 | 7258 | ≈ 337 m/s | ≈ 2070 m/s | ≈ 4850 m/s | ≈ 104 m/s | 151 |
| Argon M travel mk3 | 8165 | ≈ 379 m/s | ≈ 2330 m/s | ≈ 5460 m/s | ≈ 117 m/s | 170 |

Boost lasts 12.5 s (allround), 15 s (combat) or 11.25 s (travel). Travel drive charge is 8 s (allround, combat) or 7 s (travel).

## Thrusters

One L allround thruster. Turn values are relative to an Argon Behemoth Vanguard with L mk1 thrusters (1.0 = Behemoth turn rate).

| Thruster | Thrust strafe / pitch / yaw / roll | Strafe speed | Pitch | Yaw | Roll |
|---|---|---|---|---|---|
| L allround mk1 | 1360 / 684 / 684 / 726 | ≈ 63 m/s | 1.9x | 1.9x | 2.4x |
| L allround mk2 | 1659 / 834 / 834 / 886 | ≈ 77 m/s | 2.4x | 2.4x | 2.9x |
| L allround mk3 | 1904 / 958 / 958 / 1016 | ≈ 88 m/s | 2.7x | 2.7x | 3.3x |

With the VRO drag and the same thrusters, pitch is 30 percent slower, yaw 45 percent slower and roll 26 percent slower than in the base game (mk3: pitch 1.9x, yaw 1.5x, roll 2.4x), before VRO's own thruster changes.

The low inertia (17 against 96 for the Behemoth) and the angular jerk of 0.4 make the ship start and stop turning much faster than other L ships.

## Shields

| Shield | Capacity | Recharge | Delay |
|---|---|---|---|
| HCP internal L mk1 | 38640 | 189/s | 15 s |
| HCP internal L mk2 | 45982 | 284/s | 15 s |
| Argon M standard mk1 (each) | 5750 | 100/s | 12.5 s |
| Argon M standard mk2 (each) | 7475 | 140/s | 12.5 s |

Totals with the L and the six M shields: mk1 73140, mk2 90832 (plus the S shield).

## How the estimates work

- Top speed ≈ 1.33 x total engine thrust / drag forward. The 1.33 factor was measured against the in-game speeds of the Behemoth and the Cerberus (±5 percent).
- Boost and travel multiply the engine thrust by the engine's boost or travel factor; the real figures also depend on how the drive ramps up.
- Strafe ≈ 1.33 x thruster strafe thrust / drag horizontal.
- The steady turn rate scales with thruster thrust / angular drag; inertia only changes how fast the ship reaches it.
