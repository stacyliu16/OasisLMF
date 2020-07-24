#!/bin/bash
SCRIPT=$(readlink -f "$0") && cd $(dirname "$SCRIPT")

# --- Script Init ---

set -e
set -o pipefail
mkdir -p log
rm -R -f log/*

# --- Setup run dirs ---

find output/* ! -name '*summary-info*' -type f -exec rm -f {} +

rm -R -f work/*
mkdir work/kat/

mkdir work/gul_S1_summaryleccalc
mkdir work/gul_S1_summaryaalcalc
mkdir work/il_S1_summaryleccalc
mkdir work/il_S1_summaryaalcalc

mkfifo fifo/gul_P21

mkfifo fifo/il_P21

mkfifo fifo/gul_S1_summary_P21
mkfifo fifo/gul_S1_summaryeltcalc_P21
mkfifo fifo/gul_S1_eltcalc_P21
mkfifo fifo/gul_S1_summarysummarycalc_P21
mkfifo fifo/gul_S1_summarycalc_P21
mkfifo fifo/gul_S1_summarypltcalc_P21
mkfifo fifo/gul_S1_pltcalc_P21

mkfifo fifo/il_S1_summary_P21
mkfifo fifo/il_S1_summaryeltcalc_P21
mkfifo fifo/il_S1_eltcalc_P21
mkfifo fifo/il_S1_summarysummarycalc_P21
mkfifo fifo/il_S1_summarycalc_P21
mkfifo fifo/il_S1_summarypltcalc_P21
mkfifo fifo/il_S1_pltcalc_P21



# --- Do insured loss computes ---
eltcalc -s < fifo/il_S1_summaryeltcalc_P21 > work/kat/il_S1_eltcalc_P21 & pid1=$!
summarycalctocsv -s < fifo/il_S1_summarysummarycalc_P21 > work/kat/il_S1_summarycalc_P21 & pid2=$!
pltcalc -s < fifo/il_S1_summarypltcalc_P21 > work/kat/il_S1_pltcalc_P21 & pid3=$!
tee < fifo/il_S1_summary_P21 fifo/il_S1_summaryeltcalc_P21 fifo/il_S1_summarypltcalc_P21 fifo/il_S1_summarysummarycalc_P21 work/il_S1_summaryaalcalc/P21.bin work/il_S1_summaryleccalc/P21.bin > /dev/null & pid4=$!
summarycalc -f  -1 fifo/il_S1_summary_P21 < fifo/il_P21 &

# --- Do ground up loss computes ---
eltcalc -s < fifo/gul_S1_summaryeltcalc_P21 > work/kat/gul_S1_eltcalc_P21 & pid5=$!
summarycalctocsv -s < fifo/gul_S1_summarysummarycalc_P21 > work/kat/gul_S1_summarycalc_P21 & pid6=$!
pltcalc -s < fifo/gul_S1_summarypltcalc_P21 > work/kat/gul_S1_pltcalc_P21 & pid7=$!
tee < fifo/gul_S1_summary_P21 fifo/gul_S1_summaryeltcalc_P21 fifo/gul_S1_summarypltcalc_P21 fifo/gul_S1_summarysummarycalc_P21 work/gul_S1_summaryaalcalc/P21.bin work/gul_S1_summaryleccalc/P21.bin > /dev/null & pid8=$!
summarycalc -g  -1 fifo/gul_S1_summary_P21 < fifo/gul_P21 &

eve 21 40 | getmodel | gulcalc -S100 -L100 -r -c fifo/gul_P21 -i - | fmcalc -a2 > fifo/il_P21  &

wait $pid1 $pid2 $pid3 $pid4 $pid5 $pid6 $pid7 $pid8


# --- Do insured loss kats ---

kat work/kat/il_S1_eltcalc_P21 > output/il_S1_eltcalc.csv & kpid1=$!
kat work/kat/il_S1_pltcalc_P21 > output/il_S1_pltcalc.csv & kpid2=$!
kat work/kat/il_S1_summarycalc_P21 > output/il_S1_summarycalc.csv & kpid3=$!

# --- Do ground up loss kats ---

kat work/kat/gul_S1_eltcalc_P21 > output/gul_S1_eltcalc.csv & kpid4=$!
kat work/kat/gul_S1_pltcalc_P21 > output/gul_S1_pltcalc.csv & kpid5=$!
kat work/kat/gul_S1_summarycalc_P21 > output/gul_S1_summarycalc.csv & kpid6=$!
wait $kpid1 $kpid2 $kpid3 $kpid4 $kpid5 $kpid6
