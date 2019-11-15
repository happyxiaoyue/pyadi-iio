import time

import adi
import matplotlib.pyplot as plt
from scipy import signal
import numpy as np
import scipy.io as sio

def measure_phase_and_delay(chan0, chan1, window=None):
    assert len(chan0) == len(chan1)
    if window==None:
        window = len(chan0)
    phases = []
    delays = []
    indx = 0
    sections = len(chan0)//window
    for sec in range(sections):
        chan0_tmp = chan0[indx:indx+window]
        chan1_tmp = chan1[indx:indx+window]
        indx = indx+window+1
        cor = np.correlate(chan0_tmp, chan1_tmp, "full")
        # plt.plot(np.real(cor))
        # plt.plot(np.imag(cor))
        # plt.plot(np.abs(cor))
        # plt.show()
        i = np.argmax(np.abs(cor))
        m = cor[i]
        sample_delay = len(chan0_tmp) - i - 1
        phases.append(np.angle(m)*180/np.pi)
        delays.append(sample_delay)
    return (np.mean(phases), np.mean(delays))

def measure_phase(chan0, chan1):
    assert len(chan0) == len(chan1)
    errorV = np.angle(chan0 * np.conj(chan1)) * 180 / np.pi
    error = np.mean(errorV)
    return error


buff_size= 2 ** 17

# Create radio
uri1 = "ip:192.168.1.60"
uri2 = "ip:192.168.1.61"

print("--Connecting to devices")
master = adi.adrv9009_zu11eg(uri1)
slave = adi.adrv9009_zu11eg(uri2)
#master._ctx.set_timeout(10)
#slave._ctx.set_timeout(10)

# Desync both boards
print("--Unsyncing")
master.unsync()
slave.unsync()

# Start continous sysref
print("--Starting cont sysref")
slave.start_con_sysref()
master.start_con_sysref()
master.ext_sysref()

# Sync boards
print("--Syncing boards")
master.sync()

# Stop continuous sysref
print("--Stopping cont sysref")
slave.stop_con_sysref1()
master.stop_con_sysref1()
master.ext_sysref()
slave.stop_con_sysref2()
master.stop_con_sysref2()
master.ext_sysref()

# Configure properties
print("--Setting up transceivers")
LO = 1000000000
master.rx_enabled_channels = [0, 1, 2, 3]
master.tx_enabled_channels = [0, 1]
master.trx_lo = LO
master.trx_lo_chip_b = LO
master.tx_hardwaregain_chan0 = -10
master.tx_hardwaregain_chan1 = -10
master.tx_hardwaregain_chan0_chip_b = -10
master.tx_hardwaregain_chan1_chip_b = -10
master.gain_control_mode = "manual"
master.gain_control_mode_chip_b = "manual"
master.rx_hardwaregain_chan0 = 30
master.rx_hardwaregain_chan1 = 30
master.rx_hardwaregain_chan0_chip_b = 30
master.rx_hardwaregain_chan1_chip_b = 30
master.rx_buffer_size = buff_size

slave.rx_enabled_channels = [0, 1, 2, 3]
slave.tx_enabled_channels = [0, 1]
slave.trx_lo = LO
slave.trx_lo_chip_b = LO
slave.tx_hardwaregain_chan0 = -10
slave.tx_hardwaregain_chan1 = -10
slave.tx_hardwaregain_chan0_chip_b = -10
slave.tx_hardwaregain_chan1_chip_b = -10
slave.gain_control_mode = "manual"
slave.gain_control_mode_chip_b = "manual"
slave.rx_hardwaregain_chan0 = 30
slave.rx_hardwaregain_chan1 = 30
slave.rx_hardwaregain_chan0_chip_b = 30
slave.rx_hardwaregain_chan1_chip_b = 30
slave.rx_buffer_size = buff_size

# Read properties
print("TRX LO1 %s" % (master.trx_lo))
print("TRX LO2 %s" % (master.trx_lo_chip_b))

print("TRX LO3 %s" % (slave.trx_lo))
print("TRX LO4 %s" % (slave.trx_lo_chip_b))

### MCS
#slave.mcs()
#master.mcs()
slave._clock_chip.reg_write(0x5a, 4)
slave.mcs_ind(0)
slave.mcs_ind(1)
master._clock_chip.reg_write(0x5a, 4)
master.mcs_ind(0)
master.mcs_ind(1)
time.sleep(1)
# Step 2
master.ext_sysref()
master.mcs_ind(11)
slave.mcs_ind(11)
# Step 3 & 4
#master.mcs_ind(3)
#master.mcs_ind(4)
try:
    slave.mcs_ind(3)
except:
    pass
try:
    slave.mcs_ind(4)
except:
    pass

# Step 5
master.ext_sysref()
# Step 6
master.mcs_ind(6)
slave.mcs_ind(6)
# Step 7
master.ext_sysref()
# Step 8 & 9
master.mcs_ind(8)
master.mcs_ind(9)
slave.mcs_ind(8)
slave.mcs_ind(9)
# Step 10
master.ext_sysref()
# Step 11
master.mcs_ind(11)
# 8 pulse request
master._clock_chip.reg_write(0x5a, 1)
slave.mcs_ind(11)
slave._clock_chip.reg_write(0x5a, 1)
# cal RX phase correction
slave.rx_phase_cal(1)
master.rx_phase_cal(1)

###
# Start DMA
print("--Triggering DMA")
master.trigger_dma()
slave.trigger_dma()

# Set up buffers
print("--Initializing Buffers")
master._rx_init_channels()
slave._rx_init_channels()

# Collect data
fsr = int(master.rx_sample_rate)
for r in range(1):
    # Pulse sysref
    print("Pulsing sysref")
    master.ext_sysref()
    time.sleep(3)
    # Collect data
    print("Pulling buffers")
    x = master.rx()
    y = slave.rx()
    print("Same Chip", measure_phase(x[0], x[1]))
    print("Across Chip",measure_phase(x[0], x[2]))
    print("Same Chip (B)",measure_phase(y[0], y[1]))
    print("Across Chip (B)",measure_phase(y[0], y[2]))
    print("Across Chip (AB)",measure_phase(x[0], y[0]))
    # print("###########")
    (p, s) = measure_phase_and_delay(x[0], x[1])
    print("Same Chip Sample delay: ",s)
    (p, s) = measure_phase_and_delay(x[0], x[2])
    print("Across Chip Sample delay: ",s)
    (p, s) = measure_phase_and_delay(y[0], y[1])
    print("Same Chip (B) Sample delay: ",s)
    (p, s) = measure_phase_and_delay(y[0], y[2])
    print("Across Chip (B) Sample delay: ",s)
    (p, s) = measure_phase_and_delay(x[0], y[0])
    print("Across Chip (AB) Sample delay: ",s)
    # print("Phase delay: ",p)
    print("------------------")


    plt.plot(x[0], label='1')
    plt.plot(x[2], label='2')
    plt.plot(y[0], label='3')
    plt.plot(y[2], label='4')
    plt.legend()

    sio.savemat('np_vector.mat', {'x':x,'y':y})
#    f, Pxx_den = signal.periodogram(x[0], fsr)
#    f2, Pxx_den2 = signal.periodogram(x[1], fsr)
#    plt.clf()
#    plt.semilogy(f, Pxx_den)
#    plt.semilogy(f2, Pxx_den2)
#    plt.ylim([1e-7, 1e4])
#    plt.xlabel("frequency [Hz]")
#    plt.ylabel("PSD [V**2/Hz]")
#    plt.draw()
#    plt.pause(0.05)
#    time.sleep(0.1)

plt.show()