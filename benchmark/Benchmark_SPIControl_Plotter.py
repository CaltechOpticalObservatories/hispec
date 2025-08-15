#### PLOTTING DATA 
import matplotlib.pyplot as plt 
import numpy as np 

plt.ion()

TimeMult = 1e-9     # Multiplier to scale time vector to seconds
MicroMult = 1e-3

filename = "/home/hsdev/FSM/PDRDF/test_code/SPI_Chip_Testing/FT4222_SPI_DIV4_Sine_4000sr_50hz_Ax0_0p25_AdnacoTest08142025.csv"
array = np.genfromtxt(filename, delimiter=",") 
print(filename)

figsize = (6,4)

#plt.figure(figsize=figsize)

fig, axs = plt.subplots(2,3, figsize=(20, 8))  # 3 rows, 2 columns layout
fig.tight_layout(pad=5)
plt.suptitle(filename.split('/')[-1])

# Define a function to set xlim and
def limsetter():
    #plt.xlim(89.5, 90.5) # 300Hz Signal
    pass

plt.subplot(2,3,1); plt.plot(array[:,0]*TimeMult, array[:,1]); plt.title("Injected (ind1) | Axis 1 Commands"); plt.xlabel("Time [s]"); plt.ylabel("Mirror Command [mRad]"); limsetter()
plt.subplot(2,3,2); plt.plot(array[:,0]*TimeMult, array[:,2]); plt.title("Injected (ind2) | Axis 2 Commands"); plt.xlabel("Time [s]"); plt.ylabel("Mirror Command [mRad]"); limsetter()
#plt.subplot(2,3,3); plt.plot(array[:,0]*TimeMult, array[:,3]); plt.title("Queried (ind3) | Axis 1 Voltages"); plt.xlabel("Time [s]"); plt.ylabel("Applied Voltage [V]"); limsetter()
#plt.subplot(2,3,4); plt.plot(array[:,0]*TimeMult, array[:,4]); plt.title("Queried (ind4) | Axis 2 Voltages"); plt.xlabel("Time [s]"); plt.ylabel("Applied Voltage [V]"); limsetter()
plt.subplot(2,3,3); plt.plot(array[:,0]*TimeMult, array[:,3]); plt.title("Queried (ind3) | Axis 1 SGS POS"); plt.xlabel("Time [s]"); plt.ylabel("SGS POS [mRad]"); limsetter()
plt.subplot(2,3,4); plt.plot(array[:,0]*TimeMult, array[:,4]); plt.title("Queried (ind4) | Axis 2 SGS POS"); plt.xlabel("Time [s]"); plt.ylabel("SGS POS [mRad]"); limsetter()
#plt.subplot(2,4,7); plt.plot(array[:,0]*TimeMult, array[:,7]); plt.title("Measured (ind7) | Exe loop timing"); plt.xlabel("Time [s]"); plt.ylabel("Loop Iteration [Nanoseconds]"); limsetter()
#plt.subplot(2,4,7); plt.scatter(array[:-1,0]/1e6, np.diff(array[:,7]), 1); plt.title(f"Timing STD={np.std(np.diff(array[:,0])):0.2f} Mean={np.mean(np.diff(array[:,0])):0.2f}"); plt.xlabel('Time [s]'); plt.ylabel('Iteration Time [us]') 
#plt.subplot(2,5,7); plt.scatter(array[:-1,0] * TimeMult, np.abs(array[:-1,0] - array[:-1,7]), 1); plt.title(f"Timing STD={MicroMult * np.std(np.abs(array[:-1,0] - array[:-1,7])):0.2f} Mean={MicroMult * np.mean(np.diff(array[:,0])):0.2f}"); plt.xlabel('Time [s]'); plt.ylabel('Iteration Time [us]') 
plt.subplot(2,3,5); plt.hist((array[:,5] - array[:,0])*MicroMult, 15); plt.title(f"MOV STD={MicroMult * np.std(array[:,5] - array[:,0]):0.2f} Mean={MicroMult * np.mean(array[:,5] - array[:,0]):0.2f}"); plt.ylabel('Occurrences'); plt.xlabel('Execution Time [us]') 
plt.subplot(2,3,6); plt.scatter(array[:-1,0]* TimeMult, MicroMult * np.diff(array[:,0]), 1); plt.title(f"Timing STD={MicroMult * np.std(np.diff(array[:,0])):0.2f} Mean={MicroMult * np.mean(np.diff(array[:,0])):0.2f}"); plt.xlabel('Time [s]'); plt.ylabel('Iteration Time [us]') 
#plt.subplot(2,5,9); plt.hist((array[:,8] - array[:,7])* MicroMult, 15); plt.title(f"qVOL STD={MicroMult * np.std(array[:,8] - array[:,7]):0.2f} Mean={MicroMult * np.mean(array[:,8] - array[:,7]):0.2f}"); plt.ylabel('Occurrences'); plt.xlabel('Execution Time [us]') 
#plt.subplot(2,4,6); plt.hist((array[:,6] - array[:,5])*MicroMult, 15); plt.title(f"qPOS STD={MicroMult * np.std(array[:,6] - array[:,5]):0.2f} Mean={MicroMult * np.mean(array[:,6] - array[:,5]):0.2f}"); plt.ylabel('Occurrences'); plt.xlabel('Execution Time [us]') 

# If tag pixels rolled over, can optionally set ylim to omit rollover 
#plt.subplot(2,5,4); plt.ylim(-0.25, 2.25) 

# If ind3 shows large startup transient, can optionally set ylim for it 
    # 300Hz signal, sigScale = 0.1, ax 0
#plt.figure(3); plt.ylim(300, 320) 
#plt.figure(4); plt.ylim(238, 243) 
    # 300Hz signal, sigScale = 0.1, ax 1
#plt.figure(3); plt.ylim(309, 311) 
#plt.figure(4); plt.ylim(232, 248) 
    # 300Hz signal, sigScale = 0.3, ax 0
#plt.figure(3); plt.ylim(285, 335) 
#plt.figure(4); plt.ylim(238, 244) 
    # 300Hz signal, sigScale = 0.3, ax 0
#plt.subplot(2,5,3); plt.ylim(306, 314) 
#plt.subplot(2,5,4); plt.ylim(220, 260) 


# To generate timing jitter plot 

# To generate cropped images near the 400Hz USB August test plots 
#plt.figure(); plt.plot(array[17825:18100,0], array[17825:18100,4]); plt.title("Measured (ind4)"); 
#plt.figure(); plt.plot(array[17825:18100,0], array[17825:18100,3]); plt.title("Measured (ind3)"); 
#plt.figure(); plt.plot(array[17825:18100,0], array[17825:18100,2]); plt.title("Injected (ind2)"); 

#plt.tight_layout()

#plt.savefig('PLOT.png')

plt.show()
