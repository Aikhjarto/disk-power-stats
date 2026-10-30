# disk-power-stats

Shows when hard disks spin down and up, from the log lines smartd writes
anyway. No extra daemon or polling service is needed.

The kernel logs neither event: a disk spins down by its own standby timer,
and it spins up again on the next access, which just takes a few seconds
longer. smartd's `-n standby` directive, though, makes smartd skip sleeping
disks at its periodic checks, and it logs every change:

```
Device: /dev/sda [SAT], is in STANDBY mode, suspending checks
Device: /dev/sda [SAT], is back in ACTIVE or IDLE mode, resuming checks (7 checks skipped)
```

`disk-power-stats` reads these lines from the journal and reports, per disk,
the spin-downs and spin-ups, the time spent asleep, the shortest and median
nap, and the spin-ups per day and by hour of day. That shows what wakes the
disks (many short naps mean something polls them), whether the standby
timeout fits, and when smartd's self-tests should run so they don't wake a
sleeping disk.

Every time is up to one smartd check interval after the real event, so a
short interval (5 minutes below) is worth it. A check costs one SMART read
per spinning disk.

## Setup

### 1. Standby timer

Disks don't spin down unless a standby timer is set. `hdparm -S 241` sets
30 minutes (values 1–240 are multiples of 5 s, 241–251 multiples of 30 min).
Set it once with `hdparm -S 241 /dev/sdX`, and for every boot with a udev
rule matched by serial number, see
[examples/69-hdd-spindown.rules](examples/69-hdd-spindown.rules).

The rule must only run on `add`: `hdparm -S` sends an IDLE command, so a
rule that also matches `change` events wakes a sleeping disk whenever such an
event occurs.

Note: Advanced Power Management (`hdparm -B`) levels such as 128 only allow
head parking, not spin-down; the standby timer is separate.

### 2. smartd

In `/etc/smartd.conf`, add `-n standby,N` to the `DEFAULT` line (or to each
device line):

```
DEFAULT -n standby,288 -s (S/../.././03|L/../(01|02|03|04|05|06|07)/7/01)
DEVICESCAN
```

Without `-n standby`, smartd wakes every disk at every check. `N` is the
maximum number of skipped checks in a row; after that smartd checks the disk
anyway (and wakes it), so each disk still gets checked regularly: 288 checks
at 5 minutes are 24 hours. Don't add `,q`: it suppresses the log lines this
script needs.

Shorten the check interval (default 30 minutes) to 5 minutes:

- openSUSE: `SMARTD_CHECK_INTERVAL="300"` in `/etc/sysconfig/smartmontools`
- Debian: `smartd_opts="--interval=300"` in `/etc/default/smartmontools`

Then restart smartd (`smartd` or, on Debian, `smartmontools`).

A scheduled self-test (`-s`) that falls into a nap runs when the disk is
awake again. Use the statistics to move it to an hour when the disks spin
anyway.

## Usage

```
disk-power-stats [--since TIME] [--until TIME] [--events] [--unit UNIT]
```

- `--since`, `--until`: the period, in `journalctl` syntax
  (`"2026-11-01"`, `"-7d"`, `yesterday`); default the whole journal.
- `--events`: also list every single event.
- `--unit`: smartd's systemd unit, `smartd` (default) or, on Debian,
  `smartmontools`.
- `--input FILE`: read `journalctl -o json` output from a file (or `-`)
  instead of the local journal, e.g. from a central log server.

Example:

```
period 2026-12-30 08:00 .. 2026-12-31 14:00 (30h00); times are up to one smartd check interval late

disk       serial               downs  ups    asleep     %  shortest    median
/dev/sda   SERIALA                  2    2      1h50   6.1     20min      1h30
/dev/sdb   SERIALB                  3    2     27h45  92.5     25min      3h20
(/dev/sdb is still asleep)

spin-ups per day
              sda    sdb
2026-12-30      2      0
2026-12-31      0      2

spin-ups by hour of day
hour          sda    sdb
09:00           0      1
10:00           1      1
11:00           1      0
```

Disks are listed by device name, with the serial smartd logged at its last
start; device names can change between boots.

Spin-ups caused by smartd itself are marked in `--events`: a forced check
after `N` skipped checks, and smartd's start (it wakes every disk while
registering it).

## Requirements

Python 3.9 or newer, systemd's journal, smartmontools. Run as root or as a
member of `systemd-journal` (or `adm`) to read smartd's journal entries.

## Tests

```
python3 -m unittest discover tests
```

## License

GPL-2.0, see [LICENSE](LICENSE).
