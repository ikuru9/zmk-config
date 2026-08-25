/*                42 KEY MATRIX with ENCODER and JOYSTICK / LAYOUT MAPPING

based on Aliexpress variation of Foostan corne
https://github.com/a741725193/zmk-new_corne/blob/main/README_EN.md

  ╭────────────────────╮             ╭────╮      ╭─────────────────────╮
  │  0   1   2   3   4 │         ╭───╯  5 ╰───╮  │   6   7   8   9  10 │
  │ 11  12  13  14  15 │ ╭────╮  │ 16  17  18 │  │  19  20  21  22  23 │
  │ 24  25  26  27  28 │ │ 29 │  ╰───╮ 30 ╭───╯  │  31  32  33  34  35 │
  ╰───────╮ 36  37  38 │ ╰────╯      ╰────╯      │  39  40  41 ╭───────╯
          ╰────────────╯                         ╰─────────────╯

  ╭─────────────────────────╮              ╭─────╮      ╭─────────────────────────╮
  │ LT4  LT3  LT2  LT1  LT0 │          ╭───╯ JS0 ╰───╮  │ RT0  RT1  RT2  RT3  RT4 │
  │ LM4  LM3  LM2  LM1  LM0 │ ╭─────╮  │ JS1 JS2 JS3 │  │ RM0  RM1  RM2  RM3  RM4 │
  │ LB4  LB3  LB2  LB1  LB0 │ │ LEC │  ╰───╮ JS4 ╭───╯  │ RB0  RB1  RB2  RB3  RB4 │
  ╰─────────╮ LH2  LH1  LH0 │ ╰─────╯      ╰─────╯      │ RH0  RH1  RH2 ╭─────────╯
            ╰───────────────╯                           ╰───────────────╯
*/

#pragma once

#define LT0  4  // left-top row
#define LT1  3
#define LT2  2
#define LT3  1
#define LT4  0

#define RT0  6  // right-top row
#define RT1  7
#define RT2  8
#define RT3  9
#define RT4 10

#define LM0 11  // left-middle row
#define LM1 12
#define LM2 13
#define LM3 14
#define LM4 15

#define RM0 19  // right-middle row
#define RM1 20
#define RM2 21
#define RM3 22
#define RM4 23

#define LB0 24  // left-bottom row
#define LB1 25
#define LB2 26
#define LB3 27
#define LB4 28

#define RB0 31  // right-bottom row
#define RB1 32
#define RB2 33
#define RB3 34
#define RB4 35

#define LH0 36  // left thumb keys
#define LH1 37
#define LH2 38

#define RH0 39  // right thumb keys
#define RH1 40
#define RH2 41

#define JS0 6   // joystick keys
#define JS1 16
#define JS2 17
#define JS3 18
#define JS4 30

#define LEC 29  // left encoder key
